from __future__ import annotations

from datetime import date
from typing import Any, Protocol

from app.models.execution_plan import (
    ExecutionPlan,
    ExecutionPlanCase,
    ExecutionPlanRun,
    ExecutionPlanRunItem,
)
from app.schemas.api_report import ApiReportQuery
from app.schemas.execution_flow import ExecutionFlowSummary
from app.schemas.list_summaries import AppFeatureSummary, WebFeatureCounts
from app.schemas.report_statistics import ReportStatisticsAggregate
from app.schemas.web_execution_summary import WebExecutionSnapshot, WebExecutionSummaryQuery


class ResourceRepository(Protocol):
    def web_execution_snapshots(self, query: WebExecutionSummaryQuery) -> list[WebExecutionSnapshot]:
        ...

    def api_report_rows(self, query: ApiReportQuery) -> tuple[list[dict[str, Any]], int]:
        ...

    def list(
        self,
        table: str,
        keyword: str | None = None,
        project_id: int | None = None,
        page: int = 1,
        page_size: int = 20,
        data_filters: dict[str, Any] | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        ...

    def get(self, table: str, item_id: int) -> dict[str, Any] | None:
        ...

    def get_many(self, table: str, item_ids: list[int]) -> list[dict[str, Any]]:
        ...

    def get_related(self, table: str, parent_key: str, parent_ids: list[int], statuses: list[str] | None = None) -> list[dict[str, Any]]:
        ...

    def app_feature_summaries(self, feature_ids: list[int]) -> dict[int, AppFeatureSummary]:
        ...

    def web_feature_counts(self, feature_ids: list[int]) -> dict[int, WebFeatureCounts]:
        ...

    def report_statistics(self, project_id: int | None, start: date, end: date) -> ReportStatisticsAggregate:
        ...

    def latest_execution_records(self, case_type: str, case_ids: list[int], project_id: int | None = None) -> list[dict[str, Any]]:
        ...

    def execution_flow_summaries(self, flow_ids: list[int]) -> dict[int, ExecutionFlowSummary]:
        ...

    def create(self, table: str, data: dict[str, Any]) -> dict[str, Any]:
        ...

    def create_many(self, table: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        ...

    def update(self, table: str, item_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
        ...

    def update_if_status(self, table: str, item_id: int, expected: str, data: dict[str, Any]) -> dict[str, Any] | None:
        ...

    def complete_agent_task(self, task_id: int, node_key: str, status: str, data: dict[str, Any], records: list[dict[str, Any]]) -> dict[str, Any] | None:
        ...

    def update_many(
        self,
        table: str,
        rows: list[tuple[int, dict[str, Any]]],
    ) -> list[dict[str, Any]]:
        ...

    def delete(self, table: str, item_id: int) -> bool:
        ...

    def batch_delete(self, table: str, ids: list[int]) -> int:
        ...

    def batch_delete_with_children(self, table: str, ids: list[int], child_table: str, parent_key: str) -> int:
        ...

    def delete_by_project(self, table: str, project_id: int) -> int:
        ...


class AgentProgressRepository(ResourceRepository, Protocol):
    def patch_running_agent_task(self, task_id: int, node_key: str, patch: dict[str, Any], expected: dict[str, Any] | None = None) -> dict[str, Any] | None:
        ...

    def resolve_app_connection(self, task_id: int, node_key: str, transition: dict[str, Any]) -> dict[str, Any] | None:
        ...


class ApiModuleRepository(ResourceRepository, Protocol):
    def save_module(self, project_id: int, item_id: int | None, payload: dict[str, Any]) -> dict[str, Any] | None:
        ...

    def module_reference_count(self, item_id: int) -> int:
        ...

    def delete_module(self, project_id: int, item_id: int) -> bool:
        ...


class ExecutionPlanRepository(Protocol):
    """Persistence contract for execution plans."""

    def list(
        self,
        *,
        keyword: str | None,
        project_id: int | None,
        test_type: str | None,
        status: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[ExecutionPlan], int]:
        ...

    def get(self, plan_id: int) -> ExecutionPlan | None:
        ...

    def create(self, data: dict[str, object]) -> ExecutionPlan:
        ...

    def update(self, plan_id: int, data: dict[str, object]) -> ExecutionPlan | None:
        ...

    def delete(self, plan_id: int) -> bool:
        ...

    def batch_delete(self, plan_ids: list[int]) -> int:
        ...

    def list_test_cases(self, case_type: str, project_id: int | None) -> list[object]:
        ...

    def feature_names(self, case_type: str, feature_ids: set[int]) -> dict[int, str]:
        ...

    def create_plan_cases(self, rows: list[dict[str, object]]) -> list[ExecutionPlanCase]:
        ...

    def mark_plan_feature_cases_selected(self, plan_id: int, case_type: str, feature_ids: set[int]) -> int:
        ...

    def replace_plan_feature_selection(
        self,
        plan_id: int,
        case_type: str,
        feature_ids: set[int],
    ) -> int:
        ...

    def delete_generated_plan_cases(self, plan_id: int) -> int:
        ...

    def list_plan_cases(self, plan_id: int) -> list[ExecutionPlanCase]:
        ...

    def delete_plan_cases(self, plan_id: int) -> int:
        ...

    def list_runs(self, plan_id: int) -> list[ExecutionPlanRun]:
        ...

    def latest_run(self, plan_id: int) -> ExecutionPlanRun | None:
        ...

    def list_run_items(self, run_id: int) -> list[ExecutionPlanRunItem]:
        ...

    def create_run(self, data: dict[str, object]) -> ExecutionPlanRun:
        ...

    def update_run(self, run_id: int, data: dict[str, object]) -> ExecutionPlanRun | None:
        ...

    def create_run_items(self, rows: list[dict[str, object]]) -> list[ExecutionPlanRunItem]:
        ...
