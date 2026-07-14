from __future__ import annotations

import unittest

from app.utils.playwright_auto_recorder import ControlInfo, PlaywrightAutoRecorder


class PlaywrightAutoRecorderControlTest(unittest.TestCase):
    def test_readonly_select_input_records_select_action(self) -> None:
        recorder = PlaywrightAutoRecorder()
        control = ControlInfo(
            css=".el-select .el-input__inner",
            tag="input",
            role="",
            name="请选择仓库业务员",
            input_type="text",
            placeholder="请选择仓库业务员",
            value="",
            disabled=False,
            visible=True,
            in_dialog=False,
            readonly=True,
            class_name="el-input__inner",
        )

        self.assertEqual(recorder._default_action(control, "query"), "select_option")
        self.assertFalse(recorder._is_text_input(control))
        self.assertIn(".select_option(", recorder._script_line(control, "select_option", "超级管理员") or "")

    def test_planned_element_steps_filter_unrelated_query_page_buttons(self) -> None:
        recorder = PlaywrightAutoRecorder()
        controls = [
            ControlInfo("button.add-condition", "button", "", "添加条件", "button", "", "", False, True, False),
            ControlInfo("button.add", "button", "", "新增", "button", "", "", False, True, False),
            ControlInfo("button.query", "button", "", "查询", "button", "", "", False, True, False),
        ]
        script_lines: list[str] = []
        operations: list[dict] = []
        element_steps = [
            {"element_name": "添加条件按钮", "action": "click", "locator": "button, name=添加条件"},
            {"element_name": "查询按钮", "action": "click", "locator": "button, name=查询"},
        ]

        recorder._append_control_steps(None, "query", controls, script_lines, operations, element_steps)

        script_text = "\n".join(script_lines)
        self.assertIn("name='添加条件'", script_text)
        self.assertIn("name='查询'", script_text)
        self.assertNotIn("name='新增'", script_text)

    def test_select_plan_does_not_match_query_button(self) -> None:
        recorder = PlaywrightAutoRecorder()
        controls = [
            ControlInfo(
                ".field-select",
                "input",
                "",
                "请选择字段",
                "text",
                "请选择字段",
                "",
                False,
                True,
                False,
                readonly=True,
                class_name="el-select el-input__inner",
            ),
            ControlInfo("button.query", "button", "", "查询", "button", "", "", False, True, False),
        ]
        step = {
            "element_name": "查询字段下拉框",
            "action": "select",
            "value": "仓库编码",
            "locator": "请选择字段",
        }

        control = recorder._find_plan_control(controls, step, "query")

        self.assertIsNotNone(control)
        self.assertEqual(control.name, "请选择字段")


if __name__ == "__main__":
    unittest.main()
