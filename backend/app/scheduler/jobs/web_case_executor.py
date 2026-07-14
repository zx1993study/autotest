from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from app.repositories.interfaces import ResourceRepository
from app.scheduler.jobs.case_execution_base import CaseExecutionBase
from app.services.project_auth_service import ProjectAuthService
from app.utils.cookie_utils import normalize_playwright_cookie, normalize_playwright_cookies
from app.utils.playwright_executor import PlaywrightActionExecutor


SCREENSHOT_DIR = Path(__file__).resolve().parents[3] / "storage" / "screenshots"


class WebExecutionError(RuntimeError):
    def __init__(self, message: str, result: dict[str, Any]) -> None:
        super().__init__(message)
        self.result = result


class WebCaseExecutor(CaseExecutionBase):
    """Execute Web test cases and persist execution records."""

    def __init__(self, repository: ResourceRepository) -> None:
        super().__init__("WEB", repository)

    def execute(self, case: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        payload = {**payload, "playwright_config": self.playwright_execution_config(payload)}
        started_at = time.perf_counter()
        steps = self._case_steps(case)
        try:
            result = self._run_async_web_steps(case, payload, steps)
            status_text = "success"
            description = "Web 用例执行通过"
            error = None
        except WebExecutionError as exc:
            result = exc.result
            status_text = "failed"
            description = str(exc)
            error = str(exc)
        except Exception as exc:  # noqa: BLE001 - execution records must capture runtime failures.
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
                "name": f"WEB 用例执行 - {case['name']}",
                "project_id": case.get("project_id") or payload.get("project_id"),
                "description": description,
                "status": status_text,
                "data": {
                    "case_id": case["id"],
                    "case_type": self.case_type,
                    "mode": payload.get("mode", "local_headed"),
                    "node_id": payload.get("node_id"),
                    "playwright_config": payload.get("playwright_config", {}),
                    "steps": steps,
                    "duration_ms": self.duration_ms(started_at),
                    "url": result.get("url"),
                    "step_count": result.get("step_count"),
                    "screenshots": result.get("screenshots", []),
                    "screenshot_url": result.get("screenshot_url"),
                    "screenshot_file": result.get("screenshot_file"),
                    "screenshot_error": result.get("screenshot_error"),
                    "cookies": result.get("cookies", []),
                    "auth_saved": auth_result,
                    "assertions": self.case_assertions(case),
                    "error": error,
                },
            },
        )

    def _run_async_web_steps(
        self,
        case: dict[str, Any],
        payload: dict[str, Any],
        steps: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if sys.platform.startswith("win"):
            policy = asyncio.WindowsProactorEventLoopPolicy()
            loop = policy.new_event_loop()
            try:
                return loop.run_until_complete(self._run_web_steps(case, payload, steps))
            finally:
                loop.close()
        return asyncio.run(self._run_web_steps(case, payload, steps))

    def playwright_execution_config(self, payload: dict[str, Any]) -> dict[str, Any]:
        rows, _ = self.repository.list("system_dictionaries", page_size=10000)
        dictionary_config: dict[str, Any] = {}
        for row in rows:
            if row.get("status") != "active":
                continue
            data = row.get("data") or {}
            if data.get("dict_type") != "playwright_execution":
                continue
            key = str(data.get("dict_key") or "").strip()
            if key:
                dictionary_config[key] = data.get("dict_value")

        request_config = payload.get("config") if isinstance(payload.get("config"), dict) else {}
        merged = {**dictionary_config, **request_config}
        mode = str(merged.get("run_mode") or payload.get("mode") or "headed").lower()
        return {
            "run_mode": mode,
            "headless": mode in {"headless", "local_headless", "true", "1", "yes", "无头"},
            "slow_mo_ms": self.to_int(merged.get("slow_mo_ms"), 0) or 0,
            "step_wait_ms": self.to_int(merged.get("step_wait_ms"), 0) or 0,
            "action_timeout_ms": self.to_int(merged.get("action_timeout_ms"), 5000) or 5000,
            "screenshot": str(merged.get("screenshot") or "full_page"),
        }

    async def _run_web_steps(
        self,
        case: dict[str, Any],
        payload: dict[str, Any],
        steps: list[dict[str, Any]],
    ) -> dict[str, Any]:
        try:
            from playwright.async_api import async_playwright
        except ModuleNotFoundError as exc:
            raise RuntimeError("后端未安装 playwright，请安装后再执行 Web 用例") from exc

        project_id = case.get("project_id") or payload.get("project_id")
        target_url = self._web_case_url(case, project_id)
        auth_id = self._web_auth_id(case, payload)
        config = payload.get("playwright_config") if isinstance(payload.get("playwright_config"), dict) else {}
        headless = bool(config.get("headless", payload.get("mode") != "local_headed"))
        slow_mo_ms = self.to_int(config.get("slow_mo_ms"), 0) or 0
        action_timeout_ms = self.to_int(config.get("action_timeout_ms"), 5000) or 5000
        step_wait_ms = self.to_int(config.get("step_wait_ms"), 0) or 0
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=headless, slow_mo=slow_mo_ms)
            page = await browser.new_page()
            page.set_default_timeout(action_timeout_ms)
            result: dict[str, Any] = {"url": "", "step_count": 0, "screenshots": []}
            executed_count = 0
            screenshots: list[dict[str, Any]] = []
            current_step: dict[str, Any] | None = None
            try:
                await self._load_auth_cookies(page, auth_id, target_url)
                if target_url:
                    await page.goto(target_url)
                executor = PlaywrightActionExecutor(page, default_timeout=action_timeout_ms)
                for step in steps:
                    current_step = step
                    if self.is_truthy(step.get("skip", step.get("是否跳过"))):
                        continue
                    await executor.run_step(step)
                    executed_count += 1
                    if step_wait_ms > 0:
                        await page.wait_for_timeout(step_wait_ms)
                    if self.is_truthy(step.get("take_screenshot", step.get("是否截图"))):
                        screenshots.append(await self._capture_web_screenshot(page, case, config, step))
                cookies = await page.context.cookies()
                result.update(
                    {
                        "url": page.url,
                        "step_count": executed_count,
                        "cookies": cookies,
                        "screenshots": screenshots,
                    }
                )
                result.update(self._last_screenshot(screenshots))
                return result
            except Exception as exc:  # noqa: BLE001 - keep screenshot with failed executions.
                if current_step and self.is_truthy(current_step.get("take_screenshot", current_step.get("是否截图"))):
                    screenshots.append(await self._capture_web_screenshot(page, case, config, current_step, error=str(exc)))
                result.update(
                    {
                        "url": page.url,
                        "step_count": executed_count,
                        "error": str(exc),
                        "screenshots": screenshots,
                    }
                )
                result.update(self._last_screenshot(screenshots))
                if not headless:
                    await page.wait_for_timeout(max(step_wait_ms, 3000))
                raise WebExecutionError(str(exc), result) from exc
            finally:
                await browser.close()

    async def _capture_web_screenshot(
        self,
        page: Any,
        case: dict[str, Any],
        config: dict[str, Any],
        step: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> dict[str, Any]:
        step_order = self.to_int((step or {}).get("sort_order"), None)
        step_name = str((step or {}).get("name") or (step or {}).get("元素名称") or "")
        try:
            SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
            filename = self._screenshot_filename(case)
            path = SCREENSHOT_DIR / filename
            await page.screenshot(
                path=str(path),
                full_page=str(config.get("screenshot", "full_page")) != "viewport",
            )
            return {
                "step_order": step_order,
                "step_name": step_name,
                "screenshot_file": filename,
                "screenshot_url": f"/api/v1/screenshots/{filename}",
                "error": error,
            }
        except Exception as exc:  # noqa: BLE001 - screenshot failure should not hide execution result.
            return {
                "step_order": step_order,
                "step_name": step_name,
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
        prefix = self._safe_file_stem(self._case_identifier(case))
        timestamp = int(time.time() * 1000)
        filename = f"{prefix}_{timestamp}.png"
        while (SCREENSHOT_DIR / filename).exists():
            timestamp += 1
            filename = f"{prefix}_{timestamp}.png"
        return filename

    def _case_identifier(self, case: dict[str, Any]) -> str:
        case_data = self.case_data(case)
        for value in (
            case.get("identifier"),
            case.get("case_key"),
            case.get("case_no"),
            case_data.get("identifier"),
            case_data.get("case_key"),
            case_data.get("case_no"),
            case.get("id"),
        ):
            if value not in (None, ""):
                return str(value)
        return "case"

    def _safe_file_stem(self, value: str) -> str:
        safe = "".join(char if char.isalnum() or char in {"-", "_", "."} else "_" for char in value.strip())
        return safe.strip("._") or "case"

    def _case_steps(self, case: dict[str, Any]) -> list[dict[str, Any]]:
        steps = case.get("steps") or self.case_data(case).get("steps", [])
        request = self.case_data(case).get("request")
        if not steps and isinstance(request, dict) and isinstance(request.get("steps"), list):
            steps = request["steps"]
        return self._ordered_web_steps(self._expand_web_steps(case, steps))

    def _expand_web_steps(self, case: dict[str, Any], steps: Any) -> list[dict[str, Any]]:
        if not isinstance(steps, list):
            return []

        by_name, by_id = self._web_elements_for_case(case)
        expanded: list[dict[str, Any]] = []
        for index, raw_step in enumerate(steps):
            if not isinstance(raw_step, dict):
                continue
            data = raw_step.get("data") if isinstance(raw_step.get("data"), dict) else {}
            element = self._match_web_element(raw_step, by_name, by_id)
            element_data = element.get("data") if element and isinstance(element.get("data"), dict) else {}

            merged: dict[str, Any] = {**element_data, **data}
            merged.update({key: value for key, value in raw_step.items() if key != "data"})
            if element:
                merged["element_id"] = element.get("id")

            element_name = raw_step.get("元素名称") or raw_step.get("name") or (element or {}).get("name")
            if element_name:
                merged["name"] = str(element_name)
            merged["action"] = self._step_action(raw_step, data, element_data)
            merged["value"] = self._step_value(raw_step, data, element_data)
            merged["skip"] = self.is_truthy(raw_step.get("是否跳过", raw_step.get("skip", data.get("skip"))))
            merged["take_screenshot"] = self.is_truthy(
                raw_step.get("是否截图", raw_step.get("take_screenshot", data.get("take_screenshot")))
            )
            merged["sort_order"] = self._step_order(raw_step, data, element_data, index)
            expanded.append(merged)
        return expanded

    def _web_elements_for_case(
        self,
        case: dict[str, Any],
    ) -> tuple[dict[str, dict[str, Any]], dict[int, dict[str, Any]]]:
        source_id = case.get("source_id")
        project_id = case.get("project_id")
        rows: list[dict[str, Any]] = []
        if source_id:
            rows, _ = self.repository.list(
                "web_elements",
                project_id=int(project_id) if project_id else None,
                page_size=10000,
                data_filters={"page_id": source_id},
            )
        if not rows and project_id:
            all_rows, _ = self.repository.list("web_elements", project_id=int(project_id), page_size=10000)
            rows = [
                row
                for row in all_rows
                if str((row.get("data") or {}).get("page_id") or "") == str(source_id or "")
            ]

        by_name: dict[str, dict[str, Any]] = {}
        by_id: dict[int, dict[str, Any]] = {}
        for row in rows:
            row_id = self.to_int(row.get("id"), None)
            if row_id is not None:
                by_id[row_id] = row
            for name in self._element_name_candidates(row):
                by_name.setdefault(name, row)
        return by_name, by_id

    def _element_name_candidates(self, element: dict[str, Any]) -> list[str]:
        data = element.get("data") if isinstance(element.get("data"), dict) else {}
        candidates = [
            element.get("name"),
            data.get("name"),
            data.get("element_name"),
            data.get("label"),
            data.get("role_name"),
        ]
        return [str(value).strip() for value in candidates if str(value or "").strip()]

    def _match_web_element(
        self,
        step: dict[str, Any],
        by_name: dict[str, dict[str, Any]],
        by_id: dict[int, dict[str, Any]],
    ) -> dict[str, Any] | None:
        element_id = self.to_int(step.get("element_id"), None)
        if element_id is not None and element_id in by_id:
            return by_id[element_id]
        name = str(step.get("元素名称") or step.get("name") or "").strip()
        if name:
            return by_name.get(name)
        return None

    def _step_action(
        self,
        step: dict[str, Any],
        data: dict[str, Any],
        element_data: dict[str, Any],
    ) -> str:
        action = step.get("交互类型") or step.get("action") or data.get("action") or element_data.get("action")
        if action:
            return str(action).lower()
        element_type = str(
            element_data.get("element_type") or element_data.get("type") or data.get("element_type") or ""
        ).lower()
        if element_type in {"input", "textarea", "text"}:
            return "fill"
        if element_type in {"select", "dropdown"}:
            return "select"
        if element_type == "multi_select":
            return "multi_select"
        if element_type in {"checkbox", "radio"}:
            return "check"
        return "click"

    def _step_value(
        self,
        step: dict[str, Any],
        data: dict[str, Any],
        element_data: dict[str, Any],
    ) -> Any:
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
            (data, "index"),
            (element_data, "sort_order"),
            (element_data, "order"),
            (element_data, "index"),
        ):
            value = self.to_int(source.get(key), None)
            if value is not None:
                return value
        return index + 1

    def _ordered_web_steps(self, steps: Any) -> list[dict[str, Any]]:
        if not isinstance(steps, list):
            return []
        items = [step for step in steps if isinstance(step, dict)]
        if not items:
            return []
        if any(self._has_step_order(step) for step in items):
            return sorted(items, key=self._step_sort_key)
        if all(self.to_int(step.get("element_id")) is not None for step in items):
            return sorted(items, key=lambda step: self.to_int(step.get("element_id"), 0) or 0)
        return items

    def _has_step_order(self, step: dict[str, Any]) -> bool:
        data = step.get("data") if isinstance(step.get("data"), dict) else {}
        return any(key in step for key in ("步骤标识", "sort_order", "order", "index")) or any(
            key in data for key in ("步骤标识", "sort_order", "order", "index")
        )

    def _step_sort_key(self, step: dict[str, Any]) -> tuple[int, int]:
        data = step.get("data") if isinstance(step.get("data"), dict) else {}
        for key in ("步骤标识", "sort_order", "order", "index"):
            value = self.to_int(step.get(key), None)
            if value is not None:
                return value, self.to_int(step.get("element_id"), 0) or 0
            value = self.to_int(data.get(key), None)
            if value is not None:
                return value, self.to_int(step.get("element_id"), 0) or 0
        return 0, self.to_int(step.get("element_id"), 0) or 0

    def _web_case_url(self, case: dict[str, Any], project_id: Any) -> str:
        case_data = self.case_data(case)
        request = case_data.get("request") if isinstance(case_data.get("request"), dict) else {}
        if case_data.get("url"):
            return str(case_data["url"])
        if request.get("url"):
            return str(request["url"])
        page = self.repository.get("web_pages", int(case.get("source_id"))) if case.get("source_id") else None
        page_data = page.get("data") if page else {}
        url = str((page_data or {}).get("url") or "")
        if url.startswith("http://") or url.startswith("https://"):
            return url
        base_url = self.project_base_url(project_id)
        if base_url and url:
            return self.join_url(base_url, url)
        return base_url

    def _web_auth_id(self, case: dict[str, Any], payload: dict[str, Any]) -> Any:
        if self.is_truthy(payload.get("skip_auth")):
            return None
        if payload.get("auth_id"):
            return payload.get("auth_id")
        case_data = self.case_data(case)
        if case_data.get("auth_id"):
            return case_data.get("auth_id")
        request = case_data.get("request") if isinstance(case_data.get("request"), dict) else {}
        if request.get("auth_id"):
            return request.get("auth_id")
        page = self._source_page(case)
        page_data = page.get("data") if page else {}
        return (page_data or {}).get("auth_id") if isinstance(page_data, dict) else None

    async def _load_auth_cookies(self, page: Any, auth_id: Any, target_url: str) -> None:
        cookies = ProjectAuthService(self.repository).web_cookies(auth_id)
        if not cookies:
            return
        normalized = normalize_playwright_cookies(cookies, target_url)
        if normalized:
            await page.context.add_cookies(normalized)

    def _normalize_cookie(self, cookie: dict[str, Any], target_url: str) -> dict[str, Any]:
        return normalize_playwright_cookie(cookie, target_url)

    def _is_login_feature(self, case: dict[str, Any]) -> bool:
        page = self._source_page(case)
        page_data = page.get("data") if page else {}
        case_data = self.case_data(case)
        request = case_data.get("request") if isinstance(case_data.get("request"), dict) else {}
        markers = [
            page_data.get("feature_type") if isinstance(page_data, dict) else None,
            page.get("name") if page else None,
            case.get("name"),
            case_data.get("feature_type"),
            request.get("feature_type") if isinstance(request, dict) else None,
        ]
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
        token_name = f"{username}-web"
        target_auth_id = self.to_int(payload.get("refresh_auth_id"), None)
        return ProjectAuthService(self.repository).save_web_cookie_auth(
            case=case,
            cookies=cookies,
            auth_name=token_name,
            metadata={
                "url": result.get("url"),
                "username": username,
                "target_auth_id": target_auth_id,
                "preserve_existing_name": bool(target_auth_id),
            },
            refresh_strategy="on_login_success",
            description="Web 登录成功后自动保存 Cookie",
            stable_filename=True,
        )

    def _login_username(self, steps: list[dict[str, Any]]) -> str:
        for step in steps:
            if str(step.get("action") or "").lower() != "fill":
                continue
            text = " ".join(
                str(step.get(key) or "")
                for key in ("name", "locator", "locator_args", "role_name", "element_type")
            ).lower()
            if any(marker in text for marker in ["username", "user name", "account", "phone", "mobile", "手机号", "账号", "账户", "用户名"]):
                value = step.get("value", step.get("default_value"))
                if value not in (None, ""):
                    return self._safe_auth_name(str(value))

        for step in steps:
            if str(step.get("action") or "").lower() == "fill":
                value = step.get("value", step.get("default_value"))
                if value not in (None, ""):
                    return self._safe_auth_name(str(value))
        return ""

    def _safe_auth_name(self, value: str) -> str:
        normalized = "".join(char if char.isalnum() or char in {"-", "_", "."} else "_" for char in value.strip())
        return normalized.strip("._") or "unknown"

    def _source_page(self, case: dict[str, Any]) -> dict[str, Any] | None:
        if not case.get("source_id"):
            return None
        return self.repository.get("web_pages", int(case["source_id"]))
