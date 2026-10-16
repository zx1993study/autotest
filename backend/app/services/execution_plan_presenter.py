"""Pure ORM-to-VO mapping for execution plan services."""

from __future__ import annotations

from datetime import datetime

from app.models.execution_plan import (
    ExecutionPlan,
    ExecutionPlanCase,
    ExecutionPlanRun,
    ExecutionPlanRunItem,
)
from app.schemas.execution import (
    ExecutionPlanCaseOut,
    ExecutionPlanOut,
    ExecutionPlanRunItemOut,
    ExecutionPlanRunOut,
)


def execution_plan_out(row: ExecutionPlan) -> ExecutionPlanOut:
    """Convert a plan entity to the public list/detail representation."""

    api_ids = int_list(row.api_ids_json)
    web_feature_ids = int_list(row.web_feature_ids_json)
    return ExecutionPlanOut(
        id=row.id,
        name=row.name,
        project_id=row.project_id,
        test_rounds=row.test_rounds,
        test_type=row.test_type,
        api_ids=api_ids,
        web_feature_ids=web_feature_ids,
        api_count=len(api_ids),
        web_feature_count=len(web_feature_ids),
        description=row.description,
        requirement_title=row.requirement_title,
        requirement_document=row.requirement_document,
        generation=dict_value(row.generation_json),
        status=row.status,
        data={},
        created_at=format_time(row.created_at),
        updated_at=format_time(row.updated_at),
    )


def execution_plan_case_out(row: ExecutionPlanCase) -> ExecutionPlanCaseOut:
    """Convert one immutable plan case snapshot."""

    return ExecutionPlanCaseOut(
        id=row.id,
        plan_id=row.plan_id,
        case_type=row.case_type,
        feature_id=row.feature_id,
        feature_name=row.feature_name,
        case_id=row.case_id,
        case_name=row.case_name,
        case_version=row.case_version,
        snapshot=dict_value(row.snapshot_json),
        sort_order=row.sort_order,
        created_at=format_time(row.created_at),
        updated_at=format_time(row.updated_at),
    )


def execution_plan_run_out(row: ExecutionPlanRun) -> ExecutionPlanRunOut:
    """Convert one execution plan run."""

    return ExecutionPlanRunOut(
        id=row.id,
        plan_id=row.plan_id,
        round_no=row.round_no,
        status=row.status,
        total_count=row.total_count,
        success_count=row.success_count,
        failed_count=row.failed_count,
        pass_rate=row.pass_rate,
        started_at=format_optional_time(row.started_at),
        ended_at=format_optional_time(row.ended_at),
        created_at=format_time(row.created_at),
        updated_at=format_time(row.updated_at),
    )


def execution_plan_run_item_out(
    row: ExecutionPlanRunItem,
) -> ExecutionPlanRunItemOut:
    """Convert one case-level execution result."""

    return ExecutionPlanRunItemOut(
        id=row.id,
        run_id=row.run_id,
        plan_case_id=row.plan_case_id,
        case_type=row.case_type,
        case_id=row.case_id,
        status=row.status,
        duration_ms=row.duration_ms,
        error_message=row.error_message,
        report_record_id=row.report_record_id,
        artifact=dict_value(row.artifact_json),
        executed_at=format_optional_time(row.executed_at),
        created_at=format_time(row.created_at),
    )


def dict_value(value: object) -> dict[str, object]:
    """Return a defensive dictionary view of a JSON column."""

    return value if isinstance(value, dict) else {}


def int_list(value: object) -> list[int]:
    """Normalize a JSON array into unique positive integer IDs."""

    if not isinstance(value, list):
        return []
    result: list[int] = []
    for item in value:
        try:
            parsed = int(item)
        except (TypeError, ValueError):
            continue
        if parsed > 0 and parsed not in result:
            result.append(parsed)
    return result


def format_time(value: datetime | None) -> str:
    """Serialize required timestamps consistently."""

    return "" if value is None else value.isoformat(timespec="seconds")


def format_optional_time(value: datetime | None) -> str | None:
    """Serialize optional timestamps consistently."""

    return value.isoformat(timespec="seconds") if value else None
