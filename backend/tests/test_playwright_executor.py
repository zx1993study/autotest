from __future__ import annotations

import unittest
from typing import Any

from web_automation.engines.playwright import PlaywrightEngine


class FakeLocator:
    def __init__(
        self,
        meta: dict[str, Any] | None = None,
        call_log: list[tuple[str, str, str | None]] | None = None,
    ) -> None:
        self.meta = meta or {}
        self.call_log = call_log if call_log is not None else []
        self.clicked = 0
        self.first_used = False
        self.filled_values: list[str] = []
        self.filtered_text = ""

    @property
    def first(self) -> "FakeLocator":
        self.first_used = True
        return self

    async def wait_for(self, state: str = "visible", timeout: int = 5000) -> None:
        self.wait_state = state
        self.wait_timeout = timeout

    async def evaluate(self, script: str) -> dict[str, Any]:
        return self.meta

    async def fill(self, value: str) -> None:
        self.filled_values.append(value)

    async def click(self) -> None:
        self.clicked += 1

    async def select_option(self, **kwargs: Any) -> None:
        raise RuntimeError("custom select")

    def filter(self, *, has_text: str) -> "FakeLocator":
        self.filtered_text = has_text
        return self

    def get_by_role(self, role: str, name: str | None = None) -> "FakeLocator":
        self.call_log.append(("locator_role", role, name))
        return self


class FakePage:
    def __init__(self) -> None:
        self.call_log: list[tuple[str, str, str | None]] = []
        self.opener = FakeLocator(
            {
                "tag": "input",
                "readonly": True,
                "placeholder": "请选择仓库业务员",
                "className": "el-select el-input__inner",
            },
            self.call_log,
        )
        self.option = FakeLocator(call_log=self.call_log)

    def locator(self, selector: str) -> FakeLocator:
        self.last_selector = selector
        return self.option

    def get_by_placeholder(self, value: str) -> FakeLocator:
        self.placeholder_value = value
        return self.opener

    def get_by_text(self, value: str, exact: bool = False) -> FakeLocator:
        self.text_value = value
        return self.option

    def get_by_role(self, role: str, name: str | None = None) -> FakeLocator:
        self.call_log.append(("page_role", role, name))
        return self.option


class PlaywrightEngineTest(unittest.IsolatedAsyncioTestCase):
    async def test_fill_on_readonly_select_input_clicks_option(self) -> None:
        page = FakePage()
        engine = PlaywrightEngine(page)

        await engine.execute(
            {
                "action": "fill",
                "locator_type": "placeholder",
                "locator": "请选择仓库业务员",
                "value": "超级管理员",
            }
        )

        self.assertEqual("请选择仓库业务员", page.placeholder_value)
        self.assertEqual(1, page.opener.clicked)
        self.assertEqual(1, page.option.clicked)
        self.assertEqual("超级管理员", page.option.filtered_text)
        self.assertEqual([], page.opener.filled_values)

    async def test_role_locator_uses_first_match(self) -> None:
        page = FakePage()
        locator = PlaywrightEngine(page).locator(
            {"locator_type": "role", "locator": "button", "role_name": "查询"}
        )
        self.assertTrue(locator.first_used)
        self.assertEqual(("page_role", "button", "查询"), page.call_log[-1])

    async def test_chained_get_by_role_locator_preserves_scope(self) -> None:
        page = FakePage()
        locator = PlaywrightEngine(page).locator(
            {
                "locator_type": "playwright",
                "locator": 'page.get_by_role("dialog", name="新增活动模板配置").get_by_role("spinbutton")',
            }
        )
        self.assertTrue(locator.first_used)
        self.assertEqual(
            [
                ("page_role", "dialog", "新增活动模板配置"),
                ("locator_role", "spinbutton", None),
            ],
            page.call_log,
        )


if __name__ == "__main__":
    unittest.main()
