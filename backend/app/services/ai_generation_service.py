from __future__ import annotations

import json
import re
import socket
import threading
import time
from typing import Any
from urllib import error, request

from fastapi import HTTPException, status

from app.constants.ai_generation import (
    AI_WEB_PAGE_MAX_CONSECUTIVE_ERRORS,
    DEFAULT_SYSTEM_PROMPT,
    DEFAULT_WEB_CASE_USER_TEMPLATE,
    DEFAULT_WEB_PAGE_USER_TEMPLATE,
)
from app.core.config import settings
from app.repositories.interfaces import ResourceRepository
from app.schemas.ai import WebAiGenerationRequest, WebPageAiGenerationRequest
from app.services.ai_generation_context_builder import AiGenerationContextBuilder
from app.services.ai_generation_result_saver import AiGenerationResultSaver
from app.services.ai_generation_task_runtime import AiGenerationTaskRuntime
from app.services.ai_model_service import AiModelResourceService
from app.services.ai_task_detail_file_service import AiTaskDetailFileService
from app.services.case_draft_service import CaseDraftService
from app.services.resource_service import ResourceService
from app.services.web_page_discovery_service import WebPageDiscoveryService
from app.services.web_page_service import WebPageResourceService
from app.utils.ai_generation_utils import (
    batch_user_prompt,
    exception_message,
    looks_like_api_path,
    preview_prompt as build_prompt_preview,
    raw_page_keys,
    sanitize_ai_value,
    sanitize_text,
)
from app.utils.model_api_request import build_model_body, model_api_url, model_protocol
from app.utils.model_api_response import ModelResponseError, read_model_response


AI_REQUEST_LOCK = threading.Lock()
AI_LAST_REQUEST_AT = 0.0


class AiGenerationService:
    def __init__(self, repository: ResourceRepository) -> None:
        self.repository = repository
        self.model_service = AiModelResourceService(repository)
        self.page_service = WebPageResourceService(repository)
        self.element_service = ResourceService("web_elements", repository)
        self.prompt_service = ResourceService("ai_prompt_templates", repository)
        self.task_service = ResourceService("ai_generation_tasks", repository)
        self.draft_service = CaseDraftService("WEB", repository)
        self.discovery_service = WebPageDiscoveryService(repository)
        self.task_detail_files = AiTaskDetailFileService()
        self.task_runtime = AiGenerationTaskRuntime(repository, self.task_service, self.task_detail_files)
        self.context_builder = AiGenerationContextBuilder(repository)
        self.result_saver = AiGenerationResultSaver(
            repository,
            self.page_service,
            self.element_service,
            self.draft_service,
        )

    def submit_web_pages(self, payload: WebPageAiGenerationRequest) -> dict[str, Any]:
        project = self._required_resource("projects", payload.project_id, "项目不存在")
        task = self.task_runtime.create_task(
            name=f"AI生成Web页面-{project.get('name', payload.project_id)}-{int(time.time())}",
            project_id=payload.project_id,
            task_type="web_page_generation",
            data={
                "model_id": payload.model_id,
                "prompt_template_id": payload.prompt_template_id,
                "login_case_id": payload.login_case_id,
                "dry_run": payload.dry_run,
                "payload": sanitize_ai_value(payload.model_dump()),
            },
            status_text="queued",
        )
        return {
            "task_id": task["id"],
            "status": "queued",
            "message": "AI页面功能生成任务已提交，请在 AI 生成任务列表查看进度。",
        }

    def run_web_pages_task(self, task_id: int, payload: WebPageAiGenerationRequest) -> dict[str, Any]:
        project = self._required_resource("projects", payload.project_id, "项目不存在")
        try:
            self.task_runtime.reset_for_run(task_id)
            result = self._build_web_pages_result(payload, project, task_id)
            finish_status = "partial_success" if result.get("batch_errors") else "success"
            self.task_runtime.finish_task(task_id, finish_status, result)
            return result
        except Exception as exc:
            self.task_runtime.finish_task(task_id, "failed", {"error": exception_message(exc)})
            raise

    def run_saved_task(self, task_id: int) -> dict[str, Any]:
        task = self._required_resource("ai_generation_tasks", task_id, "AI生成任务不存在")
        task_type = self.task_runtime.task_type(task)
        if task.get("status") == "running":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="任务正在执行中")
        if task_type == "web_page_generation":
            payload = self.task_runtime.web_page_payload_from_task(task)
            return self.run_web_pages_task(task_id, payload)
        if task_type == "web_vision_discovery":
            from app.services.web_vision_discovery_service import WebVisionDiscoveryService

            payload = self.task_runtime.vision_payload_from_task(task)
            return WebVisionDiscoveryService(self.repository).run_task(task_id, payload)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前任务类型暂不支持执行")

    def get_generation_task_detail(self, task_id: int) -> dict[str, Any]:
        """Return one AI generation task with its full file-backed detail.

        List queries intentionally keep only a compact result summary in the
        database. Opening a task detail hydrates ``data.result`` from the stable
        detail file, so repeated task execution updates one file instead of
        creating a new detail artifact each time.
        """

        task = self.task_service.get(task_id)
        data = dict(task.get("data") or {})
        result_file = str(data.get("result_file") or "")
        if result_file and task.get("status") not in {"queued", "running"}:
            result = self.task_detail_files.load_result(result_file)
            if result:
                data["result"] = result
        return {**task, "data": data}

    def submit_saved_task(self, task_id: int) -> dict[str, Any]:
        task = self._required_resource("ai_generation_tasks", task_id, "AI生成任务不存在")
        task_type = self.task_runtime.task_type(task)
        if task_type not in {"web_page_generation", "web_vision_discovery"}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前任务类型暂不支持执行")
        if task.get("status") == "running":
            return {"task_id": task_id, "status": "running", "message": "任务正在执行中"}
        self.task_runtime.reset_for_queue(task_id)
        return {"task_id": task_id, "status": "queued", "message": "任务已提交执行，请刷新列表查看进度"}

    def generate_web_pages(self, payload: WebPageAiGenerationRequest) -> dict[str, Any]:
        project = self._required_resource("projects", payload.project_id, "项目不存在")
        if payload.dry_run:
            return self._build_web_pages_preview(payload, project)
        task = self.task_runtime.create_task(
            name=f"AI生成Web页面-{project.get('name', payload.project_id)}-{int(time.time())}",
            project_id=payload.project_id,
            task_type="web_page_generation",
            data={
                "model_id": payload.model_id,
                "prompt_template_id": payload.prompt_template_id,
                "login_case_id": payload.login_case_id,
                "dry_run": payload.dry_run,
            },
        )
        try:
            result = self._build_web_pages_result(payload, project, task["id"])
            finish_status = "partial_success" if result.get("batch_errors") else "success"
            self.task_runtime.finish_task(task["id"], finish_status, result)
            return result
        except Exception as exc:
            self.task_runtime.finish_task(task["id"], "failed", {"error": exception_message(exc)})
            raise

    def generate_web_tests(self, payload: WebAiGenerationRequest) -> dict[str, Any]:
        project = self._required_resource("projects", payload.project_id, "项目不存在")
        page = self._required_resource("web_pages", payload.page_id, "页面功能不存在")
        if page.get("project_id") and int(page["project_id"]) != payload.project_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="页面功能不属于当前项目")

        task = self.task_runtime.create_task(
            name=f"AI生成Web用例-{page.get('name', payload.page_id)}-{int(time.time())}",
            project_id=payload.project_id,
            task_type="web_case_generation",
            data={
                "page_id": payload.page_id,
                "model_id": payload.model_id,
                "prompt_template_id": payload.prompt_template_id,
                "strategy_ids": payload.strategy_ids,
                "dry_run": payload.dry_run,
            },
        )
        try:
            context = self.context_builder.web_case_context(project, page, payload)
            prompt = self._render_prompt(
                template_type="web_case_generation",
                prompt_template_id=payload.prompt_template_id,
                context=context,
                user_prompt=payload.user_prompt,
                default_user_template=DEFAULT_WEB_CASE_USER_TEMPLATE,
            )
            if payload.dry_run:
                result = {
                    "task_id": task["id"],
                    "dry_run": True,
                    "prompt": build_prompt_preview(prompt),
                    "context": context,
                    "saved_elements": 0,
                    "saved_drafts": 0,
                    "warnings": ["dry_run模式不会调用模型，也不会保存元素或用例草稿"],
                }
                self.task_runtime.finish_task(task["id"], "success", result)
                return result

            model_result = self._call_model(payload.model_id, prompt)
            validated = self._validate_case_result(model_result)
            saved = self.result_saver.save_web_generation_result(payload, page, task["id"], validated)
            result = {
                "task_id": task["id"],
                "dry_run": False,
                "saved_elements": saved["saved_elements"],
                "saved_drafts": saved["saved_drafts"],
                "generated": validated,
                "warnings": saved["warnings"],
            }
            self.task_runtime.finish_task(task["id"], "success", result)
            return result
        except Exception as exc:
            self.task_runtime.finish_task(task["id"], "failed", {"error": str(exc)})
            raise

    def _build_web_pages_result(
        self,
        payload: WebPageAiGenerationRequest,
        project: dict[str, Any],
        task_id: int,
    ) -> dict[str, Any]:
        if payload.dry_run:
            preview = self._build_web_pages_preview(payload, project)
            preview["task_id"] = task_id
            return preview

        discovery = self._discover_web_project(project, payload, task_id)
        contexts = self.context_builder.project_page_analysis_contexts(project, payload, discovery)
        preview_context = contexts[0] if contexts else self.context_builder.project_page_context(project, payload, discovery)
        batch_results: list[dict[str, Any]] = []
        batch_errors: list[dict[str, Any]] = []
        consecutive_errors = 0
        stopped_early = False
        total = len(contexts or [preview_context])
        for index, context in enumerate(contexts or [preview_context], start=1):
            self.task_runtime.update_task_status(
                task_id,
                "running",
                {
                    "current_batch": index,
                    "batch_count": total,
                    "progress": f"正在分析第 {index}/{total} 个页面",
                },
            )
            prompt = self._render_prompt(
                template_type="web_page_generation",
                prompt_template_id=payload.prompt_template_id,
                context=context,
                user_prompt=batch_user_prompt(payload.user_prompt, index, total),
                default_user_template=DEFAULT_WEB_PAGE_USER_TEMPLATE,
            )
            try:
                model_result = self._call_model(payload.model_id, prompt)
                batch_results.append(self._bind_result_to_current_page(model_result, context))
                consecutive_errors = 0
            except Exception as exc:
                consecutive_errors += 1
                batch_errors.append({"batch": index, "error": exception_message(exc)})
                self.task_runtime.update_task_status(
                    task_id,
                    "running",
                    {
                        "current_batch": index,
                        "batch_count": total,
                        "failed_batches": len(batch_errors),
                        "batch_errors": batch_errors,
                        "progress": f"第 {index}/{total} 个页面分析失败，继续分析下一个页面",
                    },
                )
                if consecutive_errors >= AI_WEB_PAGE_MAX_CONSECUTIVE_ERRORS:
                    stopped_early = True
                    if index < total:
                        batch_errors.append(
                            {
                                "batch": f"{index + 1}-{total}",
                                "error": f"连续 {consecutive_errors} 个页面分析失败，已停止剩余页面，避免任务长时间等待。",
                            }
                        )
                    break
                continue
        if not batch_results:
            error_message = batch_errors[0]["error"] if batch_errors else "模型没有返回有效结果"
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"AI页面功能生成全部批次失败：{error_message}",
            )
        validated = self._merge_page_results(batch_results)
        valid_capture_routes = self.result_saver.valid_capture_route_keys(discovery)
        saved = self.result_saver.save_web_pages(payload, project, validated, valid_capture_routes)
        warnings = list(saved["warnings"])
        warnings.extend(f"第 {item['batch']} 批失败：{item['error']}" for item in batch_errors)
        warnings.extend(self.context_builder.discovery_warnings(discovery))
        return {
            "task_id": task_id,
            "dry_run": False,
            "discovery": self.context_builder.discovery_result(discovery),
            "batch_count": total,
            "batch_size": 1,
            "success_batches": len(batch_results),
            "failed_batches": len(batch_errors),
            "stopped_early": stopped_early,
            "batch_errors": batch_errors,
            "generated_pages": len(validated.get("pages", [])),
            "saved_pages": saved["saved_pages"],
            "updated_pages": saved["updated_pages"],
            "skipped_pages": saved["skipped_pages"],
            "pages": saved["pages"],
            "warnings": warnings,
        }

    def _build_web_pages_preview(self, payload: WebPageAiGenerationRequest, project: dict[str, Any]) -> dict[str, Any]:
        discovery = self._discover_web_project(project, payload)
        contexts = self.context_builder.project_page_analysis_contexts(project, payload, discovery)
        preview_context = contexts[0] if contexts else self.context_builder.project_page_context(project, payload, discovery)
        preview_prompt = self._render_prompt(
            template_type="web_page_generation",
            prompt_template_id=payload.prompt_template_id,
            context=preview_context,
            user_prompt=payload.user_prompt,
            default_user_template=DEFAULT_WEB_PAGE_USER_TEMPLATE,
        )
        return {
            "dry_run": True,
            "prompt": build_prompt_preview(preview_prompt),
            "context": preview_context,
            "discovery": self.context_builder.discovery_result(discovery),
            "batch_count": len(contexts),
            "batch_size": 1,
            "saved_pages": 0,
            "warnings": ["dry_run模式不会调用模型，也不会保存页面功能"],
        }

    def _discover_web_project(
        self,
        project: dict[str, Any],
        payload: WebPageAiGenerationRequest,
        task_id: int | None = None,
    ) -> dict[str, Any]:
        if not payload.discover_after_login:
            return {"enabled": False, "reason": "任务未启用登录后页面发现"}
        config = {
            "max_pages": payload.discovery_max_pages,
            "timeout_ms": payload.discovery_timeout_ms,
            "wait_ms": payload.discovery_wait_ms,
            "headless": payload.discovery_headless,
            "login_case_id": payload.login_case_id,
        }
        if task_id:
            self.task_runtime.update_task_status(
                task_id,
                "running",
                {
                    "progress": "正在使用 Playwright 登录后采集页面路由、截图和 API 调用",
                    "discovery_config": config,
                },
            )
        discovery = self.discovery_service.discover_project(project, config)
        if task_id:
            self.task_runtime.update_task_status(
                task_id,
                "running",
                {
                    "progress": "页面采集完成，正在准备 AI 分析上下文",
                    "discovery": self.context_builder.discovery_result(discovery),
                },
            )
        if discovery.get("login_failed"):
            detail = str(discovery.get("error") or "登录用例执行失败，已停止 AI 解析")
            warnings = discovery.get("warnings") if isinstance(discovery.get("warnings"), list) else []
            if warnings:
                detail = f"{detail}：{warnings[-1]}"
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
        return discovery

    def _render_prompt(
        self,
        template_type: str,
        prompt_template_id: int | None,
        context: dict[str, Any],
        user_prompt: str | None,
        default_user_template: str,
    ) -> dict[str, str]:
        template = self._prompt_template(template_type, prompt_template_id)
        system_prompt = str(template.get("system_prompt") or DEFAULT_SYSTEM_PROMPT)
        user_template = str(template.get("user_template") or default_user_template)
        safe_user_prompt = sanitize_text(user_prompt or "请按默认策略生成。")
        rendered = user_template.replace(
            "{{context_json}}",
            json.dumps(context, ensure_ascii=False, indent=2),
        ).replace("{{user_prompt}}", safe_user_prompt)
        return {"system": system_prompt, "user": rendered}

    def _prompt_template(self, template_type: str, prompt_template_id: int | None) -> dict[str, Any]:
        if prompt_template_id:
            item = self.prompt_service.get(prompt_template_id)
            return item.get("data") if isinstance(item.get("data"), dict) else {}
        rows, _ = self.repository.list("ai_prompt_templates", keyword=None, page=1, page_size=100)
        for row in rows:
            data = row.get("data") if isinstance(row.get("data"), dict) else {}
            if row.get("status") == "active" and data.get("template_type") == template_type:
                return data
        return {}

    def _call_model(self, model_id: int | None, prompt: dict[str, str]) -> dict[str, Any]:
        model = self.model_service.active_model(model_id)
        model_data = model.get("data") if isinstance(model.get("data"), dict) else {}
        api_key = self.model_service.api_key(model)
        if not api_key:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="AI模型未配置API Key文件")

        body = {
            "model": model_data.get("model") or "gpt-4.1-mini",
            "messages": [
                {"role": "system", "content": prompt["system"]},
                {"role": "user", "content": prompt["user"]},
            ],
            "temperature": float(model_data.get("temperature") or 0.2),
            "response_format": {"type": "json_object"},
        }
        protocol = model_protocol(model_data)
        body = build_model_body(body, protocol, model_data.get("reasoning_effort"))
        api_url = model_api_url(str(model_data.get("base_url") or ""), protocol)
        req = request.Request(
            api_url,
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            method="POST",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "text/event-stream" if protocol == "responses" else "application/json",
            },
        )
        timeout = int(model_data.get("timeout_sec") or 60)
        for attempt in range(settings.ai_rate_limit_retries + 1):
            self._throttle_ai_request()
            try:
                with request.urlopen(req, timeout=timeout) as response:
                    response_json = read_model_response(response, protocol, timeout_sec=timeout)
                    break
            except TimeoutError as exc:
                raise HTTPException(
                    status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                    detail=f"AI模型响应超时，已等待 {timeout} 秒。请稍后重试，或调小每批数据量/提高模型超时时间。",
                ) from exc
            except socket.timeout as exc:
                raise HTTPException(
                    status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                    detail=f"AI模型响应超时，已等待 {timeout} 秒。请稍后重试，或调小每批数据量/提高模型超时时间。",
                ) from exc
            except error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="ignore").replace(api_key, "[redacted]")
                if self._retryable_http_status(exc.code) and attempt < settings.ai_rate_limit_retries:
                    time.sleep(self._retry_delay(exc, attempt))
                    continue
                prefix = "AI模型触发限流" if exc.code == 429 else "AI模型调用失败"
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"{prefix}: HTTP {exc.code}，已重试 {attempt} 次：{detail}",
                ) from exc
            except error.URLError as exc:
                raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"AI模型连接失败: {exc.reason}") from exc
            except ModelResponseError as exc:
                raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc).replace(api_key, "[redacted]")) from exc

        try:
            content = response_json["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="AI模型响应格式不正确") from exc
        return self._parse_json_content(content)

    def _throttle_ai_request(self) -> None:
        global AI_LAST_REQUEST_AT
        min_interval_sec = max(0, settings.ai_request_min_interval_ms) / 1000
        if min_interval_sec <= 0:
            return
        with AI_REQUEST_LOCK:
            now = time.monotonic()
            wait_sec = AI_LAST_REQUEST_AT + min_interval_sec - now
            if wait_sec > 0:
                time.sleep(wait_sec)
            AI_LAST_REQUEST_AT = time.monotonic()

    def _retry_delay(self, exc: error.HTTPError, attempt: int) -> float:
        retry_after = str(exc.headers.get("Retry-After") or "").strip()
        if retry_after.isdigit():
            return min(60.0, max(0.2, float(retry_after)))
        base_sec = max(0.2, settings.ai_rate_limit_backoff_ms / 1000)
        return min(60.0, base_sec * (2**attempt))

    def _retryable_http_status(self, status_code: int) -> bool:
        return status_code == 429 or status_code in {408, 500, 502, 503, 504}

    def _chat_completions_url(self, base_url: str) -> str:
        return model_api_url(base_url, "chat_completions")

    def _parse_json_content(self, content: str) -> dict[str, Any]:
        text = content.strip()
        fenced = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, flags=re.S)
        if fenced:
            text = fenced.group(1).strip()
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="AI模型未返回合法JSON") from exc
        if not isinstance(parsed, dict):
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="AI模型JSON根节点必须是对象")
        return parsed

    def _validate_page_result(self, result: dict[str, Any]) -> dict[str, Any]:
        pages = result.get("pages") if isinstance(result.get("pages"), list) else []
        return {"pages": [item for item in pages if isinstance(item, dict)]}

    def _bind_result_to_current_page(self, result: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        current_page = context.get("current_page") if isinstance(context.get("current_page"), dict) else {}
        interfaces = context.get("api_interfaces") if isinstance(context.get("api_interfaces"), list) else []
        related_interface_ids = [
            int(item["id"])
            for item in interfaces
            if isinstance(item, dict) and str(item.get("id") or "").isdigit()
        ]
        route = str(current_page.get("route") or "").strip()
        url = str(current_page.get("url") or "").strip()
        if not route and not url:
            return result
        pages = []
        for page in self._validate_page_result(result).get("pages", []):
            bound = dict(page)
            original_route = bound.get("route")
            original_url = bound.get("url")
            if looks_like_api_path(original_route):
                bound["ai_suggested_route"] = original_route
            if looks_like_api_path(original_url):
                bound["ai_suggested_url"] = original_url
            bound["route"] = route or original_route
            bound["url"] = url or original_url
            bound["source_page_route"] = route
            bound["source_page_url"] = url
            if related_interface_ids:
                bound["related_interface_ids"] = related_interface_ids
            pages.append(bound)
        return {**result, "pages": pages}

    def _merge_page_results(self, results: list[dict[str, Any]]) -> dict[str, Any]:
        merged: list[dict[str, Any]] = []
        seen: set[str] = set()
        for result in results:
            for page in self._validate_page_result(result).get("pages", []):
                keys = raw_page_keys(page)
                if any(key in seen for key in keys):
                    continue
                merged.append(page)
                seen.update(keys)
        return {"pages": merged}

    def _validate_case_result(self, result: dict[str, Any]) -> dict[str, Any]:
        elements = result.get("elements") if isinstance(result.get("elements"), list) else []
        cases = result.get("cases") if isinstance(result.get("cases"), list) else []
        return {
            "elements": [item for item in elements if isinstance(item, dict)],
            "cases": [item for item in cases if isinstance(item, dict)],
        }

    def _required_resource(self, table: str, item_id: int, message: str) -> dict[str, Any]:
        item = self.repository.get(table, item_id)
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)
        return item


