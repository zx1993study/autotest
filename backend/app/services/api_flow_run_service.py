from copy import deepcopy
from datetime import UTC, datetime

from app.core.exceptions import BusinessRuleError, ResourceNotFoundError
from app.services.api_flow_preparation_service import ApiFlowPreparationService
from app.services.api_flow_scenario_service import ApiFlowScenarioService
from app.services.execution_flow_service import ExecutionFlowService
from app.services.resource_service import ResourceService


class ApiFlowRunService(ResourceService):
    """Own batch history and its internal scenario/node evidence."""

    def __init__(self, repository):
        super().__init__("api_flow_runs", repository)

    def create_batch(self, flow_id, payload):
        flow = ExecutionFlowService(self.repository).get(flow_id)
        if flow["status"] != "active":
            raise BusinessRuleError("流程未启用")
        scenarios = ApiFlowScenarioService(self.repository)
        selected = []
        for scene_id in dict.fromkeys(payload["scenario_ids"]):
            scene = scenarios.get_for_flow(flow_id, scene_id)
            if scene["status"] != "active":
                raise BusinessRuleError(f"{scene['name']}已停用")
            if scene["data"]["template_version"] != flow["data"]["version"]:
                raise BusinessRuleError(f"{scene['name']}需要先同步模板")
            selected.append(scene)
        snapshots = ApiFlowPreparationService(self.repository).build(flow, selected, payload.get("inputs", {}))
        concurrency = payload["concurrency"] if payload["mode"] == "parallel" else 1
        batch = super().create({"name": f"{flow['name']} - {datetime.now(UTC).strftime('%m-%d %H:%M:%S')}",
                                "project_id": flow["project_id"], "status": "queued", "data": {
                                    "flow_id": flow_id, "flow_name": flow["name"], "template_version": flow["data"]["version"],
                                    "mode": payload["mode"], "concurrency": concurrency,
                                    "results": [{"scenario_id": row["scenario"]["id"], "name": row["scenario"]["name"],
                                                 "test_point": row["scenario"].get("description") or row["scenario"]["name"],
                                                 "status": "queued", "nodes": []} for row in snapshots]}})
        from app.scheduler.jobs.api_flow_jobs import submit_api_flow_batch
        submit_api_flow_batch(batch["id"], snapshots, concurrency)
        return batch

    def list_for_flow(self, flow_id):
        ExecutionFlowService(self.repository).get(flow_id)
        rows, _ = self.repository.list(self.table, page_size=200, data_filters={"flow_id": flow_id})
        return [self._reconcile(row, summary=True) for row in rows]

    def get_for_flow(self, flow_id, batch_id):
        row = super().get(batch_id)
        if row["data"]["flow_id"] != flow_id:
            raise ResourceNotFoundError("运行记录不属于当前流程")
        return self._reconcile(row)

    def cancel(self, flow_id, batch_id):
        row = self.get_for_flow(flow_id, batch_id)
        from app.scheduler.jobs.api_flow_jobs import cancel_batch
        requested = cancel_batch(batch_id) if row["status"] in {"queued", "running"} else False
        return {"requested": requested, "message": "已请求取消，当前请求结束后停止" if requested else "批次已结束"}

    def mark_running(self, batch_id):
        super().update(batch_id, {"status": "running"})

    def save_result(self, batch_id, result):
        row = super().get(batch_id)
        data = deepcopy(row["data"])
        data["results"] = [result if item["scenario_id"] == result["scenario_id"] else item for item in data["results"]]
        super().update(batch_id, {"data": data})
        scene = self.repository.get("api_flow_scenarios", result["scenario_id"])
        if scene and result["status"] != "running":
            scene_data = {**scene["data"], "latest_status": result["status"], "latest_run_id": batch_id}
            self.repository.update("api_flow_scenarios", scene["id"], {"data": scene_data})

    def finish(self, batch_id):
        row = super().get(batch_id)
        statuses = [item["status"] for item in row["data"]["results"]]
        status = "cancelled" if "cancelled" in statuses else "success" if all(s == "success" for s in statuses) else "failed"
        super().update(batch_id, {"status": status})

    def interrupt(self, batch_id):
        row = super().get(batch_id)
        return super().update(batch_id, self._interruption_payload(row))

    def interrupt_many(self, rows):
        if not rows:
            return []
        return self.repository.update_many(self.table, [
            (row["id"], self._interruption_payload(row)) for row in rows
        ])

    @staticmethod
    def _interruption_payload(row):
        data = deepcopy(row["data"])
        for result in data["results"]:
            if result["status"] in {"queued", "running"}:
                result.update(status="interrupted", error="服务重启或执行异常，批次已中断")
        return {"status": "interrupted", "data": data}

    def _reconcile(self, row, summary=False):
        from app.scheduler.jobs.api_flow_jobs import is_batch_active
        if row["status"] in {"queued", "running"} and not is_batch_active(row["id"]):
            row = self.interrupt(row["id"])
        if summary:
            row = deepcopy(row)
            row["data"]["results"] = [{key: result.get(key) for key in ("scenario_id", "name", "status", "duration_ms")}
                                        for result in row["data"]["results"]]
        return row
