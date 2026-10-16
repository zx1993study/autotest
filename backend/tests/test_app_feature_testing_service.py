from __future__ import annotations

import unittest
from copy import deepcopy
from datetime import datetime, timezone

from app.services.app_feature_testing_service import AppFeatureTestingService
from app.services.app_agent_execution_service import AppAgentExecutionService


class FakeResourceRepository:
    def __init__(self) -> None:
        self.next_id = 100
        self.rows: dict[str, list[dict[str, object]]] = {
            "projects": [{"id": 1, "name": "移动端项目", "project_id": None, "status": "active", "data": {}}],
            "agent_nodes": [{"id": 7, "name": "PC", "status": "active", "data": {"node_key": "node-one", "agent_status": "online", "last_seen_at": datetime.now(timezone.utc).isoformat(), "capabilities": ["case_execution", "app_execution"]}}],
            "app_features": [
                {
                    "id": 10,
                    "name": "登录",
                    "project_id": 1,
                    "description": "",
                    "status": "active",
                    "data": {"default_device_id": 30},
                }
            ],
            "app_feature_scenarios": [],
            "app_scenario_runs": [],
            "app_entries": [],
            "app_devices": [
                {
                    "id": 30,
                    "name": "iPhone",
                    "project_id": 1,
                    "status": "active",
                    "data": {"platform": "iOS", "connection_status": "online", "wda_url": "http://127.0.0.1:8100"},
                }
            ],
            "project_knowledge": [
                {
                    "id": 40,
                    "name": "登录失败经验",
                    "project_id": 1,
                    "status": "active",
                    "data": {
                        "domain": "APP",
                        "kind": "app_failure_lesson",
                        "knowledge_key": "app.login.failure.lesson",
                        "priority": "P1",
                        "content": "登录按钮优先使用文本定位，失败时等待首页文案。",
                    },
                }
            ],
        }

    def list(
        self,
        table: str,
        keyword: str | None = None,
        project_id: int | None = None,
        page: int = 1,
        page_size: int = 20,
        data_filters: dict[str, object] | None = None,
    ) -> tuple[list[dict[str, object]], int]:
        rows = [deepcopy(row) for row in self.rows.get(table, []) if not row.get("deleted")]
        if project_id is not None:
            rows = [row for row in rows if row.get("project_id") in {project_id, None}]
        if keyword:
            rows = [row for row in rows if keyword in str(row.get("name") or "") or keyword in str(row.get("description") or "")]
        for key, value in (data_filters or {}).items():
            if value in (None, ""):
                continue
            if key == "status":
                rows = [row for row in rows if row.get("status") == value]
            else:
                rows = [row for row in rows if isinstance(row.get("data"), dict) and row["data"].get(key) == value]
        total = len(rows)
        start = (page - 1) * page_size
        return rows[start : start + page_size], total

    def get(self, table: str, item_id: int) -> dict[str, object] | None:
        for row in self.rows.get(table, []):
            if row.get("id") == item_id and not row.get("deleted"):
                return deepcopy(row)
        return None

    def app_feature_summaries(self, feature_ids):
        result = {}
        for key in feature_ids:
            scenes = [row for row in self.rows["app_feature_scenarios"] if not row.get("deleted") and row.get("data", {}).get("feature_id") == key]
            runs = [row["data"]["last_run"] for row in scenes if isinstance(row.get("data", {}).get("last_run"), dict)]
            latest = max(runs, key=lambda row: str(row.get("updated_at") or row.get("created_at") or ""), default=None)
            result[key] = {"scenario_count": len(scenes), "last_run": latest}
        return result

    def create(self, table: str, data: dict[str, object]) -> dict[str, object]:
        row = {
            "id": self.next_id,
            "created_at": "2026-10-08T10:00:00",
            "updated_at": "2026-10-08T10:00:00",
            **deepcopy(data),
        }
        self.next_id += 1
        self.rows.setdefault(table, []).append(row)
        return deepcopy(row)

    def update(self, table: str, item_id: int, data: dict[str, object]) -> dict[str, object] | None:
        for row in self.rows.get(table, []):
            if row.get("id") != item_id or row.get("deleted"):
                continue
            row.update(deepcopy(data))
            row["updated_at"] = "2026-10-08T10:01:00"
            return deepcopy(row)
        return None

    def delete(self, table: str, item_id: int) -> bool:
        for row in self.rows.get(table, []):
            if row.get("id") == item_id:
                row["deleted"] = True
                return True
        return False

    def batch_delete(self, table: str, ids: list[int]) -> int:
        return sum(1 for item_id in ids if self.delete(table, item_id))


class AppFeatureTestingServiceTest(unittest.TestCase):
    def finish(self, repository, queued, record):
        task = queued["agent_task"]
        task["status"] = record["status"]
        task["data"]["saved_records"] = [record]
        AppAgentExecutionService(repository).finish(task)
        return {"run": repository.get("app_scenario_runs", queued["run"]["id"])}

    def test_dynamic_input_and_variables_are_saved_as_templates_but_run_records_actual_values(self) -> None:
        repository = FakeResourceRepository()
        service = AppFeatureTestingService(repository)
        variables = {"customer_phone": {"generator": "phone", "prefix": "138"}}
        scenario = service.create_scenario(10, {"name": "Dynamic input", "variables": variables,
            "input_info": {"phone": {"value": "{{customer_phone}}"}},
            "operation_steps": [{"action": "input", "input_key": "phone"}]})
        self.assertEqual(variables, scenario["data"]["variables"])
        service.update_scenario(scenario["id"], {"variables": {"customer_phone": {"generator": "phone", "prefix": "139"}}})
        override = {"customer_phone": {"generator": "phone", "prefix": "137"}}
        queued = service.run_scenario(scenario["id"], {"variables": override})
        result = self.finish(repository, queued, {"id": 500, "status": "success", "data": {
                "input_snapshot": {"phone": {"value": "13700000001"}},
                "dynamic_values": {"values": {"customer_phone": "13700000001"}}}})
        self.assertEqual(override, queued["agent_task"]["data"]["payload"]["execution"]["config"]["variables"])
        self.assertEqual("13700000001", result["run"]["data"]["input_snapshot"]["phone"]["value"])
        self.assertEqual("13700000001", result["run"]["data"]["dynamic_values"]["values"]["customer_phone"])
        stored = repository.get("app_feature_scenarios", scenario["id"])
        self.assertEqual("{{customer_phone}}", stored["data"]["input_info"]["phone"]["value"])
        self.assertEqual("139", stored["data"]["variables"]["customer_phone"]["prefix"])

    def test_generate_from_text_persists_scenario_with_input_info(self) -> None:
        repository = FakeResourceRepository()
        service = AppFeatureTestingService(repository)

        result = service.generate_scenario_from_text(
            10,
            {
                "name": "账号密码登录成功",
                "prompt": "在账号输入test001，然后点击登录，然后校验首页",
                "device_id": 30,
                "record_video": True,
            },
        )

        scenario = result["scenario"]
        data = scenario["data"]
        self.assertEqual("app_feature_scenarios", "app_feature_scenarios")
        self.assertEqual(10, data["feature_id"])
        self.assertEqual("natural_language", data["source_type"])
        self.assertGreaterEqual(len(data["operation_steps"]), 3)
        self.assertTrue(data["input_info"])
        input_step = next(step for step in data["operation_steps"] if step.get("action") == "input")
        self.assertIn("input_key", input_step)
        self.assertTrue(str(input_step["value"]).startswith("${"))
        self.assertEqual("rule", data["generation_meta"]["mode"])
        self.assertEqual([40], data["generation_meta"]["knowledge_ids"])

    def test_run_scenario_records_evidence_and_updates_last_run(self) -> None:
        repository = FakeResourceRepository()
        repository.rows["app_feature_scenarios"].append(
            {
                "id": 20,
                "name": "账号密码登录成功",
                "project_id": 1,
                "description": "",
                "status": "active",
                "data": {
                    "feature_id": 10,
                    "device_id": 30,
                    "record_video": True,
                    "operation_steps": [
                        {"name": "输入账号", "action": "input", "input_key": "username", "value": "${username}"},
                        {"name": "点击登录", "action": "tap", "locator_type": "text", "locator": "登录"},
                    ],
                    "input_info": {"username": {"label": "账号", "type": "text", "value": "old"}},
                    "assertions": [],
                },
            }
        )
        service = AppFeatureTestingService(repository)

        queued = service.run_scenario(20, {"input_info": {"username": "new-user"}})
        result = self.finish(repository, queued, {
                "id": 200,
                "name": "执行记录",
                "project_id": 1,
                "status": "success",
                "description": "ok",
                "created_at": "2026-10-08T10:02:00",
                "updated_at": "2026-10-08T10:02:00",
                "data": {
                    "device_id": 30,
                    "device_name": "iPhone",
                    "duration_ms": 1234,
                    "video_url": "/api/v1/app-recordings/demo.mp4",
                    "screenshot_url": "/api/v1/screenshots/demo.png",
                    "step_timeline": [],
                    "screenshots": [],
                },
            })

        self.assertEqual("success", result["run"]["status"])
        self.assertEqual("new-user", result["run"]["data"]["input_snapshot"]["username"]["value"])
        scenario = repository.get("app_feature_scenarios", 20)
        feature = repository.get("app_features", 10)
        self.assertEqual("success", scenario["data"]["last_run"]["status"])
        self.assertEqual(20, feature["data"]["last_run"]["scenario_id"])

    def test_run_scenario_archives_failure_as_app_knowledge(self) -> None:
        repository = FakeResourceRepository()
        repository.rows["app_feature_scenarios"].append(
            {
                "id": 21,
                "name": "账号密码登录失败",
                "project_id": 1,
                "description": "",
                "status": "active",
                "data": {
                    "feature_id": 10,
                    "device_id": 30,
                    "record_video": True,
                    "operation_steps": [{"name": "点击登录", "action": "tap", "locator_type": "text", "locator": "登录"}],
                    "input_info": {},
                    "assertions": [],
                },
            }
        )
        service = AppFeatureTestingService(repository)

        queued = service.run_scenario(21, {})
        result = self.finish(repository, queued, {
                "id": 201,
                "name": "执行记录",
                "project_id": 1,
                "status": "failed",
                "description": "app element not found: 登录",
                "created_at": "2026-10-08T10:02:00",
                "updated_at": "2026-10-08T10:02:00",
                "data": {
                    "device_id": 30,
                    "device_name": "iPhone",
                    "error": "app element not found: 登录",
                    "step_timeline": [{"name": "点击登录", "action": "tap", "status": "failed", "error": "app element not found: 登录"}],
                    "screenshots": [],
                },
            })

        self.assertEqual("failed", result["run"]["status"])
        failure_knowledge = [
            row
            for row in repository.rows["project_knowledge"]
            if isinstance(row.get("data"), dict) and row["data"].get("run_id") == result["run"]["id"]
        ]
        self.assertEqual(1, len(failure_knowledge))
        self.assertEqual("app_failure_lesson", failure_knowledge[0]["data"]["kind"])


if __name__ == "__main__":
    unittest.main()
