from __future__ import annotations

from typing import Any

from app.repositories.interfaces import ResourceRepository
from app.services.resource_service import ResourceService


TEST_CASE_TABLES = {
    "API": "api_test_cases",
    "WEB": "web_test_cases",
    "APP": "app_test_cases",
    "MINIAPP": "miniapp_test_cases",
}


def test_case_table(case_type: str) -> str:
    """Return the persistence table for a test-case domain."""

    return TEST_CASE_TABLES.get(case_type.upper(), "test_cases")


class TestCaseService(ResourceService):
    """Manage formal test-case CRUD and query enrichment.

    Execution orchestration lives in ``app.scheduler.jobs.case_execution_jobs``.
    Keeping this service focused on case data avoids coupling CRUD workflows to
    Playwright, Appium, or HTTP execution engines.
    """

    def __init__(self, case_type: str, repository: ResourceRepository) -> None:
        self.case_type = case_type.upper()
        super().__init__(test_case_table(self.case_type), repository)

    def list(
        self,
        keyword: str | None,
        project_id: int | None,
        page: int,
        page_size: int,
    ) -> tuple[list[dict[str, Any]], int]:
        rows, total = self.repository.list(self.table, keyword, project_id, page, page_size)
        rows = [self._normalize_case(item) for item in rows]
        return [self._enrich_case(item) for item in rows], total

    def get(self, item_id: int) -> dict[str, Any]:
        return self._enrich_case(self._normalize_case(super().get(item_id)))

    def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        payload = self._case_payload(payload)
        payload["case_type"] = self.case_type
        payload.setdefault("data", {})
        return super().create(payload)

    def _interface(self, source_id: Any) -> dict[str, Any] | None:
        if not source_id:
            return None
        return self.repository.get("api_interfaces", int(source_id))

    def _project(self, project_id: Any) -> dict[str, Any] | None:
        if not project_id:
            return None
        return self.repository.get("projects", int(project_id))

    def _enrich_case(self, case: dict[str, Any]) -> dict[str, Any]:
        case = self._normalize_case(case)
        case = self._with_strategy_summaries(case)
        if self.case_type != "API":
            return case

        data = dict(case.get("data") or {})
        interface = self._interface(case.get("source_id"))
        interface_data = interface.get("data") if interface else {}
        project = self._project(case.get("project_id"))
        data.update(
            {
                "project_name": project.get("name") if project else "",
                "api_method": (interface_data or {}).get("method") or "",
                "api_path": ((interface_data or {}).get("path") or interface.get("name")) if interface else "",
            }
        )
        return {**case, "data": data}

    def _case_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        data = self._clean_case_data(payload.get("data") or {})
        data["case_type"] = self.case_type
        normalized = dict(payload)
        normalized["data"] = data
        normalized["case_type"] = self.case_type
        return normalized

    def _normalize_case(self, case: dict[str, Any]) -> dict[str, Any]:
        data = self._clean_case_data(case.get("data") or {})
        data.setdefault("case_type", self.case_type)
        return {**case, "case_type": self.case_type, "data": data}

    def _clean_case_data(self, value: Any) -> dict[str, Any]:
        if not isinstance(value, dict):
            return {}
        return {
            key: item
            for key, item in value.items()
            if key not in {"assertions", "strategies", "strategy", "strategy_ids"}
        }

    def _with_strategy_summaries(self, case: dict[str, Any]) -> dict[str, Any]:
        strategy_ids = self._strategy_ids(case.get("strategy_ids"))
        if not strategy_ids:
            return {**case, "strategy_ids": [], "strategies": []}

        strategies: list[dict[str, Any]] = []
        for strategy_id in strategy_ids:
            strategy = self.repository.get("project_knowledge", strategy_id)
            if not strategy:
                continue
            data = strategy.get("data") if isinstance(strategy.get("data"), dict) else {}
            strategies.append(
                {
                    "id": strategy.get("id"),
                    "name": strategy.get("name"),
                    "key": data.get("knowledge_key"),
                    "category": data.get("category"),
                    "domain": data.get("domain"),
                }
            )
        return {**case, "strategy_ids": strategy_ids, "strategies": strategies}

    def _strategy_ids(self, value: Any) -> list[int]:
        if not isinstance(value, list):
            return []

        result: list[int] = []
        seen: set[int] = set()
        for item in value:
            try:
                strategy_id = int(item)
            except (TypeError, ValueError):
                continue
            if strategy_id in seen:
                continue
            seen.add(strategy_id)
            result.append(strategy_id)
        return result
