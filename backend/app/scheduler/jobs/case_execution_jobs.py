from __future__ import annotations

from typing import Any

from app.core.exceptions import BusinessRuleError, ResourceNotFoundError
from app.repositories.interfaces import ResourceRepository
from app.scheduler.jobs.api_case_executor import ApiCaseExecutor
from app.scheduler.jobs.app_case_executor import AppCaseExecutor
from app.services.test_case_service import test_case_table
from app.scheduler.jobs.web_case_executor import WebCaseExecutor


def run_case_execution_job(
    case_type: str,
    payload: dict[str, Any],
    repository: ResourceRepository,
) -> dict[str, Any]:
    """Execute selected formal test cases and return the aggregated result.

    The router is only responsible for request validation and response
    wrapping. This scheduler job owns execution orchestration: loading selected
    cases, selecting the domain executor, and summarizing generated records.
    """

    normalized_type = case_type.upper()
    case_ids = [int(case_id) for case_id in payload.get("case_ids", []) if case_id]
    if not case_ids:
        raise BusinessRuleError("请选择要执行的用例")

    cases = _load_cases(normalized_type, case_ids, repository)
    if not cases:
        raise ResourceNotFoundError("未找到可执行的正式用例")

    executor = _executor(normalized_type, repository)
    records = [executor.execute(case, payload) for case in cases]
    success_count = sum(1 for record in records if record.get("status") == "success")
    failed_count = sum(1 for record in records if record.get("status") == "failed")
    return {
        "total": len(records),
        "success_count": success_count,
        "failed_count": failed_count,
        "queued_count": len(records) - success_count - failed_count,
        "records": records,
    }


def _load_cases(
    case_type: str,
    case_ids: list[int],
    repository: ResourceRepository,
) -> list[dict[str, Any]]:
    table = test_case_table(case_type)
    cases: list[dict[str, Any]] = []
    for case_id in case_ids:
        item = repository.get(table, case_id)
        if item:
            cases.append(_normalize_case(case_type, item))
    return cases


def _normalize_case(case_type: str, case: dict[str, Any]) -> dict[str, Any]:
    data = case.get("data") if isinstance(case.get("data"), dict) else {}
    data = {
        key: value
        for key, value in data.items()
        if key not in {"assertions", "strategies", "strategy", "strategy_ids"}
    }
    data.setdefault("case_type", case_type)
    return {**case, "case_type": case_type, "data": data}


def _executor(
    case_type: str,
    repository: ResourceRepository,
) -> ApiCaseExecutor | WebCaseExecutor | AppCaseExecutor:
    if case_type == "API":
        return ApiCaseExecutor(repository)
    if case_type == "WEB":
        return WebCaseExecutor(repository)
    return AppCaseExecutor(repository, case_type)
