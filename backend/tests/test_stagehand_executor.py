from __future__ import annotations

import unittest

from web_automation.cache import cached_selector
from web_automation.engines.stagehand import (
    ObservedActionCache,
    StagehandModelConfig,
    StagehandSession,
    build_step_instruction,
    stagehand_available,
)


class BuildStepInstructionTest(unittest.TestCase):
    def test_should_compose_fill_instruction_with_description_hint(self) -> None:
        step = {"name": "用户名", "action": "fill", "value": "admin", "description": "登录页第一个输入框"}
        instruction = build_step_instruction(step)
        self.assertIn("用户名", instruction)
        self.assertIn("admin", instruction)
        self.assertIn("登录页第一个输入框", instruction)

    def test_should_compose_click_instruction_without_value(self) -> None:
        step = {"name": "登录按钮", "action": "click"}
        instruction = build_step_instruction(step)
        self.assertEqual("点击「登录按钮」", instruction)

    def test_should_compose_select_and_check_instructions(self) -> None:
        select_step = {"name": "状态", "action": "select", "value": "启用"}
        check_step = {"name": "记住我", "action": "check"}
        uncheck_step = {"name": "记住我", "action": "uncheck"}
        self.assertIn("选择「启用」", build_step_instruction(select_step))
        self.assertIn("勾选", build_step_instruction(check_step))
        self.assertIn("取消勾选", build_step_instruction(uncheck_step))

    def test_should_support_chinese_step_keys(self) -> None:
        step = {"元素名称": "查询", "交互类型": "click"}
        self.assertEqual("点击「查询」", build_step_instruction(step))

    def test_should_fall_back_to_description_as_target(self) -> None:
        step = {"action": "click", "description": "右上角更多按钮"}
        self.assertIn("右上角更多按钮", build_step_instruction(step))


class CachedSelectorTest(unittest.TestCase):
    def test_should_read_selector_from_ai_cache(self) -> None:
        step = {"ai_cache": {"selector": "#login-btn"}}
        self.assertEqual("#login-btn", cached_selector(step))

    def test_should_return_empty_when_cache_missing(self) -> None:
        self.assertEqual("", cached_selector({}))
        self.assertEqual("", cached_selector({"ai_cache": "invalid"}))
        self.assertEqual("", cached_selector({"ai_cache": {"selector": "  "}}))


class ObservedActionCacheTest(unittest.TestCase):
    def test_should_serialize_cache_dict(self) -> None:
        cache = ObservedActionCache(
            selector="button.submit",
            method="click",
            arguments=[],
            description="提交按钮",
            model="gpt-4o",
            source_url="https://example.test",
            observed_at="2026-08-05T10:00:00+00:00",
        )
        data = cache.as_dict()
        self.assertEqual("button.submit", data["selector"])
        self.assertEqual("gpt-4o", data["model"])
        self.assertEqual("2026-08-05T10:00:00+00:00", data["observed_at"])


class StagehandSessionTest(unittest.TestCase):
    def test_sdk_config_uses_local_playwright_mode_and_openai_compatible_base_url(self) -> None:
        session = StagehandSession(
            StagehandModelConfig(
                model_name="gpt-4o-mini",
                api_key="k",
                base_url="https://gateway.example.test/v1",
                timeout_ms=12000,
            )
        )
        values = session._sdk_config_values()
        self.assertEqual("LOCAL", values["env"])
        self.assertFalse(values["use_api"])
        self.assertEqual("https://gateway.example.test/v1", values["model_client_options"]["api_base"])
        self.assertEqual(0, values["model_client_options"]["num_retries"])
        self.assertEqual(12, values["model_client_options"]["request_timeout"])
        if stagehand_available():
            from stagehand import StagehandConfig

            config = StagehandConfig(**session._supported_kwargs(StagehandConfig, values))
            self.assertEqual("gpt-4o-mini", config.model_name)
            self.assertEqual("k", config.model_api_key)
            self.assertEqual(values["model_client_options"], config.model_client_options)

    def test_should_raise_clear_error_when_sdk_missing(self) -> None:
        if stagehand_available():
            self.skipTest("stagehand SDK 已安装，跳过缺失场景")
        session = StagehandSession(StagehandModelConfig(model_name="m", api_key="k"))
        with self.assertRaisesRegex(RuntimeError, "未安装 stagehand"):
            import asyncio

            asyncio.run(session.start())


if __name__ == "__main__":
    unittest.main()
