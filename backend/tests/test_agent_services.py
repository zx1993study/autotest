from __future__ import annotations

import base64
import unittest
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import patch

from app.core.exceptions import BusinessRuleError
from app.schemas.agent import (
    AgentHeartbeatRequest,
    AgentRegisterRequest,
    AgentTaskClaimRequest,
    AgentTaskCreateRequest,
    AgentTaskReportRequest,
    AgentTokenProvisionRequest,
)
from app.services.agent_node_service import AgentNodeService
from app.services import agent_task_service as agent_task_service_module
from app.services.agent_task_service import AgentTaskService
from app.services.case_execution_dispatcher import CaseExecutionDispatcher
from app.services.project_auth_service import ProjectAuthService
from app.scheduler.jobs.web_case_executor import WebCaseExecutor


PNG_BYTES = b"\x89PNG\r\n\x1a\nbackend-test"


class FakeResourceRepository:
    """Small in-memory repository for Agent service tests."""

    def __init__(self) -> None:
        self.tables: dict[str, list[dict[str, Any]]] = {}
        self.next_id = 1

    def list(
        self,
        table: str,
        keyword: str | None = None,
        project_id: int | None = None,
        page: int = 1,
        page_size: int = 20,
        data_filters: dict[str, Any] | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        rows = list(self.tables.get(table, []))
        for key, value in (data_filters or {}).items():
            if key == "status":
                rows = [row for row in rows if row.get("status") == value]
                continue
            rows = [row for row in rows if row.get("data", {}).get(key) == value]
        start = (page - 1) * page_size
        return rows[start : start + page_size], len(rows)

    def get(self, table: str, item_id: int) -> dict[str, Any] | None:
        return next((row for row in self.tables.get(table, []) if row["id"] == item_id), None)

    def create(self, table: str, data: dict[str, Any]) -> dict[str, Any]:
        row = {
            "id": self.next_id,
            "name": data.get("name") or "Untitled",
            "project_id": data.get("project_id"),
            "description": data.get("description"),
            "status": data.get("status") or "active",
            "data": data.get("data") or {},
            "source_id": data.get("source_id"),
            "steps": data.get("steps") or [],
            "assertions": data.get("assertions") or [],
        }
        self.next_id += 1
        self.tables.setdefault(table, []).append(row)
        return row

    def create_many(self, table: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [self.create(table, row) for row in rows]

    def update(self, table: str, item_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
        row = self.get(table, item_id)
        if not row:
            return None
        for key, value in data.items():
            if value is not None:
                row[key] = value
        return row

    def update_if_status(self, table, item_id, expected, data):
        row = self.get(table, item_id)
        return self.update(table, item_id, data) if row and row.get("status") == expected else None

    def complete_agent_task(self, task_id, node_key, status, data, records):
        row = self.get("agent_tasks", task_id)
        if row["status"] in {"success", "failed", "canceled"}:
            return row
        data["saved_records"] = self.create_many("execution_records", records)
        return self.update("agent_tasks", task_id, {"status": status, "data": data})

    def patch_running_agent_task(self, task_id, node_key, patch, expected=None):
        row = self.get("agent_tasks", task_id)
        if not row or row["status"] != "running" or row["data"].get("claimed_by") != node_key:
            return None
        if expected is not None and any(row["data"].get(key, {}) != value for key, value in expected.items()):
            return None
        return self.update("agent_tasks", task_id, {"data": {**row["data"], **patch}})

    def resolve_app_connection(self, task_id, node_key, transition):
        task = self.get('agent_tasks', task_id)
        resource = transition['resource']
        row = self.get(resource['table'], resource['id'])
        if not task or task['status'] != 'running' or task['data'].get('claimed_by') != node_key or \
                any(task['data'].get(k) != v for k,v in transition['expected'].items()):
            return None
        if not row or row['status'] != 'active' or row.get('project_id') != resource['project_id'] or row['name'] != resource.get('name', row['name']) or \
                any(row['data'].get(k) != v for k,v in resource['expected_data'].items()):
            return None
        self.update(resource['table'], row['id'], {'data':{**row['data'], **resource['patch']}})
        return self.update('agent_tasks', task_id, {'data':{**task['data'], **transition['patch']}})

    def delete(self, table: str, item_id: int) -> bool:
        return False

    def batch_delete(self, table: str, ids: list[int]) -> int:
        return 0

    def delete_by_project(self, table: str, project_id: int) -> int:
        return 0


class AgentServiceTest(unittest.TestCase):
    def test_register_and_heartbeat_update_agent_node(self) -> None:
        repository = FakeResourceRepository()
        service = AgentNodeService(repository)

        node = service.register(
            AgentRegisterRequest(
                node_key="local-win-01",
                name="本机调试节点",
                version="0.1.0",
                capabilities=["case_execution"],
            )
        )
        updated = service.heartbeat(
            "local-win-01",
            AgentHeartbeatRequest(current_task_id=12, capabilities=["case_execution", "stagehand"]),
        )

        self.assertEqual(node["id"], updated["id"])
        self.assertEqual(updated["data"]["agent_status"], "online")
        self.assertEqual(updated["data"]["current_task_id"], 12)
        self.assertIn("stagehand", updated["data"]["capabilities"])

    def test_agent_token_is_node_scoped_and_hash_is_hidden(self) -> None:
        repository = FakeResourceRepository()
        service = AgentNodeService(repository)

        provisioned = service.provision_token(
            AgentTokenProvisionRequest(
                node_key="local-win-01",
                name="本机调试节点",
                capabilities=["case_execution"],
            )
        )
        token = provisioned["agent_token"]
        node = service.verify_token("local-win-01", token)

        self.assertTrue(str(token).startswith("agt_"))
        self.assertTrue(node["data"]["has_agent_token"])
        self.assertNotIn("agent_token_hash", node["data"])
        self.assertNotIn("agent_token_hash", provisioned["node"]["data"])
        with self.assertRaises(BusinessRuleError):
            service.verify_token("local-win-01", "wrong-token")

    def test_set_default_local_headed_keeps_single_default_node(self) -> None:
        repository = FakeResourceRepository()
        service = AgentNodeService(repository)
        first = service.register(
            AgentRegisterRequest(
                node_key="local-win-01",
                name="本机调试节点 1",
                capabilities=["case_execution"],
            )
        )
        second = service.register(
            AgentRegisterRequest(
                node_key="local-win-02",
                name="本机调试节点 2",
                capabilities=["case_execution"],
            )
        )

        service.set_default_local_headed(int(first["id"]))
        default_node = service.set_default_local_headed(int(second["id"]))

        self.assertTrue(default_node["data"]["default_local_headed"])
        self.assertFalse(repository.get("agent_nodes", int(first["id"]))["data"]["default_local_headed"])

    def test_task_claim_and_report_follow_agent_task_status(self) -> None:
        repository = FakeResourceRepository()
        service = AgentTaskService(repository)
        service.create(
            AgentTaskCreateRequest(
                task_type="case_execution",
                node_key="local-win-01",
                payload={"case_type": "WEB"},
            )
        )

        claimed = service.claim_next(
            AgentTaskClaimRequest(node_key="local-win-01", capabilities=["case_execution"]).node_key,
            ["case_execution"],
        )
        self.assertIsNotNone(claimed)
        assert claimed is not None
        self.assertEqual(claimed["status"], "running")

        reported = service.report(
            int(claimed["id"]),
            AgentTaskReportRequest(
                node_key="local-win-01",
                lease_token=claimed["data"]["lease_token"],
                status="success",
                result={
                    "records": [
                        {
                            "name": "WEB 用例执行 - 登录",
                            "project_id": 1,
                            "status": "success",
                            "data": {"case_id": 1, "case_type": "WEB"},
                        }
                    ]
                },
            ),
        )
        self.assertIsNotNone(reported)
        assert reported is not None
        self.assertEqual(reported["status"], "success")
        self.assertEqual(reported["data"]["saved_records"][0]["data"]["case_id"], 1)

    def test_agent_report_persists_screenshot_artifact(self) -> None:
        repository = FakeResourceRepository()
        service = AgentTaskService(repository)
        task = service.create(
            AgentTaskCreateRequest(
                task_type="case_execution",
                node_key="local-win-01",
                payload={"case_type": "WEB"},
            )
        )
        original_dir = agent_task_service_module.SCREENSHOT_DIR
        claimed = service.claim_next("local-win-01", ["case_execution"])
        with tempfile.TemporaryDirectory() as temp_dir:
            agent_task_service_module.SCREENSHOT_DIR = Path(temp_dir)
            try:
                reported = service.report(
                    int(task["id"]),
                    AgentTaskReportRequest(
                        node_key="local-win-01",
                        lease_token=claimed["data"]["lease_token"],
                        status="success",
                        result={
                            "records": [
                                {
                                    "name": "WEB case",
                                    "project_id": 1,
                                    "status": "success",
                                    "data": {
                                        "case_id": 1,
                                        "case_type": "WEB",
                                        "screenshots": [
                                            {
                                                "screenshot_file": "case_1.png",
                                                "screenshot_base64": base64.b64encode(PNG_BYTES).decode("ascii"),
                                                "local_path": "D:\\agent\\case_1.png",
                                            }
                                        ],
                                    },
                                }
                            ]
                        },
                    ),
                )
            finally:
                agent_task_service_module.SCREENSHOT_DIR = original_dir

            self.assertTrue((Path(temp_dir) / "case_1.png").exists())
        self.assertIsNotNone(reported)
        assert reported is not None
        saved_data = reported["data"]["saved_records"][0]["data"]
        screenshot = saved_data["screenshots"][0]
        self.assertEqual(saved_data["screenshot_url"], "/api/v1/screenshots/case_1.png")
        self.assertEqual(screenshot["screenshot_url"], "/api/v1/screenshots/case_1.png")
        self.assertNotIn("screenshot_base64", screenshot)
        self.assertNotIn("local_path", screenshot)

    def test_dispatcher_queues_web_headed_execution_with_node(self) -> None:
        repository = FakeResourceRepository()
        repository.create(
            "web_test_cases",
            {
                "name": "登录",
                "project_id": 1,
                "source_id": 2,
                "status": "active",
                "data": {"url": "http://example.test/login"},
                "steps": [{"name": "登录", "action": "click"}],
            },
        )
        repository.create(
            "web_pages",
            {
                "name": "登录页",
                "project_id": 1,
                "data": {"url": "/login"},
            },
        )
        dispatcher = CaseExecutionDispatcher(repository)

        result = dispatcher.execute(
            "WEB",
            {"mode": "local_headed", "node_id": "local-win-01", "case_ids": [1]},
        )

        self.assertEqual(result["queued_count"], 1)
        self.assertEqual(result["agent_task"]["status"], "pending")
        self.assertEqual(result["agent_task"]["data"]["task_type"], "case_execution")
        self.assertEqual(result["agent_task"]["data"]["payload"]["cases"][0]["name"], "登录")
        self.assertEqual(result["agent_task"]["data"]["payload"]["cases"][0]["steps"][0]["name"], "登录")

    def test_agent_auth_context_is_task_scoped_and_single_use(self) -> None:
        repository = FakeResourceRepository()
        auth = repository.create(
            "project_auth",
            {
                "name": "Web Cookie",
                "project_id": 1,
                "status": "active",
                "data": {
                    "auth_type": "cookie",
                    "login_case_type": "WEB",
                    "login_case_id": 99,
                    "cookies": [{"name": "sid", "value": "abc", "url": "http://example.test"}],
                },
            },
        )
        case = repository.create(
            "web_test_cases",
            {
                "name": "新增仓库",
                "project_id": 1,
                "source_id": None,
                "status": "active",
                "data": {"url": "http://example.test/warehouse", "auth_id": auth["id"]},
                "steps": [{"name": "新增", "action": "click"}],
            },
        )
        dispatcher = CaseExecutionDispatcher(repository)
        queued = dispatcher.execute(
            "WEB",
            {"mode": "local_headed", "node_id": "local-win-01", "case_ids": [case["id"]]},
        )
        task = queued["agent_task"]
        service = AgentTaskService(repository)
        claimed = service.claim_next("local-win-01", ["case_execution"])
        self.assertIsNotNone(claimed)
        assert claimed is not None

        context = claimed["data"]["payload"]["context"]
        snapshot = context["auth_snapshots"][str(case["id"])]
        auth_context = service.consume_auth_context(int(task["id"]), "local-win-01", snapshot["snapshot_id"])

        self.assertEqual(auth_context["snapshot_id"], snapshot["snapshot_id"])
        self.assertEqual(auth_context["cookies"][0]["name"], "sid")
        self.assertEqual(auth_context["storage_state"]["cookies"][0]["value"], "abc")
        with self.assertRaises(BusinessRuleError):
            service.consume_auth_context(int(task["id"]), "local-win-01", snapshot["snapshot_id"])

    def test_ai_engine_task_requires_stagehand_capability_and_consumes_model_secret_once(self) -> None:
        repository = FakeResourceRepository()
        repository.create(
            "ai_models",
            {
                "name": "Stagehand Model",
                "status": "active",
                "data": {
                    "model": "gpt-test",
                    "base_url": "https://api.example.test/v1",
                    "api_key_file": "stagehand.json",
                    "is_current": True,
                },
            },
        )
        case = repository.create(
            "web_test_cases",
            {
                "name": "新增仓库",
                "project_id": 1,
                "source_id": None,
                "status": "active",
                "data": {"url": "http://example.test/warehouse"},
                "steps": [{"name": "新增", "action": "click"}],
            },
        )

        queued = CaseExecutionDispatcher(repository).execute(
            "WEB",
            {
                "mode": "local_headed",
                "node_id": "local-win-01",
                "case_ids": [case["id"]],
                "config": {"engine": "stagehand"},
            },
        )
        task = queued["agent_task"]
        context = task["data"]["payload"]["context"]

        self.assertNotIn("api_key", context["ai_model"])
        self.assertTrue(str(context["ai_model"]["snapshot_id"]).startswith("ai_"))

        service = AgentTaskService(repository)
        self.assertIsNone(service.claim_next("local-win-01", ["case_execution"]))
        claimed = service.claim_next("local-win-01", ["case_execution", "stagehand"])
        self.assertIsNotNone(claimed)
        assert claimed is not None

        snapshot_id = context["ai_model"]["snapshot_id"]
        with patch("app.services.ai_secret_service.AiSecretService.load_api_key", return_value="sk-test"):
            model_context = service.consume_ai_model_context(int(task["id"]), "local-win-01", snapshot_id)

        self.assertNotIn("api_key", model_context)
        self.assertEqual(model_context["transport"], "platform_proxy")
        self.assertEqual(model_context["model_name"], "gpt-test")
        with self.assertRaises(BusinessRuleError):
            service.consume_ai_model_context(int(task["id"]), "local-win-01", snapshot_id)

    def test_web_auth_context_keeps_top_level_cookies_when_storage_state_is_empty(self) -> None:
        service = ProjectAuthService(FakeResourceRepository())

        storage_state = service._auth_storage_state(
            {"storage_state": {"cookies": [], "origins": []}},
            [{"name": "Admin-Token", "value": "abc", "domain": "test.example.com", "path": "/"}],
        )

        self.assertEqual(storage_state["cookies"][0]["name"], "Admin-Token")

    def test_server_web_execution_ignores_headed_config(self) -> None:
        repository = FakeResourceRepository()
        repository.create(
            "system_dictionaries",
            {
                "name": "Playwright run mode",
                "status": "active",
                "data": {
                    "dict_type": "playwright_execution",
                    "dict_key": "run_mode",
                    "dict_value": "headed",
                },
            },
        )

        config = WebCaseExecutor(repository).playwright_execution_config(
            {"mode": "server_headless", "config": {"run_mode": "headed"}}
        )

        self.assertEqual(config["run_mode"], "server_headless")
        self.assertTrue(config["headless"])


if __name__ == "__main__":
    unittest.main()
