from __future__ import annotations

import unittest
from typing import Any

from app.utils.select_control_resolver import SelectControlError, SelectControlResolver


class FakeLocator:
    def __init__(
        self,
        count_value: int = 1,
        *,
        fail_click: bool = False,
        allow_force: bool = False,
        parent: "FakeLocator | None" = None,
        filtered: "FakeLocator | None" = None,
        child: "FakeLocator | None" = None,
    ) -> None:
        self.count_value = count_value
        self.fail_click = fail_click
        self.allow_force = allow_force
        self.parent = parent
        self.filtered = filtered
        self.child = child
        self.clicked = 0

    @property
    def first(self) -> "FakeLocator":
        return self

    def click(self, force: bool = False) -> None:
        self.force = force
        if self.fail_click and not (force and self.allow_force):
            raise RuntimeError("click failed")
        self.clicked += 1

    def count(self) -> int:
        return self.count_value

    def or_(self, other: "FakeLocator") -> "FakeLocator":
        return self if self.count_value else other

    def filter(self, has_text: str) -> "FakeLocator":
        self.filter_text = has_text
        return self.filtered or self

    def locator(self, selector: str) -> "FakeLocator":
        self.parent_selector = selector
        return self.child or self.parent or self


class FakePage:
    def __init__(self, option_count: int = 1, first_option_count: int | None = None) -> None:
        self.opener = FakeLocator()
        self.option = FakeLocator(option_count)
        first_count = option_count if first_option_count is None else first_option_count
        self.first_option = FakeLocator(first_count)
        self.tree_content = FakeLocator(first_count, filtered=self.option, child=self.first_option)

    def get_by_text(self, value: str, exact: bool = False) -> FakeLocator:
        self.option_text = value
        self.option_exact = exact
        return self.option

    def get_by_role(self, role: str, name: str | None = None) -> FakeLocator:
        self.option_role = role
        self.option_role_name = name
        return self.option

    def locator(self, selector: str) -> FakeLocator:
        self.selector = selector
        if selector == SelectControlResolver.TREE_CONTENT_VISIBLE_SELECTOR:
            return self.tree_content
        return self.option


class SelectControlResolverTest(unittest.TestCase):
    def test_readonly_placeholder_is_select_like(self) -> None:
        self.assertTrue(
            SelectControlResolver.is_select_like(
                tag="input",
                role="",
                input_type="text",
                name="请选择仓库业务员",
                placeholder="请选择仓库业务员",
                class_name="el-input__inner",
                readonly=True,
            )
        )

    def test_missing_option_selects_first_available_option(self) -> None:
        page = FakePage(option_count=0, first_option_count=1)

        SelectControlResolver.sync_select(page, page.opener, "超级管理员", control_name="仓库业务员")

        self.assertEqual(page.opener.clicked, 1)
        self.assertEqual(page.first_option.clicked, 1)

    def test_empty_value_selects_first_available_option(self) -> None:
        page = FakePage(option_count=0, first_option_count=1)

        SelectControlResolver.sync_select(page, page.opener, "", control_name="仓库业务员")

        self.assertEqual(page.opener.clicked, 1)
        self.assertEqual(page.first_option.clicked, 1)

    def test_default_first_option_uses_visible_option_selector(self) -> None:
        self.assertIn(":visible", SelectControlResolver.OPTION_VISIBLE_SELECTOR)
        self.assertNotEqual(SelectControlResolver.OPTION_SELECTOR, SelectControlResolver.OPTION_VISIBLE_SELECTOR)

    def test_empty_options_still_raise_clear_error(self) -> None:
        page = FakePage(option_count=0, first_option_count=0)

        with self.assertRaisesRegex(SelectControlError, "未找到任何下拉选项"):
            SelectControlResolver.sync_select(page, page.opener, "超级管理员", control_name="仓库业务员")

    def test_opener_falls_back_to_parent_container(self) -> None:
        page = FakePage(option_count=1)
        parent = FakeLocator()
        inner_input = FakeLocator(fail_click=True, parent=parent)

        SelectControlResolver.sync_select(page, inner_input, "超级管理员", control_name="仓库业务员")

        self.assertEqual(inner_input.clicked, 0)
        self.assertEqual(parent.clicked, 1)
        self.assertEqual(page.option.clicked, 1)

    def test_opener_uses_force_click_when_normal_click_is_intercepted(self) -> None:
        page = FakePage(option_count=1)
        opener = FakeLocator(fail_click=True, allow_force=True)

        SelectControlResolver.sync_select(page, opener, "超级管理员", control_name="仓库业务员")

        self.assertTrue(opener.force)
        self.assertEqual(opener.clicked, 1)
        self.assertEqual(page.option.clicked, 1)

    def test_values_support_list_and_comma_text(self) -> None:
        self.assertEqual(SelectControlResolver.values(["A", " ", "B"]), ["A", "B"])
        self.assertEqual(SelectControlResolver.values("A, B"), ["A", "B"])
        self.assertEqual(SelectControlResolver.values(None), [])


if __name__ == "__main__":
    unittest.main()
