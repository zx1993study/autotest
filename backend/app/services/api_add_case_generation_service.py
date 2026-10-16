"""Generate formal add cases from OpenAPI plus explicitly verified business inputs."""

import hashlib
import json
from copy import deepcopy

from app.core.exceptions import BusinessRuleError
from app.schemas.api_add_campaign import ApiAddCampaignRequest
from app.services.api_case_template_builder import ApiCaseTemplateBuilder
from app.services.api_natural_input_service import timestamp_text
from app.services.openapi_schema_service import OpenApiSchemaService
from app.services.test_case_service import TestCaseService

STRATEGIES = {"normal", "required", "boundary", "enum", "format", "type", "auth"}


class ApiAddCaseGenerationService:
    def __init__(self, repository):
        self.repository = repository
        self.cases = TestCaseService("API", repository)
        self.builder = ApiCaseTemplateBuilder()

    def generate(self, payload: ApiAddCampaignRequest):
        snapshot = OpenApiSchemaService(self.repository).get_for_project(payload.project_id, payload.snapshot_id)
        schema_hash = snapshot["data"]["schema_hash"]
        existing, _ = self.repository.list("api_test_cases", project_id=payload.project_id, page_size=10000,
                                           data_filters={"campaign_key": payload.campaign_key})
        by_key = {row["data"].get("generation_key"): row for row in existing}
        result = []
        prepared = [(profile, self._interface(profile.source_id, payload), self._fields(profile, payload.project_id))
                    for profile in payload.profiles]
        for profile, interface, fields in prepared:
            normal = {"method": "POST", "path": interface["data"]["path"], "params": deepcopy(profile.params),
                      "content_type": interface["data"].get("content_type") or "application/json"}
            generated = self.builder.build_from_openapi(interface, fields, STRATEGIES, normal_request=normal)
            for item in generated:
                case_payload = self._case_payload(item, interface, profile, payload, schema_hash)
                previous = by_key.get(case_payload["data"]["generation_key"])
                saved = self.cases.update(previous["id"], case_payload) if previous else self.cases.create(case_payload)
                result.append(saved)
                by_key[case_payload["data"]["generation_key"]] = saved
        kept_keys = {case["data"]["generation_key"] for case in result}
        sources = {profile.source_id for profile in payload.profiles}
        for previous in existing:
            if previous.get("source_id") in sources and previous["data"].get("generation_key") not in kept_keys:
                self.cases.update(previous["id"], {**previous, "status": "inactive"})
        return result

    def _interface(self, source_id, payload):
        interface = self.repository.get("api_interfaces", source_id)
        data = (interface or {}).get("data") or {}
        if not interface or interface.get("project_id") != payload.project_id:
            raise BusinessRuleError("添加接口不属于当前项目")
        if data.get("method") != "POST" or "Add " not in interface["name"]:
            raise BusinessRuleError("本批次只允许添加接口")
        if int(data.get("schema_snapshot_id") or 0) != payload.snapshot_id:
            raise BusinessRuleError("添加接口不属于选定 OpenAPI 快照")
        return interface

    def _fields(self, profile, project_id):
        fields, _ = self.repository.list("api_fields", project_id=project_id, page_size=10000,
                                         data_filters={"interface_id": profile.source_id})
        selected = []
        for field in fields:
            data = field.get("data") or {}
            name = data.get("name") or field["name"]
            if str(data.get("interface_id")) != str(profile.source_id):
                continue
            if name not in profile.params or name in profile.excluded_fields:
                continue
            row = deepcopy(field)
            constraints = profile.field_constraints.get(name, {})
            row["data"]["schema"] = {**(data.get("schema") or {}), **constraints}
            if name in profile.required_fields:
                row["data"]["required"] = True
            selected.append(row)
        missing = set(profile.params) - {row["data"].get("name") or row["name"] for row in selected}
        unfilled = set(profile.required_fields) - set(profile.params)
        if missing or unfilled:
            raise BusinessRuleError(f"接口 {profile.source_id} 参数核对失败：未知/排除 {sorted(missing)}；未填写必填 {sorted(unfilled)}")
        return selected

    def _case_payload(self, item, interface, profile, payload, schema_hash):
        scenario = item["openapi_scenario"]
        key = f"{profile.source_id}:{scenario['key']}"
        for name in profile.unique_text_fields:
            if scenario.get("field") == f"body.{name}":
                continue
            value = item.get("params", {}).get(name)
            if isinstance(value, str):
                maximum = profile.field_constraints.get(name, {}).get("maxLength")
                item["params"][name] = timestamp_text(value, maximum, key)
        negative = item.get("category") in {"required_missing", "enum_invalid", "format_invalid", "type_invalid", "auth"}
        if scenario["strategy"] == "boundary":
            negative = "invalid" in scenario.get("variant", "")
        item["assertions"] = ([{"type": "api_rejection", "expected": "auth" if scenario["strategy"] == "auth" else "validation"}]
                              if negative else [{"type": "status", "expected": 200},
                                                {"type": "json_pointer", "path": "/code", "expected": 200}])
        if negative and profile.rejection_messages.get(scenario["key"]):
            item["assertions"][0]["allowed_business_errors"] = profile.rejection_messages[scenario["key"]]
        item["campaign_key"] = payload.campaign_key
        item["generation_key"] = key
        item["input_baseline"] = {"table": profile.table_name, "excluded_fields": profile.excluded_fields,
                                  "notes": profile.notes, "snapshot_id": payload.snapshot_id, "schema_hash": schema_hash}
        canonical = json.dumps(item, ensure_ascii=False, sort_keys=True)
        item["openapi_generation"] = {"generator_version": "openapi-db-add-v1", "snapshot_id": payload.snapshot_id,
                                     "schema_hash": schema_hash, "generation_key": key,
                                     "fingerprint": hashlib.sha256(canonical.encode()).hexdigest()}
        return {"project_id": payload.project_id, "source_id": profile.source_id, "name": item["name"],
                "description": "OpenAPI 策略；参数经业务库只读核对；仅添加接口", "status": "active",
                "data": item, "assertions": item["assertions"]}
