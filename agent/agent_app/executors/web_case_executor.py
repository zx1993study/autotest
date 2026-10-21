from __future__ import annotations

import asyncio
import base64
import time
import uuid
from pathlib import Path
from typing import Any

from web_automation.compiler import ExecutionPlanCompiler
from web_automation.engines.pipeline import ActionStrategyPipeline, AiBudget
from web_automation.engines.playwright import PlaywrightEngine
from web_automation.engines.stagehand import StagehandModelConfig, StagehandSession
from web_automation.models import CompiledCase, ExecutionPlan, RunConfig
from web_automation.pages.dynamic_page import DynamicPage
from web_automation.outcomes import verification_error

from agent_app.executors.result_builder import build_execution_record, summarize_records
from agent_app.utils.playwright_runtime import chromium_launch_options, prepare_recording_runtime
from agent_app.utils.time_utils import duration_ms, now_millis
from agent_app.windows.task_window import TaskBrowserWindow
from agent_app.executors.web_manual_input import wait_manual_input, outcome_metadata
from agent_app.runtime.task_cancelled import TaskCancelled
from agent_app.executors.web_secret_redaction import redact_record


class LocalWebCaseExecutor:
    """Execute all Web engines through the shared async runtime."""

    def __init__(self, artifacts_dir: Path) -> None:
        self.artifacts_dir = artifacts_dir
        self.screenshot_dir = artifacts_dir / "screenshots"
        self.compiler = ExecutionPlanCompiler()
        self.window_context = None

    def _window(self, case, config):
        if config.headless or not self.window_context:
            return TaskBrowserWindow(None, None, 0, None, case.name)
        return TaskBrowserWindow(*self.window_context, case.name)

    def execute(self, task_payload: dict[str, Any]) -> dict[str, Any]:
        prepare_recording_runtime()
        plan = self.compiler.compile(task_payload)
        execution = task_payload.get("execution") if isinstance(task_payload.get("execution"), dict) else {}
        records = asyncio.run(self._execute_plan(plan, execution))
        result = summarize_records(records)
        result["manifest_version"] = plan.manifest_version
        result["result_version"] = plan.result_version
        return result

    async def _execute_plan(
        self,
        plan: ExecutionPlan,
        execution: dict[str, Any],
    ) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for case in plan.cases:
            records.append(await self._execute_case(case, plan, execution))
        return records

    async def _execute_case(
        self,
        case: CompiledCase,
        plan: ExecutionPlan,
        execution: dict[str, Any],
    ) -> dict[str, Any]:
        started_at = time.perf_counter()
        steps = [dict(item) for item in case.steps]
        result: dict[str, Any] = {
            "steps": steps,
            "screenshots": [],
            "step_count": 0,
            "url": "",
            "engine": plan.config.engine,
            "assertion_results": [],
        }
        status = "success"
        description = "Web 用例本地执行通过"
        error_message: str | None = None
        try:
            if case.raw.get("_dynamic_error"):
                raise ValueError(str(case.raw["_dynamic_error"]))
            if not steps:
                raise RuntimeError("未读取到执行步骤，请检查正式用例步骤或页面元素是否已保存")
            if error := verification_error(steps):
                raise ValueError(error)
            if any(s.get('sensitive') for s in steps) and plan.config.engine != 'playwright':
                raise ValueError('密码用例只允许使用确定性 Playwright 执行，不能发送给 AI 执行器')
            if plan.config.engine == "playwright":
                await self._run_playwright(case, plan.config, steps, result)
            else:
                await self._run_stagehand(case, plan, steps, result)
            if outcome_metadata(steps, result['step_count'], 'success')['business_result'] != 'passed':
                raise RuntimeError('脚本未完整执行，业务结果未验证')
        except TaskCancelled:
            raise
        except Exception as exc:  # noqa: BLE001 - failures are reported to the platform.
            status = "failed"
            description = str(exc)
            error_message = str(exc)
        result["duration_ms"] = duration_ms(started_at)
        result.update(outcome_metadata(steps, result['step_count'], status))
        if status == 'success':
            description = result['result_label']
        return redact_record(build_execution_record(case.raw, execution, status, description, result, error_message), case.raw, case.auth_context)

    async def _run_playwright(
        self,
        case: CompiledCase,
        config: RunConfig,
        steps: list[dict[str, Any]],
        result: dict[str, Any],
    ) -> None:
        try:
            from playwright.async_api import async_playwright
        except ModuleNotFoundError as exc:
            raise RuntimeError("本地 Agent 未安装 playwright，请安装后再执行 Web 任务") from exc

        window = self._window(case, config)
        private = any(s.get('action') == 'manual' or s.get('sensitive') for s in steps)
        record_video = config.record_video and not private
        if private:
            result['privacy_notice'] = '包含敏感输入，已关闭录屏；结果截图自动遮蔽敏感字段'
        try:
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(
                    **chromium_launch_options(headless=config.headless, slow_mo_ms=config.slow_mo_ms)
                )
                video_dir = self.artifacts_dir / "web-cases" / uuid.uuid4().hex
                if record_video:
                    video_dir.mkdir(parents=True, exist_ok=True)
                browser_context = await browser.new_context(**({"record_video_dir": str(video_dir), "viewport": {"width": 1366, "height": 900}} if record_video else {}))
                page = await browser_context.new_page()
                try:
                    self._active_window = window
                    await window.attach(page)
                    await window.set_phase("running")
                    await self._execute_steps(page, case, config, steps, result, None)
                finally:
                    await browser_context.close()
                    if record_video and page.video:
                        result["video_local_path"] = str(await page.video.path())
                    await browser.close()
        finally:
            await window.close()

    async def _run_stagehand(
        self,
        case: CompiledCase,
        plan: ExecutionPlan,
        steps: list[dict[str, Any]],
        result: dict[str, Any],
    ) -> None:
        model = self._stagehand_model(plan.ai_model)
        window = self._window(case, plan.config)
        try:
            async with StagehandSession(model, headless=plan.config.headless) as session:
                await window.attach(session.page)
                await window.set_phase("running")
                await self._execute_steps(session.page, case, plan.config, steps, result, session)
        finally:
            await window.close()

    async def _execute_steps(
        self,
        page: Any,
        case: CompiledCase,
        config: RunConfig,
        steps: list[dict[str, Any]],
        result: dict[str, Any],
        stagehand: StagehandSession | None,
    ) -> None:
        dynamic_page = DynamicPage(
            page,
            action_timeout_ms=config.action_timeout_ms,
            navigation_timeout_ms=config.navigation_timeout_ms,
        )
        await dynamic_page.prepare(case.target_url, case.auth_context)
        cache_updates: list[dict[str, Any]] = []
        cache_invalidations: list[int] = []

        def save_cache(element_id: int, cache: dict[str, Any]) -> None:
            cache_updates.append({"element_id": element_id, "cache": cache})

        def invalidate_cache(element_id: int) -> None:
            if element_id not in cache_invalidations:
                cache_invalidations.append(element_id)

        budget = AiBudget(config.max_ai_calls_per_case)
        pipeline = ActionStrategyPipeline(
            engine=config.engine,
            budget=budget,
            target_url=case.target_url,
            max_healing_time_ms=config.max_healing_time_ms,
            disable_ai_after_429=config.disable_ai_after_429,
            save_cache=save_cache,
            invalidate_cache=invalidate_cache,
        )
        healing: list[dict[str, Any]] = []
        events: list[dict[str, Any]] = []
        cache_hits = 0
        healed_steps = 0
        current_step: dict[str, Any] | None = None
        last_assertion = max((i for i, s in enumerate(steps, 1) if s.get('action') == 'assert' and not s.get('skip')), default=0)
        try:
            for index, step in enumerate(steps, 1):
                current_step = step
                if self._truthy(step.get("skip")):
                    continue
                if self.window_context:
                    _, api, task_id, lease = self.window_context
                    if (await asyncio.to_thread(api.web_state, task_id, lease)).get('cancel_requested'):
                        raise TaskCancelled('用户已中止操作')
                if step.get('action') == 'manual':
                    if config.headless:
                        raise RuntimeError('人工输入不支持无头模式')
                    await wait_manual_input(page, step, self.window_context, self._active_window, index, case.id)
                    result['step_count'] += 1
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
                    events.extend(pipeline.last_events)
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
                    healing.append(outcome.healing)
                events.extend(outcome.events)
                result["step_count"] += 1
                if config.step_wait_ms > 0:
                    await page.wait_for_timeout(config.step_wait_ms)
                private = any(s.get('action') == 'manual' or s.get('sensitive') for s in steps)
                result_step = step.get('capture_result') or (step.get('action') == 'assert' and index == last_assertion)
                if (result_step or self._truthy(step.get("take_screenshot"))) and (not private or result_step):
                    result["screenshots"].append(await self._capture_screenshot(page, case, step))
            result["url"] = str(getattr(page, "url", "") or "")
            result["cookies"] = await page.context.cookies()
            result["storage_state"] = await page.context.storage_state()
        except Exception as exc:  # noqa: BLE001 - always retain a failure screenshot for diagnostics.
            result["url"] = str(getattr(page, "url", "") or "")
            result["screenshots"].append(await self._capture_screenshot(page, case, current_step or {}, str(exc)))
            raise
        finally:
            result["healing"] = healing
            result["events"] = events
            result["cache_updates"] = cache_updates
            result["cache_invalidations"] = cache_invalidations
            result["ai_usage"] = {
                "llm_calls": budget.calls,
                "cache_hits": cache_hits,
                "healed_steps": healed_steps,
                "budget": config.max_ai_calls_per_case,
            }
            self._apply_last_screenshot(result)

    def _stagehand_model(self, snapshot: dict[str, Any]) -> StagehandModelConfig:
        api_key = str(snapshot.get("api_key") or "").strip()
        if not api_key:
            raise RuntimeError("任务缺少 AI 模型配置，无法使用 AI 执行引擎")
        timeout_sec = self._to_int(snapshot.get("timeout_sec"), 0) or 0
        return StagehandModelConfig(
            model_name=str(snapshot.get("model_name") or snapshot.get("model") or ""),
            api_key=api_key,
            base_url=str(snapshot.get("base_url") or ""),
            timeout_ms=timeout_sec * 1000 if timeout_sec else 30000,
            max_retries=0,
        )

    async def _capture_screenshot(
        self,
        page: Any,
        case: CompiledCase,
        step: dict[str, Any],
        error: str | None = None,
    ) -> dict[str, Any]:
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        filename = f"case_{case.id or 'unknown'}_{now_millis()}.png"
        path = self.screenshot_dir / filename
        try:
            await page.screenshot(path=str(path), full_page=False,
                                  mask=PlaywrightEngine(page).screenshot_masks(list(case.steps)))
            return {
                "step_order": step.get("sort_order"),
                "step_name": step.get("name") or step.get("元素名称") or "",
                "screenshot_file": filename,
                "screenshot_base64": base64.b64encode(path.read_bytes()).decode("ascii"),
                "screenshot_mime_type": "image/png",
                "local_path": str(path),
                "error": error,
            }
        except Exception as exc:  # noqa: BLE001
            return {"screenshot_error": str(exc), "error": error}

    def _apply_last_screenshot(self, result: dict[str, Any]) -> None:
        screenshots = result.get("screenshots") if isinstance(result.get("screenshots"), list) else []
        for screenshot in reversed(screenshots):
            if isinstance(screenshot, dict) and screenshot.get("screenshot_file"):
                result["screenshot_file"] = screenshot["screenshot_file"]
                return

    def _truthy(self, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        if isinstance(value, (int, float)):
            return value != 0
        return str(value).strip().lower() in {"1", "true", "yes", "y", "on", "是", "跳过", "截图"}

    def _to_int(self, value: Any, default: int | None = None) -> int | None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default
