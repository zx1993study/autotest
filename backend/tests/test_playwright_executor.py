from __future__ import annotations

import unittest
from typing import Any

from app.utils.playwright_executor import PlaywrightActionExecutor


class FakeLocator:
    def __init__(self, meta: dict[str, Any] | None = None, count_value: int = 1) -> None:
        self.meta = meta or {}
        self.count_value = count_value
        self.clicked = 0
        self.filled_values: list[str] = []

    @property
    def first(self) -> "FakeLocator":
        return self

    async def wait_for(self, state: str = "visible", timeout: int = 5000) -> None:
        self.wait_state = state
        self.wait_timeout = timeout

    async def evaluate(self, script: str) -> dict[str, Any]:
        self.evaluate_script = script
        return self.meta

    async def fill(self, value: str) -> None:
        self.filled_values.append(value)

    async def click(self) -> None:
        self.clicked += 1

    async def count(self) -> int:
        return self.count_value

    def nth(self, index: int) -> "FakeLocator":
        self.nth_index = index
        return self

    def or_(self, other: "FakeLocator") -> "FakeLocator":
        return self if self.count_value else other


class FakePage:
    def __init__(self) -> None:
        self.opener = FakeLocator(
            {
                "readonly": True,
                "text": "请选择仓库业务员 el-select el-input__inner",
            }
        )
        self.option = FakeLocator(count_value=1)

    def get_by_placeholder(self, value: str) -> FakeLocator:
        self.placeholder_value = value
        return self.opener

    def get_by_text(self, value: str, exact: bool = False) -> FakeLocator:
        self.option_text = value
        self.option_exact = exact
        return self.option

    def get_by_role(self, role: str, name: str | None = None) -> FakeLocator:
        self.option_role = role
        self.option_role_name = name
        return self.option


class PlaywrightActionExecutorTest(unittest.IsolatedAsyncioTestCase):
    async def test_fill_on_readonly_select_input_clicks_option(self) -> None:
        page = FakePage()
        executor = PlaywrightActionExecutor(page)
        step = {
            "action": "fill",
            "locator_type": "placeholder",
            "locator": "请选择仓库业务员",
            "value": "超级管理员",
        }

        await executor.run_step(step)

        self.assertEqual(page.placeholder_value, "请选择仓库业务员")
        self.assertEqual(page.option_text, "超级管理员")
        self.assertEqual(page.opener.clicked, 1)
        self.assertEqual(page.option.clicked, 1)
        self.assertEqual(page.opener.filled_values, [])


if __name__ == "__main__":
    unittest.main()
