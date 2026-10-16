"""Generate API/Web/App case drafts from normalized project resources."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.repositories.interfaces import ResourceRepository
from app.services.api_case_template_builder import ApiCaseTemplateBuilder
from app.services.case_draft_service import CaseDraftService
from app.services.web_case_template_builder import WebCaseTemplateBuilder


@dataclass(frozen=True, slots=True)
class GeneratedCaseSpec:
    """Generated test case plus the source feature it belongs to."""

    case_type: str
    source_id: int
    source_name: str
    case_json: dict[str, Any]


class TestGenerationService:
    """Read resources and delegate pure test-case template construction."""

    def __init__(self, repository: ResourceRepository) -> None:
        self.repository = repository
        self.api_builder = ApiCaseTemplateBuilder()
        self.web_builder = WebCaseTemplateBuilder()

    def generate_api_drafts(
        self,
        project_id: int,
        source_ids: list[int],
        strategy: str,
        strategy_ids: list[int] | None = None,
    ) -> dict[str, int]:
        """Generate and persist API case drafts."""

        cases = self.build_api_case_specs(
            project_id,
            source_ids,
            strategy,
            strategy_ids,
        )
        for item in cases:
            self._create_draft("API", project_id, item.source_id, item.case_json)
        return {"draft_count": len(cases)}

    def generate_asset_drafts(
        self,
        case_type: str,
        asset_table: str,
        element_table: str,
        project_id: int,
        source_ids: list[int],
        strategy: str,
        strategy_ids: list[int] | None = None,
    ) -> dict[str, int]:
        """Generate and persist page-based case drafts."""

        cases = self.build_asset_case_specs(
            case_type,
            asset_table,
            element_table,
            project_id,
            source_ids,
            strategy,
            strategy_ids,
        )
        for item in cases:
            self._create_draft(case_type, project_id, item.source_id, item.case_json)
        return {"draft_count": len(cases)}

    def build_api_case_specs(
        self,
        project_id: int,
        source_ids: list[int],
        strategy: str,
        strategy_ids: list[int] | None = None,
    ) -> list[GeneratedCaseSpec]:
        """Build API cases from interfaces, field templates and knowledge."""

        interfaces = self._items("api_interfaces", project_id, source_ids)
        fields = self._items("api_fields", project_id, [])
        strategies = self._strategy_items(project_id, strategy_ids or [], "API")
        result: list[GeneratedCaseSpec] = []
        for item in interfaces:
            item_fields = [
                field
                for field in fields
                if field.get("data", {}).get("interface_id") == item["id"]
            ]
            result.extend(
                GeneratedCaseSpec("API", int(item["id"]), str(item["name"]), case_json)
                for case_json in self.api_builder.build(
                    item,
                    item_fields,
                    strategy,
                    strategies,
                )
            )
        return result

    def build_asset_case_specs(
        self,
        case_type: str,
        asset_table: str,
        element_table: str,
        project_id: int,
        source_ids: list[int],
        strategy: str,
        strategy_ids: list[int] | None = None,
    ) -> list[GeneratedCaseSpec]:
        """Build UI cases from selected pages, elements and knowledge."""

        assets = self._items(asset_table, project_id, source_ids)
        elements = self._items(element_table, project_id, [])
        strategies = self._strategy_items(
            project_id,
            strategy_ids or [],
            case_type,
        )
        result: list[GeneratedCaseSpec] = []
        for asset in assets:
            asset_elements = [
                item
                for item in elements
                if item.get("data", {}).get("page_id") == asset["id"]
            ]
            result.extend(
                GeneratedCaseSpec(
                    case_type,
                    int(asset["id"]),
                    str(asset["name"]),
                    case_json,
                )
                for case_json in self.web_builder.build(
                    case_type,
                    asset,
                    asset_elements,
                    strategy,
                    strategies,
                )
            )
        return result

    def _items(
        self,
        table: str,
        project_id: int,
        ids: list[int],
    ) -> list[dict[str, Any]]:
        items, _ = self.repository.list(
            table,
            project_id=project_id,
            page_size=10000,
        )
        if ids:
            allowed = set(ids)
            return [item for item in items if item["id"] in allowed]
        return items

    def _create_draft(
        self,
        case_type: str,
        project_id: int,
        source_id: int,
        case_json: dict[str, Any],
    ) -> None:
        CaseDraftService(case_type, self.repository).create(
            {
                "name": case_json["name"],
                "project_id": project_id,
                "case_type": case_type,
                "source_id": source_id,
                "status": "draft",
                "case_json": case_json,
                "data": case_json,
                "assertions": self._dict_list(case_json.get("assertions")),
                "strategy_ids": self._int_list(case_json.get("strategy_ids")),
            }
        )

    def _strategy_items(
        self,
        project_id: int,
        strategy_ids: list[int],
        case_type: str,
    ) -> list[dict[str, Any]]:
        if not strategy_ids:
            return []
        rows, _ = self.repository.list("project_knowledge", page_size=10000)
        allowed_ids = set(strategy_ids)
        allowed_domains = {case_type.upper(), "COMMON"}
        result: list[dict[str, Any]] = []
        for item in rows:
            data = item.get("data") if isinstance(item.get("data"), dict) else {}
            if item.get("id") not in allowed_ids:
                continue
            if str(data.get("domain") or "COMMON").upper() not in allowed_domains:
                continue
            if item.get("project_id") not in (None, project_id):
                continue
            result.append(item)
        return result

    def _dict_list(self, value: object) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            return []
        return [item for item in value if isinstance(item, dict)]

    def _int_list(self, value: object) -> list[int]:
        if not isinstance(value, list):
            return []
        result: list[int] = []
        for item in value:
            try:
                result.append(int(item))
            except (TypeError, ValueError):
                continue
        return result
