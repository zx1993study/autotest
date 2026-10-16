from __future__ import annotations

from typing import Any

from app.repositories.interfaces import ResourceRepository
from app.schemas.cases import CaseExecutionSummary
from app.services.resource_service import ResourceService
from app.utils.api_response import extract_response_code

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
        source_id: int | None = None,
        status: Any = None,
        include_latest_execution: bool = False,
    ) -> tuple[list[dict[str, Any]], int]:
        data_filters: dict[str, Any] = {}
        if source_id is not None:
            data_filters["source_id"] = source_id
        if status is not None:
            data_filters["status"] = getattr(status, "value", status)
        rows, total = self.repository.list(
            self.table,
            keyword,
            project_id,
            page,
            page_size,
            data_filters or None,
        )
        rows = [self._normalize_case(item) for item in rows]
        rows = self._enrich_cases(rows)
        if include_latest_execution and self.case_type == "API":
            rows = self._with_latest_executions(rows, project_id)
        return rows, total

    def get(self, item_id: int) -> dict[str, Any]:
        return self._enrich_case(self._normalize_case(super().get(item_id)))

    def _with_latest_executions(self, cases: list[dict[str, Any]], project_id: int | None) -> list[dict[str, Any]]:
        records = self.repository.latest_execution_records(self.case_type, [int(case["id"]) for case in cases], project_id)
        latest = {}
        for record in records:
            data = record.get("data") or {}
            try:
                case_id = int(data["case_id"])
            except (KeyError, ValueError, TypeError):
                continue
            latest[(record.get("project_id"), case_id)] = self._execution_summary(record)
        return [{**case, "latest_execution": latest.get((case.get("project_id"), int(case["id"])))} for case in cases]

    def _execution_summary(self, record: dict[str, Any]) -> dict[str, Any]:
        data = record.get("data") or {}
        status = str(record.get("status") or "exception")
        error = str(data.get("error") or "") or None
        if status in {"error", "exception"} or (status == "failed" and error):
            status = "exception"
        if status not in {"success", "failed", "exception", "queued", "running", "cancelled", "skipped"}:
            status = "exception"
        code = data["response_code"] if "response_code" in data else extract_response_code(data.get("response_body"))
        return CaseExecutionSummary(
            record_id=record["id"], status=status, response_code=code,
            http_status=data.get("response_status"), error=error,
            executed_at=record.get("created_at"),
        ).model_dump()

    def list_generated_for_plan(
        self,
        project_id: int,
        plan_id: int,
    ) -> list[dict[str, Any]]:
        """Return formal cases owned by one execution-plan generation run."""

        rows, _ = self.repository.list(
            self.table,
            project_id=project_id,
            page=1,
            page_size=10000,
            data_filters={"generated_plan_id": plan_id},
        )
        return [self._normalize_case(item) for item in rows]

    def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        payload = self._case_payload(payload)
        payload["case_type"] = self.case_type
        payload.setdefault("data", {})
        return super().create(payload)

    def _related(self, table: str, item_id: Any, related=None) -> dict[str, Any] | None:
        if not item_id:
            return None
        if related is not None:
            return related.get(table, {}).get(int(item_id))
        return self.repository.get(table, int(item_id))

    def _enrich_cases(self, cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
        ids = {"project_knowledge": {key for row in cases for key in self._strategy_ids(row.get("strategy_ids"))}}
        if self.case_type == "API":
            ids.update({
                "api_interfaces": {int(row["source_id"]) for row in cases if row.get("source_id")},
                "projects": {int(row["project_id"]) for row in cases if row.get("project_id")},
            })
        related = {
            table: {int(row["id"]): row for row in self.repository.get_many(table, list(keys))}
            for table, keys in ids.items() if keys
        }
        return [self._enrich_case(row, related) for row in cases]

    def _enrich_case(self, case: dict[str, Any], related=None) -> dict[str, Any]:
        case = self._normalize_case(case)
        case = self._with_strategy_summaries(case, related)
        if self.case_type != "API":
            return case

        data = dict(case.get("data") or {})
        interface = self._related("api_interfaces", case.get("source_id"), related)
        interface_data = interface.get("data") if interface else {}
        project = self._related("projects", case.get("project_id"), related)
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

    def _with_strategy_summaries(self, case: dict[str, Any], related=None) -> dict[str, Any]:
        strategy_ids = self._strategy_ids(case.get("strategy_ids"))
        if not strategy_ids:
            return {**case, "strategy_ids": [], "strategies": []}

        strategies: list[dict[str, Any]] = []
        for strategy_id in strategy_ids:
            strategy = self._related("project_knowledge", strategy_id, related)
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
