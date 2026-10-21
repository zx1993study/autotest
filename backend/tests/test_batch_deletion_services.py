import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleError, ResourceNotFoundError
from app.models.resource_record import ResourceRecord
from app.repositories.sqlalchemy_resource_repository import SqlAlchemyResourceRepository
from app.services.app_feature_testing_service import AppFeatureTestingService
from app.services.execution_flow_service import ExecutionFlowService


class BatchDeletionServicesTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        ResourceRecord.__table__.create(self.engine)
        self.db = Session(self.engine)
        self.repo = SqlAlchemyResourceRepository(self.db)
        self.addCleanup(self.engine.dispose)
        self.addCleanup(self.db.close)

    def create(self, table, **payload):
        return self.repo.create(table, {"name": "Test", **payload})["id"]

    def test_app_feature_batch_is_idempotent_and_keeps_run_history(self):
        first = self.create("app_features")
        second = self.create("app_features")
        child = self.create("app_feature_scenarios", data={"feature_id": first})
        history = self.create("app_scenario_runs", data={"feature_id": first})
        service = AppFeatureTestingService(self.repo)
        self.assertEqual(service.batch_delete_features([first, first, 9999]), {"deleted_count": 1})
        self.assertEqual(service.batch_delete_features([first]), {"deleted_count": 0})
        self.assertIsNone(self.repo.get("app_feature_scenarios", child))
        self.assertIsNotNone(self.repo.get("app_scenario_runs", history))
        self.assertTrue(service.delete_feature(second))
        with self.assertRaises(ResourceNotFoundError):
            service.delete_feature(second)

    def test_active_flow_rejects_entire_batch_without_partial_deletion(self):
        first = self.create("execution_flows")
        second = self.create("execution_flows")
        child = self.create("api_flow_scenarios", data={"flow_id": first})
        stale = self.create("api_flow_runs", status="queued", data={"flow_id": first, "results": []})
        active = self.create("api_flow_runs", status="running", data={"flow_id": second, "results": []})
        with patch("app.scheduler.jobs.api_flow_jobs.is_batch_active", side_effect=lambda key: key == active), self.assertRaises(BusinessRuleError):
            ExecutionFlowService(self.repo).batch_delete([first, second])
        for table, key in (("execution_flows", first), ("execution_flows", second), ("api_flow_scenarios", child)):
            self.assertIsNotNone(self.repo.get(table, key))
        self.assertEqual(self.repo.get("api_flow_runs", stale)["status"], "queued")

    def test_stale_runs_reconcile_once_and_completed_history_is_untouched(self):
        first = self.create("execution_flows")
        second = self.create("execution_flows")
        child = self.create("api_flow_scenarios", data={"flow_id": first})
        queued = self.create("api_flow_runs", status="queued", data={"flow_id": first, "results": [{"status": "queued"}]})
        running = self.create("api_flow_runs", status="running", data={"flow_id": second, "results": [{"status": "running"}, {"status": "success"}]})
        completed = self.create("api_flow_runs", status="success", data={"flow_id": first, "results": [{"status": "success"}]})
        service = ExecutionFlowService(self.repo)
        with patch("app.scheduler.jobs.api_flow_jobs.is_batch_active", return_value=False), patch.object(
            self.repo, "update_many", wraps=self.repo.update_many,
        ) as update_many:
            self.assertEqual(service.batch_delete([first, second, first, 9999]), {"deleted_count": 2})
        self.assertEqual(update_many.call_count, 1)
        self.assertIsNone(self.repo.get("api_flow_scenarios", child))
        self.assertEqual(self.repo.get("api_flow_runs", queued)["data"]["results"][0]["status"], "interrupted")
        self.assertEqual(self.repo.get("api_flow_runs", running)["data"]["results"][1]["status"], "success")
        self.assertEqual(self.repo.get("api_flow_runs", completed)["status"], "success")
        self.assertEqual(service.batch_delete([first, second]), {"deleted_count": 0})
        with self.assertRaises(ResourceNotFoundError):
            service.delete(first)
