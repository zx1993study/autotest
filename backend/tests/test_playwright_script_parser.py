from __future__ import annotations

import unittest

from app.utils.playwright_script_parser import PlaywrightCodegenParser


class PlaywrightCodegenParserTest(unittest.TestCase):
    def setUp(self) -> None:
        self.parser = PlaywrightCodegenParser()

    def test_keeps_feature_button_separate_from_following_textbox(self) -> None:
        script = """
page.get_by_role("button", name="新增").click()
page.get_by_role("textbox", name="请输入用户昵称").click()
page.get_by_role("textbox", name="请输入用户昵称").fill("tester")
"""

        elements = self.parser.parse(script)

        self.assertEqual(len(elements), 2)
        self.assertEqual(elements[0]["element_type"], "button")
        self.assertEqual(elements[0]["action"], "click")
        self.assertEqual(elements[1]["element_type"], "input")
        self.assertEqual(elements[1]["action"], "fill")

    def test_merges_select_opener_and_option_click(self) -> None:
        script = """
page.get_by_role("textbox", name="请选择角色").click()
page.get_by_text("管理员").click()
"""

        elements = self.parser.parse(script)

        self.assertEqual(len(elements), 1)
        self.assertEqual(elements[0]["element_type"], "select")
        self.assertEqual(elements[0]["action"], "select")
        self.assertEqual(elements[0]["default_value"], "管理员")


    def test_select_option_on_placeholder_is_saved_as_select(self) -> None:
        script = """
page.get_by_placeholder("请选择仓库业务员").select_option("超级管理员")
"""

        elements = self.parser.parse(script)

        self.assertEqual(len(elements), 1)
        self.assertEqual(elements[0]["element_type"], "select")
        self.assertEqual(elements[0]["action"], "select")
        self.assertEqual(elements[0]["locator_type"], "placeholder")
        self.assertEqual(elements[0]["default_value"], "超级管理员")


if __name__ == "__main__":
    unittest.main()
