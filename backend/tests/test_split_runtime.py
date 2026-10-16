from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.storage import storage_path
from app.core.exceptions import BusinessRuleError
from app.models.resource_record import ResourceRecord
from app.repositories.sqlalchemy_resource_repository import SqlAlchemyResourceRepository
from app.schemas.agent import AgentTaskCreateRequest, AgentTaskReportRequest
from app.services.agent_task_service import AgentTaskService
from app.services.app_feature_testing_service import AppFeatureTestingService
from test_agent_services import FakeResourceRepository


class SplitRuntimeTest(unittest.TestCase):
    def test_storage_is_outside_binary_tree(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {"AUTOTEST_STORAGE_DIR": temp}):
            self.assertEqual(storage_path("auth"), Path(temp).resolve() / "auth")

    def test_claim_is_compare_and_swap_and_report_is_transactional(self):
        engine = create_engine("sqlite://")
        ResourceRecord.__table__.create(engine)
        with Session(engine) as db:
            repository = SqlAlchemyResourceRepository(db)
            service = AgentTaskService(repository)
            task = service.create(AgentTaskCreateRequest(task_type="case_execution", node_key="node-one", payload={"case_type": "APP"}))
            claimed = service.claim_next("node-one", ["case_execution", "app_execution"])
            self.assertIsNotNone(claimed)
            self.assertIsNone(repository.update_if_status("agent_tasks", task["id"], "pending", {"status": "running"}))
            report = AgentTaskReportRequest(node_key="node-one", lease_token=claimed["data"]["lease_token"], status="success", result={"records": [{"name": "result", "status": "success", "data": {"case_type": "APP"}}]})
            service.report(task["id"], report)
            service.report(task["id"], report)
            self.assertEqual(repository.list("execution_records")[1], 1)
            with self.assertRaises(BusinessRuleError):
                service.report(task["id"], report.model_copy(update={"node_key": "node-two"}))
        engine.dispose()

    def test_scenario_is_queued_and_completed_without_server_device_access(self):
        repository = FakeResourceRepository()
        repository.create("agent_nodes", {"name": "PC", "status": "active", "data": {"node_key": "node-one", "agent_status": "online", "last_seen_at": datetime.now(timezone.utc).isoformat(), "capabilities": ["case_execution", "app_execution"]}})
        device = repository.create("app_devices", {"name": "iPhone", "data": {"node_key": "node-one", "wda_url": "http://192.168.50.184:8100"}})
        feature = repository.create("app_features", {"name": "Feature", "project_id": 1})
        service = AppFeatureTestingService(repository)
        scenario = service.create_scenario(feature["id"], {"name": "Scenario", "device_id": device["id"], "operation_steps": [{"action": "wait", "value": 1}]})
        queued = service.run_scenario(scenario["id"], {"node_id": "node-one"})
        task_service = AgentTaskService(repository)
        task = task_service.claim_next("node-one", ["case_execution", "app_execution"])
        task_service.report(task["id"], AgentTaskReportRequest(node_key="node-one", lease_token=task["data"]["lease_token"], status="success", result={"records": [{"name": "Scenario", "status": "success", "data": {"duration_ms": 10}}]}))
        self.assertEqual(service.get_run(queued["run"]["id"])["status"], "success")
        self.assertEqual(service.get_scenario(scenario["id"])["data"]["last_run"]["status"], "success")


if __name__ == "__main__":
    unittest.main()
