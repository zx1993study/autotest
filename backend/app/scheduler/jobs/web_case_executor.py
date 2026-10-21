from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path
from typing import Any

from web_automation.compiler import ExecutionPlanCompiler
from web_automation.engines.pipeline import ActionStrategyPipeline, AiBudget
from web_automation.engines.stagehand import (
    DEFAULT_STAGEHAND_TIMEOUT_MS,
    StagehandModelConfig,
    StagehandSession,
)
from web_automation.models import CompiledCase, RunConfig
from web_automation.pages.dynamic_page import DynamicPage
from web_automation.outcomes import outcome_metadata, verification_error

from app.core.exceptions import BusinessRuleError
from app.enums.business import WebEngineEnum
from app.repositories.interfaces import ResourceRepository
from app.scheduler.jobs.case_execution_base import CaseExecutionBase
from app.services.ai_model_service import AiModelResourceService
from app.services.project_auth_service import ProjectAuthService
from app.services.ui_testing_service import UiTestingService


from app.core.storage import storage_path

SCREENSHOT_DIR = storage_path("screenshots")


class WebExecutionError(RuntimeError):
    def __init__(self, message: str, result: dict[str, Any]) -> None:
        super().__init__(message)
        self.result = result


class WebCaseExecutor(CaseExecutionBase):
    """Compile and execute one Web case through the shared runtime."""

    def __init__(self, repository: ResourceRepository) -> None:
        super().__init__("WEB", repository)
        self.compiler = ExecutionPlanCompiler()

    def execute(self, case: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        engine_config = self.web_engine_config(case, payload)
        playwright_config = self.playwright_execution_config(payload)
        execution = {
            "mode": payload.get("mode", "server_headless"),
            "node_id": payload.get("node_id"),
            "project_id": payload.get("project_id"),
            "config": {**playwright_config, **engine_config, "headless": True},
        }
        compiled = self.compiler.compile_case(case, self._execution_context(case, payload), payload)
        case = compiled.raw
        run_config = RunConfig.from_execution(execution)
        runtime_payload = {
            **payload,
            "execution": execution,
            "playwright_config": playwright_config,
            "engine_config": engine_config,
            "compiled_case": compiled,
            "run_config": run_config,
        }
        steps = [dict(item) for item in compiled.steps]
        started_at = time.perf_counter()
        try:
            if case.get("_dynamic_error"):
                raise ValueError(str(case["_dynamic_error"]))
            if not steps:
                raise WebExecutionError(
                    "未读取到执行步骤，请检查正式用例步骤或页面元素是否已保存",
                    {"url": compiled.target_url, "step_count": 0, "screenshots": []},
                )
            if message := verification_error(steps):
                raise ValueError(message)
            result = self._run_async_web_steps(case, runtime_payload, steps)
            if outcome_metadata(steps, result.get('step_count', 0), 'success')['business_result'] != 'passed':
                raise WebExecutionError('脚本未完整执行，业务结果未验证', result)
            status_text = "success"
            description = "操作及业务验证通过"
            error = None
        except WebExecutionError as exc:
            result = exc.result
            status_text = "failed"
            description = str(exc)
            error = str(exc)
        except Exception as exc:  # noqa: BLE001
            result = {}
            status_text = "failed"
            description = str(exc)
            error = str(exc)

        auth_result = None
        if status_text == "success" and self._is_login_feature(case):
            auth_result = self._save_login_auth(case, steps, result, payload)

        return self.repository.create(
            "execution_records",
            {
                "name": f"WEB 用例执行 - {case.get('name') or case.get('id')}",
                "project_id": case.get("project_id") or payload.get("project_id"),
                "description": description,
                "status": status_text,
                "data": {
                    "case_id": case.get("id"),
                    "case_type": self.case_type,
                    "mode": execution["mode"],
                    "node_id": payload.get("node_id"),
                    "engine": run_config.engine,
                    "manifest_version": "1.0",
                    "result_version": "1.0",
                    "playwright_config": playwright_config,
                    "steps": steps,
                    "duration_ms": self.duration_ms(started_at),
                    "url": result.get("url"),
                    "step_count": result.get("step_count", 0),
                    "healing": result.get("healing", []),
                    "ai_usage": result.get("ai_usage"),
                    "events": result.get("events", []),
                    "screenshots": result.get("screenshots", []),
                    "screenshot_url": result.get("screenshot_url"),
                    "screenshot_file": result.get("screenshot_file"),
                    "screenshot_error": result.get("screenshot_error"),
                    "cookies": result.get("cookies", []),
                    "storage_state": result.get("storage_state", {}),
                    "auth_saved": auth_result,
                    "assertions": self.case_assertions(case),
                    "assertion_results": result.get("assertion_results", []),
                    "dynamic_values": case.get("_dynamic_values", {}),
                    "error": error,
                    **outcome_metadata(steps, result.get('step_count', 0), status_text),
                },
            },
        )

    def _run_async_web_steps(
        self,
        case: dict[str, Any],
        payload: dict[str, Any],
        steps: list[dict[str, Any]],
    ) -> dict[str, Any]:
        compiled = payload.get("compiled_case")
        config = payload.get("run_config")
        if not isinstance(compiled, CompiledCase) or not isinstance(config, RunConfig):
            compiled = self.compiler.compile_case(case, self._execution_context(case, payload))
            config = RunConfig.from_execution(payload.get("execution"))
        if sys.platform.startswith("win"):
            loop = asyncio.WindowsProactorEventLoopPolicy().new_event_loop()
            try:
                return loop.run_until_complete(self._run_web_steps(compiled, config, steps, payload))
            finally:
                loop.close()
        return asyncio.run(self._run_web_steps(compiled, config, steps, payload))

    async def _run_web_steps(
        self,
        case: CompiledCase,
        config: RunConfig,
        steps: list[dict[str, Any]],
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        if config.engine == WebEngineEnum.PLAYWRIGHT.code:
            return await self._run_playwright_session(case, config, steps)
        return await self._run_stagehand_session(case, config, steps, payload)

    async def _run_playwright_session(
        self,
        case: CompiledCase,
        config: RunConfig,
        steps: list[dict[str, Any]],
    ) -> dict[str, Any]:
        try:
            from playwright.async_api import async_playwright
        except ModuleNotFoundError as exc:
            raise RuntimeError("后端未安装 playwright，请安装后再执行 Web 用例") from exc
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True, slow_mo=config.slow_mo_ms)
            browser_context = await browser.new_context()
            page = await browser_context.new_page()
            try:
                return await self._execute_steps(page, case, config, steps, None)
            finally:
                await browser_context.close()
                await browser.close()

    async def _run_stagehand_session(
        self,
        case: CompiledCase,
        config: RunConfig,
        steps: list[dict[str, Any]],
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        async with StagehandSession(self._stagehand_model_config(payload), headless=True) as session:
            return await self._execute_steps(session.page, case, config, steps, session)

    async def _execute_steps(
        self,
        page: Any,
        case: CompiledCase,
        config: RunConfig,
        steps: list[dict[str, Any]],
        stagehand: StagehandSession | None,
    ) -> dict[str, Any]:
        dynamic_page = DynamicPage(
            page,
            action_timeout_ms=config.action_timeout_ms,
            navigation_timeout_ms=config.navigation_timeout_ms,
        )
        await dynamic_page.prepare(case.target_url, case.auth_context)
        element_service = UiTestingService("web_pages", "web_elements", self.repository)
        budget = AiBudget(config.max_ai_calls_per_case)
        pipeline = ActionStrategyPipeline(
            engine=config.engine,
            budget=budget,
            target_url=case.target_url,
            max_healing_time_ms=config.max_healing_time_ms,
            disable_ai_after_429=config.disable_ai_after_429,
            save_cache=element_service.update_ai_cache,
            invalidate_cache=element_service.invalidate_ai_cache,
        )
        result: dict[str, Any] = {
            "url": "",
            "step_count": 0,
            "screenshots": [],
            "healing": [],
            "events": [],
            "assertion_results": [],
        }
        cache_hits = 0
        healed_steps = 0
        current_step: dict[str, Any] | None = None
        try:
            for index, step in enumerate(steps, 1):
                current_step = step
                if self.is_truthy(step.get("skip")):
                    continue

                async def ai_action() -> dict[str, Any]:
                    if stagehand is None:
                        raise RuntimeError("Stagehand session is unavailable")
                    return await stagehand.resolve_and_execute(step)

                try:
                    outcome = await pipeline.execute(
                        step,
                        static_action=lambda: dynamic_page.execute(step),
                        cached_action=lambda selector: dynamic_page.execute_cached(step, selector),
                        ai_action=ai_action,
                    )
                except Exception:
                    result["events"].extend(pipeline.last_events)
                    if dynamic_page.engine.last_assertion:
                        result['assertion_results'].append({"step": index, "name": step.get('name'), **dynamic_page.engine.last_assertion})
                    raise
                if dynamic_page.engine.last_assertion:
                    result['assertion_results'].append({"step": index, "name": step.get('name'), **dynamic_page.engine.last_assertion})
                if outcome.cache_update:
                    step["ai_cache"] = outcome.cache_update
                if outcome.source == "ai_cache":
                    cache_hits += 1
                if outcome.healed and outcome.healing:
                    healed_steps += 1
                    result["healing"].append(outcome.healing)
                result["events"].extend(outcome.events)
                result["step_count"] += 1
                if config.step_wait_ms > 0:
                    await page.wait_for_timeout(config.step_wait_ms)
                if self.is_truthy(step.get("take_screenshot")):
                    result["screenshots"].append(await self._capture_web_screenshot(page, case, config, step))
            result["url"] = str(getattr(page, "url", "") or "")
            result["cookies"] = await page.context.cookies()
            result["storage_state"] = await page.context.storage_state()
            result["ai_usage"] = {
                "llm_calls": budget.calls,
                "cache_hits": cache_hits,
                "healed_steps": healed_steps,
                "budget": config.max_ai_calls_per_case,
            }
            result.update(self._last_screenshot(result["screenshots"]))
            return result
        except Exception as exc:  # noqa: BLE001
            result["url"] = str(getattr(page, "url", "") or "")
            result["error"] = str(exc)
            result["ai_usage"] = {
                "llm_calls": budget.calls,
                "cache_hits": cache_hits,
                "healed_steps": healed_steps,
                "budget": config.max_ai_calls_per_case,
            }
            result["screenshots"].append(
                await self._capture_web_screenshot(page, case, config, current_step, error=str(exc))
            )
            result.update(self._last_screenshot(result["screenshots"]))
            raise WebExecutionError(str(exc), result) from exc

    def playwright_execution_config(self, payload: dict[str, Any]) -> dict[str, Any]:
        merged = {
            **self._execution_dictionary_config(),
            **(payload.get("config") if isinstance(payload.get("config"), dict) else {}),
        }
        return {
            "run_mode": "server_headless",
            "headless": True,
            "slow_mo_ms": self.to_int(merged.get("slow_mo_ms"), 0) or 0,
            "step_wait_ms": self.to_int(merged.get("step_wait_ms"), 0) or 0,
            "action_timeout_ms": self.to_int(merged.get("action_timeout_ms"), 5000) or 5000,
            "navigation_timeout_ms": self.to_int(merged.get("navigation_timeout_ms"), 30000) or 30000,
            "screenshot": str(merged.get("screenshot") or "full_page"),
            "max_ai_calls_per_case": self.to_int(merged.get("max_ai_calls_per_case"), 3) or 3,
            "max_healing_time_ms": self.to_int(merged.get("max_healing_time_ms"), 30000) or 30000,
            "disable_ai_after_429": merged.get("disable_ai_after_429", True),
        }

    def web_engine_config(self, case: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        request_config = payload.get("config") if isinstance(payload.get("config"), dict) else {}
        case_data = self.case_data(case)
        dictionary_config = self._execution_dictionary_config()
        raw_engine = (
            request_config.get("engine")
            or case_data.get("engine")
            or dictionary_config.get("engine")
            or WebEngineEnum.HYBRID.code
        )
        engine = str(raw_engine).strip().lower()
        if engine not in {item.code for item in WebEngineEnum}:
            raise BusinessRuleError(f"不支持的 Web 执行引擎：{raw_engine}")
        model_id = self.to_int(
            request_config.get("model_id") or case_data.get("model_id") or dictionary_config.get("stagehand_model_id"),
            None,
        )
        return {"engine": engine, "model_id": model_id}

    def _execution_dictionary_config(self) -> dict[str, Any]:
        rows, _ = self.repository.list("system_dictionaries", page_size=10000)
        result: dict[str, Any] = {}
        for row in rows:
            data = row.get("data") if isinstance(row.get("data"), dict) else {}
            if row.get("status") != "active" or data.get("dict_type") != "playwright_execution":
                continue
            key = str(data.get("dict_key") or "").strip()
            if key:
                result[key] = data.get("dict_value")
        return result

    def _stagehand_model_config(self, payload: dict[str, Any]) -> StagehandModelConfig:
        engine_config = payload.get("engine_config") if isinstance(payload.get("engine_config"), dict) else {}
        model_service = AiModelResourceService(self.repository)
        model = model_service.active_model(self.to_int(engine_config.get("model_id"), None))
        data = model.get("data") if isinstance(model.get("data"), dict) else {}
        api_key = model_service.api_key(model)
        if not api_key:
            raise BusinessRuleError("AI 模型未配置 API Key，无法使用 AI 执行引擎")
        timeout_sec = self.to_int(data.get("timeout_sec"), 0) or 0
        return StagehandModelConfig(
            model_name=str(data.get("model") or ""),
            api_key=api_key,
            base_url=str(data.get("base_url") or ""),
            timeout_ms=timeout_sec * 1000 if timeout_sec else DEFAULT_STAGEHAND_TIMEOUT_MS,
            max_retries=0,
        )

    def _execution_context(self, case: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        page = self._source_page(case)
        project_id = case.get("project_id") or payload.get("project_id")
        project = self.repository.get("projects", int(project_id)) if project_id else None
        source_id = self.to_int(case.get("source_id"), None)
        elements: list[dict[str, Any]] = []
        if source_id is not None:
            elements, _ = self.repository.list(
                "web_elements",
                project_id=self.to_int(project_id, None),
                page=1,
                page_size=10000,
                data_filters={"page_id": source_id},
            )
        auth_id = self._web_auth_id(case, payload)
        auth_context = ProjectAuthService(self.repository).web_auth_context(auth_id) if auth_id else {}
        return {
            "pages": {str(page["id"]): page} if page else {},
            "projects": {str(project["id"]): project} if project else {},
            "elements": elements,
            "auth_context": auth_context,
        }

    def _case_steps(self, case: dict[str, Any]) -> list[dict[str, Any]]:
        return [dict(item) for item in self.compiler.compile_case(case, self._execution_context(case, {})).steps]

    def _web_case_url(self, case: dict[str, Any], project_id: Any) -> str:
        return self.compiler.compile_case(case, self._execution_context(case, {"project_id": project_id})).target_url

    async def _capture_web_screenshot(
        self,
        page: Any,
        case: CompiledCase,
        config: RunConfig,
        step: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> dict[str, Any]:
        try:
            SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
            filename = self._screenshot_filename(case)
            from web_automation.engines.playwright import PlaywrightEngine
            await page.screenshot(path=str(SCREENSHOT_DIR / filename), full_page=config.screenshot != "viewport",
                                  mask=PlaywrightEngine(page).screenshot_masks(list(case.steps)))
            return {
                "step_order": (step or {}).get("sort_order"),
                "step_name": (step or {}).get("name") or "",
                "screenshot_file": filename,
                "screenshot_url": f"/api/v1/screenshots/{filename}",
                "error": error,
            }
        except Exception as exc:  # noqa: BLE001
            return {"screenshot_error": str(exc), "error": error}

    def _last_screenshot(self, screenshots: list[dict[str, Any]]) -> dict[str, Any]:
        for screenshot in reversed(screenshots):
            if screenshot.get("screenshot_url"):
                return {
                    "screenshot_url": screenshot.get("screenshot_url"),
                    "screenshot_file": screenshot.get("screenshot_file"),
                }
        errors = [str(item.get("screenshot_error")) for item in screenshots if item.get("screenshot_error")]
        return {"screenshot_error": "; ".join(errors)} if errors else {}

    def _screenshot_filename(self, case: CompiledCase) -> str:
        value = str(case.id or case.name or "case")
        prefix = "".join(char if char.isalnum() or char in {"-", "_", "."} else "_" for char in value)
        timestamp = int(time.time() * 1000)
        filename = f"{prefix.strip('._') or 'case'}_{timestamp}.png"
        while (SCREENSHOT_DIR / filename).exists():
            timestamp += 1
            filename = f"{prefix.strip('._') or 'case'}_{timestamp}.png"
        return filename

    def _web_auth_id(self, case: dict[str, Any], payload: dict[str, Any]) -> Any:
        if self.is_truthy(payload.get("skip_auth")):
            return None
        if payload.get("auth_id"):
            return payload.get("auth_id")
        data = self.case_data(case)
        request = data.get("request") if isinstance(data.get("request"), dict) else {}
        page = self._source_page(case)
        page_data = page.get("data") if page and isinstance(page.get("data"), dict) else {}
        return data.get("auth_id") or request.get("auth_id") or page_data.get("auth_id")

    def _is_login_feature(self, case: dict[str, Any]) -> bool:
        page = self._source_page(case)
        page_data = page.get("data") if page and isinstance(page.get("data"), dict) else {}
        markers = [page_data.get("feature_type"), page.get("name") if page else None, case.get("name")]
        return any(str(item or "").lower() == "login" or "登录" in str(item or "") for item in markers)

    def _save_login_auth(
        self,
        case: dict[str, Any],
        steps: list[dict[str, Any]],
        result: dict[str, Any],
        payload: dict[str, Any],
    ) -> dict[str, Any] | None:
        cookies = result.get("cookies")
        if not isinstance(cookies, list) or not cookies:
            return None
        username = self._login_username(steps) or "unknown"
        target_auth_id = self.to_int(payload.get("refresh_auth_id"), None)
        return ProjectAuthService(self.repository).save_web_cookie_auth(
            case=case,
            cookies=cookies,
            auth_name=f"{username}-web",
            metadata={
                "url": result.get("url"),
                "username": username,
                "storage_state": result.get("storage_state"),
                "target_auth_id": target_auth_id,
                "preserve_existing_name": bool(target_auth_id),
            },
            refresh_strategy="on_login_success",
            description="Web 登录成功后自动保存 Cookie",
            stable_filename=True,
        )

    def _login_username(self, steps: list[dict[str, Any]]) -> str:
        fill_steps = [step for step in steps if str(step.get("action") or "").lower() == "fill"]
        for step in fill_steps:
            text = " ".join(str(step.get(key) or "") for key in ("name", "locator", "role_name")).lower()
            if any(marker in text for marker in ("username", "account", "phone", "手机号", "账号", "用户名")):
                return self._safe_auth_name(str(step.get("value") or step.get("default_value") or ""))
        if fill_steps:
            return self._safe_auth_name(str(fill_steps[0].get("value") or fill_steps[0].get("default_value") or ""))
        return ""

    def _safe_auth_name(self, value: str) -> str:
        result = "".join(char if char.isalnum() or char in {"-", "_", "."} else "_" for char in value.strip())
        return result.strip("._") or "unknown"

    def _source_page(self, case: dict[str, Any]) -> dict[str, Any] | None:
        source_id = self.to_int(case.get("source_id"), None)
        return self.repository.get("web_pages", source_id) if source_id is not None else None
