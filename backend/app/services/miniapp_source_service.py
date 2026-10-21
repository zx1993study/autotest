import hashlib
import json

from app.core.exceptions import BusinessRuleError, ResourceNotFoundError
from app.schemas.miniapp_source import SourceCatalogImport
from app.services.api_flow_scenario_service import ApiFlowScenarioService
from app.services.execution_flow_service import ExecutionFlowService
from app.services.resource_service import ResourceService
from app.services.test_case_service import TestCaseService


def definition_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


class MiniappSourceService:
    """Import immutable source definitions into existing pages and formal cases."""

    def __init__(self, repository):
        self.repository = repository
        self.pages = ResourceService("miniapp_pages", repository)
        self.cases = TestCaseService("MINIAPP", repository)

    def import_catalog(self, payload: SourceCatalogImport):
        if not self.repository.get("projects", payload.project_id):
            raise ResourceNotFoundError("项目不存在")
        source = payload.metadata.source.model_dump()
        repository = source["repository"].rstrip("/")
        existing_pages = self._indexed("miniapp_pages", payload.project_id)
        existing_cases = self._indexed("miniapp_test_cases", payload.project_id)
        result = {"created_pages": 0, "created_cases": 0, "skipped_cases": 0, "conflicts": [], "case_ids": []}
        for definition in payload.cases:
            page_key = f"{repository}#{definition.route}"
            page = existing_pages.get(page_key)
            if not page:
                page = self.pages.create({"project_id": payload.project_id, "name": definition.route.rsplit("/", 2)[-2] + " / " + definition.title.split("：")[0],
                                          "data": {"source_key": page_key, "source": source, "route": definition.route,
                                                   "host_app": "wechat", "miniapp_name": "FieldNovaMini"}})
                existing_pages[page_key] = page
                result["created_pages"] += 1
            key = f"{repository}#{definition.id}"
            item = definition.model_dump()
            digest = definition_hash(item)
            previous = existing_cases.get(key)
            if previous:
                result["case_ids"].append(previous["id"])
                if previous["data"].get("source_revision") != source["revision"] or previous["data"].get("definition_hash") != digest:
                    result["conflicts"].append({"source_id": definition.id, "case_id": previous["id"]})
                else:
                    result["skipped_cases"] += 1
                continue
            case = self.cases.create({"project_id": payload.project_id, "source_id": page["id"], "name": definition.title,
                                      "description": "源码测试定义；未执行不代表通过。", "steps": [{"description": step} for step in definition.steps],
                                      "assertions": [{"type": "business_expectation", "expected": text} for text in definition.expected],
                                      "data": {"source_key": key, "source_revision": source["revision"], "definition_hash": digest,
                                               "execution_engine": "source_catalog", "category": definition.category,
                                               "automation": definition.automation, "route": definition.route, "definition": item}})
            existing_cases[key] = case
            result["created_cases"] += 1
            result["case_ids"].append(case["id"])
        return result

    def bind_business(self, case_id, payload):
        case = self.cases.get(case_id)
        if case["data"].get("execution_engine") != "source_catalog":
            raise BusinessRuleError("仅源码用例支持关联业务流程")
        scene = ApiFlowScenarioService(self.repository).get_for_flow(payload.flow_id, payload.scenario_id)
        flow = ExecutionFlowService(self.repository).get(payload.flow_id)
        if scene["project_id"] != case["project_id"] or flow["project_id"] != case["project_id"]:
            raise BusinessRuleError("业务流程必须属于同一项目")
        if flow["status"] != "active" or scene["status"] != "active":
            raise BusinessRuleError("请选择启用的业务流程及场景")
        binding = {"flow_id": payload.flow_id, "scenario_id": payload.scenario_id}
        return self.cases.update(case_id, {"data": {**case["data"], "api_business": binding}})

    def _indexed(self, table, project_id):
        result, page = {}, 1
        while True:
            rows, total = self.repository.list(table, project_id=project_id, page=page, page_size=500)
            result.update({row["data"]["source_key"]: row for row in rows if row.get("data", {}).get("source_key")})
            if page * 500 >= total:
                return result
            page += 1
