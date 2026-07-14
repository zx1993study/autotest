from __future__ import annotations

import re
import time
from typing import Any, Callable

from app.utils.cookie_utils import normalize_playwright_cookies
from app.utils.playwright_auto_recorder_matcher import PlaywrightControlMatcherMixin
from app.utils.playwright_auto_recorder_steps import PlaywrightStepGeneratorMixin
from app.utils.playwright_auto_recorder_types import (
    SCREENSHOT_DIR,
    ControlInfo,
    ensure_windows_playwright_event_loop_policy as _ensure_windows_playwright_event_loop_policy,
)


class PlaywrightAutoRecorder(PlaywrightControlMatcherMixin, PlaywrightStepGeneratorMixin):
    """Drive a page with Playwright and emit codegen-like script lines for parsing."""

    MENU_LABELS = ("更多", "操作", "更多操作", "More", "Actions", "...")
    FEATURE_LABELS: dict[str, tuple[str, ...]] = {
        "add": ("新增", "添加", "新建", "创建", "Add", "New", "Create"),
        "edit": ("编辑", "修改", "Edit", "Update"),
        "delete": ("删除", "移除", "Delete", "Remove"),
        "detail": ("详情", "查看", "Detail", "View"),
        "query": ("查询", "搜索", "筛选", "过滤", "Search", "Filter"),
        "import": ("导入", "上传", "Import", "Upload"),
        "export": ("导出", "下载", "Export", "Download"),
        "login": ("登录", "登 录", "Login", "Sign in"),
    }
    CANCEL_LABELS = ("取消", "关闭", "否", "放弃", "Cancel", "Close", "No")
    EXTRA_CANCEL_LABELS = ("\u53d6\u6d88", "\u5173\u95ed", "\u5426", "\u653e\u5f03", "Cancel", "Close", "No")
    SUBMIT_LABELS = ("\u4fdd\u5b58", "\u63d0\u4ea4", "\u786e\u5b9a", "\u786e\u8ba4", "\u5b8c\u6210", "Save", "Submit", "OK", "Confirm")
    DESTRUCTIVE_LABELS = ("\u5220\u9664", "\u79fb\u9664", "Delete", "Remove")
    SUBMIT_RE = re.compile("\u4fdd\u5b58|\u63d0\u4ea4|\u786e\u5b9a|\u786e\u8ba4|\u5b8c\u6210|Save|Submit|OK|Confirm", re.I)
    DESTRUCTIVE_RE = re.compile("\u5220\u9664|\u79fb\u9664|Delete|Remove", re.I)

    def record(
        self,
        target_url: str,
        feature_type: str,
        feature_name: str,
        cookies: list[dict[str, Any]] | None = None,
        instruction: str | None = None,
        timeout_sec: int = 120,
        headless: bool = True,
    ) -> dict[str, Any]:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright

        timeout_ms = max(3000, min(int(timeout_sec or 120) * 1000, 300000))
        deadline = time.time() + timeout_ms / 1000
        script_lines: list[str] = [
            "from playwright.sync_api import Page",
            "",
            "def test_ai_recorded(page: Page):",
            f"    page.goto({target_url!r})",
        ]
        operations: list[dict[str, Any]] = []
        warnings: list[str] = []

        _ensure_windows_playwright_event_loop_policy()
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=headless)
            context = browser.new_context()
            try:
                normalized_cookies = normalize_playwright_cookies(cookies or [], target_url)
                if normalized_cookies:
                    context.add_cookies(normalized_cookies)

                page = context.new_page()
                page.set_default_timeout(min(timeout_ms, 10000))
                page.goto(target_url, wait_until="domcontentloaded", timeout=timeout_ms)
                try:
                    page.wait_for_load_state("networkidle", timeout=min(timeout_ms, 5000))
                except PlaywrightTimeoutError:
                    warnings.append("页面网络请求未完全静止，已继续采集当前可见元素。")

                feature = self._normalize_feature_type(feature_type)
                controls = self._visible_controls(page)
                if not controls:
                    warnings.append("页面未发现可见输入框、按钮、链接或下拉框。")

                if feature in {"add", "edit", "delete", "detail", "import", "export"}:
                    self._open_feature_entry(page, feature, script_lines, operations, warnings)
                    self._short_wait(page, deadline)
                    controls = self._prefer_dialog_controls(self._visible_controls(page))
                else:
                    controls = self._prefer_dialog_controls(controls)

                self._append_control_steps(page, feature, controls, script_lines, operations)
                self._perform_safe_feature_actions(page, feature, controls, script_lines, operations, warnings, deadline)

                return {
                    "script_text": "\n".join(script_lines) + "\n",
                    "operations": operations,
                    "warnings": warnings,
                    "target_url": target_url,
                    "feature_type": feature,
                    "feature_name": feature_name,
                    "instruction": instruction,
                }
            finally:
                context.close()
                browser.close()

    def capture_context(
        self,
        target_url: str,
        feature_type: str,
        feature_name: str,
        cookies: list[dict[str, Any]] | None = None,
        timeout_sec: int = 120,
        headless: bool = True,
    ) -> dict[str, Any]:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright

        timeout_ms = max(3000, min(int(timeout_sec or 120) * 1000, 300000))
        warnings: list[str] = []
        _ensure_windows_playwright_event_loop_policy()
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=headless)
            context = browser.new_context()
            try:
                normalized_cookies = normalize_playwright_cookies(cookies or [], target_url)
                if normalized_cookies:
                    context.add_cookies(normalized_cookies)

                page = context.new_page()
                page.set_default_timeout(min(timeout_ms, 10000))
                page.goto(target_url, wait_until="domcontentloaded", timeout=timeout_ms)
                try:
                    page.wait_for_load_state("networkidle", timeout=min(timeout_ms, 5000))
                except PlaywrightTimeoutError:
                    warnings.append("Page network did not become idle before context capture.")

                controls = self._visible_controls(page)
                return {
                    "target_url": target_url,
                    "title": self._safe_page_title(page),
                    "feature_type": self._normalize_feature_type(feature_type),
                    "feature_name": feature_name,
                    "controls": [self._control_context(item, index) for index, item in enumerate(controls, start=1)],
                    "warnings": warnings,
                }
            finally:
                context.close()
                browser.close()

    def record_with_plan(
        self,
        target_url: str,
        feature_type: str,
        feature_name: str,
        operation_steps: list[dict[str, Any]],
        cookies: list[dict[str, Any]] | None = None,
        instruction: str | None = None,
        timeout_sec: int = 120,
        headless: bool = True,
    ) -> dict[str, Any]:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright

        timeout_ms = max(3000, min(int(timeout_sec or 120) * 1000, 300000))
        deadline = time.time() + timeout_ms / 1000
        warnings: list[str] = []

        _ensure_windows_playwright_event_loop_policy()
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=headless)
            context = browser.new_context()
            try:
                normalized_cookies = normalize_playwright_cookies(cookies or [], target_url)
                if normalized_cookies:
                    context.add_cookies(normalized_cookies)

                page = context.new_page()
                page.set_default_timeout(min(timeout_ms, 10000))
                page.goto(target_url, wait_until="domcontentloaded", timeout=timeout_ms)
                try:
                    page.wait_for_load_state("networkidle", timeout=min(timeout_ms, 5000))
                except PlaywrightTimeoutError:
                    warnings.append("Page network did not become idle before AI operations.")

                return self._record_plan_on_loaded_page(
                    page,
                    target_url,
                    feature_type,
                    feature_name,
                    operation_steps,
                    [],
                    warnings,
                    instruction,
                    deadline,
                )
            finally:
                context.close()
                browser.close()

    def capture_and_record_with_plan(
        self,
        target_url: str,
        feature_type: str,
        feature_name: str,
        plan_builder: Callable[[dict[str, Any]], dict[str, Any]],
        cookies: list[dict[str, Any]] | None = None,
        instruction: str | None = None,
        timeout_sec: int = 120,
        headless: bool = True,
    ) -> dict[str, Any]:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright

        timeout_ms = max(3000, min(int(timeout_sec or 120) * 1000, 300000))
        deadline = time.time() + timeout_ms / 1000
        warnings: list[str] = []

        _ensure_windows_playwright_event_loop_policy()
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=headless)
            context = browser.new_context()
            try:
                normalized_cookies = normalize_playwright_cookies(cookies or [], target_url)
                if normalized_cookies:
                    context.add_cookies(normalized_cookies)

                page = context.new_page()
                page.set_default_timeout(min(timeout_ms, 10000))
                page.goto(target_url, wait_until="domcontentloaded", timeout=timeout_ms)
                try:
                    page.wait_for_load_state("networkidle", timeout=min(timeout_ms, 5000))
                except PlaywrightTimeoutError:
                    warnings.append("Page network did not become idle before context capture.")

                feature = self._normalize_feature_type(feature_type)
                capture = {
                    "target_url": target_url,
                    "title": self._safe_page_title(page),
                    "feature_type": feature,
                    "feature_name": feature_name,
                    "controls": [
                        self._control_context(item, index)
                        for index, item in enumerate(self._visible_controls(page), start=1)
                    ],
                    "warnings": list(warnings),
                }
                plan = plan_builder(capture)
                operation_steps = plan.get("operation_steps") if isinstance(plan.get("operation_steps"), list) else []
                element_steps = plan.get("element_steps") if isinstance(plan.get("element_steps"), list) else []
                recording = self._record_plan_on_loaded_page(
                    page,
                    target_url,
                    feature_type,
                    feature_name,
                    operation_steps,
                    element_steps,
                    warnings,
                    instruction,
                    deadline,
                )
                recording["capture"] = capture
                recording["ai_plan"] = plan
                return recording
            finally:
                context.close()
                browser.close()

    def _record_plan_on_loaded_page(
        self,
        page: Any,
        target_url: str,
        feature_type: str,
        feature_name: str,
        operation_steps: list[dict[str, Any]],
        element_steps: list[dict[str, Any]],
        warnings: list[str],
        instruction: str | None,
        deadline: float,
    ) -> dict[str, Any]:
        script_lines: list[str] = [
            "from playwright.sync_api import Page",
            "",
            "def test_ai_recorded(page: Page):",
            f"    page.goto({target_url!r})",
        ]
        operations: list[dict[str, Any]] = []
        executed_steps: list[dict[str, Any]] = []
        feature_screenshot: dict[str, Any] = {}
        feature = self._normalize_feature_type(feature_type)
        deferred_close_steps: list[dict[str, Any]] = []
        executable_steps: list[dict[str, Any]] = []
        for step in operation_steps:
            if time.time() >= deadline:
                warnings.append("AI operation timeout reached.")
                break
            if not self._is_allowed_plan_step_for_feature(step, feature):
                warnings.append(
                    f"AI step skipped because it does not belong to {feature} feature: "
                    f"{step.get('element_name') or step.get('name') or step.get('locator') or step}"
                )
                continue
            if feature == "delete" and self._step_mentions_cancel(step):
                deferred_close_steps.append(step)
                continue
            if feature in {"add", "edit", "query", "import"} and self._step_mentions_cancel(step):
                warnings.append("AI cancel/close step skipped; this feature should submit or query after element collection.")
                continue
            executable_steps.append(step)
            executed = self._execute_plan_step(page, step, feature, script_lines, operations, warnings)
            executed_steps.append(executed)
            self._short_wait(page, deadline)
            if not feature_screenshot and self._normalize_plan_action(step.get("action")) == "click" and executed.get("executed"):
                feature_screenshot = self._capture_feature_screenshot(page, feature, feature_name)
                if feature_screenshot.get("screenshot_error"):
                    warnings.append(f"Feature screenshot failed: {feature_screenshot['screenshot_error']}")

        matched_count = sum(1 for item in executed_steps if item.get("matched"))
        if executable_steps and matched_count == 0:
            raise RuntimeError("AI operation plan did not match any visible page controls.")

        if executable_steps:
            controls_for_save = self._prefer_dialog_controls(self._visible_controls(page))
            self._append_control_steps(page, feature, controls_for_save, script_lines, operations, element_steps)
            self._perform_safe_feature_actions(
                page,
                feature,
                controls_for_save,
                script_lines,
                operations,
                warnings,
                deadline,
            )

        closed_by_ai = False
        for step in deferred_close_steps:
            executed = self._execute_plan_step(page, step, feature, script_lines, operations, warnings)
            executed_steps.append(executed)
            closed_by_ai = closed_by_ai or bool(executed.get("executed"))
            self._short_wait(page, deadline)

        if not executable_steps and not closed_by_ai:
            controls = self._visible_controls(page)
            controls_for_save = self._prefer_dialog_controls(controls)
            self._append_control_steps(page, feature, controls_for_save, script_lines, operations, element_steps)
            self._perform_safe_feature_actions(
                page,
                feature,
                controls_for_save,
                script_lines,
                operations,
                warnings,
                deadline,
            )

        return {
            "script_text": "\n".join(script_lines) + "\n",
            "operations": operations,
            "executed_ai_steps": executed_steps,
            "warnings": warnings,
            "feature_screenshot": feature_screenshot,
            "screenshot_url": feature_screenshot.get("screenshot_url"),
            "screenshot_file": feature_screenshot.get("screenshot_file"),
            "screenshot_error": feature_screenshot.get("screenshot_error"),
            "target_url": target_url,
            "feature_type": feature,
            "feature_name": feature_name,
            "instruction": instruction,
        }

    def _capture_feature_screenshot(self, page: Any, feature_type: str, feature_name: str) -> dict[str, Any]:
        try:
            SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
            filename = self._feature_screenshot_filename(feature_type, feature_name)
            page.screenshot(path=str(SCREENSHOT_DIR / filename), full_page=True)
            return {
                "screenshot_file": filename,
                "screenshot_url": f"/api/v1/screenshots/{filename}",
            }
        except Exception as exc:  # noqa: BLE001 - screenshot failure should not stop element scanning.
            return {"screenshot_error": str(exc)}

    def _feature_screenshot_filename(self, feature_type: str, feature_name: str) -> str:
        raw_name = f"{feature_type}_{feature_name}".strip("_") or "web_function"
        safe_name = re.sub(r"[^A-Za-z0-9_-]+", "_", raw_name).strip("_")[:80] or "web_function"
        return f"ai_element_{safe_name}_{int(time.time() * 1000)}.png"

    def _execute_plan_step(
        self,
        page: Any,
        step: dict[str, Any],
        feature: str,
        script_lines: list[str],
        operations: list[dict[str, Any]],
        warnings: list[str],
    ) -> dict[str, Any]:
        controls = self._visible_controls(page)
        control = self._find_plan_control(controls, step, feature)
        action = self._normalize_plan_action(step.get("action"))
        value = str(step.get("value") or step.get("default_value") or "")
        result = {
            "step_id": step.get("step_id"),
            "element_name": step.get("element_name") or step.get("name"),
            "action": action,
            "value": value,
            "matched": bool(control),
        }
        if not control:
            warnings.append(f"AI step skipped, element not found: {result['element_name'] or step}")
            return result

        if action == "click":
            if feature == "delete" and (self._looks_like_submit(control) or self._looks_like_destructive(control)):
                warnings.append(f"AI step skipped for safety: {control.name}")
                result["executed"] = False
                result["locator"] = self._locator_text(control)
                return result
            if feature in {"add", "edit", "import"} and self._looks_like_submit(control):
                warnings.append(f"AI submit step deferred until after element collection: {control.name}")
                result["executed"] = False
                result["deferred"] = True
                result["locator"] = self._locator_text(control)
                return result
            if feature == "query" and self._looks_like_query(control):
                warnings.append(f"AI query step deferred until after element collection: {control.name}")
                result["executed"] = False
                result["deferred"] = True
                result["locator"] = self._locator_text(control)
                return result
            result["executed"] = self._click_control(
                page,
                control,
                script_lines,
                operations,
                str(step.get("purpose") or "AI planned click"),
            )
            result["locator"] = self._locator_text(control)
            return result

        if action == "record":
            script_action = self._record_action_for_control(control, feature)
            if not script_action:
                warnings.append(f"AI step skipped, unsupported record target: {control.name}")
                result["executed"] = False
                result["locator"] = self._locator_text(control)
                return result
            sample_value = value or self._sample_value(control)
            line = self._script_line(control, script_action, sample_value)
            self._append_script_line(script_lines, line)
            operations.append(
                {
                    "name": control.name,
                    "action": script_action,
                    "value": value,
                    "locator": self._locator_text(control),
                    "reason": step.get("purpose") or "AI planned record-only element",
                    "in_dialog": control.in_dialog,
                    "recorded_only": True,
                }
            )
            result["executed"] = False
            result["recorded_only"] = True
            result["locator"] = self._locator_text(control)
            return result

        script_action = "select_option" if action in {"select", "multi_select"} else action
        if script_action == "fill" and self._is_select_like_control(control):
            script_action = "select_option"
        if script_action not in {"fill", "select_option", "check", "click"}:
            warnings.append(f"AI step skipped, unsupported action: {action}")
            result["executed"] = False
            return result

        line = self._script_line(control, script_action, value or self._sample_value(control))
        self._append_script_line(script_lines, line)
        executed = self._apply_safe_control_action(
            page,
            control,
            script_action,
            value or self._sample_value(control),
            operations,
        )
        operations.append(
            {
                "name": control.name,
                "action": script_action,
                "value": value,
                "locator": self._locator_text(control),
                "reason": step.get("purpose") or "AI planned operation",
                "in_dialog": control.in_dialog,
            }
        )
        result["executed"] = executed
        result["locator"] = self._locator_text(control)
        return result

    def _safe_page_title(self, page: Any) -> str:
        try:
            return str(page.title() or "")
        except Exception:
            return ""

    def _open_feature_entry(
        self,
        page: Any,
        feature: str,
        script_lines: list[str],
        operations: list[dict[str, Any]],
        warnings: list[str],
    ) -> None:
        labels = self.FEATURE_LABELS.get(feature, ())
        controls = self._visible_controls(page)
        trigger = self._find_control(controls, labels, buttons_only=True)

        if not trigger:
            menu = self._find_control(controls, self.MENU_LABELS, buttons_only=True)
            if menu and self._click_control(page, menu, script_lines, operations, "打开更多操作"):
                self._short_wait(page)
                controls = self._visible_controls(page)
                trigger = self._find_control(controls, labels, buttons_only=True)

        if not trigger:
            warnings.append(f"未找到 {feature} 功能入口，已改为采集当前页面可见元素。")
            return

        self._click_control(page, trigger, script_lines, operations, f"进入{feature}功能")

    def _perform_safe_feature_actions(
        self,
        page: Any,
        feature: str,
        controls: list[ControlInfo],
        script_lines: list[str],
        operations: list[dict[str, Any]],
        warnings: list[str],
        deadline: float,
    ) -> None:
        if feature in {"add", "edit", "import"}:
            submit = self._find_submit_control(controls)
            if submit and time.time() < deadline:
                self._click_control(page, submit, script_lines, operations, "提交或保存功能表单")
            else:
                warnings.append("未找到保存/确定按钮，已完成元素采集但未提交。")
        elif feature == "delete":
            cancel = self._find_cancel_control(controls)
            if cancel:
                self._click_control(page, cancel, script_lines, operations, "取消业务变更", record_script=False)
            else:
                warnings.append("未找到取消/关闭按钮，为避免误删除，没有继续点击确认按钮。")
        elif feature == "query":
            query = self._find_query_control(controls)
            if query and time.time() < deadline:
                self._click_control(page, query, script_lines, operations, "执行查询")


