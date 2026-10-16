from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlsplit


class DiscoveryBrowserSession:
    """Plain Playwright avoids SDK signal handlers in server job threads."""

    def __init__(self, *, headless=True, launch_options=None, storage_state=None):
        self.options = {"headless": headless, **(launch_options or {})}
        self.storage_state = storage_state
        self.playwright = self.browser = self.context = self.page = None

    async def __aenter__(self):
        from playwright.async_api import async_playwright

        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(**self.options)
            self.context = await self.browser.new_context(viewport={"width": 1440, "height": 900}, storage_state=self.storage_state)
            self.page = await self.context.new_page()
            return self
        except Exception:
            await self.close()
            raise

    async def __aexit__(self, *args):
        await self.close()

    async def close(self):
        try:
            if self.browser:
                await self.browser.close()
        finally:
            if self.playwright:
                await self.playwright.stop()

    async def goto(self, url, timeout_ms=30000):
        await self.page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)

    async def screenshot(self, path, *, full_page=True):
        await self.page.screenshot(path=path, full_page=full_page)


async def is_login_page(page: Any) -> bool:
    location = urlsplit(str(page.url))
    if re.search(r"(?:^|/)(?:login|signin|sign-in)(?:/|$|\?)", location.path + "/" + location.fragment, re.IGNORECASE):
        return True
    return await page.locator('input[type="password"]:visible').count() > 0


async def open_feature(page: Any, hint: str) -> dict:
    if not hint:
        raise ValueError("AI 未提供功能入口文案")
    if re.search(r"删除|清空|禁用|支付|注销|退出|提交|保存|确认|delete|remove|clear|disable|pay|logout|submit|save|confirm", hint, re.IGNORECASE):
        raise ValueError("风险入口仅记录候选，不在发现阶段自动点击")
    last_error = None
    for role in ("button", "link", None):
        try:
            locator = page.get_by_role(role, name=hint, exact=True) if role else page.get_by_text(hint, exact=True)
            if await locator.count() != 1:
                raise ValueError("功能入口不唯一，请补充行选择条件")
            await locator.click(timeout=3000)
            return {"name": hint, "text": hint, "type": "button", "element_type": "button", "action": "click", "locator_type": "text", "locator": hint, "source": "vision_discovery"}
        except Exception as exc:  # noqa: BLE001 - try the next exact locator.
            last_error = exc
    raise RuntimeError(f"未找到可见功能入口：{hint}") from last_error


async def close_feature(page: Any, return_url: str):
    try:
        await page.keyboard.press("Escape")
        dialog = page.locator(".el-dialog:visible, .ant-modal:visible, [role='dialog']:visible").first
        if await dialog.count():
            await dialog.get_by_role("button", name=re.compile(r"^(取消|关闭|Cancel|Close)$", re.IGNORECASE)).first.click(timeout=1500)
    except Exception:  # noqa: BLE001, S110 - dialog may already be closed by Escape.
        pass
    if str(page.url) != return_url:
        await page.goto(return_url, wait_until="domcontentloaded", timeout=30000)
