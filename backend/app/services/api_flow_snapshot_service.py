from copy import deepcopy

from app.core.exceptions import BusinessRuleError
from app.services.project_auth_service import ProjectAuthService
from app.services.test_case_service import TestCaseService


class ApiFlowSnapshotService:
    def __init__(self, repository):
        self.repository = repository
        self._auth_headers = {}

    def build(self, flow, scenario, inputs):
        project_id = flow["project_id"]
        references = {"projects": [self.repository.get("projects", project_id)]}
        nodes = [node for node in flow["data"]["nodes"]
                 if scenario["data"]["nodes"].get(node["key"], {}).get("mode") != "skip"]
        references["api_interfaces"] = [self.repository.get("api_interfaces", api_id)
                                        for api_id in dict.fromkeys(node["api_id"] for node in nodes)]
        for table in ("api_fields", "api_import_tasks"):
            references[table], _ = self.repository.list(table, project_id=project_id, page_size=10000)
        api_ids = {str(node["api_id"]) for node in nodes}
        references["api_fields"] = [row for row in references["api_fields"]
                                    if str((row.get("data") or {}).get("interface_id")) in api_ids]
        cases = {}
        for node in nodes:
            override = scenario["data"]["nodes"].get(node["key"], {})
            case_id = override.get("case_id") or node.get("case_id")
            if not case_id:
                continue
            case = TestCaseService("API", self.repository).get(case_id)
            interface = next(row for row in references["api_interfaces"] if row["id"] == node["api_id"])
            cases[node["key"]] = self._freeze_auth(case, interface, node, override)
        return deepcopy({"flow": flow, "scenario": scenario, "inputs": inputs,
                         "references": references, "cases": cases})

    def _freeze_auth(self, case, interface, node, override):
        case = deepcopy(case)
        data = case.setdefault("data", {})
        legacy = data.pop("request", {})
        data = {**legacy, **data}
        case["data"] = data
        auth_id = node.get("auth_id") or data.get("auth_id") or interface["data"].get("auth_id")
        request = {**data, **node["request"], **override.get("request", {})}
        if auth_id and not request.get("skip_auth"):
            auth = self.repository.get("project_auth", int(auth_id))
            if not auth or auth.get("project_id") != case.get("project_id"):
                raise BusinessRuleError("用例认证配置不存在或不属于当前项目")
            if auth_id not in self._auth_headers:
                self._auth_headers[auth_id] = ProjectAuthService(self.repository).auth_headers(auth_id)
            headers = self._auth_headers[auth_id]
            if not headers:
                raise BusinessRuleError("认证配置没有有效的 Token 或 Cookie")
            data["headers"] = {**data.get("headers", {}), **headers}
        data["skip_auth"] = True
        return case
