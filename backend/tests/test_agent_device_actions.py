from datetime import datetime, timezone
import unittest
from unittest.mock import patch

from app.core.exceptions import BusinessRuleError
from app.schemas.app_device import DiscoveredDeviceImportRequest
from app.schemas.agent import AgentTaskReportRequest
from app.services.agent_device_discovery_service import AgentDeviceDiscoveryService
from app.services.agent_task_service import AgentTaskService
from app.services.app_device_import_service import AppDeviceImportService
from test_agent_services import FakeResourceRepository


class AgentDeviceActionsTest(unittest.TestCase):
    def setUp(self):
        self.repo = FakeResourceRepository()
        self.repo.create("agent_nodes", {"name": "PC", "status": "active", "data": {"node_key": "test-node", "capabilities": ["case_execution", "app_execution", "device_discovery"], "agent_status": "online", "last_seen_at": datetime.now(timezone.utc).isoformat()}})
        self.device = self.repo.create("app_devices", {"name": "iPhone", "data": {"node_key": "test-node", "platform": "iOS", "udid": "phone", "wda_url": "http://192.168.1.4:8100", "secret": "must-not-send"}})

    def test_scan_only_sends_device_connection_fields(self):
        queued = AgentDeviceDiscoveryService(self.repo).queue("test-node")
        known = queued["agent_task"]["data"]["payload"]["known_devices"]
        self.assertNotIn("secret", known[0]["data"])

    def test_check_updates_device_after_agent_report_and_is_idempotent(self):
        service = AgentDeviceDiscoveryService(self.repo)
        task = service.queue_check([self.device["id"]])["agent_tasks"][0]
        tasks = AgentTaskService(self.repo)
        claimed = tasks.claim_next("test-node", ["device_discovery"])
        report = AgentTaskReportRequest(node_key="test-node", lease_token=claimed["data"]["lease_token"], status="success", result={"items": [{"existing_id": self.device["id"]}], "records": []})
        tasks.report(task["id"], report)
        tasks.report(task["id"], report)
        self.assertEqual(self.repo.get("app_devices", self.device["id"])["data"]["wda_status"], "online")

    def test_import_preserves_existing_configuration_and_node_binding(self):
        payload = DiscoveredDeviceImportRequest(items=[{"platform": "iOS", "udid": "phone", "node_key": "test-node", "wda_url": "http://192.168.1.5:8100"}])
        result = AppDeviceImportService(self.repo).import_discovered(payload)
        self.assertEqual(result["updated_count"], 1)
        self.assertEqual(result["updated"][0]["data"]["secret"], "must-not-send")
        payload.items[0]["node_key"] = "other-node"
        with self.assertRaises(BusinessRuleError):
            AppDeviceImportService(self.repo).import_discovered(payload)

    def test_old_pages_and_server_wda_start_are_not_registered(self):
        from app.api.v1.router import api_router

        paths = {route.path for route in api_router.routes}
        for path in ("/app-testing/pages", "/app-testing/elements", "/app-testing/case-drafts", "/app-testing/cases", "/app-testing/devices/wda/start"):
            self.assertNotIn(path, paths)


if __name__ == "__main__":
    unittest.main()
