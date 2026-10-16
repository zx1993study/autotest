from datetime import UTC, datetime

from app.core.exceptions import ResourceNotFoundError
from app.schemas.agent import AgentTaskCreateRequest
from app.services.agent_task_service import AgentTaskService
from app.services.app_agent_execution_service import AppAgentExecutionService


class AgentDeviceDiscoveryService:
    def __init__(self, repository):
        self.repository = repository

    def queue(self, node_key, subnet=None, ports=None):
        node_key = AppAgentExecutionService(self.repository)._node(node_key)
        devices, _ = self.repository.list("app_devices", page=1, page_size=10000)
        known = [self._device(item) for item in devices if not (item.get("data") or {}).get("node_key") or (item.get("data") or {}).get("node_key") == node_key]
        task = AgentTaskService(self.repository).create(AgentTaskCreateRequest(task_type="device_discovery", node_key=node_key, payload={"subnet": subnet, "ports": ports or [8100], "known_devices": known}))
        return {"queued": True, "agent_task": task}

    def queue_check(self, ids):
        devices, _ = self.repository.list("app_devices", page=1, page_size=10000)
        if ids:
            devices = [item for item in devices if item["id"] in ids]
            if len(devices) != len(set(ids)):
                raise ResourceNotFoundError("设备不存在")
        groups = {}
        for item in devices:
            key = AppAgentExecutionService(self.repository)._node((item.get("data") or {}).get("node_key"))
            groups.setdefault(key, []).append(self._device(item))
        tasks = [AgentTaskService(self.repository).create(AgentTaskCreateRequest(task_type="device_discovery", node_key=key, payload={"action": "check", "known_devices": items})) for key, items in groups.items()]
        return {"queued": True, "agent_tasks": tasks}

    def finish(self, task):
        data = task.get("data") or {}
        payload = data.get("payload") or {}
        if data.get("task_type") != "device_discovery" or payload.get("action") != "check" or task.get("status") != "success":
            return
        online = {item.get("existing_id") for item in (data.get("result") or {}).get("items", [])}
        for saved in payload.get("known_devices", []):
            row = self.repository.get("app_devices", int(saved["id"]))
            if not row:
                continue
            row_data = row.get("data") or {}
            if row_data.get("node_key") and row_data["node_key"] != data.get("node_key"):
                continue
            status = "online" if row["id"] in online else "offline"
            self.repository.update("app_devices", row["id"], {"data": {**row_data, "connection_status": status, "wda_status": status, "last_check_at": datetime.now(UTC).isoformat()}})

    @staticmethod
    def _device(item):
        allowed = ("platform", "wda_url", "udid", "platform_version", "device_name", "device_form_factor", "node_key")
        return {"id": item["id"], "name": item.get("name"), "data": {key: value for key, value in (item.get("data") or {}).items() if key in allowed}}
