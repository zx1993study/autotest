from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from app.repositories.interfaces import ResourceRepository
from app.scheduler.jobs.case_execution_base import CaseExecutionBase
from app.utils.appium_executor import AppiumActionExecutor


SCREENSHOT_DIR = Path(__file__).resolve().parents[3] / "storage" / "screenshots"


class AppExecutionError(RuntimeError):
    def __init__(self, message: str, result: dict[str, Any]) -> None:
        super().__init__(message)
        self.result = result


class AppCaseExecutor(CaseExecutionBase):
    """Execute App and MiniApp test cases and persist execution records."""

    def __init__(self, repository: ResourceRepository, case_type: str = "APP") -> None:
        super().__init__(case_type.upper(), repository)

    def execute(self, case: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        started_at = time.perf_counter()
        steps = self._case_steps(case)
        config = self._appium_config(case, payload)
        try:
            result = self._run_app_steps(case, steps, config)
            status_text = "success"
            description = "App case execution passed"
            error = None
        except AppExecutionError as exc:
            result = exc.result
            status_text = "failed"
            description = str(exc)
            error = str(exc)
        except Exception as exc:  # noqa: BLE001 - execution records must capture runtime failures.
            result = {}
            status_text = "failed"
            description = str(exc)
            error = str(exc)

        return self.repository.create(
            "execution_records",
            {
                "name": f"APP 用例执行 - {case['name']}",
                "project_id": case.get("project_id") or payload.get("project_id"),
                "description": description,
                "status": status_text,
                "data": {
                    "case_id": case["id"],
                    "case_type": self.case_type,
                    "mode": payload.get("mode", "local_appium"),
                    "node_id": payload.get("node_id"),
                    "appium_config": self._safe_config(config),
                    "steps": steps,
                    "duration_ms": self.duration_ms(started_at),
                    "step_count": result.get("step_count", 0),
                    "screenshots": result.get("screenshots", []),
                    "screenshot_url": result.get("screenshot_url"),
                    "screenshot_file": result.get("screenshot_file"),
                    "screenshot_error": result.get("screenshot_error"),
                    "assertions": self.case_assertions(case),
                    "error": error,
                },
            },
        )

    def _run_app_steps(self, case: dict[str, Any], steps: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
        try:
            from appium import webdriver
            from appium.options.android import UiAutomator2Options
            from appium.options.ios import XCUITestOptions
        except ModuleNotFoundError as exc:
            raise RuntimeError("backend missing Appium dependency, run: pip install Appium-Python-Client") from exc

        server_url = str(config.get("server_url") or "http://127.0.0.1:4723").rstrip("/")
        capabilities = dict(config.get("capabilities") or {})
        platform = str(capabilities.get("platformName") or config.get("platform") or "Android")
        if platform.lower() == "ios":
            options = XCUITestOptions().load_capabilities(capabilities)
        else:
            options = UiAutomator2Options().load_capabilities(capabilities)

        driver = webdriver.Remote(server_url, options=options)
        self._switch_context(driver, config)
        result: dict[str, Any] = {"step_count": 0, "screenshots": []}
        screenshots: list[dict[str, Any]] = []
        executed_count = 0
        current_step: dict[str, Any] | None = None
        try:
            executor = AppiumActionExecutor(
                driver,
                default_timeout=self.to_int(config.get("implicit_wait_sec"), 10) or 10,
                platform=platform,
            )
            driver.implicitly_wait(self.to_int(config.get("implicit_wait_sec"), 10) or 10)
            for step in steps:
                current_step = step
                if self.is_truthy(step.get("skip", step.get("是否跳过"))):
                    continue
                executor.run_step(step)
                executed_count += 1
                wait_ms = self.to_int(step.get("wait_ms") or config.get("step_wait_ms"), 0) or 0
                if wait_ms > 0:
                    time.sleep(wait_ms / 1000)
                if self.is_truthy(step.get("take_screenshot", step.get("是否截图"))):
                    screenshots.append(self._capture_screenshot(driver, case, step))
            result.update({"step_count": executed_count, "screenshots": screenshots})
            result.update(self._last_screenshot(screenshots))
            return result
        except Exception as exc:  # noqa: BLE001 - keep screenshots with failed executions.
            if current_step:
                screenshots.append(self._capture_screenshot(driver, case, current_step, error=str(exc)))
            result.update({"step_count": executed_count, "screenshots": screenshots, "error": str(exc)})
            result.update(self._last_screenshot(screenshots))
            raise AppExecutionError(str(exc), result) from exc
        finally:
            driver.quit()

    def _appium_config(self, case: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        case_data = self.case_data(case)
        page = self._source_page(case)
        page_data = page.get("data") if page and isinstance(page.get("data"), dict) else {}
        request_config = payload.get("config") if isinstance(payload.get("config"), dict) else {}
        merged = {**page_data, **case_data, **request_config}
        platform = str(merged.get("platform") or "Android")
        capabilities = self._capabilities(merged, platform)
        return {
            "server_url": merged.get("appium_server_url") or merged.get("server_url") or "http://127.0.0.1:4723",
            "platform": platform,
            "capabilities": capabilities,
            "context": str(merged.get("context") or merged.get("webview_context") or "").strip(),
            "context_keyword": str(merged.get("context_keyword") or merged.get("miniapp_name") or "").strip(),
            "implicit_wait_sec": self.to_int(merged.get("implicit_wait_sec"), 10) or 10,
            "step_wait_ms": self.to_int(merged.get("step_wait_ms"), 0) or 0,
        }

    def _capabilities(self, data: dict[str, Any], platform: str) -> dict[str, Any]:
        raw = data.get("capabilities")
        capabilities = dict(raw) if isinstance(raw, dict) else {}
        capabilities.setdefault("platformName", platform)
        if platform.lower() == "ios":
            capabilities.setdefault("automationName", data.get("automation_name") or "XCUITest")
            if data.get("bundle_id"):
                capabilities.setdefault("bundleId", data.get("bundle_id"))
        else:
            capabilities.setdefault("automationName", data.get("automation_name") or "UiAutomator2")
            if data.get("package_name"):
                capabilities.setdefault("appPackage", data.get("package_name"))
            if data.get("activity"):
                capabilities.setdefault("appActivity", data.get("activity"))
        for source_key, capability_key in (
            ("device_name", "deviceName"),
            ("udid", "udid"),
            ("platform_version", "platformVersion"),
            ("no_reset", "noReset"),
            ("full_reset", "fullReset"),
            ("app_path", "app"),
            ("chrome_driver_executable", "chromedriverExecutable"),
            ("chrome_driver_port", "chromedriverPort"),
            ("system_port", "systemPort"),
        ):
            if data.get(source_key) not in (None, ""):
                capabilities.setdefault(capability_key, data.get(source_key))
        if self.case_type == "MINIAPP":
            capabilities.setdefault("autoWebview", bool(data.get("auto_webview", False)))
            chrome_options = data.get("chrome_options")
            if isinstance(chrome_options, dict):
                capabilities.setdefault("chromeOptions", chrome_options)
        return capabilities

    def _case_steps(self, case: dict[str, Any]) -> list[dict[str, Any]]:
        steps = case.get("steps") or self.case_data(case).get("steps", [])
        request = self.case_data(case).get("request")
        if not steps and isinstance(request, dict) and isinstance(request.get("steps"), list):
            steps = request["steps"]
        return self._ordered_steps(self._expand_steps(case, steps))

    def _expand_steps(self, case: dict[str, Any], steps: Any) -> list[dict[str, Any]]:
        if not isinstance(steps, list):
            return []
        by_name, by_id = self._elements_for_case(case)
        expanded: list[dict[str, Any]] = []
        for index, raw_step in enumerate(steps):
            if not isinstance(raw_step, dict):
                continue
            data = raw_step.get("data") if isinstance(raw_step.get("data"), dict) else {}
            element = self._match_element(raw_step, by_name, by_id)
            element_data = element.get("data") if element and isinstance(element.get("data"), dict) else {}
            merged: dict[str, Any] = {**element_data, **data}
            merged.update({key: value for key, value in raw_step.items() if key != "data"})
            if element:
                merged["element_id"] = element.get("id")
            merged["name"] = str(
                raw_step.get("元素名称") or raw_step.get("name") or (element or {}).get("name") or f"step-{index + 1}"
            )
            merged["action"] = self._step_action(raw_step, data, element_data)
            merged["value"] = self._step_value(raw_step, data, element_data)
            merged["skip"] = self.is_truthy(raw_step.get("是否跳过", raw_step.get("skip", data.get("skip"))))
            merged["take_screenshot"] = self.is_truthy(
                raw_step.get("是否截图", raw_step.get("take_screenshot", data.get("take_screenshot")))
            )
            merged["sort_order"] = self._step_order(raw_step, data, element_data, index)
            expanded.append(merged)
        return expanded

    def _elements_for_case(
        self,
        case: dict[str, Any],
    ) -> tuple[dict[str, dict[str, Any]], dict[int, dict[str, Any]]]:
        source_id = case.get("source_id")
        project_id = case.get("project_id")
        rows: list[dict[str, Any]] = []
        if source_id:
            rows, _ = self.repository.list(
                self._element_table(),
                project_id=int(project_id) if project_id else None,
                page_size=10000,
                data_filters={"page_id": source_id},
            )
        by_name: dict[str, dict[str, Any]] = {}
        by_id: dict[int, dict[str, Any]] = {}
        for row in rows:
            row_id = self.to_int(row.get("id"), None)
            if row_id is not None:
                by_id[row_id] = row
            for name in self._element_name_candidates(row):
                by_name.setdefault(name, row)
        return by_name, by_id

    def _source_page(self, case: dict[str, Any]) -> dict[str, Any] | None:
        source_id = self.to_int(case.get("source_id"), None)
        if source_id is None:
            return None
        return self.repository.get(self._page_table(), source_id)

    def _page_table(self) -> str:
        return "miniapp_pages" if self.case_type == "MINIAPP" else "app_pages"

    def _element_table(self) -> str:
        return "miniapp_elements" if self.case_type == "MINIAPP" else "app_elements"

    def _switch_context(self, driver: Any, config: dict[str, Any]) -> None:
        if self.case_type != "MINIAPP":
            return
        context = str(config.get("context") or "").strip()
        keyword = str(config.get("context_keyword") or "").strip()
        if not context and not keyword:
            return
        contexts = [str(item) for item in (getattr(driver, "contexts", []) or [])]
        target = ""
        if context:
            target = next((item for item in contexts if item == context), "")
        if not target and keyword:
            lower_keyword = keyword.lower()
            target = next((item for item in contexts if lower_keyword in item.lower()), "")
        if not target:
            target = next((item for item in contexts if item.upper().startswith("WEBVIEW")), "")
        if not target:
            raise RuntimeError(f"miniapp webview context not found, available contexts: {contexts}")
        driver.switch_to.context(target)

    def _match_element(
        self,
        step: dict[str, Any],
        by_name: dict[str, dict[str, Any]],
        by_id: dict[int, dict[str, Any]],
    ) -> dict[str, Any] | None:
        element_id = self.to_int(step.get("element_id"), None)
        if element_id is not None and element_id in by_id:
            return by_id[element_id]
        name = str(step.get("元素名称") or step.get("name") or "").strip()
        return by_name.get(name) if name else None

    def _element_name_candidates(self, element: dict[str, Any]) -> list[str]:
        data = element.get("data") if isinstance(element.get("data"), dict) else {}
        candidates = [element.get("name"), data.get("name"), data.get("text"), data.get("content_desc")]
        return [str(value).strip() for value in candidates if str(value or "").strip()]

    def _step_action(self, step: dict[str, Any], data: dict[str, Any], element_data: dict[str, Any]) -> str:
        action = step.get("交互类型") or step.get("action") or data.get("action") or element_data.get("action")
        if action:
            return str(action).lower()
        element_type = str(element_data.get("element_type") or data.get("element_type") or "").lower()
        return "input" if element_type == "input" else "tap"

    def _step_value(self, step: dict[str, Any], data: dict[str, Any], element_data: dict[str, Any]) -> Any:
        for source, key in (
            (step, "元素值"),
            (step, "value"),
            (step, "default_value"),
            (data, "value"),
            (data, "default_value"),
            (element_data, "default_value"),
            (element_data, "example"),
        ):
            if key in source:
                return source[key]
        return None

    def _step_order(
        self,
        step: dict[str, Any],
        data: dict[str, Any],
        element_data: dict[str, Any],
        index: int,
    ) -> int:
        for source, key in (
            (step, "步骤标识"),
            (step, "sort_order"),
            (step, "order"),
            (step, "index"),
            (data, "sort_order"),
            (data, "order"),
            (element_data, "sort_order"),
            (element_data, "order"),
        ):
            value = self.to_int(source.get(key), None)
            if value is not None:
                return value
        return index + 1

    def _ordered_steps(self, steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return sorted(steps, key=lambda step: (self.to_int(step.get("sort_order"), 0) or 0, self.to_int(step.get("element_id"), 0) or 0))

    def _capture_screenshot(
        self,
        driver: Any,
        case: dict[str, Any],
        step: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> dict[str, Any]:
        try:
            SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
            filename = self._screenshot_filename(case)
            path = SCREENSHOT_DIR / filename
            driver.save_screenshot(str(path))
            return {
                "step_order": (step or {}).get("sort_order"),
                "step_name": (step or {}).get("name"),
                "screenshot_file": filename,
                "screenshot_url": f"/api/v1/screenshots/{filename}",
                "error": error,
            }
        except Exception as exc:  # noqa: BLE001 - screenshot failure should not hide execution result.
            return {
                "step_order": (step or {}).get("sort_order") if step else None,
                "step_name": (step or {}).get("name") if step else None,
                "screenshot_error": str(exc),
                "error": error,
            }

    def _last_screenshot(self, screenshots: list[dict[str, Any]]) -> dict[str, Any]:
        for screenshot in reversed(screenshots):
            if screenshot.get("screenshot_url"):
                return {
                    "screenshot_url": screenshot.get("screenshot_url"),
                    "screenshot_file": screenshot.get("screenshot_file"),
                }
        errors = [item.get("screenshot_error") for item in screenshots if item.get("screenshot_error")]
        return {"screenshot_error": "; ".join(str(item) for item in errors)} if errors else {}

    def _screenshot_filename(self, case: dict[str, Any]) -> str:
        prefix = self._safe_file_stem(str(case.get("id") or case.get("name") or "app_case"))
        timestamp = int(time.time() * 1000)
        filename = f"{prefix}_{timestamp}.png"
        while (SCREENSHOT_DIR / filename).exists():
            timestamp += 1
            filename = f"{prefix}_{timestamp}.png"
        return filename

    def _safe_file_stem(self, value: str) -> str:
        safe = "".join(char if char.isalnum() or char in {"-", "_", "."} else "_" for char in value.strip())
        return safe.strip("._") or "app_case"

    def _safe_config(self, config: dict[str, Any]) -> dict[str, Any]:
        safe = dict(config)
        capabilities = dict(safe.get("capabilities") or {})
        for key in ("password", "token", "accessKey", "secret"):
            if key in capabilities:
                capabilities[key] = "***"
        safe["capabilities"] = capabilities
        return safe
