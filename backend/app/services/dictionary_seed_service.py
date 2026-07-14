from __future__ import annotations

from typing import Any

from app.repositories.interfaces import ResourceRepository


PLAYWRIGHT_DEFAULTS: list[dict[str, Any]] = [
    {
        "name": "Playwright 执行模式",
        "status": "active",
        "description": "headed 为有头执行，headless 为无头执行。",
        "data": {
            "dict_type": "playwright_execution",
            "dict_key": "run_mode",
            "dict_value": "headed",
            "sort_order": 10,
        },
    },
    {
        "name": "Playwright 步骤慢放(ms)",
        "status": "active",
        "description": "每个 Playwright 操作自动慢放的毫秒数。",
        "data": {
            "dict_type": "playwright_execution",
            "dict_key": "slow_mo_ms",
            "dict_value": "300",
            "sort_order": 20,
        },
    },
    {
        "name": "Playwright 步骤等待(ms)",
        "status": "active",
        "description": "每个用例步骤执行后额外等待的毫秒数。",
        "data": {
            "dict_type": "playwright_execution",
            "dict_key": "step_wait_ms",
            "dict_value": "300",
            "sort_order": 30,
        },
    },
    {
        "name": "Playwright 操作超时(ms)",
        "status": "active",
        "description": "元素等待、点击、输入等操作的默认超时时间。",
        "data": {
            "dict_type": "playwright_execution",
            "dict_key": "action_timeout_ms",
            "dict_value": "5000",
            "sort_order": 40,
        },
    },
    {
        "name": "Playwright 截图方式",
        "status": "active",
        "description": "full_page 为整页截图，viewport 为当前视口截图。",
        "data": {
            "dict_type": "playwright_execution",
            "dict_key": "screenshot",
            "dict_value": "full_page",
            "sort_order": 50,
        },
    },
]


class DictionarySeedService:
    def __init__(self, repository: ResourceRepository) -> None:
        self.repository = repository

    def seed_playwright_defaults(self, overwrite: bool = False) -> dict[str, int]:
        rows, _ = self.repository.list("system_dictionaries", page_size=10000)
        existing = {
            item.get("data", {}).get("dict_key"): item
            for item in rows
            if item.get("data", {}).get("dict_type") == "playwright_execution"
        }

        created = 0
        updated = 0
        for payload in PLAYWRIGHT_DEFAULTS:
            dict_key = payload["data"]["dict_key"]
            current = existing.get(dict_key)
            if current and overwrite:
                self.repository.update("system_dictionaries", current["id"], payload)
                updated += 1
            elif not current:
                self.repository.create("system_dictionaries", payload)
                created += 1
        return {"created_count": created, "updated_count": updated}
