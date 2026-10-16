from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import Mock

from agent_app.api.client import AgentApiClient
from agent_app.api.tasks import AgentTaskApi
from agent_app.config import AgentConfig
from agent_app.executors.web_case_executor import LocalWebCaseExecutor
from agent_app.runtime.task_runner import AgentTaskRunner
from web_automation.compiler import ExecutionPlanCompiler
from web_automation.engines.stagehand import build_step_instruction


class ExecutionPlanCompilerTest(unittest.TestCase):
    def test_dynamic_values_are_frozen_per_case_and_distinct_in_batch(self) -> None:
        case = {"id": 1, "name": "Dynamic", "steps": [{"action": "fill", "value": "{{random_phone}}"}, {"action": "fill", "value": "{{random_phone}}"}]}
        plan = ExecutionPlanCompiler().compile({"cases": [case, {**case, "id": 2}]})
        first, second = plan.cases
        self.assertRegex(first.steps[0]["value"], r"^138\d{8}$")
        self.assertEqual(first.steps[0]["value"], first.steps[1]["value"])
        self.assertNotEqual(first.steps[0]["value"], second.steps[0]["value"])
        self.assertEqual(first.steps[0]["value"], first.raw["_dynamic_values"]["values"]["random_phone"])
        self.assertEqual("{{random_phone}}", case["steps"][0]["value"])

    def test_compiles_elements_target_url_and_hybrid_default(self) -> None:
        payload = {
            "execution": {"mode": "local_headed"},
            "cases": [
                {
                    "id": 1,
                    "name": "登录",
                    "project_id": 10,
                    "source_id": 20,
                    "steps": [{"元素名称": "用户名", "元素值": "admin"}],
                }
            ],
            "context": {
                "projects": {"10": {"id": 10, "data": {"base_url": "https://example.test/app"}}},
                "pages": {"20": {"id": 20, "data": {"route": "/login"}}},
                "elements": [
                    {
                        "id": 30,
                        "name": "用户名",
                        "data": {
                            "page_id": 20,
                            "element_type": "input",
                            "locator_type": "placeholder",
                            "locator": "请输入用户名",
                        },
                    }
                ],
            },
        }

        plan = ExecutionPlanCompiler().compile(payload)

        self.assertEqual("hybrid", plan.config.engine)
        self.assertFalse(plan.config.headless)
        self.assertEqual("https://example.test/app/login", plan.cases[0].target_url)
        self.assertEqual(30, plan.cases[0].steps[0]["element_id"])
        self.assertEqual("fill", plan.cases[0].steps[0]["action"])
        self.assertEqual("admin", plan.cases[0].steps[0]["value"])

    def test_rejects_unknown_manifest_version(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported manifest version"):
            ExecutionPlanCompiler().compile({"manifest_version": "2.0", "cases": []})


class LocalWebCaseExecutorTest(unittest.TestCase):
    def test_empty_case_returns_versioned_failure_without_starting_browser(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = LocalWebCaseExecutor(Path(temp_dir)).execute(
                {
                    "execution": {"mode": "local_headed", "config": {"engine": "hybrid"}},
                    "cases": [{"id": 1, "name": "空用例", "project_id": 1, "steps": []}],
                    "context": {},
                }
            )

        self.assertEqual(1, result["failed_count"])
        self.assertEqual("1.0", result["manifest_version"])
        self.assertEqual("1.0", result["result_version"])
        self.assertIn("未读取到执行步骤", result["records"][0]["description"])

    def test_stagehand_model_requires_api_key(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            executor = LocalWebCaseExecutor(Path(temp_dir))
            with self.assertRaisesRegex(RuntimeError, "缺少 AI 模型配置"):
                executor._stagehand_model({})

    def test_build_step_instruction_is_shared(self) -> None:
        self.assertEqual("点击「登录」", build_step_instruction({"name": "登录", "action": "click"}))
        self.assertIn(
            "admin",
            build_step_instruction({"name": "用户名", "action": "fill", "value": "admin"}),
        )


class TaskRunnerDispatchTest(unittest.TestCase):
    def build_runner(self, tmp_dir: str) -> AgentTaskRunner:
        config = AgentConfig(
            server_url="http://127.0.0.1:8000",
            token="agt_test",
            node_key="node-1",
            node_name="node-1",
            artifacts_dir=Path(tmp_dir),
        )
        api = AgentTaskApi(AgentApiClient(config.server_url, config.token), config)
        return AgentTaskRunner(config, api)

    def test_all_web_engines_use_the_unified_executor(self) -> None:
        for engine in ("playwright", "stagehand", "hybrid"):
            with self.subTest(engine=engine), tempfile.TemporaryDirectory() as tmp_dir:
                runner = self.build_runner(tmp_dir)
                calls: list[dict[str, Any]] = []
                runner.web_executor = Mock()
                runner.web_executor.execute.side_effect = lambda payload: calls.append(payload) or {"records": []}
                task = {
                    "id": 1,
                    "data": {
                        "task_type": "case_execution",
                        "payload": {
                            "case_type": "WEB",
                            "cases": [],
                            "execution": {"config": {"engine": engine}},
                            "context": {},
                        },
                    },
                }

                runner.run(task)

                self.assertEqual(1, len(calls))

    def test_legacy_codegen_task_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            runner = self.build_runner(tmp_dir)
            task = {"id": 1, "data": {"task_type": "web_codegen", "payload": {}}}
            with self.assertRaisesRegex(ValueError, "暂不支持"):
                runner.run(task)


if __name__ == "__main__":
    unittest.main()
