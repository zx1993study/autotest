from copy import deepcopy

from app.core.exceptions import BusinessRuleError, ResourceNotFoundError
from app.schemas.api_flow_scenario import ScenarioDefinition
from app.services.api_flow_validation import validate_references
from app.services.execution_flow_service import ExecutionFlowService
from app.services.resource_service import ResourceService


class ApiFlowScenarioService(ResourceService):
    def __init__(self, repository):
        super().__init__("api_flow_scenarios", repository)
        self.flows = ExecutionFlowService(repository)

    def list_for_flow(self, flow_id):
        self.flows.get(flow_id)
        rows, _ = self.repository.list(self.table, page_size=10000, data_filters={"flow_id": flow_id})
        return rows

    def get_for_flow(self, flow_id, scene_id):
        item = super().get(scene_id)
        if (item.get("data") or {}).get("flow_id") != flow_id:
            raise ResourceNotFoundError("场景不属于当前流程")
        return item

    def create_for_flow(self, flow_id, payload):
        flow = self.flows.get(flow_id)
        data = ScenarioDefinition.model_validate(payload.get("data") or {}).model_dump()
        data.update(flow_id=flow_id, template_version=flow["data"]["version"])
        validate_references(self.repository, flow["project_id"], flow["data"], data)
        return super().create({**payload, "project_id": flow["project_id"], "data": data})

    def update_for_flow(self, flow_id, scene_id, payload):
        item = self.get_for_flow(flow_id, scene_id)
        flow = self.flows.get(flow_id)
        if "data" in payload and payload["data"] is not None:
            if item["data"]["template_version"] != flow["data"]["version"]:
                raise BusinessRuleError("模板已变化，请先同步模板再编辑场景")
            data = ScenarioDefinition.model_validate(payload["data"]).model_dump()
            data.update(flow_id=flow_id, template_version=flow["data"]["version"])
            validate_references(self.repository, flow["project_id"], flow["data"], data)
            data.update({key: item["data"][key] for key in ("latest_status", "latest_run_id") if key in item["data"]})
            payload = {**payload, "data": data}
        return super().update(scene_id, payload)

    def copy_for_flow(self, flow_id, scene_id):
        scene = deepcopy(self.get_for_flow(flow_id, scene_id))
        payload = {key: scene.get(key) for key in ("name", "description", "status", "data")}
        payload["name"] += "（副本）"
        if scene["data"]["template_version"] != self.flows.get(flow_id)["data"]["version"]:
            raise BusinessRuleError("请先同步场景模板再复制")
        return self.create_for_flow(flow_id, payload)

    def sync(self, flow_id, scene_id):
        scene = self.get_for_flow(flow_id, scene_id)
        flow = self.flows.get(flow_id)
        keys = {node["key"] for node in flow["data"]["nodes"]}
        data = deepcopy(scene["data"])
        data["nodes"] = {key: value for key, value in data["nodes"].items() if key in keys}
        if data["expected_end"] not in {"auto", *keys}:
            data["expected_end"] = "auto"
        data["template_version"] = flow["data"]["version"]
        validate_references(self.repository, flow["project_id"], flow["data"], data)
        return super().update(scene_id, {"data": data})

    def delete_for_flow(self, flow_id, scene_id):
        self.get_for_flow(flow_id, scene_id)
        return super().delete(scene_id)
