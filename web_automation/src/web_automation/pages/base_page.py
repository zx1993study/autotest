from __future__ import annotations

from typing import Any

from web_automation.cookies import normalize_playwright_cookies


class BasePage:
    """Browser lifecycle helpers shared by dynamic Page Objects."""

    def __init__(self, page: Any, *, action_timeout_ms: int, navigation_timeout_ms: int) -> None:
        self.page = page
        self.action_timeout_ms = action_timeout_ms
        self.navigation_timeout_ms = navigation_timeout_ms

    async def prepare(self, target_url: str, auth_context: dict[str, Any]) -> None:
        self.page.set_default_timeout(self.action_timeout_ms)
        self.page.set_default_navigation_timeout(self.navigation_timeout_ms)
        await self._apply_auth(auth_context, target_url)
        await self.goto(target_url)

    async def goto(self, target_url: str) -> None:
        if not target_url:
            return
        try:
            await self.page.goto(
                target_url,
                wait_until="domcontentloaded",
                timeout=self.navigation_timeout_ms,
            )
        except Exception as exc:  # noqa: BLE001 - slow SPAs may be usable after navigation timeout.
            current_url = str(getattr(self.page, "url", "") or "")
            if current_url and current_url != "about:blank":
                await self.page.wait_for_timeout(1000)
                return
            raise RuntimeError(f"Page navigation failed: {target_url}: {exc}") from exc

    async def _apply_auth(self, auth_context: dict[str, Any], target_url: str) -> None:
        headers = auth_context.get("headers") if isinstance(auth_context.get("headers"), dict) else {}
        clean_headers = {str(key): str(value) for key, value in headers.items() if key and value not in (None, "")}
        if clean_headers and hasattr(self.page, "set_extra_http_headers"):
            await self.page.set_extra_http_headers(clean_headers)

        storage_state = auth_context.get("storage_state") if isinstance(auth_context.get("storage_state"), dict) else {}
        raw_cookies = auth_context.get("cookies")
        if not isinstance(raw_cookies, list):
            raw_cookies = storage_state.get("cookies")
        cookies = normalize_playwright_cookies(raw_cookies if isinstance(raw_cookies, list) else [], target_url)
        if cookies:
            await self.page.context.add_cookies(cookies)

        origins = storage_state.get("origins") if isinstance(storage_state.get("origins"), list) else []
        for origin in origins:
            if not isinstance(origin, dict):
                continue
            origin_url = str(origin.get("origin") or "")
            items = origin.get("localStorage")
            if not isinstance(items, list):
                items = origin.get("local_storage")
            if not isinstance(items, list):
                items = []
            pairs = {
                str(item.get("name")): str(item.get("value"))
                for item in items
                if isinstance(item, dict) and item.get("name") not in (None, "")
            }
            if not origin_url or not pairs:
                continue
            script = (
                f"if (window.location.origin === {origin_url!r}) {{"
                + "".join(f"localStorage.setItem({key!r}, {value!r});" for key, value in pairs.items())
                + "}"
            )
            await self.page.context.add_init_script(script)
