from __future__ import annotations

import asyncio
import importlib.util
import re
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

from app.repositories.interfaces import ResourceRepository
from app.scheduler.jobs.case_execution_jobs import run_case_execution_job
from app.services.project_auth_service import ProjectAuthService
from app.utils.cookie_utils import normalize_playwright_cookie, normalize_playwright_cookies


from app.core.storage import storage_path

DISCOVERY_SCREENSHOT_DIR = storage_path("screenshots")


class WebPageDiscoveryService:
    def __init__(self, repository: ResourceRepository) -> None:
        self.repository = repository

    def discover_project(self, project: dict[str, Any], config: dict[str, Any] | None = None) -> dict[str, Any]:
        if importlib.util.find_spec("playwright") is None:
            return {"enabled": False, "error": "后端未安装 playwright，无法进行登录后页面发现"}
        config = dict(config or {})
        try:
            self._prepare_login_auth(project, config)
            return self._run_async_discovery(project, config)
        except Exception as exc:  # noqa: BLE001 - discovery is optional context for AI generation.
            base_url = self._project_base_url(project)
            return {
                "enabled": True,
                "base_url": base_url,
                "start_url": self._start_url(project, base_url) if base_url else "",
                "error": self._exception_message(exc),
                "captured_pages": [],
                "api_calls": [],
                "warnings": [],
            }

    def _run_async_discovery(self, project: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
        if sys.platform.startswith("win"):
            policy = asyncio.WindowsProactorEventLoopPolicy()
            loop = policy.new_event_loop()
            try:
                return loop.run_until_complete(self._discover_project(project, config))
            finally:
                loop.close()
        return asyncio.run(self._discover_project(project, config))

    async def _discover_project(self, project: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
        from playwright.async_api import async_playwright

        base_url = self._project_base_url(project)
        if not base_url:
            return {"enabled": False, "error": "项目未配置 Web 地址，无法进行页面发现"}

        project_id = int(project["id"])
        max_pages = self._to_int(config.get("max_pages"), 30)
        timeout_ms = self._to_int(config.get("timeout_ms"), 15000)
        wait_ms = self._to_int(config.get("wait_ms"), 1000)
        headless = self._truthy(config.get("headless", True))
        start_url = self._post_login_start_url(project, base_url, config)
        api_calls: list[dict[str, Any]] = []
        router_route_candidates: list[dict[str, str]] = []
        warnings: list[str] = list(config.get("_login_warnings") or [])

        if config.get("_login_failed"):
            return {
                "enabled": True,
                "base_url": base_url,
                "start_url": start_url,
                "auth_loaded": False,
                "login_executed": bool(config.get("_login_executed")),
                "login_failed": True,
                "login_record_id": config.get("_login_record_id"),
                "login_auth_id": config.get("_login_auth_id"),
                "login_final_url": config.get("_login_url"),
                "error": str(config.get("_login_error") or "登录用例执行失败，已停止页面采集和 AI 解析"),
                "captured_pages": [],
                "api_calls": [],
                "warnings": warnings,
            }

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=headless)
            context = await browser.new_context(viewport={"width": 1440, "height": 900})
            page = await context.new_page()
            try:
                auth_loaded = await self._load_web_auth(context, project_id, base_url, config)
                page.on("response", lambda response: self._track_response(api_calls, router_route_candidates, response, base_url))
                await page.goto(start_url, wait_until="domcontentloaded", timeout=timeout_ms)
                await page.wait_for_timeout(wait_ms)
                login_executed = bool(config.get("_login_executed"))
                if not auth_loaded or await self._looks_like_login_page(page):
                    warnings.append("登录后页面仍未进入系统内部，请检查登录用例执行结果或 Cookie 鉴权是否有效")
                    return {
                        "enabled": True,
                        "base_url": base_url,
                        "start_url": start_url,
                        "auth_loaded": auth_loaded,
                        "login_executed": login_executed,
                        "login_failed": True,
                        "login_record_id": config.get("_login_record_id"),
                        "login_auth_id": config.get("_login_auth_id"),
                        "login_final_url": config.get("_login_url"),
                        "error": "登录后页面仍停留在登录页，已停止页面采集和 AI 解析",
                        "captured_pages": [],
                        "api_calls": self._compact_api_calls(api_calls),
                        "warnings": warnings,
                    }

                candidates = await self._collect_route_candidates(page, base_url, project_id, max_pages, router_route_candidates)
                pages = await self._visit_candidates(page, candidates, base_url, max_pages, timeout_ms, wait_ms, api_calls, warnings)
                return {
                    "enabled": True,
                    "base_url": base_url,
                    "start_url": start_url,
                    "auth_loaded": auth_loaded,
                    "login_executed": login_executed,
                    "login_record_id": config.get("_login_record_id"),
                    "login_auth_id": config.get("_login_auth_id"),
                    "login_final_url": config.get("_login_url"),
                    "route_count": len(candidates),
                    "router_route_count": len(router_route_candidates),
                    "routes": self._route_summary(candidates),
                    "captured_pages": pages,
                    "api_calls": self._compact_api_calls(api_calls),
                    "warnings": warnings,
                }
            except Exception as exc:  # noqa: BLE001 - discovery is optional context for AI generation.
                return {
                    "enabled": True,
                    "base_url": base_url,
                    "start_url": start_url,
                    "error": self._exception_message(exc),
                    "captured_pages": [],
                    "api_calls": self._compact_api_calls(api_calls),
                    "warnings": warnings,
                }
            finally:
                await self._safe_close_playwright_resource(context)
                await self._safe_close_playwright_resource(browser)

    async def _safe_close_playwright_resource(self, resource: Any) -> None:
        try:
            await resource.close()
        except Exception:  # noqa: BLE001 - cleanup errors must not override discovery results.
            return

    def _prepare_login_auth(self, project: dict[str, Any], config: dict[str, Any]) -> None:
        project_id = self._to_int(project.get("id"))
        if not project_id:
            return
        login_case_id = self._to_int(config.get("login_case_id"))
        if not login_case_id and self._default_web_auth_id(project_id):
            return

        login_case = self._login_case(project_id, login_case_id)
        if not login_case:
            message = f"未找到指定的 Web 登录正式用例：{login_case_id}" if login_case_id else "未找到功能类型为登录的 Web 正式用例"
            config["_login_failed"] = True
            config["_login_error"] = message
            config["_login_warnings"] = [message]
            return

        timeout_ms = self._to_int(config.get("timeout_ms"), 15000) or 15000
        wait_ms = self._to_int(config.get("wait_ms"), 1000) or 1000
        headless = self._truthy(config.get("headless", True))
        run_mode = "local_headless" if headless else "local_headed"
        execution = run_case_execution_job(
            "WEB",
            {
                "project_id": project_id,
                "case_ids": [int(login_case["id"])],
                "mode": run_mode,
                "config": {
                    "run_mode": "headless" if headless else "headed",
                    "action_timeout_ms": timeout_ms,
                    "step_wait_ms": wait_ms,
                    "screenshot": "viewport",
                },
            },
            self.repository,
        )
        records = execution.get("records") if isinstance(execution.get("records"), list) else []
        record = records[0] if records and isinstance(records[0], dict) else {}
        record_data = record.get("data") if isinstance(record.get("data"), dict) else {}
        config["_login_executed"] = True
        config["_login_record_id"] = record.get("id")
        config["_login_url"] = record_data.get("url")
        auth_saved = record_data.get("auth_saved") if isinstance(record_data.get("auth_saved"), dict) else {}
        if auth_saved.get("auth_id"):
            config["_login_auth_id"] = auth_saved.get("auth_id")
        cookies = record_data.get("cookies")
        if isinstance(cookies, list):
            config["_login_cookies"] = cookies
        if record.get("status") != "success":
            error = record_data.get("error") or record.get("description") or "登录用例执行失败"
            config["_login_failed"] = True
            config["_login_error"] = str(error)
            config["_login_warnings"] = [f"登录用例 {login_case.get('name')} 执行失败: {error}"]
            return
        config["_login_warnings"] = [f"已通过后台正式 Web 用例执行登录：{login_case.get('name')}"]

    async def _load_web_auth(self, context: Any, project_id: int, base_url: str, config: dict[str, Any]) -> bool:
        cookies = config.get("_login_cookies")
        if not isinstance(cookies, list) or not cookies:
            auth_id = self._to_int(config.get("_login_auth_id")) or self._default_web_auth_id(project_id)
            cookies = ProjectAuthService(self.repository).web_cookies(auth_id)
        return await self._add_cookies_to_context(context, cookies, base_url)

    async def _add_cookies_to_context(self, context: Any, cookies: Any, base_url: str) -> bool:
        if not isinstance(cookies, list) or not cookies:
            return False
        normalized = normalize_playwright_cookies(cookies, base_url)
        if normalized:
            await context.add_cookies(normalized)
            return True
        return False

    async def _load_default_web_auth(self, context: Any, project_id: int, base_url: str) -> bool:
        auth_id = self._default_web_auth_id(project_id)
        if not auth_id:
            return False
        cookies = ProjectAuthService(self.repository).web_cookies(auth_id)
        return await self._add_cookies_to_context(context, cookies, base_url)

    def _login_case(self, project_id: int, login_case_id: int | None = None) -> dict[str, Any] | None:
        if login_case_id:
            case = self.repository.get("web_test_cases", login_case_id)
            if (
                case
                and case.get("status") == "active"
                and int(case.get("project_id") or 0) == project_id
                and self._is_login_case(case)
            ):
                return case
            return None
        rows, _ = self.repository.list("web_test_cases", project_id=project_id, page=1, page_size=1000)
        for row in rows:
            if row.get("status") != "active":
                continue
            if self._is_login_case(row):
                return row
        return None

    def _is_login_case(self, case: dict[str, Any]) -> bool:
        data = case.get("data") if isinstance(case.get("data"), dict) else {}
        page = self.repository.get("web_pages", int(case["source_id"])) if case.get("source_id") else None
        page_data = page.get("data") if isinstance(page, dict) and isinstance(page.get("data"), dict) else {}
        markers = [
            case.get("name"),
            data.get("feature_type"),
            page.get("name") if page else None,
            page_data.get("feature_type"),
        ]
        return any(str(item or "").lower() == "login" or "登录" in str(item or "") for item in markers)

    def _case_steps(self, case: dict[str, Any]) -> list[dict[str, Any]]:
        steps = case.get("steps") if isinstance(case.get("steps"), list) else []
        data = case.get("data") if isinstance(case.get("data"), dict) else {}
        if not steps and isinstance(data.get("steps"), list):
            steps = data["steps"]
        request = data.get("request") if isinstance(data.get("request"), dict) else {}
        if not steps and isinstance(request.get("steps"), list):
            steps = request["steps"]
        return [step for step in steps if isinstance(step, dict)]

    def _login_case_url(self, login_case: dict[str, Any], base_url: str) -> str:
        data = login_case.get("data") if isinstance(login_case.get("data"), dict) else {}
        for value in (data.get("url"), data.get("route")):
            text = str(value or "").strip()
            if text:
                return self._absolute_url(text, base_url)
        source_id = self._to_int(login_case.get("source_id"))
        if not source_id:
            return ""
        page = self.repository.get("web_pages", source_id)
        page_data = page.get("data") if isinstance(page, dict) and isinstance(page.get("data"), dict) else {}
        for value in (page_data.get("url"), page_data.get("route")):
            text = str(value or "").strip()
            if text:
                return self._absolute_url(text, base_url)
        return ""

    async def _looks_like_login_page(self, page: Any) -> bool:
        try:
            text = (await page.locator("body").inner_text(timeout=3000)).lower()
        except Exception:  # noqa: BLE001
            text = ""
        url = str(page.url or "").lower()
        login_markers = ("login", "登录", "用户名", "账号", "密码")
        return any(marker in url or marker in text for marker in login_markers)

    async def _collect_route_candidates(
        self,
        page: Any,
        base_url: str,
        project_id: int,
        max_pages: int,
        router_route_candidates: list[dict[str, str]] | None = None,
    ) -> list[dict[str, str]]:
        candidates: dict[str, dict[str, str]] = {}
        self._add_candidate(candidates, page.url, page.url, "当前页面", base_url)

        for item in await self._dom_route_candidates(page):
            self._add_candidate(candidates, item.get("url"), item.get("url"), item.get("text"), base_url)

        for item in await self._click_route_candidates(page, base_url, max_pages, candidates):
            self._add_candidate(candidates, item.get("url"), item.get("route"), item.get("text"), base_url)

        for item in router_route_candidates or []:
            self._add_candidate(candidates, item.get("url"), item.get("route"), item.get("text"), base_url)

        for item in self._stored_page_candidates(project_id, base_url):
            self._add_candidate(candidates, item.get("url"), item.get("route"), item.get("name"), base_url)

        rows = list(candidates.values())
        rows.sort(key=lambda item: (self._route_score(item.get("route", "")), item.get("route", "")))
        return rows[:max_pages]

    async def _dom_route_candidates(self, page: Any) -> list[dict[str, str]]:
        script = """
        () => {
          const rows = [];
          const push = (url, text) => {
            if (!url) return;
            rows.push({ url, text: (text || '').trim().slice(0, 80) });
          };
          document.querySelectorAll('a[href]').forEach(el => push(el.href, el.innerText || el.textContent));
          document.querySelectorAll('[data-url],[data-path],[data-route],[route],[to]').forEach(el => {
            push(el.getAttribute('data-url') || el.getAttribute('data-path') || el.getAttribute('data-route') || el.getAttribute('route') || el.getAttribute('to'), el.innerText || el.textContent);
          });
          return rows;
        }
        """
        try:
            rows = await page.evaluate(script)
        except Exception:  # noqa: BLE001 - DOM candidates are best effort.
            return []
        return [item for item in rows if isinstance(item, dict)]

    async def _click_route_candidates(
        self,
        page: Any,
        base_url: str,
        max_pages: int,
        existing: dict[str, dict[str, str]],
    ) -> list[dict[str, str]]:
        start_url = page.url
        candidates = await self._clickable_navigation_candidates(page)
        if not candidates:
            return []
        discovered: list[dict[str, str]] = []
        seen = set(existing)
        for index, item in enumerate(candidates[: max(max_pages * 3, max_pages)]):
            if len(seen) >= max_pages:
                break
            selector = str(item.get("selector") or "")
            label = str(item.get("text") or "")
            if not selector or self._dangerous_click_label(label):
                continue
            try:
                locator = page.locator(selector).first
                if not await locator.is_visible(timeout=1000):
                    continue
                before_url = page.url
                await locator.click(timeout=3000)
                await page.wait_for_timeout(800)
                after_url = page.url
                if after_url == before_url:
                    continue
                if not self._same_host_or_path(after_url, base_url):
                    continue
                route = self._route_from_url(after_url, base_url)
                key = route or after_url
                if key and key not in seen:
                    seen.add(key)
                    discovered.append({"url": after_url, "route": route, "text": label or f"菜单{index + 1}"})
            except Exception:  # noqa: BLE001 - clicking navigation is best effort.
                continue
            finally:
                try:
                    if page.url != start_url:
                        await page.goto(start_url, wait_until="domcontentloaded", timeout=5000)
                        await page.wait_for_timeout(500)
                except Exception:  # noqa: BLE001
                    pass
        return discovered

    async def _clickable_navigation_candidates(self, page: Any) -> list[dict[str, str]]:
        script = """
        () => {
          const rows = [];
          const selectors = [
            'a[href]',
            '[role="menuitem"]',
            '.el-menu-item',
            '.el-sub-menu__title',
            '.ant-menu-item',
            '.ant-menu-submenu-title',
            '[data-url]',
            '[data-path]',
            '[data-route]',
            '[to]'
          ];
          const cssPath = (el) => {
            const parts = [];
            let node = el;
            while (node && node.nodeType === 1 && parts.length < 6) {
              let part = node.tagName.toLowerCase();
              if (node.id) {
                part += '#' + CSS.escape(node.id);
                parts.unshift(part);
                break;
              }
              const cls = Array.from(node.classList || []).filter(Boolean).slice(0, 2);
              if (cls.length) part += '.' + cls.map(item => CSS.escape(item)).join('.');
              const parent = node.parentElement;
              if (parent) {
                const same = Array.from(parent.children).filter(child => child.tagName === node.tagName);
                if (same.length > 1) part += `:nth-of-type(${same.indexOf(node) + 1})`;
              }
              parts.unshift(part);
              node = parent;
            }
            return parts.join(' > ');
          };
          const push = (el) => {
            const rect = el.getBoundingClientRect();
            const style = window.getComputedStyle(el);
            if (rect.width <= 0 || rect.height <= 0 || style.visibility === 'hidden' || style.display === 'none') return;
            const text = (el.innerText || el.textContent || el.getAttribute('aria-label') || el.getAttribute('title') || '').trim().slice(0, 80);
            if (!text && !el.getAttribute('href') && !el.getAttribute('data-url') && !el.getAttribute('data-path') && !el.getAttribute('data-route') && !el.getAttribute('to')) return;
            rows.push({ selector: cssPath(el), text });
          };
          document.querySelectorAll(selectors.join(',')).forEach(push);
          return rows.slice(0, 300);
        }
        """
        try:
            rows = await page.evaluate(script)
        except Exception:  # noqa: BLE001
            return []
        result: list[dict[str, str]] = []
        seen: set[str] = set()
        for item in rows:
            if not isinstance(item, dict):
                continue
            selector = str(item.get("selector") or "")
            if not selector or selector in seen:
                continue
            seen.add(selector)
            result.append({"selector": selector, "text": str(item.get("text") or "")})
        return result

    async def _visit_candidates(
        self,
        page: Any,
        candidates: list[dict[str, str]],
        base_url: str,
        max_pages: int,
        timeout_ms: int,
        wait_ms: int,
        api_calls: list[dict[str, Any]],
        warnings: list[str],
    ) -> list[dict[str, Any]]:
        DISCOVERY_SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        pages: list[dict[str, Any]] = []
        seen: set[str] = set()
        for candidate in candidates:
            if len(pages) >= max_pages:
                break
            url = candidate.get("url") or ""
            route = candidate.get("route") or self._route_from_url(url, base_url)
            key = route or url
            if not url or key in seen:
                continue
            seen.add(key)

            before_count = len(api_calls)
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                await page.wait_for_timeout(wait_ms)
                final_route = self._route_from_url(page.url, base_url) or route
                final_key = final_route or page.url
                if final_key != key and final_key in seen:
                    continue
                if self._should_skip_route(final_route):
                    continue
                seen.add(final_key)
                screenshot_file = self._screenshot_filename(route or url)
                await page.screenshot(path=str(DISCOVERY_SCREENSHOT_DIR / screenshot_file), full_page=True)
                text = await self._page_text(page)
                buttons = await self._visible_actions(page)
                if self._is_blank_page_capture(text, buttons):
                    warnings.append(f"{final_route or page.url} 页面为空白，已跳过")
                    continue
                page_api_calls = api_calls[before_count:]
                pages.append(
                    {
                        "title": await page.title(),
                        "name_hint": candidate.get("name") or await page.title(),
                        "route": final_route,
                        "url": page.url,
                        "screenshot_file": screenshot_file,
                        "screenshot_url": f"/api/v1/screenshots/{screenshot_file}",
                        "text": text,
                        "visible_actions": buttons,
                        "api_calls": self._compact_api_calls(page_api_calls),
                    }
                )
            except Exception as exc:  # noqa: BLE001 - keep scanning other routes.
                warnings.append(f"{route or url} 采集失败: {exc}")
        return pages

    def _is_blank_page_capture(self, text: str, actions: list[str]) -> bool:
        normalized = re.sub(r"\s+", "", str(text or ""))
        if not normalized:
            return True
        if len(normalized) <= 8 and not actions:
            return True
        blank_markers = {"404", "401", "403", "notfound", "forbidden", "unauthorized"}
        return normalized.lower() in blank_markers

    def _route_summary(self, candidates: list[dict[str, str]]) -> list[dict[str, str]]:
        rows: list[dict[str, str]] = []
        seen: set[str] = set()
        for item in candidates:
            route = str(item.get("route") or "").strip()
            url = str(item.get("url") or "").strip()
            key = route or url
            if not key or key in seen:
                continue
            seen.add(key)
            rows.append(
                {
                    "route": route,
                    "url": url,
                    "name": str(item.get("name") or item.get("text") or route or url),
                    "source": str(item.get("source") or ""),
                }
            )
        return rows

    async def _page_text(self, page: Any) -> str:
        try:
            text = await page.locator("body").inner_text(timeout=3000)
        except Exception:  # noqa: BLE001
            return ""
        return self._short_text(text, 1200)

    async def _visible_actions(self, page: Any) -> list[str]:
        script = """
        () => Array.from(document.querySelectorAll('button,a,[role="button"],.el-button,.ant-btn'))
          .filter(el => {
            const rect = el.getBoundingClientRect();
            const style = window.getComputedStyle(el);
            return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
          })
          .map(el => (el.innerText || el.textContent || el.getAttribute('aria-label') || el.getAttribute('title') || '').trim())
          .filter(Boolean)
          .slice(0, 80)
        """
        try:
            values = await page.evaluate(script)
        except Exception:  # noqa: BLE001
            return []
        result: list[str] = []
        for value in values:
            text = str(value).strip()
            if text and text not in result:
                result.append(text)
        return result[:40]

    def _stored_page_candidates(self, project_id: int, base_url: str) -> list[dict[str, str]]:
        rows, _ = self.repository.list("web_pages", project_id=project_id, page=1, page_size=1000)
        result: list[dict[str, str]] = []
        for row in rows:
            data = row.get("data") if isinstance(row.get("data"), dict) else {}
            route = str(data.get("route") or "").strip()
            url = str(data.get("url") or "").strip()
            if not url and route:
                url = urljoin(base_url.rstrip("/") + "/", route.lstrip("/"))
            if url:
                result.append({"url": url, "route": route, "name": str(row.get("name") or "")})
        return result

    def _track_response(
        self,
        api_calls: list[dict[str, Any]],
        router_route_candidates: list[dict[str, str]],
        response: Any,
        base_url: str,
    ) -> None:
        try:
            asyncio.create_task(self._append_api_call(api_calls, router_route_candidates, response, base_url))
        except Exception:  # noqa: BLE001 - response listener should never break discovery.
            return

    async def _append_api_call(
        self,
        api_calls: list[dict[str, Any]],
        router_route_candidates: list[dict[str, str]],
        response: Any,
        base_url: str,
    ) -> None:
        try:
            url = response.url
            if not self._looks_like_api(url, base_url):
                return
            request = response.request
            parsed = urlparse(url)
            api_calls.append(
                {
                    "method": request.method,
                    "url": self._safe_url(url),
                    "path": parsed.path,
                    "status": response.status,
                    "resource_type": request.resource_type,
                }
            )
            if self._looks_like_router_response(parsed.path):
                payload = await response.json()
                self._append_router_candidates(router_route_candidates, payload, base_url)
        except Exception:  # noqa: BLE001 - request listener should never break discovery.
            return

    def _looks_like_router_response(self, path: str) -> bool:
        return str(path or "").rstrip("/").lower().endswith("/getrouters")

    def _append_router_candidates(self, target: list[dict[str, str]], payload: Any, base_url: str) -> None:
        rows = self._router_candidates_from_payload(payload, base_url)
        existing = {item.get("route") or item.get("url") for item in target}
        for item in rows:
            key = item.get("route") or item.get("url")
            if not key or key in existing:
                continue
            existing.add(key)
            target.append(item)

    def _router_candidates_from_payload(self, payload: Any, base_url: str) -> list[dict[str, str]]:
        roots = payload
        if isinstance(payload, dict):
            for key in ("data", "rows", "routes", "routers"):
                if isinstance(payload.get(key), list):
                    roots = payload[key]
                    break
        if not isinstance(roots, list):
            return []
        result: list[dict[str, str]] = []

        def walk(nodes: list[Any], parent_route: str = "") -> None:
            for node in nodes:
                if not isinstance(node, dict):
                    continue
                route = self._join_route(parent_route, str(node.get("path") or ""))
                meta = node.get("meta") if isinstance(node.get("meta"), dict) else {}
                name = str(meta.get("title") or node.get("name") or route or "").strip()
                hidden = node.get("hidden") is True
                if route and not hidden and not self._should_skip_route(route) and not route.startswith(("http://", "https://")):
                    result.append({"url": self._absolute_url(route, base_url), "route": route, "text": name})
                children = node.get("children")
                if isinstance(children, list):
                    walk(children, route)

        walk(roots)
        return result

    def _join_route(self, parent_route: str, child_route: str) -> str:
        child = child_route.strip()
        if not child or child == "#":
            return parent_route
        if child.startswith(("http://", "https://")):
            return child
        if child.startswith("/"):
            return child
        parent = parent_route.strip()
        if not parent or parent == "/":
            return f"/{child.strip('/')}"
        return f"{parent.rstrip('/')}/{child.strip('/')}"

    def _compact_api_calls(self, api_calls: list[dict[str, Any]], limit: int = 80) -> list[dict[str, Any]]:
        seen: set[str] = set()
        result: list[dict[str, Any]] = []
        for item in api_calls:
            key = f"{item.get('method')} {item.get('path')} {item.get('status')}"
            if key in seen:
                continue
            seen.add(key)
            result.append(item)
            if len(result) >= limit:
                break
        return result

    def _looks_like_api(self, url: str, base_url: str) -> bool:
        parsed = urlparse(url)
        base = urlparse(base_url)
        if parsed.scheme not in {"http", "https"}:
            return False
        if parsed.hostname != base.hostname:
            return True
        path = parsed.path.lower()
        if any(marker in path for marker in ("/api/", "/dev-api/", "/prod-api/", "/openapi", "/graphql")):
            return True
        return path.endswith(".json")

    def _default_web_auth_id(self, project_id: int) -> int | None:
        rows, _ = self.repository.list("project_auth", project_id=project_id, page=1, page_size=500)
        for row in rows:
            data = row.get("data") if isinstance(row.get("data"), dict) else {}
            if str(data.get("login_case_type") or "").upper() == "WEB" and row.get("status") == "active":
                return self._to_int(row.get("id"))
        for row in rows:
            data = row.get("data") if isinstance(row.get("data"), dict) else {}
            if str(data.get("login_case_type") or "").upper() == "WEB":
                return self._to_int(row.get("id"))
        return None

    def _normalize_cookie(self, cookie: dict[str, Any], target_url: str) -> dict[str, Any]:
        return normalize_playwright_cookie(cookie, target_url)

    def _add_candidate(
        self,
        candidates: dict[str, dict[str, str]],
        url: str | None,
        route: str | None,
        name: str | None,
        base_url: str,
    ) -> None:
        normalized_url = self._absolute_url(str(url or route or ""), base_url)
        if not normalized_url:
            return
        normalized_route = self._route_from_url(normalized_url, base_url)
        if not self._same_host_or_path(normalized_url, base_url):
            return
        key = normalized_route or normalized_url
        if self._should_skip_route(normalized_route):
            return
        if key in candidates:
            if name and not candidates[key].get("name"):
                candidates[key]["name"] = name
            return
        candidates[key] = {"url": normalized_url, "route": normalized_route, "name": str(name or "")}

    def _absolute_url(self, value: str, base_url: str) -> str:
        text = value.strip()
        if not text or text.startswith(("javascript:", "mailto:", "tel:")):
            return ""
        if text.startswith("#"):
            return base_url.rstrip("/") + "/" + text
        if text.startswith(("http://", "https://")):
            return text
        return urljoin(base_url.rstrip("/") + "/", text.lstrip("/"))

    def _same_host_or_path(self, url: str, base_url: str) -> bool:
        parsed = urlparse(url)
        base = urlparse(base_url)
        return parsed.hostname == base.hostname

    def _route_from_url(self, url: str, base_url: str) -> str:
        parsed = urlparse(url)
        if not parsed.path:
            return "/"
        base_path = urlparse(base_url).path.rstrip("/")
        path = parsed.path
        if base_path and path.startswith(base_path):
            path = path[len(base_path) :] or "/"
        if parsed.query:
            return f"{path}?{parsed.query}"
        if parsed.fragment:
            return f"{path}#{parsed.fragment}"
        return path

    def _project_base_url(self, project: dict[str, Any]) -> str:
        data = project.get("data") if isinstance(project.get("data"), dict) else {}
        return str(data.get("base_url") or data.get("project_url") or data.get("url") or "").strip()

    def _start_url(self, project: dict[str, Any], base_url: str) -> str:
        data = project.get("data") if isinstance(project.get("data"), dict) else {}
        for key in ("home_url", "start_url", "login_success_url", "login_url"):
            value = str(data.get(key) or "").strip()
            if value:
                return self._absolute_url(value, base_url)
        login_page = self._login_page(project.get("id"), base_url)
        if login_page:
            return login_page
        return base_url

    def _login_page(self, project_id: Any, base_url: str) -> str:
        try:
            rows, _ = self.repository.list("web_pages", project_id=int(project_id), page=1, page_size=1000)
        except (TypeError, ValueError):
            return ""
        for row in rows:
            data = row.get("data") if isinstance(row.get("data"), dict) else {}
            markers = f"{row.get('name', '')} {data.get('feature_type', '')}".lower()
            if "login" not in markers and "登录" not in markers:
                continue
            url = str(data.get("url") or data.get("route") or "").strip()
            if url:
                return self._absolute_url(url, base_url)
        return ""

    def _post_login_start_url(self, project: dict[str, Any], base_url: str, config: dict[str, Any]) -> str:
        login_url = str(config.get("_login_url") or "").strip()
        if login_url and not self._looks_like_login_url(login_url):
            return self._absolute_url(login_url, base_url)
        data = project.get("data") if isinstance(project.get("data"), dict) else {}
        for key in ("home_url", "start_url", "login_success_url"):
            value = str(data.get(key) or "").strip()
            if value:
                return self._absolute_url(value, base_url)
        return base_url

    def _looks_like_login_url(self, url: str) -> bool:
        return "login" in str(url or "").lower() or "登录" in str(url or "")

    def _should_skip_route(self, route: Any) -> bool:
        text = str(route or "").strip().lower()
        if not text:
            return False
        if text in {"/404", "/401", "/redirect"}:
            return True
        if text.startswith("/redirect/") or text.startswith("/error/"):
            return True
        if "pathmatch" in text or ":path" in text:
            return True
        return False

    def _dangerous_click_label(self, label: str) -> bool:
        text = str(label or "").strip().lower()
        if not text:
            return False
        markers = (
            "删除",
            "提交",
            "保存",
            "确定",
            "确认",
            "禁用",
            "启用",
            "logout",
            "退出",
            "重置密码",
            "批量删除",
        )
        return any(marker in text for marker in markers)

    def _route_score(self, route: str) -> int:
        text = route.lower()
        if "login" in text or "登录" in text:
            return 0
        if text in {"/", ""}:
            return 1
        return 2

    def _screenshot_filename(self, route: str) -> str:
        safe = re.sub(r"[^0-9a-zA-Z._-]+", "_", route.strip("/#?") or "home").strip("._-")
        safe = safe[:80] or "page"
        return f"discovery_{safe}_{int(time.time() * 1000)}.png"

    def _safe_url(self, url: str) -> str:
        parsed = urlparse(url)
        return parsed._replace(query="", fragment="").geturl()

    def _short_text(self, value: Any, max_length: int) -> str:
        text = re.sub(r"\s+", " ", str(value or "")).strip()
        return text[:max_length]

    def _to_int(self, value: Any, default: int | None = None) -> int | None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def _truthy(self, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        if isinstance(value, (int, float)):
            return value != 0
        return str(value).strip().lower() in {"1", "true", "yes", "y", "on", "是"}

    def _exception_message(self, exc: Exception) -> str:
        text = str(exc).strip()
        return text if text else exc.__class__.__name__
