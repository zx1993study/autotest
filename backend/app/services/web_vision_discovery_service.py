"""Screenshot-driven Web page feature and element discovery.

The vision model is invoked in two batches at most: once for the page overview,
then once with all successfully captured feature screenshots. Feature entries
are opened and closed sequentially without submitting forms.
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from web_automation.discovery.browser import (
    DiscoveryBrowserSession,
    close_feature,
    is_login_page,
    open_feature,
)
from web_automation.discovery.target import is_login_url, require_target_page
from web_automation.discovery.dom import collect_dom, safe_dom

from app.core.config import settings
from app.core.exceptions import BusinessRuleError, ResourceNotFoundError
from app.core.storage import storage_path
from app.repositories.interfaces import ResourceRepository
from app.schemas.ai import WebVisionDiscoveryRequest
from app.services.ai_generation_task_runtime import AiGenerationTaskRuntime
from app.services.ai_model_service import AiModelResourceService
from app.services.ai_task_detail_file_service import AiTaskDetailFileService
from app.services.project_auth_service import ProjectAuthService
from app.services.resource_service import ResourceService
from app.services.ui_testing_service import UiTestingService
from app.services.web_page_management_service import WebPageManagementService
from app.services.web_page_service import WebPageResourceService
from app.services.web_target_url_service import resolve_web_target_url
from app.utils.ai_generation_utils import exception_message, sanitize_ai_value
from app.utils.cancellable_model_request import ModelRequestCancelled
from app.utils.vision_llm_client import VisionLlmClient
from app.utils.web_vision_prompts import (
    DEFAULT_ELEMENT_EXTRACTION_PROMPT,
    DEFAULT_FUNCTION_DISCOVERY_PROMPT,
    VISION_ELEMENT_TEMPLATE_TYPE,
    VISION_FUNCTION_TEMPLATE_TYPE,
)

DISCOVERY_SCREENSHOT_DIR = storage_path("screenshots")
VISION_CACHE_DIR = storage_path("ai-cache", "vision")
VISION_TASK_TYPE = "web_vision_discovery"
ENTRY_OPEN_TIMEOUT_MS = 3000


@dataclass(frozen=True)
class FeatureCapture:
    feature_id: str
    feature_name: str
    screenshot_path: str
    entry_element: dict[str, Any] | None
    requests: tuple[dict[str, Any], ...] = ()
    dom: tuple[dict[str, Any], ...] = ()


class WebVisionDiscoveryService:
    def __init__(self, repository: ResourceRepository) -> None:
        self.repository = repository
        self.last_client = None
        self.cancel_check = None
        self.feature_outputs: dict[str, dict[str, Any]] = {}
        self.model_service = AiModelResourceService(repository)
        self.page_service = WebPageResourceService(repository)
        self.ui_service = UiTestingService("web_pages", "web_elements", repository)
        self.auth_service = ProjectAuthService(repository)
        self.prompt_service = ResourceService("ai_prompt_templates", repository)
        task_service = ResourceService("ai_generation_tasks", repository)
        self.task_runtime = AiGenerationTaskRuntime(repository, task_service, AiTaskDetailFileService())

    def check_cancelled(self):
        if self.cancel_check and self.cancel_check():
            raise ModelRequestCancelled("用户已中止 AI 分析")

    def submit(self, payload: WebVisionDiscoveryRequest) -> dict[str, Any]:
        page = self._required_page(payload.page_id)
        if page.get("project_id") != payload.project_id:
            raise BusinessRuleError("页面不属于当前项目")
        model = self.model_service.active_model(payload.vision_model_id)
        self._vision_client(int(model["id"]))
        payload = payload.model_copy(update={"vision_model_id": int(model["id"])})
        task = self.task_runtime.create_task(
            name=f"AI视觉发现-{page.get('name', payload.page_id)}-{int(time.time())}",
            project_id=payload.project_id,
            task_type=VISION_TASK_TYPE,
            data={
                "vision_model_id": payload.vision_model_id,
                "page_id": payload.page_id,
                "model_id": model["id"],
                "model_name": (model.get("data") or {}).get("model"),
                "model_http_calls": 0,
                "prompt_template_id": payload.prompt_template_id,
                "payload": sanitize_ai_value(payload.model_dump()),
            },
            status_text="queued",
        )
        return {
            "task_id": task["id"],
            "status": "queued",
            "message": "AI 视觉发现任务已提交，请在 AI 生成任务列表查看进度。",
            "model_name": (model.get("data") or {}).get("model"),
        }

    def run_task(self, task_id: int, payload: WebVisionDiscoveryRequest) -> dict[str, Any]:
        if not payload.headless:
            from app.services.web_vision_agent_service import WebVisionAgentService

            return WebVisionAgentService(self.repository).queue(payload, task_id)
        self._required_page(payload.page_id)
        try:
            self.check_cancelled()
            self.task_runtime.reset_for_run(task_id, only_if_active=True)
            result = self.discover(payload)
            finish_status = "partial_success" if result.get("feature_errors") else "success"
            self.check_cancelled()
            self.task_runtime.finish_task(task_id, finish_status, result, only_if_active=True)
            return result
        except Exception as exc:
            if self.cancel_check and self.cancel_check():
                raise ModelRequestCancelled("用户已中止 AI 分析") from exc
            self.task_runtime.finish_task(task_id, "failed", {"error": exception_message(exc), "model_id": payload.vision_model_id, "model_name": getattr(self.last_client, "model", ""), "model_http_calls": getattr(self.last_client, "requests_made", 0), "execution_mode": "server_headless"}, only_if_active=True)
            raise

    def discover(self, payload: WebVisionDiscoveryRequest) -> dict[str, Any]:
        page = self._required_page(payload.page_id)
        client = self._vision_client(payload.vision_model_id)
        client.timeout_sec = None
        client.cancel_check = self.cancel_check
        target_url = resolve_web_target_url(self.repository, page)
        return self._run_async(self._discover_page(payload, page, target_url, client))

    def _run_async(self, coro: Any) -> dict[str, Any]:
        if sys.platform.startswith("win"):
            policy = asyncio.WindowsProactorEventLoopPolicy()
            loop = policy.new_event_loop()
            try:
                return loop.run_until_complete(coro)
            finally:
                loop.close()
        return asyncio.run(coro)

    async def _discover_page(
        self,
        payload: WebVisionDiscoveryRequest,
        page: dict[str, Any],
        target_url: str,
        client: VisionLlmClient,
    ) -> dict[str, Any]:
        page_id = int(page["id"])
        warnings: list[str] = []
        feature_errors: list[dict[str, Any]] = []
        saved_features: list[dict[str, Any]] = []
        screenshots: list[str] = []
        async with DiscoveryBrowserSession(headless=payload.headless) as session:
            browser_page = session.page
            browser_page.set_default_timeout(ENTRY_OPEN_TIMEOUT_MS)
            if not is_login_url(target_url):
                await self._load_auth(browser_page, payload, page, target_url)
            await session.goto(target_url, timeout_ms=30000)
            await browser_page.wait_for_timeout(1000)
            if not is_login_url(target_url) and await is_login_page(browser_page):
                raise BusinessRuleError("页面仍处于登录页，请选择本地有头模式并完成验证码登录后继续")
            require_target_page(target_url, str(browser_page.url))
            self.check_cancelled()

            overview_shot = await self._screenshot(session, page_id, "overview")
            require_target_page(target_url, str(browser_page.url))
            screenshots.append(overview_shot)
            if not payload.dry_run:
                self._save_overview(page, overview_shot, await collect_dom(browser_page))
            features, discovery_warnings = self._discover_features(
                client,
                page,
                target_url,
                overview_shot,
                payload.user_prompt,
                payload.prompt_template_id,
            )
            warnings.extend(discovery_warnings)
            if not features:
                warnings.append("视觉模型未在页面上识别到功能入口")
            features = self._filter_features(features, payload)
            self._save_page_features(page, features, payload)

            captures, capture_errors = await self._collect_feature_captures(
                session,
                page_id,
                features,
                screenshots,
            )
            feature_errors.extend(capture_errors)
            saved_features, save_errors = self._extract_and_save_captures(
                client,
                payload,
                page,
                captures,
            )
            feature_errors.extend(save_errors)

        return {
            "task_type": VISION_TASK_TYPE,
            "dry_run": payload.dry_run,
            "page_id": page_id,
            "target_url": target_url,
            "features": [str(item.get("feature") or "") for item in features],
            "saved_features": saved_features,
            "feature_errors": feature_errors,
            "saved_elements": sum(int(item.get("element_count") or 0) for item in saved_features),
            "screenshots": screenshots,
            "warnings": warnings,
            "vision_batches": 1 + int(bool(captures)),
            "model_http_calls": getattr(client, "requests_made", 0),
            "execution_mode": "server_headless",
        }

    async def _collect_feature_captures(
        self,
        session: DiscoveryBrowserSession,
        page_id: int,
        features: list[dict[str, Any]],
        screenshots: list[str],
    ) -> tuple[list[FeatureCapture], list[dict[str, Any]]]:
        captures: list[FeatureCapture] = []
        errors: list[dict[str, Any]] = []
        for feature_index, feature in enumerate(features, start=1):
            feature_name = str(feature.get("feature") or "").strip()
            if not feature_name:
                continue
            if str(feature.get("risk") or "").lower() == "destructive":
                errors.append({"feature": feature_name, "error": "风险功能已记录候选，请补充目标数据和确认条件后生成脚本"})
                continue
            try:
                captures.append(
                    await self._capture_feature(
                        session,
                        page_id,
                        feature,
                        feature_index,
                        screenshots,
                    )
                )
            except Exception as exc:  # noqa: BLE001 - one broken feature must not stop the sweep.
                errors.append({"feature": feature_name, "error": exception_message(exc)})
        return captures, errors

    def _extract_and_save_captures(
        self,
        client: VisionLlmClient,
        payload: WebVisionDiscoveryRequest,
        page: dict[str, Any],
        captures: list[FeatureCapture],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        if not captures:
            return [], []
        if not payload.dry_run:
            from app.services.web_discovery_evidence_service import WebDiscoveryEvidenceService

            for capture in captures:
                WebDiscoveryEvidenceService(self.repository).attach(page, capture.feature_name, capture.screenshot_path, capture.dom)
        try:
            extracted = self._extract_feature_elements_batch(
                client,
                page,
                captures,
                payload.user_prompt,
                payload.prompt_template_id,
            )
        except Exception as exc:  # noqa: BLE001 - report one batch failure against each affected feature.
            message = exception_message(exc)
            return [], [{"feature": capture.feature_name, "error": message} for capture in captures]

        saved_features: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []
        for capture in captures:
            self.check_cancelled()
            elements = list(extracted.get(capture.feature_id, []))
            if capture.entry_element:
                elements.insert(0, capture.entry_element)
            try:
                stats = self._save_feature_elements(payload, int(page["id"]), capture.feature_name, elements)
                if not payload.dry_run:
                    from app.services.web_feature_testing_service import (
                        WebFeatureTestingService,
                    )

                    stats["feature_id"] = WebFeatureTestingService(self.repository).persist_discovery(page, capture, self.feature_outputs.get(capture.feature_id) or {}, elements)
                saved_features.append({"feature": capture.feature_name, **stats})
            except Exception as exc:  # noqa: BLE001 - persistence remains isolated per feature.
                errors.append({"feature": capture.feature_name, "error": exception_message(exc)})
        return saved_features, errors

    def _discover_features(
        self,
        client: VisionLlmClient,
        page: dict[str, Any],
        target_url: str,
        screenshot_path: str,
        user_prompt: str | None,
        prompt_template_id: int | None,
    ) -> tuple[list[dict[str, Any]], list[str]]:
        template = self._prompt_template(VISION_FUNCTION_TEMPLATE_TYPE, prompt_template_id)
        prompt = self._render_prompt(template or DEFAULT_FUNCTION_DISCOVERY_PROMPT, page, target_url, user_prompt)
        image = Path(screenshot_path).read_bytes()
        result = client.complete_json("你是一名资深 Web 测试工程师，擅长从页面截图识别功能入口。", prompt, [image])
        raw_features = result.get("features") if isinstance(result, dict) else None
        raw_warnings = result.get("warnings") if isinstance(result, dict) else None
        warnings = [str(item) for item in raw_warnings if str(item).strip()] if isinstance(raw_warnings, list) else []
        if not isinstance(raw_features, list):
            return [], warnings
        return [item for item in raw_features if isinstance(item, dict)], warnings

    async def _capture_feature(
        self,
        session: DiscoveryBrowserSession,
        page_id: int,
        feature: dict[str, Any],
        feature_index: int,
        screenshots: list[str],
    ) -> FeatureCapture:
        feature_name = str(feature.get("feature") or "").strip()
        entry_hint = str(feature.get("entry_hint") or feature_name).strip()
        return_url = str(session.page.url)
        try:
            entry_element = None if feature.get("capture_mode") == "current_page" else await self._open_feature_entry(session, entry_hint)
            await session.page.wait_for_timeout(800)
            shot_path = await self._screenshot(session, page_id, feature_name, full_page=False)
            screenshots.append(shot_path)
            return FeatureCapture(
                feature_id=f"feature_{feature_index}",
                feature_name=feature_name,
                screenshot_path=shot_path,
                entry_element=entry_element,
                dom=tuple(await collect_dom(session.page)),
            )
        finally:
            await close_feature(session.page, return_url)

    def _save_feature_elements(
        self,
        payload: WebVisionDiscoveryRequest,
        page_id: int,
        feature_name: str,
        elements: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if payload.dry_run:
            return {"element_count": len(elements)}
        saved = self.ui_service.scan_elements(
            payload.project_id,
            page_id,
            None,
            feature_name,
            {"elements": elements},
            payload.existing_element_strategy,
        )
        return {"element_count": int(saved.get("element_count") or 0)}

    async def _open_feature_entry(self, session: DiscoveryBrowserSession, entry_hint: str) -> dict[str, Any] | None:
        return await open_feature(session.page, entry_hint)

    def _extract_feature_elements_batch(
        self,
        client: VisionLlmClient,
        page: dict[str, Any],
        captures: list[FeatureCapture],
        user_prompt: str | None,
        prompt_template_id: int | None,
    ) -> dict[str, list[dict[str, Any]]]:
        template = self._prompt_template(VISION_ELEMENT_TEMPLATE_TYPE, prompt_template_id)
        prompt = self._render_prompt(
            template or DEFAULT_ELEMENT_EXTRACTION_PROMPT,
            page,
            resolve_web_target_url(self.repository, page),
            user_prompt,
            feature="对应图片标注的功能",
        )
        image_labels = "\n".join(
            f'- 图片 {index}: feature_id="{capture.feature_id}", feature="{capture.feature_name}"'
            for index, capture in enumerate(captures, start=1)
        )
        prompt = f"""{prompt}

本次为批量提取。以下图片按传入顺序一一对应：
{image_labels}

必须分别分析每张图片，不要把不同功能的元素混在一起。即使某张图片没有可操作元素，也要返回对应 feature_id 和空 elements。
批量模式只输出以下合法 JSON，且 feature_id 必须原样返回：
{{
  "features": [
    {{"feature_id": "feature_1", "feature": "新增", "elements": [], "parameters": [], "candidate": null, "api_candidates": [], "warnings": []}}
  ]
}}
"""
        prompt += "\nWeb DSL v2：生成 name、steps、input_info。动作限 click/fill/select/multi_select/check/uncheck/hover/assert/wait/manual。断言可选，缺少业务成功标识不阻止生成操作脚本，不得编造断言。parameters 用英文 key、label、type、required、options、condition、validation；未知必填用 required:null，规则对象未知用 {}。使用下面 Playwright 实采 DOM 的 locators 和 frame_selector，字段值用{{参数key}}，密码使用 sensitive:true 的 fill 引用且无默认值，验证码必须 manual 且无 value，两者不放入 input_info。加入已确认的功能入口步骤。不执行提交，不编造 DOM/API；截图无法确认的内容放 warnings。"
        prompt += "\n步骤格式：action只选一个动作；使用locator_type和locator，不输出可执行代码。role定位需有role及role_name。fill/select/multi_select的value引用输入；账号是可编辑文本，密码是password参数与sensitive:true的fill引用，不输出密码默认值，验证码才是manual且没有value。仅明确要求验证时生成assert，并在该步骤提供expected非空预期文本，不能用value替代expected。"
        prompt += "\n实际页面：" + resolve_web_target_url(self.repository, page)
        prompt += "\n真实 DOM（无输入值）：" + json.dumps([{ "feature_id": c.feature_id, "controls": safe_dom(c.dom)} for c in captures], ensure_ascii=False)
        images = [Path(capture.screenshot_path).read_bytes() for capture in captures]
        result = client.complete_json(
            "你是一名资深 Web 测试工程师，擅长从多张功能截图批量提取可操作元素。",
            prompt,
            images,
        )
        raw_groups = result.get("features") if isinstance(result, dict) else None
        if not isinstance(raw_groups, list) and len(captures) == 1 and isinstance(result, dict):
            legacy_elements = result.get("elements")
            if isinstance(legacy_elements, list):
                raw_groups = [{"feature_id": captures[0].feature_id, "elements": legacy_elements}]
        if not isinstance(raw_groups, list):
            return {}

        known_ids = {capture.feature_id for capture in captures}
        ids_by_name = {
            capture.feature_name: capture.feature_id
            for capture in captures
        }
        elements_by_feature: dict[str, list[dict[str, Any]]] = {}
        for group in raw_groups:
            if not isinstance(group, dict):
                continue
            feature_id = str(group.get("feature_id") or "").strip()
            if not feature_id:
                feature_id = ids_by_name.get(str(group.get("feature") or "").strip(), "")
            if feature_id not in known_ids:
                continue
            self.feature_outputs[feature_id] = {key: group.get(key) for key in ("parameters", "candidate", "api_candidates", "warnings")}
            raw_elements = group.get("elements")
            if not isinstance(raw_elements, list):
                raw_elements = []
            normalized_elements: list[dict[str, Any]] = []
            for item in raw_elements:
                if not isinstance(item, dict):
                    continue
                normalized = self._normalize_element(item)
                if normalized:
                    normalized_elements.append(normalized)
            elements_by_feature[feature_id] = normalized_elements
        return elements_by_feature

    def _normalize_element(self, item: dict[str, Any]) -> dict[str, Any] | None:
        name = str(item.get("name") or "").strip()
        if not name:
            return None
        return {
            "name": name,
            "text": name,
            "type": str(item.get("element_type") or item.get("type") or "button"),
            "element_type": str(item.get("element_type") or item.get("type") or "button"),
            "action": str(item.get("action") or "click").lower(),
            "description": str(item.get("description") or ""),
            "required": bool(item.get("required")),
            "default_value": item.get("default_value"),
            "example": item.get("example"),
            "source": "vision_discovery",
            "options": item.get("options") if isinstance(item.get("options"), list) else [],
        }

    def _filter_features(
        self,
        features: list[dict[str, Any]],
        payload: WebVisionDiscoveryRequest,
    ) -> list[dict[str, Any]]:
        filtered: list[dict[str, Any]] = []
        source = self._required_page(payload.page_id)
        if is_login_url(resolve_web_target_url(self.repository, source)):
            feature = next((f for f in features if "登录" in str(f.get("feature") or "") or is_login_url("/" + str(f.get("feature") or ""))), {})
            return [{**feature, "feature": source["name"] if (source.get("data") or {}).get("feature_type") == "login" else "登录", "entry_hint": "", "capture_mode": "current_page", "risk": "safe"}]
        specific_feature = str((source.get("data") or {}).get("feature_type") or "page") != "page"
        for feature in features:
            if specific_feature and str(feature.get("feature") or "") != source["name"]:
                continue
            risk = str(feature.get("risk") or "").lower()
            if risk == "destructive" and not payload.include_destructive:
                continue
            filtered.append(feature)
            if len(filtered) >= payload.max_functions:
                break
        return filtered

    def _save_page_features(
        self,
        page: dict[str, Any],
        features: list[dict[str, Any]],
        payload: WebVisionDiscoveryRequest,
    ) -> None:
        self.check_cancelled()
        if payload.dry_run:
            return
        data = dict(page.get("data") or {})
        data["features"] = sanitize_ai_value(
            [
                {
                    "feature": item.get("feature"),
                    "entry_hint": item.get("entry_hint"),
                    "risk": item.get("risk") or "safe",
                }
                for item in features
            ]
        )
        data["vision_discovered_at"] = int(time.time())
        self.page_service.update(int(page["id"]), {"data": data})
        from app.services.web_feature_testing_service import WebFeatureTestingService

        workspace = WebFeatureTestingService(self.repository)
        management = WebPageManagementService(self.repository)
        if not data.get("page_group_id"):
            management.synchronize_project(payload.project_id)
            page = self._required_page(page["id"])
        group_id = (page.get("data") or {}).get("page_group_id")
        if group_id:
            rows, _ = self.repository.list("web_pages", project_id=payload.project_id, page_size=10000, data_filters={"page_group_id": group_id})
            for item in features:
                name = str(item.get("feature") or "").strip()
                if name and not any(r["name"] == name for r in rows):
                    kind = "login" if item.get("capture_mode") == "current_page" else "delete" if item.get("risk") == "destructive" else "other"
                    workspace.save_feature(group_id, {"name": name, "feature_type": kind, "description": "发现候选，尚未确认操作条件"})

    def _vision_client(self, vision_model_id: int | None) -> VisionLlmClient:
        model = self.model_service.active_model(vision_model_id)
        data = model.get("data") if isinstance(model.get("data"), dict) else {}
        if data.get("supports_vision") is not True:
            raise BusinessRuleError("所选 AI 模型未开启视觉能力，请在 AI 模型管理中勾选「支持视觉」")
        api_key = self.model_service.api_key(model)
        if not api_key:
            raise BusinessRuleError("AI 模型未配置 API Key，无法进行视觉发现")
        self.last_client = VisionLlmClient(
            base_url=str(data.get("base_url") or ""),
            api_key=api_key,
            model=str(data.get("model") or ""),
            api_protocol=str(data.get("api_protocol") or "chat_completions"),
            reasoning_effort=data.get("reasoning_effort") or None,
            timeout_sec=self._int_or(data.get("timeout_sec"), 120),
            temperature=float(data.get("temperature") or 0.2),
            cache_dir=VISION_CACHE_DIR,
            cache_enabled=settings.ai_cache_enabled,
            min_interval_ms=settings.ai_request_min_interval_ms,
            rate_limit_retries=settings.ai_rate_limit_retries,
            rate_limit_backoff_ms=settings.ai_rate_limit_backoff_ms,
        )
        return self.last_client

    async def _load_auth(
        self,
        browser_page: Any,
        payload: WebVisionDiscoveryRequest,
        page: dict[str, Any],
        target_url: str,
    ) -> None:
        page_data = page.get("data") if isinstance(page.get("data"), dict) else {}
        auth_id = payload.auth_id or page_data.get("auth_id")
        if not auth_id:
            return
        from web_automation.pages.base_page import BasePage

        context = self.auth_service.web_auth_context(int(auth_id), target_url)
        await BasePage(browser_page, action_timeout_ms=3000, navigation_timeout_ms=30000)._apply_auth(context, target_url)

    async def _screenshot(
        self,
        session: DiscoveryBrowserSession,
        page_id: int,
        label: str,
        *,
        full_page: bool = True,
    ) -> str:
        DISCOVERY_SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        safe_label = "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in label).strip("_") or "page"
        filename = f"vision_{page_id}_{safe_label}_{int(time.time() * 1000)}.png"
        path = DISCOVERY_SCREENSHOT_DIR / filename
        await session.screenshot(str(path), full_page=full_page)
        return str(path)

    def _prompt_template(self, template_type: str, prompt_template_id: int | None) -> str:
        if prompt_template_id:
            item = self.prompt_service.get(prompt_template_id)
            data = item.get("data") if isinstance(item.get("data"), dict) else {}
            if data.get("template_type") == template_type:
                return str(data.get("user_template") or "")
        rows, _ = self.repository.list("ai_prompt_templates", keyword=None, page=1, page_size=100)
        for row in rows:
            data = row.get("data") if isinstance(row.get("data"), dict) else {}
            if row.get("status") == "active" and data.get("template_type") == template_type:
                return str(data.get("user_template") or "")
        return ""

    def _render_prompt(
        self,
        template: str,
        page: dict[str, Any],
        target_url: str,
        user_prompt: str | None,
        *,
        feature: str = "",
    ) -> str:
        page_data = page.get("data") if isinstance(page.get("data"), dict) else {}
        rendered = template.replace("{{page_name}}", str(page.get("name") or ""))
        rendered = rendered.replace("{{page_url}}", target_url or str(page_data.get("url") or ""))
        rendered = rendered.replace("{{feature}}", feature)
        if page_data.get("feature_type", "page") != "page":
            rendered += f"\n仅分析功能：{page['name']}；features 中功能名称须原样返回，其他功能不要分析。"
        return rendered.replace("{{user_prompt}}", str(user_prompt or ""))

    def _required_page(self, page_id: int) -> dict[str, Any]:
        page = self.repository.get("web_pages", int(page_id))
        if not page:
            raise ResourceNotFoundError(f"Web 页面不存在：{page_id}")
        return page

    def _save_overview(self, page, screenshot, dom):
        from app.services.web_discovery_evidence_service import WebDiscoveryEvidenceService

        if (page.get("data") or {}).get("feature_type", "page") != "page":
            return WebDiscoveryEvidenceService(self.repository).attach(page, page["name"], screenshot, dom)
        row = self._required_page(page["id"])
        data = {**(row.get("data") or {}), "discovery_screenshots": [screenshot], "dom_snapshot": safe_dom(dom)}
        return self.repository.update("web_pages", row["id"], {"data": data})

    @staticmethod
    def _int_or(value: Any, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default
