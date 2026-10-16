from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any

from app.core.exceptions import BusinessRuleError
from app.repositories.interfaces import ResourceRepository
from app.schemas.openapi_case_generation import OpenApiCaseGenerationRequest
from app.services.api_case_template_builder import ApiCaseTemplateBuilder
from app.services.case_draft_service import CaseDraftService
from app.services.openapi_schema_service import OpenApiSchemaService


GENERATOR_VERSION = "openapi-native-v1"


class OpenApiCaseGenerationService:
    """Preview and persist deterministic API case drafts from imported OpenAPI metadata."""

    def __init__(self, repository: ResourceRepository) -> None:
        self.repository = repository
        self.snapshots = OpenApiSchemaService(repository)
        self.builder = ApiCaseTemplateBuilder()
        self.drafts = CaseDraftService("API", repository)

    def preview(self, payload: OpenApiCaseGenerationRequest) -> dict[str, Any]:
        prepared, snapshot, truncated = self._prepare(payload)
        exact, by_key = self._existing_maps(payload.project_id)
        items = [self._preview_item(item, exact, by_key) for item in prepared]
        return {
            "snapshot": self._snapshot_view(snapshot),
            "total": len(items),
            "truncated": truncated,
            "summary": {
                "new": sum(1 for item in items if item["action"] == "new"),
                "update": sum(1 for item in items if item["action"] == "update"),
                "unchanged": sum(1 for item in items if item["action"] == "unchanged"),
            },
            "items": items,
        }

    def generate(self, payload: OpenApiCaseGenerationRequest) -> dict[str, Any]:
        prepared, snapshot, truncated = self._prepare(payload)
        if payload.selected_fingerprints is not None:
            selected = set(payload.selected_fingerprints)
            if not selected:
                raise BusinessRuleError("请至少选择一条预览用例")
            available = {item["fingerprint"] for item in prepared}
            unknown = selected - available
            if unknown:
                raise BusinessRuleError("预览结果已变化，请重新预览后再生成")
            prepared = [item for item in prepared if item["fingerprint"] in selected]

        exact, by_key = self._existing_maps(payload.project_id)
        created_count = 0
        updated_count = 0
        skipped_count = 0
        draft_ids: list[int] = []
        for item in prepared:
            fingerprint = str(item["fingerprint"])
            generation_key = str(item["generation_key"])
            if fingerprint in exact:
                skipped_count += 1
                draft_ids.append(int(exact[fingerprint]["id"]))
                continue

            draft_payload = self._draft_payload(payload.project_id, item)
            previous = by_key.get(generation_key)
            if previous and str(previous.get("status") or "") == "draft":
                draft = self.drafts.update(int(previous["id"]), draft_payload)
                updated_count += 1
            else:
                draft = self.drafts.create(draft_payload)
                created_count += 1
            draft_ids.append(int(draft["id"]))
            exact[fingerprint] = draft
            by_key[generation_key] = draft

        return {
            "snapshot": self._snapshot_view(snapshot),
            "selected_count": len(prepared),
            "draft_count": created_count + updated_count,
            "created_count": created_count,
            "updated_count": updated_count,
            "skipped_count": skipped_count,
            "truncated": truncated,
            "draft_ids": draft_ids,
        }

    def _prepare(
        self,
        payload: OpenApiCaseGenerationRequest,
    ) -> tuple[list[dict[str, Any]], dict[str, Any], bool]:
        snapshot = self.snapshots.get_for_project(payload.project_id, payload.snapshot_id)
        snapshot_data = self._data(snapshot)
        snapshot_id = int(snapshot["id"])
        schema_hash = str(snapshot_data.get("schema_hash") or "")
        if not schema_hash:
            raise BusinessRuleError("Schema 快照缺少内容指纹，请重新导入")

        interfaces, _ = self.repository.list("api_interfaces", project_id=payload.project_id, page_size=10000)
        requested_ids = set(payload.source_ids)
        project_ids = {int(item["id"]) for item in interfaces}
        missing = requested_ids - project_ids
        if missing:
            raise BusinessRuleError("部分所选接口不存在或不属于当前项目")
        if requested_ids:
            interfaces = [item for item in interfaces if int(item["id"]) in requested_ids]

        snapshot_interfaces = [
            item
            for item in interfaces
            if self._interface_snapshot_id(item) in {None, snapshot_id}
            and (
                not self._data(item).get("schema_hash")
                or str(self._data(item).get("schema_hash")) == schema_hash
            )
        ]
        if requested_ids and len(snapshot_interfaces) != len(interfaces):
            raise BusinessRuleError("部分所选接口不属于当前 Schema 快照，请刷新接口列表")
        if not snapshot_interfaces:
            raise BusinessRuleError("当前 Schema 快照没有可生成用例的接口")

        fields, _ = self.repository.list("api_fields", project_id=payload.project_id, page_size=10000)
        fields_by_interface: dict[int, list[dict[str, Any]]] = {}
        for field in fields:
            interface_id = self._to_int(self._data(field).get("interface_id"))
            if interface_id is not None:
                fields_by_interface.setdefault(interface_id, []).append(field)
        knowledge = self._knowledge_strategies(payload.project_id, payload.strategy_ids)

        prepared: list[dict[str, Any]] = []
        seen_keys: set[str] = set()
        truncated = False
        for interface in snapshot_interfaces:
            source_id = int(interface["id"])
            generated_cases = self.builder.build_from_openapi(
                interface,
                fields_by_interface.get(source_id, []),
                set(payload.strategies),
                knowledge,
            )
            for generated in generated_cases:
                item = self._decorate_case(generated, interface, snapshot_id, schema_hash)
                generation_key = str(item["generation_key"])
                if generation_key in seen_keys:
                    continue
                if len(prepared) >= payload.max_cases:
                    truncated = True
                    break
                seen_keys.add(generation_key)
                prepared.append(item)
            if truncated:
                break
        if not prepared:
            raise BusinessRuleError("所选接口在当前策略下没有可生成的用例")
        return prepared, snapshot, truncated

    def _decorate_case(
        self,
        generated: dict[str, Any],
        interface: dict[str, Any],
        snapshot_id: int,
        schema_hash: str,
    ) -> dict[str, Any]:
        case_json = deepcopy(generated)
        scenario = case_json.get("openapi_scenario") if isinstance(case_json.get("openapi_scenario"), dict) else {}
        interface_data = self._data(interface)
        method = str(interface_data.get("method") or case_json.get("method") or "GET").upper()
        path = str(interface_data.get("path") or case_json.get("path") or "")
        operation_id = str(interface_data.get("operation_id") or "")
        scenario_key = str(scenario.get("key") or case_json.get("category") or "normal")
        generation_key = f"openapi:{method}:{path}:{scenario_key}"
        canonical = json.dumps(case_json, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        fingerprint = hashlib.sha256(f"{schema_hash}|{generation_key}|{canonical}".encode("utf-8")).hexdigest()
        case_json["openapi_generation"] = {
            "generator_version": GENERATOR_VERSION,
            "snapshot_id": snapshot_id,
            "schema_hash": schema_hash,
            "operation_id": operation_id,
            "method": method,
            "path": path,
            "generation_key": generation_key,
            "fingerprint": fingerprint,
            "strategy": scenario.get("strategy"),
            "field": scenario.get("field"),
            "variant": scenario.get("variant"),
        }
        return {
            "source_id": int(interface["id"]),
            "source_name": str(interface.get("name") or f"{method} {path}"),
            "case_json": case_json,
            "generation_key": generation_key,
            "fingerprint": fingerprint,
        }

    def _preview_item(
        self,
        item: dict[str, Any],
        exact: dict[str, dict[str, Any]],
        by_key: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        case_json = item["case_json"]
        scenario = case_json.get("openapi_scenario") if isinstance(case_json.get("openapi_scenario"), dict) else {}
        fingerprint = str(item["fingerprint"])
        generation_key = str(item["generation_key"])
        previous = by_key.get(generation_key)
        exact_match = exact.get(fingerprint)
        action = "unchanged" if exact_match else "update" if previous and previous.get("status") == "draft" else "new"
        return {
            "fingerprint": fingerprint,
            "generation_key": generation_key,
            "source_id": item["source_id"],
            "source_name": item["source_name"],
            "name": case_json.get("name"),
            "category": case_json.get("category"),
            "strategy": scenario.get("strategy"),
            "field": scenario.get("field"),
            "variant": scenario.get("variant"),
            "method": case_json.get("method"),
            "path": case_json.get("path"),
            "assertions": case_json.get("assertions") if isinstance(case_json.get("assertions"), list) else [],
            "action": action,
            "existing_draft_id": (exact_match or previous or {}).get("id"),
        }

    def _draft_payload(self, project_id: int, item: dict[str, Any]) -> dict[str, Any]:
        case_json = item["case_json"]
        metadata = case_json.get("openapi_generation") if isinstance(case_json.get("openapi_generation"), dict) else {}
        strategy = str(metadata.get("strategy") or "normal")
        field = str(metadata.get("field") or "")
        description = f"由 OpenAPI Schema 自动生成；策略：{strategy}"
        if field:
            description += f"；字段：{field}"
        return {
            "name": str(case_json.get("name") or item["source_name"])[:128],
            "project_id": project_id,
            "case_type": "API",
            "source_id": item["source_id"],
            "status": "draft",
            "description": description,
            "case_json": case_json,
            "data": case_json,
            "assertions": self._dict_list(case_json.get("assertions")),
            "strategy_ids": self._int_list(case_json.get("strategy_ids")),
        }

    def _existing_maps(
        self,
        project_id: int,
    ) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
        rows, _ = self.repository.list(
            "case_drafts",
            project_id=project_id,
            page_size=10000,
            data_filters={"case_type": "API"},
        )
        exact: dict[str, dict[str, Any]] = {}
        by_key: dict[str, dict[str, Any]] = {}
        for row in rows:
            metadata = self._generation_metadata(row)
            fingerprint = str(metadata.get("fingerprint") or "")
            generation_key = str(metadata.get("generation_key") or "")
            if fingerprint:
                exact.setdefault(fingerprint, row)
            if generation_key:
                by_key.setdefault(generation_key, row)
        return exact, by_key

    def _generation_metadata(self, item: dict[str, Any]) -> dict[str, Any]:
        for key in ("case_json", "data"):
            value = item.get(key)
            if not isinstance(value, dict):
                continue
            metadata = value.get("openapi_generation")
            if isinstance(metadata, dict):
                return metadata
        return {}

    def _knowledge_strategies(self, project_id: int, strategy_ids: list[int]) -> list[dict[str, Any]]:
        if not strategy_ids:
            return []
        rows, _ = self.repository.list("project_knowledge", page_size=10000)
        requested = set(strategy_ids)
        result = []
        for item in rows:
            data = self._data(item)
            if int(item["id"]) not in requested:
                continue
            if item.get("project_id") not in (None, project_id):
                continue
            if str(data.get("domain") or "COMMON").upper() not in {"COMMON", "API"}:
                continue
            result.append(item)
        if {int(item["id"]) for item in result} != requested:
            raise BusinessRuleError("部分用例知识库策略不存在或不适用于 API")
        return result

    def _snapshot_view(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        data = self._data(snapshot)
        return {
            "id": snapshot["id"],
            "name": snapshot.get("name"),
            "schema_hash": data.get("schema_hash"),
            "openapi_version": data.get("openapi_version"),
            "operation_count": data.get("operation_count"),
            "source_type": data.get("source_type"),
            "source": data.get("source"),
        }

    def _interface_snapshot_id(self, interface: dict[str, Any]) -> int | None:
        return self._to_int(self._data(interface).get("schema_snapshot_id"))

    def _to_int(self, value: Any) -> int | None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _data(self, item: dict[str, Any]) -> dict[str, Any]:
        value = item.get("data")
        return value if isinstance(value, dict) else {}

    def _dict_list(self, value: Any) -> list[dict[str, Any]]:
        return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []

    def _int_list(self, value: Any) -> list[int]:
        if not isinstance(value, list):
            return []
        result = []
        for item in value:
            converted = self._to_int(item)
            if converted is not None:
                result.append(converted)
        return result
