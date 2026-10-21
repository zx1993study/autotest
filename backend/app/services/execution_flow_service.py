import json
from copy import deepcopy

from app.core.exceptions import BusinessRuleError
from app.services.api_flow_validation import parse_definition, validate_references
from app.services.resource_service import ResourceService


class ExecutionFlowService(ResourceService):
    def __init__(self, repository):
        super().__init__("execution_flows", repository)

    def get(self, item_id):
        item = deepcopy(super().get(item_id))
        item["data"] = self.definition(item)
        return item

    def list(self, *args, **kwargs):
        rows, total = super().list(*args, **kwargs)
        summaries = self.repository.execution_flow_summaries([row["id"] for row in rows]) if rows else {}
        status_labels = {"success": "通过", "failed": "失败", "running": "执行中", "queued": "排队中",
                         "cancelled": "已取消", "interrupted": "已中断"}
        for row in rows:
            data = self.definition(row)
            summary = summaries[row["id"]]
            status = summary["latest_status"]
            row["data"] = {**data, "node_count": len(data["nodes"]), "scenario_count": summary["scenario_count"],
                           "latest_status": status_labels.get(status, status) if status is not None else "未执行"}
        return rows, total

    def create(self, payload):
        payload = deepcopy(payload)
        self._project(payload.get("project_id"))
        definition = parse_definition(payload.get("data") or {})
        definition["version"] = 1
        validate_references(self.repository, payload["project_id"], definition)
        payload["data"] = definition
        return super().create(payload)

    def update(self, item_id, payload):
        previous = self.get(item_id)
        project_id = payload.get("project_id", previous.get("project_id"))
        self._project(project_id)
        if project_id != previous.get("project_id"):
            _, scene_count = self.repository.list("api_flow_scenarios", page_size=1, data_filters={"flow_id": item_id})
            if previous["data"]["nodes"] or scene_count:
                raise BusinessRuleError("已有节点或场景的流程不能直接更换项目")
        data = parse_definition(payload.get("data", previous["data"]))
        if "data" in payload and data["version"] != previous["data"]["version"]:
            raise BusinessRuleError("模板版本已变化，请刷新后保存")
        comparable = {key: data[key] for key in ("inputs", "nodes")}
        old = {key: previous["data"][key] for key in ("inputs", "nodes")}
        data["version"] = previous["data"]["version"] + int(comparable != old)
        validate_references(self.repository, project_id, data)
        return super().update(item_id, {**payload, "data": data})

    def copy(self, item_id):
        original = self.get(item_id)
        from app.services.api_flow_scenario_service import ApiFlowScenarioService
        scenarios = ApiFlowScenarioService(self.repository)
        source_scenes = scenarios.list_for_flow(item_id)
        if any(scene["data"]["template_version"] != original["data"]["version"] for scene in source_scenes):
            raise BusinessRuleError("请先同步所有场景模板再复制流程")
        for scene in source_scenes:
            validate_references(self.repository, original["project_id"], original["data"], scene["data"])
        copied = self.create({"name": original["name"] + "（副本）", "project_id": original["project_id"],
                              "description": original.get("description"), "data": original["data"]})
        for scene in source_scenes:
            scenarios.create_for_flow(copied["id"], {key: scene[key] for key in ("name", "description", "status", "data")})
        return copied

    def delete(self, item_id):
        self.get(item_id)
        if not self.batch_delete([item_id])["deleted_count"]:
            return super().delete(item_id)
        return True

    def batch_delete(self, ids):
        from app.scheduler.jobs.api_flow_jobs import is_batch_active
        from app.services.api_flow_run_service import ApiFlowRunService

        existing = self.repository.get_many(self.table, list(dict.fromkeys(ids)))
        flow_ids = [row["id"] for row in existing]
        if not flow_ids:
            return {"deleted_count": 0}
        batches = self.repository.get_related("api_flow_runs", "flow_id", flow_ids, ["queued", "running"])
        if any(is_batch_active(row["id"]) for row in batches):
            raise BusinessRuleError("流程正在执行，请先取消并等待结束")
        ApiFlowRunService(self.repository).interrupt_many(batches)
        count = self.repository.batch_delete_with_children(self.table, flow_ids, "api_flow_scenarios", "flow_id")
        return {"deleted_count": count}

    def _project(self, project_id):
        if not project_id or not self.repository.get("projects", project_id):
            raise BusinessRuleError("请先选择有效项目")

    @staticmethod
    def definition(item):
        data = item.get("data") or {}
        if "nodes" in data or not data.get("steps"):
            return parse_definition(data)
        nodes = []
        for index, step in enumerate(data["steps"]):
            if not step.get("api_id"):
                continue
            try:
                params = json.loads(step.get("case_json") or "{}")
            except (TypeError, ValueError):
                params = {}
            nodes.append({"key": f"node_{index + 1}", "name": step.get("api_label") or f"节点 {index + 1}",
                          "api_id": int(step["api_id"]), "case_id": int(step["case_id"]) if step.get("case_id") else None,
                          "auth_id": int(step["auth_id"]) if step.get("auth_id") else None,
                          "params": params if isinstance(params, dict) else {}})
        return parse_definition({"nodes": nodes})
