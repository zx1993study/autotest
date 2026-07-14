from __future__ import annotations

import json
import re
import socket
import time
from typing import Any
from urllib import error, request
from urllib.parse import urljoin

from fastapi import HTTPException, status

from app.utils.playwright_auto_recorder import PlaywrightAutoRecorder

from app.constants.ai_generation import (
    AI_WEB_PAGE_MAX_CONSECUTIVE_ERRORS,
    DEFAULT_SYSTEM_PROMPT,
    DEFAULT_WEB_CASE_USER_TEMPLATE,
    DEFAULT_WEB_FUNCTION_ELEMENT_USER_TEMPLATE,
    DEFAULT_WEB_PAGE_USER_TEMPLATE,
)
from app.repositories.interfaces import ResourceRepository
from app.schemas.ai import WebAiGenerationRequest, WebFunctionElementGenerationRequest, WebPageAiGenerationRequest
from app.services.ai_generation_context_builder import AiGenerationContextBuilder
from app.services.ai_generation_result_saver import AiGenerationResultSaver
from app.services.ai_generation_task_runtime import AiGenerationTaskRuntime
from app.services.ai_model_service import AiModelResourceService
from app.services.ai_task_detail_file_service import AiTaskDetailFileService
from app.services.case_draft_service import CaseDraftService
from app.services.project_auth_service import ProjectAuthService
from app.services.resource_service import ResourceService
from app.services.ui_testing_service import UiTestingService
from app.services.web_page_discovery_service import WebPageDiscoveryService
from app.services.web_page_service import WebPageResourceService
from app.utils.ai_generation_utils import (
    batch_user_prompt,
    exception_message,
    int_or_default,
    looks_like_api_path,
    optional_int,
    preview_prompt as build_prompt_preview,
    raw_page_keys,
    sanitize_ai_value,
    sanitize_text,
)


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
        self.ui_service = UiTestingService("web_pages", "web_elements", repository)
        self.auth_service = ProjectAuthService(repository)
        self.task_detail_files = AiTaskDetailFileService()
        self.task_runtime = AiGenerationTaskRuntime(repository, self.task_service, self.task_detail_files)
        self.context_builder = AiGenerationContextBuilder(repository)
        self.result_saver = AiGenerationResultSaver(
            repository,
            self.page_service,
            self.element_service,
            self.draft_service,
        )
        self.auto_recorder = PlaywrightAutoRecorder()

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
        if task_type == "web_function_element_generation":
            payload = self.task_runtime.web_function_element_payload_from_task(task)
            return self.run_web_function_elements_task(task_id, payload)
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
        if task_type not in {"web_page_generation", "web_function_element_generation"}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前任务类型暂不支持执行")
        if task.get("status") == "running":
            return {"task_id": task_id, "status": "running", "message": "任务正在执行中"}
        self.task_runtime.reset_for_queue(task_id)
        return {"task_id": task_id, "status": "queued", "message": "任务已提交执行，请刷新列表查看进度"}

    def run_web_function_elements_task(
        self,
        task_id: int,
        payload: WebFunctionElementGenerationRequest,
    ) -> dict[str, Any]:
        project = self._required_resource("projects", payload.project_id, "项目不存在")
        try:
            self.task_runtime.reset_for_run(task_id)
            result = self._build_web_function_elements_result(payload, project, task_id)
            finish_status = "partial_success" if result.get("failed_pages") else "success"
            self.task_runtime.finish_task(task_id, finish_status, result)
            return result
        except Exception as exc:
            self.task_runtime.finish_task(task_id, "failed", {"error": exception_message(exc)})
            raise

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

    def _build_web_function_elements_result(
        self,
        payload: WebFunctionElementGenerationRequest,
        project: dict[str, Any],
        task_id: int,
    ) -> dict[str, Any]:
        pages = self._web_function_scan_pages(payload)
        if not pages:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="没有找到需要扫描的页面功能")

        results: list[dict[str, Any]] = []
        failed_pages: list[dict[str, Any]] = []
        total = len(pages)
        for index, page in enumerate(pages, start=1):
            self.task_runtime.update_task_status(
                task_id,
                "running",
                {
                    "current_page": index,
                    "page_count": total,
                    "current_page_name": page.get("name"),
                    "progress": f"正在自动识别第 {index}/{total} 个页面功能并扫描元素",
                },
            )
            try:
                results.append(
                    self._record_and_parse_web_page(
                        payload,
                        project,
                        page,
                        task_id=task_id,
                        page_index=index,
                        page_count=total,
                    )
                )
            except Exception as exc:
                failed_pages.append(
                    {
                        "page_id": page.get("id"),
                        "page_name": page.get("name"),
                        "error": exception_message(exc),
                    }
                )

        return {
            "task_type": "web_function_element_generation",
            "scan_scope": payload.scan_scope,
            "existing_element_strategy": payload.existing_element_strategy,
            "page_count": total,
            "success_pages": len(results),
            "failed_pages": failed_pages,
            "saved_elements": sum(int(item.get("element_count") or 0) for item in results),
            "created_elements": sum(int(item.get("created_count") or 0) for item in results),
            "updated_elements": sum(int(item.get("updated_count") or 0) for item in results),
            "skipped_elements": sum(int(item.get("skipped_count") or 0) for item in results),
            "pages": results,
            "instruction": payload.scan_instruction,
            "warnings": self._web_function_element_warnings(payload),
        }

    def _web_function_scan_pages(self, payload: WebFunctionElementGenerationRequest) -> list[dict[str, Any]]:
        scope = str(payload.scan_scope or "single").lower()
        if scope == "single":
            if not payload.page_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="单个页面扫描必须选择页面功能")
            page = self._required_resource("web_pages", payload.page_id, "页面功能不存在")
            self._ensure_project_resource(page, payload.project_id, "页面功能不属于当前项目")
            return [page]

        if scope == "multiple":
            if not payload.page_ids:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="多个页面扫描必须选择页面功能")
            pages = []
            for page_id in payload.page_ids:
                page = self._required_resource("web_pages", page_id, "页面功能不存在")
                self._ensure_project_resource(page, payload.project_id, "页面功能不属于当前项目")
                pages.append(page)
            return pages

        if scope == "all":
            rows, _ = self.repository.list("web_pages", project_id=payload.project_id, page=1, page_size=5000)
            return rows

        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="扫描方式仅支持 single/multiple/all")

    def _record_and_parse_web_page(
        self,
        payload: WebFunctionElementGenerationRequest,
        project: dict[str, Any],
        page: dict[str, Any],
        task_id: int | None = None,
        page_index: int = 1,
        page_count: int = 1,
    ) -> dict[str, Any]:
        target_url = self._web_page_target_url(project, page)
        if not target_url:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="页面地址为空，无法自动扫描元素")
        return self._auto_scan_web_function_page(
            payload,
            project,
            page,
            target_url,
            task_id=task_id,
            page_index=page_index,
            page_count=page_count,
        )

    def _auto_scan_web_function_page(
        self,
        payload: WebFunctionElementGenerationRequest,
        project: dict[str, Any],
        page: dict[str, Any],
        target_url: str,
        task_id: int | None = None,
        page_index: int = 1,
        page_count: int = 1,
    ) -> dict[str, Any]:
        """Automatically operate one page function and persist discovered elements.

        The AI model decides the feature entry and operation path from a
        headless page capture. PlaywrightAutoRecorder then performs the safe UI
        actions and emits a Playwright-like script so the existing element
        parser and persistence rules stay unchanged.
        """

        page_data = page.get("data") if isinstance(page.get("data"), dict) else {}
        feature_type = str(page_data.get("feature_type") or "page")
        feature_name = str(page.get("name") or feature_type)
        cookies = self.auth_service.web_cookies(self._page_auth_id(page))
        ai_context: dict[str, Any] = {}
        model_result: dict[str, Any] = {}
        model_error: str | None = None
        ai_plan: dict[str, Any] = {"recording_plan": [], "operation_steps": [], "element_steps": [], "warnings": []}
        warnings: list[str] = []

        def plan_builder(capture: dict[str, Any]) -> dict[str, Any]:
            nonlocal ai_context, model_result, model_error, ai_plan
            ai_context = self._web_function_element_context(project, page, target_url, capture, payload)
            prompt = self._render_prompt(
                "web_function_element_generation",
                payload.prompt_template_id,
                ai_context,
                self._web_function_element_user_prompt(payload),
                DEFAULT_WEB_FUNCTION_ELEMENT_USER_TEMPLATE,
            )
            try:
                model_result = self._call_model(payload.model_id, prompt)
                ai_plan = self._validate_web_function_element_result(model_result)
                if not ai_plan.get("operation_steps"):
                    warnings.append("AI 未返回可执行动作，已切换为规则化自动扫描。")
            except Exception as exc:  # noqa: BLE001 - element scan should still work when AI provider is unavailable.
                model_error = exception_message(exc)
                warnings.append(f"AI 动作规划失败，已切换为规则化自动扫描：{model_error}")
                ai_plan = {"recording_plan": [], "operation_steps": [], "element_steps": [], "warnings": [model_error]}
            return ai_plan

        if task_id:
            self.task_runtime.update_task_status(
                task_id,
                "running",
                {
                    "current_page": page_index,
                    "page_count": page_count,
                    "current_page_name": page.get("name"),
                    "codegen_session_id": None,
                    "codegen_browser_running": False,
                    "progress": f"第 {page_index}/{page_count} 个页面：正在以无头模式加载页面并由 AI 识别功能控件",
                },
            )

        try:
            recording = self.auto_recorder.capture_and_record_with_plan(
                target_url,
                feature_type,
                feature_name,
                plan_builder,
                cookies=cookies,
                instruction=payload.scan_instruction,
                timeout_sec=payload.operation_timeout_sec,
                headless=True,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"自动扫描页面失败：{exception_message(exc)}",
            ) from exc

        ai_plan = recording.get("ai_plan") if isinstance(recording.get("ai_plan"), dict) else ai_plan
        capture = recording.get("capture") if isinstance(recording.get("capture"), dict) else {}
        if not ai_context and capture:
            ai_context = self._web_function_element_context(project, page, target_url, capture, payload)
        warnings = self._merge_warnings(warnings, recording.get("warnings"), ai_plan.get("warnings"))
        if model_error:
            model_result = {"error": model_error}

        if task_id:
            self.task_runtime.update_task_status(
                task_id,
                "running",
                {
                    "current_page": page_index,
                    "page_count": page_count,
                    "current_page_name": page.get("name"),
                    "codegen_session_id": None,
                    "codegen_browser_running": False,
                    "progress": f"第 {page_index}/{page_count} 个页面：自动操作完成，正在保存扫描到的元素",
                },
            )

        script_text = str(recording.get("script_text") or "")
        if not script_text.strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="自动扫描未生成可解析脚本")

        parsed = self.ui_service.parse_playwright_script(
            payload.project_id,
            int(page["id"]),
            script_text,
            "ai_auto",
            payload.existing_element_strategy,
        )
        elements = self._web_function_saved_elements(payload.project_id, int(page["id"]))
        if not int(parsed.get("element_count") or 0) and not elements:
            fallback = self._save_web_function_ai_element_steps(
                payload,
                page,
                target_url,
                feature_name,
                ai_plan.get("element_steps") if isinstance(ai_plan.get("element_steps"), list) else [],
            )
            if fallback:
                parsed = {**parsed, **fallback}
                elements = self._web_function_saved_elements(payload.project_id, int(page["id"]))

        if not int(parsed.get("element_count") or 0) and not elements:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="自动扫描未识别到可保存的页面元素")

        return {
            "page_id": page.get("id"),
            "page_name": page.get("name"),
            "target_url": target_url,
            "script_text": script_text,
            "ai_plan": ai_plan,
            "ai_context": ai_context or capture,
            "model_result": model_result,
            "operations": recording.get("operations") if isinstance(recording.get("operations"), list) else [],
            "executed_ai_steps": (
                recording.get("executed_ai_steps") if isinstance(recording.get("executed_ai_steps"), list) else []
            ),
            "warnings": warnings,
            "codegen_session": None,
            "automation_session": {
                "mode": "ai_auto",
                "headless": True,
                "feature_type": feature_type,
                "timeout_sec": payload.operation_timeout_sec,
            },
            "feature_screenshot": recording.get("feature_screenshot") or {},
            "screenshot_url": recording.get("screenshot_url"),
            "screenshot_file": recording.get("screenshot_file"),
            "screenshot_error": recording.get("screenshot_error"),
            "element_count": int(parsed.get("element_count") or len(elements)),
            "created_count": parsed.get("created_count", 0),
            "updated_count": parsed.get("updated_count", 0),
            "skipped_count": parsed.get("skipped_count", 0),
            "deduplicated_count": parsed.get("deduplicated_count", 0),
            "deleted_stale_count": parsed.get("deleted_stale_count", 0),
            "existing_element_strategy": parsed.get("existing_strategy") or payload.existing_element_strategy,
            "elements": [{"id": item.get("id"), "name": item.get("name"), "data": item.get("data")} for item in elements],
        }

    def _save_web_function_ai_element_steps(
        self,
        payload: WebFunctionElementGenerationRequest,
        page: dict[str, Any],
        target_url: str,
        feature_name: str,
        element_steps: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Persist AI-declared element metadata when no executable script step was parsed."""

        elements = [
            normalized
            for index, item in enumerate(element_steps, start=1)
            if isinstance(item, dict)
            for normalized in [self._normalize_web_function_element_step(item, index)]
            if normalized
        ]
        if not elements:
            return {}
        stats = self.ui_service.scan_elements(
            payload.project_id,
            int(page["id"]),
            target_url,
            feature_name,
            {"elements": elements},
            payload.existing_element_strategy,
        )
        return {
            "page_id": page.get("id"),
            "element_count": stats.get("element_count", 0),
            "created_count": stats.get("created_count", 0),
            "updated_count": stats.get("updated_count", 0),
            "skipped_count": stats.get("skipped_count", 0),
            "deduplicated_count": stats.get("deduplicated_count", 0),
            "deleted_stale_count": 0,
            "existing_strategy": payload.existing_element_strategy,
        }

    def _normalize_web_function_element_step(self, item: dict[str, Any], index: int) -> dict[str, Any] | None:
        name = str(item.get("element_name") or item.get("name") or item.get("locator") or f"element {index}").strip()
        locator = str(item.get("locator") or item.get("css") or item.get("text") or "").strip()
        if not name or not locator:
            return None
        locator_type = str(item.get("locator_type") or "").strip().lower()
        if not locator_type:
            locator_type = "css" if locator.startswith(("#", ".", "[", "/")) else "text"
        element_type = str(item.get("element_type") or item.get("type") or "button").strip().lower()
        action = self._normalize_ai_operation_action(item.get("action") or self._default_web_element_action(element_type))
        normalized = {
            "name": name[:128],
            "description": item.get("description") or item.get("purpose"),
            "type": element_type,
            "element_type": element_type,
            "action": action,
            "locator_type": locator_type,
            "locator": locator,
            "default_value": item.get("default_value") or item.get("value"),
            "example": item.get("example"),
            "required": bool(item.get("required")),
            "take_screenshot": bool(item.get("take_screenshot")),
            "container": item.get("container"),
            "source": "playwright_ai_auto",
        }
        if locator_type == "role":
            role, role_name = self._role_locator_parts(locator)
            normalized["role"] = role
            normalized["role_name"] = role_name
            normalized["locator_args"] = locator
        return normalized

    def _default_web_element_action(self, element_type: str) -> str:
        if element_type in {"input", "textarea", "text"}:
            return "fill"
        if element_type in {"select", "multi_select"}:
            return "select"
        if element_type in {"checkbox", "radio"}:
            return "check"
        return "click"

    def _role_locator_parts(self, locator: str) -> tuple[str, str | None]:
        role_match = re.match(r"\s*([A-Za-z_][\w-]*)", locator)
        name_match = re.search(r"name\s*[:=]\s*['\"]?([^,'\"]+)", locator)
        role = role_match.group(1) if role_match else "button"
        name = name_match.group(1).strip() if name_match else None
        return role, name

    def _web_function_saved_elements(self, project_id: int, page_id: int) -> list[dict[str, Any]]:
        rows, _ = self.repository.list(
            "web_elements",
            project_id=project_id,
            page=1,
            page_size=5000,
            data_filters={"page_id": page_id},
        )
        return rows

    def _merge_warnings(self, *values: Any) -> list[str]:
        merged: list[str] = []
        seen: set[str] = set()
        for value in values:
            candidates = value if isinstance(value, list) else [value]
            for item in candidates:
                text = str(item or "").strip()
                if not text or text in seen:
                    continue
                seen.add(text)
                merged.append(text)
        return merged

    def _web_page_target_url(self, project: dict[str, Any], page: dict[str, Any]) -> str:
        page_data = page.get("data") if isinstance(page.get("data"), dict) else {}
        url = str(page_data.get("url") or "").strip()
        if url.startswith("http://") or url.startswith("https://"):
            return url
        project_data = project.get("data") if isinstance(project.get("data"), dict) else {}
        base_url = str(project_data.get("base_url") or project.get("description") or "").strip()
        route = str(page_data.get("route") or url or "").strip()
        if not base_url:
            return route
        return urljoin(base_url.rstrip("/") + "/", route.lstrip("/"))

    def _page_auth_id(self, page: dict[str, Any]) -> int | None:
        data = page.get("data") if isinstance(page.get("data"), dict) else {}
        return optional_int(data.get("auth_id"))

    def _ensure_project_resource(self, item: dict[str, Any], project_id: int, message: str) -> None:
        if item.get("project_id") and int(item["project_id"]) != int(project_id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

    def _web_function_element_warnings(self, payload: WebFunctionElementGenerationRequest) -> list[str]:
        return [
            "后台会自动打开目标页面，加载该页面配置的 Web 鉴权 Cookie，并由 AI 识别当前页面功能入口与控件。",
            "AI 会生成安全操作计划，Playwright 会自动点击入口、填写安全示例值、扫描弹窗或抽屉内元素并保存。",
            "删除类功能只允许打开确认区域并取消/关闭，不会继续提交真实删除；AI 不可用时会切换为规则化自动扫描。",
        ]

    def _web_function_element_context(
        self,
        project: dict[str, Any],
        page: dict[str, Any],
        target_url: str,
        capture: dict[str, Any],
        payload: WebFunctionElementGenerationRequest,
    ) -> dict[str, Any]:
        page_data = page.get("data") if isinstance(page.get("data"), dict) else {}
        project_data = project.get("data") if isinstance(project.get("data"), dict) else {}
        controls = capture.get("controls") if isinstance(capture.get("controls"), list) else []
        return sanitize_ai_value(
            {
                "project": {
                    "id": project.get("id"),
                    "name": project.get("name"),
                    "base_url": project_data.get("base_url") or project.get("description"),
                },
                "page": {
                    "id": page.get("id"),
                    "name": page.get("name"),
                    "description": page.get("description"),
                    "route": page_data.get("route"),
                    "url": page_data.get("url"),
                    "feature_type": page_data.get("feature_type"),
                    "module": page_data.get("module"),
                },
                "target_url": target_url,
                "scan_scope": payload.scan_scope,
                "scan_instruction": payload.scan_instruction,
                "saved_user_prompt": payload.user_prompt,
                "browser_capture": {
                    "title": capture.get("title"),
                    "control_count": len(controls),
                    "controls": controls[:120],
                    "warnings": capture.get("warnings") if isinstance(capture.get("warnings"), list) else [],
                },
                "safety_rules": [
                    "For add/edit/query/import, collect and operate all related controls first, then click save/query/confirm.",
                    "For delete, do not submit destructive deletion; open confirm dialog and cancel/close after collecting controls.",
                    "Open target modal/drawer/page first, then collect only controls related to the current function.",
                    "Ignore navigation, pagination, profile menus, and unrelated layout controls.",
                ],
            }
        )

    def _web_function_element_user_prompt(self, payload: WebFunctionElementGenerationRequest) -> str:
        return (
            "Only analyze and operate the selected current Web page function. "
            "Use browser_capture.controls as the source of truth. "
            "When possible, return control_index from browser_capture.controls for every operation step. "
            "Do not generate new page-function records. Do not use API paths as page URLs. "
            "Open the target function entry first. Do not click final save/query/confirm directly; the recorder will collect visible controls first and then perform safe submit/query automatically. "
            "For delete, open the confirm dialog and cancel/close without deleting. "
            f"Scan instruction: {payload.scan_instruction or ''}"
        )

    def _validate_web_function_element_result(self, result: dict[str, Any]) -> dict[str, Any]:
        raw_steps = result.get("operation_steps") if isinstance(result.get("operation_steps"), list) else []
        operation_steps: list[dict[str, Any]] = []
        for index, item in enumerate(raw_steps, start=1):
            if not isinstance(item, dict):
                continue
            action = self._normalize_ai_operation_action(item.get("action"))
            if action not in {"click", "fill", "select", "multi_select", "check", "record"}:
                continue
            name = str(item.get("element_name") or item.get("name") or item.get("locator") or "").strip()
            if not name:
                continue
            operation_steps.append(
                {
                    "step_id": int_or_default(item.get("step_id"), index),
                    "element_name": name,
                    "action": action,
                    "value": str(item.get("value") or item.get("default_value") or ""),
                    "locator": str(item.get("locator") or ""),
                    "locator_type": str(item.get("locator_type") or ""),
                    "control_index": optional_int(
                        item.get("control_index") or item.get("controlIndex") or item.get("index")
                    ),
                    "purpose": str(item.get("purpose") or item.get("instruction") or ""),
                }
            )

        recording_plan = result.get("recording_plan") if isinstance(result.get("recording_plan"), list) else []
        element_steps = result.get("element_steps") if isinstance(result.get("element_steps"), list) else []
        warnings = result.get("warnings") if isinstance(result.get("warnings"), list) else []
        return {
            "recording_plan": [item for item in recording_plan if isinstance(item, dict)],
            "operation_steps": operation_steps,
            "element_steps": [item for item in element_steps if isinstance(item, dict)],
            "warnings": [str(item) for item in warnings],
        }

    def _normalize_ai_operation_action(self, value: Any) -> str:
        text = str(value or "click").strip().lower()
        aliases = {
            "input": "fill",
            "type": "fill",
            "set_value": "fill",
            "select_option": "select",
            "choose": "select",
            "collect": "record",
            "capture": "record",
            "record_only": "record",
            "tap": "click",
            "press": "click",
        }
        return aliases.get(text, text)

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
        api_url = self._chat_completions_url(str(model_data.get("base_url") or ""))
        req = request.Request(
            api_url,
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            method="POST",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with request.urlopen(req, timeout=int(model_data.get("timeout_sec") or 60)) as response:
                raw = response.read().decode("utf-8")
        except TimeoutError as exc:
            timeout = int(model_data.get("timeout_sec") or 60)
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=f"AI模型响应超时，已等待 {timeout} 秒。请稍后重试，或调小每批数据量/提高模型超时时间。",
            ) from exc
        except socket.timeout as exc:
            timeout = int(model_data.get("timeout_sec") or 60)
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=f"AI模型响应超时，已等待 {timeout} 秒。请稍后重试，或调小每批数据量/提高模型超时时间。",
            ) from exc
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"AI模型调用失败: {detail}") from exc
        except error.URLError as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"AI模型连接失败: {exc.reason}") from exc

        try:
            response_json = json.loads(raw)
            content = response_json["choices"][0]["message"]["content"]
        except json.JSONDecodeError as exc:
            preview = raw.strip()[:120]
            if preview.lower().startswith("<!doctype") or preview.lower().startswith("<html"):
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"AI模型接口返回了网页内容，请检查接口地址是否为 OpenAI 兼容 API 地址：{api_url}",
                ) from exc
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="AI模型响应不是合法 JSON") from exc
        except (KeyError, IndexError, TypeError) as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="AI模型响应格式不正确") from exc
        return self._parse_json_content(content)

    def _chat_completions_url(self, base_url: str) -> str:
        base = (base_url or "https://api.openai.com/v1").rstrip("/")
        if base.endswith("/chat/completions"):
            return base
        parsed = urlparse(base)
        if parsed.path in {"", "/"}:
            return f"{base}/v1/chat/completions"
        has_version_path = any(part.startswith("v") and part[1:].isdigit() for part in parsed.path.split("/") if part)
        if not has_version_path:
            return f"{base}/v1/chat/completions"
        return f"{base}/chat/completions"

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


