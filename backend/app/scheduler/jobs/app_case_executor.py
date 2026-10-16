from __future__ import annotations

import base64
import subprocess
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen
from web_automation.dynamic_values import prepare_dynamic_execution

from app.repositories.interfaces import ResourceRepository
from app.scheduler.jobs.case_execution_base import CaseExecutionBase
from app.utils.appium_executor import AppiumActionExecutor


from app.core.storage import storage_path

SCREENSHOT_DIR = storage_path("screenshots")
RECORDING_DIR = storage_path("app-recordings")
DEFAULT_APPIUM_SERVER_URL = "http://127.0.0.1:4723"


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
        steps: list[dict[str, Any]] = []
        config: dict[str, Any] = {}
        preflight: dict[str, Any] = {}
        try:
            original_case = case
            case, payload, dynamic = prepare_dynamic_execution(case, payload)
            steps = dynamic.resolve(self._case_steps(original_case), "$.steps")
            case["_dynamic_values"] = dynamic.snapshot()
            config = self._appium_config(case, payload)
            preflight = self._preflight_checks(config)
            if self._script_path(case):
                result = self._run_python_script(case, config)
            else:
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

        device = config.get("device") if isinstance(config.get("device"), dict) else {}
        device_data = device.get("data") if isinstance(device.get("data"), dict) else {}
        device_name = str(device.get("name") or device_data.get("device_name") or device_data.get("udid") or "").strip()
        return self.repository.create(
            "execution_records",
            {
                "name": f"APP 用例执行 - {case['name']}{f' - {device_name}' if device_name else ''}",
                "project_id": case.get("project_id") or payload.get("project_id"),
                "description": description,
                "status": status_text,
                "data": {
                    "case_id": case["id"],
                    "case_type": self.case_type,
                    "mode": payload.get("mode", "local_appium"),
                    "node_id": payload.get("node_id"),
                    "device_id": config.get("device_id"),
                    "device_name": device_name or None,
                    "device_platform": device_data.get("platform"),
                    "device_form_factor": device_data.get("device_form_factor"),
                    "preflight": preflight,
                    "appium_config": self._safe_config(config),
                    "steps": steps,
                    "step_timeline": result.get("step_timeline", []),
                    "duration_ms": self.duration_ms(started_at),
                    "step_count": result.get("step_count", 0),
                    "screenshots": result.get("screenshots", []),
                    "screenshot_url": result.get("screenshot_url"),
                    "screenshot_file": result.get("screenshot_file"),
                    "screenshot_error": result.get("screenshot_error"),
                    "video_file": result.get("video_file"),
                    "video_url": result.get("video_url"),
                    "video_error": result.get("video_error"),
                    "record_video": config.get("record_video"),
                    "assertions": self.case_assertions(case),
                    "dynamic_values": case.get("_dynamic_values", {}),
                    "input_snapshot": self.case_data(case).get("input_info", {}),
                    "error": error,
                },
            },
        )

    def _run_python_script(self, case: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
        case_data = self.case_data(case)
        script_path = self._script_path(case)
        if not script_path:
            raise RuntimeError("python script execution requires data.script_path")
        script_file = Path(script_path)
        if not script_file.exists():
            raise RuntimeError(f"python script not found: {script_path}")
        python_path = str(case_data.get("script_python") or sys.executable)
        command = [python_path, str(script_file)]
        command.extend(self._script_cli_args(case_data, config))
        timeout = self.to_int(case_data.get("script_timeout_sec"), 180) or 180
        started_at = time.perf_counter()
        step_record = {
            "index": 1,
            "sort_order": 1,
            "name": case_data.get("script_step_name") or script_file.name,
            "action": "python_script",
            "started_at": datetime.now().isoformat(timespec="seconds"),
        }
        try:
            completed = subprocess.run(
                command,
                cwd=str(script_file.parent),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            step_record.update({"status": "failed", "error": f"script timeout after {timeout}s"})
            result = {
                "step_count": 0,
                "step_timeline": [step_record],
                "screenshots": [],
                "error": step_record["error"],
                "stdout": exc.stdout or "",
                "stderr": exc.stderr or "",
            }
            raise AppExecutionError(str(step_record["error"]), result) from exc
        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
        step_record["duration_ms"] = self.duration_ms(started_at)
        step_record["stdout"] = stdout[-4000:]
        if stderr:
            step_record["stderr"] = stderr[-4000:]
        if completed.returncode != 0:
            message = stderr.strip() or stdout.strip() or f"script exited with {completed.returncode}"
            step_record.update({"status": "failed", "error": message[-1000:]})
            result = {
                "step_count": 0,
                "step_timeline": [step_record],
                "screenshots": [],
                "error": message,
                "stdout": stdout,
                "stderr": stderr,
            }
            raise AppExecutionError(message, result)
        step_record["status"] = "success"
        return {
            "step_count": 1,
            "step_timeline": [step_record],
            "screenshots": [],
            "stdout": stdout,
            "stderr": stderr,
        }

    def _script_path(self, case: dict[str, Any]) -> str:
        data = self.case_data(case)
        if str(data.get("execution_mode") or "").lower() == "python_script":
            return str(data.get("script_path") or "").strip()
        return str(data.get("script_path") or "").strip()

    def _script_cli_args(self, case_data: dict[str, Any], config: dict[str, Any]) -> list[str]:
        args: list[str] = []
        capabilities = config.get("capabilities") if isinstance(config.get("capabilities"), dict) else {}
        script_args = case_data.get("script_args") if isinstance(case_data.get("script_args"), dict) else {}
        wda_url = self._first_text(script_args.get("wda_url"), capabilities.get("webDriverAgentUrl"), case_data.get("wda_url"))
        bundle_id = self._first_text(script_args.get("bundle_id"), capabilities.get("bundleId"), case_data.get("bundle_id"))
        if wda_url:
            args.extend(["--wda-url", wda_url])
        if bundle_id:
            args.extend(["--bundle-id", bundle_id])
        input_info = case_data.get("input_info") if isinstance(case_data.get("input_info"), dict) else {}
        arg_map = case_data.get("script_arg_map") if isinstance(case_data.get("script_arg_map"), dict) else {}
        for key, flag in arg_map.items():
            value = self._script_input_value(input_info.get(str(key)), script_args.get(str(key)))
            if value in (None, ""):
                continue
            args.extend([str(flag), str(value)])
        for key, value in script_args.items():
            if key in {"wda_url", "bundle_id"} or key in arg_map:
                continue
            if isinstance(value, bool):
                if value:
                    args.append(f"--{str(key).replace('_', '-')}")
                continue
            if value not in (None, ""):
                args.extend([f"--{str(key).replace('_', '-')}", str(value)])
        return args

    def _script_input_value(self, item: Any, fallback: Any = None) -> Any:
        if isinstance(item, dict):
            if item.get("value") not in (None, ""):
                return item.get("value")
            if item.get("default") not in (None, ""):
                return item.get("default")
        return fallback

    def _first_text(self, *values: Any) -> str:
        for value in values:
            text = str(value or "").strip()
            if text:
                return text
        return ""

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
        result: dict[str, Any] = {"step_count": 0, "screenshots": [], "step_timeline": []}
        screenshots: list[dict[str, Any]] = []
        step_timeline: list[dict[str, Any]] = []
        executed_count = 0
        recording_state = self._start_screen_recording(driver, config)
        try:
            executor = AppiumActionExecutor(
                driver,
                default_timeout=self.to_int(config.get("implicit_wait_sec"), 10) or 10,
                platform=platform,
            )
            driver.implicitly_wait(self.to_int(config.get("implicit_wait_sec"), 10) or 10)
            for index, step in enumerate(steps, start=1):
                step_record = self._step_record(step, index)
                step_started = time.perf_counter()
                step_timeline.append(step_record)
                try:
                    if self.is_truthy(step.get("skip", step.get("是否跳过"))):
                        step_record["status"] = "skipped"
                        continue
                    executor.run_step(step)
                    executed_count += 1
                    wait_ms = self.to_int(step.get("wait_ms") or config.get("step_wait_ms"), 0) or 0
                    if wait_ms > 0:
                        time.sleep(wait_ms / 1000)
                    if self.is_truthy(step.get("take_screenshot", step.get("是否截图"))):
                        screenshot = self._capture_screenshot(driver, case, step)
                        screenshots.append(screenshot)
                        step_record.update(self._screenshot_step_meta(screenshot))
                    step_record["status"] = "success"
                except Exception as exc:  # noqa: BLE001 - failed step details belong in the execution record.
                    step_record["status"] = "failed"
                    step_record["error"] = str(exc)
                    screenshot = self._capture_screenshot(driver, case, step, error=str(exc))
                    screenshots.append(screenshot)
                    step_record.update(self._screenshot_step_meta(screenshot))
                    result.update(
                        {
                            "step_count": executed_count,
                            "screenshots": screenshots,
                            "step_timeline": step_timeline,
                            "error": str(exc),
                        }
                    )
                    result.update(self._last_screenshot(screenshots))
                    raise AppExecutionError(str(exc), result) from exc
                finally:
                    step_record["duration_ms"] = self.duration_ms(step_started)
            result.update({"step_count": executed_count, "screenshots": screenshots})
            result["step_timeline"] = step_timeline
            result.update(self._last_screenshot(screenshots))
            return result
        except Exception as exc:  # noqa: BLE001 - keep screenshots with failed executions.
            result.update({"step_count": executed_count, "screenshots": screenshots, "step_timeline": step_timeline, "error": str(exc)})
            result.update(self._last_screenshot(screenshots))
            if isinstance(exc, AppExecutionError):
                raise
            raise AppExecutionError(str(exc), result) from exc
        finally:
            result.update(self._stop_screen_recording(driver, case, recording_state))
            driver.quit()

    def _appium_config(self, case: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        case_data = self.case_data(case)
        page = self._source_page(case)
        page_data = page.get("data") if page and isinstance(page.get("data"), dict) else {}
        request_config = payload.get("config") if isinstance(payload.get("config"), dict) else {}
        device = request_config.get("device") if isinstance(request_config.get("device"), dict) else {}
        device_data = device.get("data") if isinstance(device.get("data"), dict) else {}
        entry_data = self._entry_data(page_data, case_data, request_config)
        merged = {**entry_data, **device_data, **page_data, **case_data, **request_config}
        merged["capabilities"] = self._merged_capabilities(entry_data, device_data, page_data, case_data, request_config)
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
            "device_id": request_config.get("device_id"),
            "device": device,
            "record_video": self.is_truthy(merged.get("record_video", True)),
            "health_check": self.is_truthy(merged.get("health_check", True)),
        }

    def _entry_data(self, *sources: dict[str, Any]) -> dict[str, Any]:
        entry_id = None
        for source in sources:
            entry_id = self.to_int(source.get("entry_id"), None)
            if entry_id is not None:
                break
        if entry_id is None:
            return {}
        entry = self.repository.get("app_entries", entry_id)
        data = entry.get("data") if entry and isinstance(entry.get("data"), dict) else {}
        return data if isinstance(data, dict) else {}

    def _merged_capabilities(self, *sources: dict[str, Any]) -> dict[str, Any]:
        capabilities: dict[str, Any] = {}
        for source in sources:
            raw = source.get("capabilities")
            if isinstance(raw, dict):
                capabilities.update(raw)
        return capabilities

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
            ("wda_local_port", "wdaLocalPort"),
            ("wda_url", "webDriverAgentUrl"),
            ("wda_remote_port", "wdaRemotePort"),
            ("wda_bundle_id", "updatedWDABundleId"),
            ("use_preinstalled_wda", "usePreinstalledWDA"),
            ("use_new_wda", "useNewWDA"),
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
        if self.case_type != "MINIAPP":
            return {}, {}
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
        if self.case_type != "MINIAPP":
            return None
        source_id = self.to_int(case.get("source_id"), None)
        if source_id is None:
            return None
        return self.repository.get("miniapp_pages", source_id)

    def _element_table(self) -> str:
        return "miniapp_elements"

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

    def _preflight_checks(self, config: dict[str, Any]) -> dict[str, Any]:
        if not self.is_truthy(config.get("health_check", True)):
            return {"enabled": False, "checks": []}
        checks: list[dict[str, Any]] = []
        server_url = str(config.get("server_url") or DEFAULT_APPIUM_SERVER_URL).rstrip("/")
        checks.append(self._http_status_check("appium_server", urljoin(f"{server_url}/", "status")))
        device = config.get("device") if isinstance(config.get("device"), dict) else {}
        data = device.get("data") if isinstance(device.get("data"), dict) else {}
        if data:
            checks.append(
                {
                    "name": "device_pool_status",
                    "ok": str(data.get("connection_status") or "").lower() != "offline",
                    "status": data.get("connection_status") or "unknown",
                    "device_id": config.get("device_id"),
                }
            )
            wda_url = data.get("wda_url")
            if str(data.get("platform") or "").lower() == "ios" and wda_url:
                checks.append(self._http_status_check("wda", urljoin(f"{str(wda_url).rstrip('/')}/", "status")))
        return {
            "enabled": True,
            "ok": all(check.get("ok") for check in checks) if checks else True,
            "checks": checks,
        }

    def _http_status_check(self, name: str, status_url: str) -> dict[str, Any]:
        try:
            request = Request(status_url, headers={"Accept": "application/json"})
            with urlopen(request, timeout=3) as response:  # noqa: S310 - user-configured automation endpoint.
                raw = response.read().decode("utf-8", errors="ignore")
            return {"name": name, "ok": True, "url": status_url, "status_code": response.status, "preview": raw[:240]}
        except (OSError, URLError) as exc:
            return {"name": name, "ok": False, "url": status_url, "error": str(exc)}

    def _step_record(self, step: dict[str, Any], index: int) -> dict[str, Any]:
        return {
            "index": index,
            "sort_order": step.get("sort_order"),
            "name": step.get("name") or f"step-{index}",
            "action": step.get("action"),
            "started_at": datetime.now().isoformat(timespec="seconds"),
        }

    def _screenshot_step_meta(self, screenshot: dict[str, Any]) -> dict[str, Any]:
        return {
            key: screenshot[key]
            for key in ("screenshot_file", "screenshot_url", "screenshot_error")
            if screenshot.get(key)
        }

    def _start_screen_recording(self, driver: Any, config: dict[str, Any]) -> dict[str, Any]:
        if not self.is_truthy(config.get("record_video", False)):
            return {"enabled": False}
        if not hasattr(driver, "start_recording_screen"):
            return {"enabled": True, "started": False, "error": "driver does not support screen recording"}
        try:
            driver.start_recording_screen()
            return {"enabled": True, "started": True, "started_at": datetime.now().isoformat(timespec="seconds")}
        except Exception as exc:  # noqa: BLE001 - recording failure should not block functional execution.
            return {"enabled": True, "started": False, "error": str(exc)}

    def _stop_screen_recording(self, driver: Any, case: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
        if not state.get("started"):
            return {"video_error": state.get("error")} if state.get("error") else {}
        try:
            raw = driver.stop_recording_screen()
            if not raw:
                return {"video_error": "screen recording returned empty payload"}
            RECORDING_DIR.mkdir(parents=True, exist_ok=True)
            filename = self._recording_filename(case)
            path = RECORDING_DIR / filename
            path.write_bytes(base64.b64decode(raw))
            return {
                "video_file": filename,
                "video_url": f"/api/v1/app-recordings/{filename}",
                "recording_started_at": state.get("started_at"),
                "recording_finished_at": datetime.now().isoformat(timespec="seconds"),
            }
        except Exception as exc:  # noqa: BLE001 - preserve execution result even when video write fails.
            return {"video_error": str(exc)}

    def _recording_filename(self, case: dict[str, Any]) -> str:
        prefix = self._safe_file_stem(str(case.get("id") or case.get("name") or "app_case"))
        return f"{prefix}_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}.mp4"

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
