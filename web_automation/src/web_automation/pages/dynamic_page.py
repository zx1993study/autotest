from __future__ import annotations

from typing import Any

from web_automation.engines.playwright import PlaywrightEngine
from web_automation.pages.base_page import BasePage


class DynamicPage(BasePage):
    """Page Object backed by platform element JSON instead of generated code."""

    def __init__(self, page: Any, *, action_timeout_ms: int, navigation_timeout_ms: int) -> None:
        super().__init__(
            page,
            action_timeout_ms=action_timeout_ms,
            navigation_timeout_ms=navigation_timeout_ms,
        )
        self.engine = PlaywrightEngine(page, default_timeout=action_timeout_ms)

    async def execute(self, step: dict[str, Any]) -> None:
        await self.engine.execute(step)

    async def execute_cached(self, step: dict[str, Any], selector: str) -> None:
        await self.engine.execute_selector(step, selector)

