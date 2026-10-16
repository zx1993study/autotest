from __future__ import annotations

from datetime import UTC, datetime

from web_automation.models import MANIFEST_VERSION

from app.core.exceptions import BusinessRuleError
from app.schemas.agent import AgentTaskCreateRequest


class AppAgentExecutionService:
    def __init__(self, repository) -> None:
        self.repository = repository

    def prepare_formal(self, cases, payload):
        config = dict(payload.get("config") or {})
        device_ids = config.get("device_ids") or []
        if len(device_ids) > 1:
            raise BusinessRuleError("手机任务请按设备分别提交")
        device_id = config.get("device_id") or (device_ids[0] if device_ids else None) or (cases[0].get("data") or {}).get("device_id")
        device = self.repository.get("app_devices", int(device_id)) if device_id else None
        if not device:
            raise BusinessRuleError("请选择执行设备")
        from app.services.app_exploration_service import AppExplorationService
        tasks,_ = self.repository.list('agent_tasks',page_size=10000)
        AppExplorationService.require_available(device['id'],tasks)
        bound = (device.get("data") or {}).get("node_key")
        key = payload.get("node_id")
        if bound and key and bound != key:
            raise BusinessRuleError("设备已绑定其他执行节点")
        key = self._node(key or bound)
        prepared = []
        for case in cases:
            data = dict(case.get("data") or {})
            if data.get("entry_id"):
                entry = self.repository.get("app_entries", int(data["entry_id"]))
                entry_data = (entry or {}).get("data") or {}
                data.setdefault("bundle_id", entry_data.get("bundle_id") or entry_data.get("bundleId"))
            prepared.append({**case, "data": data})
        return prepared, {**payload, "node_id": key, "mode": "remote_node", "config": config}, {"device": device}

    def queue(self, scenario, device, case, execution, node_key=None):
        from app.services.agent_task_service import AgentTaskService

        if not device:
            raise BusinessRuleError("请选择执行设备")
        device_data = device.get("data") or {}
        bound = str(device_data.get("node_key") or "")
        if bound and node_key and bound != node_key:
            raise BusinessRuleError("设备已绑定其他执行节点")
        node_key = self._node(node_key or bound)
        from app.services.app_exploration_service import AppExplorationService
        tasks,_ = self.repository.list('agent_tasks',page_size=10000)
        AppExplorationService.require_available(device['id'],tasks)
        data = scenario.get("data") or {}
        entry = self.repository.get("app_entries", int(data["entry_id"])) if data.get("entry_id") else None
        entry_data = (entry or {}).get("data") or {}
        bundle_id = str(entry_data.get("bundle_id") or entry_data.get("bundleId") or device_data.get("bundle_id") or "")
        run = self.repository.create("app_scenario_runs", {"name": f"{scenario.get('name')} - Agent", "project_id": scenario.get("project_id"), "status": "queued", "data": {"scenario_id": scenario["id"], "feature_id": data.get("feature_id"), "device_id": device["id"], "device_name": device.get("name"), "input_snapshot": case["data"].get("input_info", {}), "node_key": node_key}})
        try:
            task = AgentTaskService(self.repository).create(AgentTaskCreateRequest(task_type="case_execution", node_key=node_key, payload={"manifest_version": MANIFEST_VERSION, "case_type": "APP", "cases": [case], "execution": execution, "context": {"scenario_id": scenario["id"], "run_id": run["id"], "device": device, "bundle_id": bundle_id}}))
        except Exception:
            self.repository.update("app_scenario_runs", int(run["id"]), {"status": "failed", "description": "任务创建失败，设备未执行"})
            raise
        run = self.repository.update("app_scenario_runs", int(run["id"]), {"data": {**run["data"], "agent_task_id": task["id"]}}) or run
        return {"run": run, "execution_record": None, "agent_task": task, "queued": True}

    def _node(self, key):
        rows, _ = self.repository.list("agent_nodes", page=1, page_size=10000)
        candidates = []
        for row in rows:
            data = row.get("data") or {}
            if key and data.get("node_key") != key:
                continue
            if row.get("status") != "active" or "app_execution" not in data.get("capabilities", []):
                continue
            try:
                seen = datetime.fromisoformat(str(data.get("last_seen_at") or ""))
                age = (datetime.now(UTC) - seen.replace(tzinfo=seen.tzinfo or UTC)).total_seconds()
            except ValueError:
                continue
            if age < 90 and data.get("agent_status") in {"online", "busy"}:
                candidates.append(str(data["node_key"]))
        if len(candidates) != 1:
            raise BusinessRuleError("请选择一个在线且已安装手机插件的执行节点")
        return candidates[0]

    def finish(self, task):
        data = task.get("data") or {}
        if data.get('task_type') == 'app_exploration':
            from app.services.app_exploration_result_service import AppExplorationResultService

            AppExplorationResultService(self.repository).finish(task)
            return
        context = (data.get("payload") or {}).get("context") or {}
        run_id = context.get("run_id")
        if not run_id:
            return
        run = self.repository.get("app_scenario_runs", int(run_id))
        if not run:
            return
        records = data.get("saved_records") or []
        record = records[0] if records else {}
        run_data = {**run.get("data", {}), **record.get("data", {}), "execution_record_id": record.get("id"), "error": (record.get("data") or {}).get("error") or data.get("error") or ""}
        run = self.repository.update("app_scenario_runs", int(run_id), {"status": task["status"], "description": run_data["error"], "data": run_data}) or run
        from app.services.app_feature_testing_service import AppFeatureTestingService

        service = AppFeatureTestingService(self.repository)
        scenario = self.repository.get("app_feature_scenarios", int(context["scenario_id"]))
        if not scenario:
            return
        feature_id = (scenario.get("data") or {}).get("feature_id")
        feature = self.repository.get("app_features", int(feature_id)) if feature_id else None
        service._update_last_run(scenario, run)
        if feature:
            service._update_feature_last_run(feature, run)
        if task["status"] == "failed":
            service._archive_failure_knowledge(scenario, run, feature, run_data.get("device_id"))
