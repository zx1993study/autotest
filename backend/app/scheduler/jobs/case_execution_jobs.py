from __future__ import annotations

from typing import Any

from app.core.exceptions import BusinessRuleError, ResourceNotFoundError
from app.repositories.interfaces import ResourceRepository
from app.scheduler.jobs.api_case_batch_jobs import run_api_case_batch
from app.scheduler.jobs.api_case_executor import ApiCaseExecutor
from app.scheduler.jobs.app_case_executor import AppCaseExecutor
from app.scheduler.jobs.web_case_executor import WebCaseExecutor
from app.services.test_case_service import test_case_table


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
    if normalized_type == "API":
        case_ids = list(dict.fromkeys(case_ids))
    if not case_ids:
        raise BusinessRuleError("请选择要执行的用例")

    cases = _load_cases(normalized_type, case_ids, repository)
    if not cases:
        raise ResourceNotFoundError("未找到可执行的正式用例")

    executor = _executor(normalized_type, repository)
    records = _execute_cases(normalized_type, cases, payload, repository, executor)
    success_count = sum(1 for record in records if record.get("status") == "success")
    failed_count = sum(1 for record in records if record.get("status") == "failed")
    return {
        "total": len(records),
        "success_count": success_count,
        "failed_count": failed_count,
        "queued_count": len(records) - success_count - failed_count,
        "records": records,
    }


def _execute_cases(
    case_type: str,
    cases: list[dict[str, Any]],
    payload: dict[str, Any],
    repository: ResourceRepository,
    executor: ApiCaseExecutor | WebCaseExecutor | AppCaseExecutor,
) -> list[dict[str, Any]]:
    if case_type == "API":
        return run_api_case_batch(cases, payload, repository)
    config = payload.get("config") if isinstance(payload.get("config"), dict) else {}
    payload = {**payload, "_dynamic_phone_reservations": set()}
    device_ids = _device_ids(config.get("device_ids"))
    if case_type not in {"APP", "MINIAPP"} or not device_ids:
        return [executor.execute(case, payload) for case in cases]

    records: list[dict[str, Any]] = []
    for device_id in device_ids:
        device = repository.get("app_devices", device_id)
        if not device:
            continue
        for case in cases:
            next_payload = dict(payload)
            next_config = dict(config)
            next_config["device_id"] = device_id
            next_config["device"] = device
            next_payload["config"] = next_config
            records.append(executor.execute(case, next_payload))
    if not records:
        raise ResourceNotFoundError("未找到可执行设备")
    return records


def _device_ids(value: Any) -> list[int]:
    if not isinstance(value, list):
        return []
    result: list[int] = []
    for item in value:
        try:
            device_id = int(item)
        except (TypeError, ValueError):
            continue
        if device_id > 0 and device_id not in result:
            result.append(device_id)
    return result


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
    if case_type == "APP":
        raise BusinessRuleError("App 操作必须通过本地 Agent 执行")
    if case_type == "API":
        return ApiCaseExecutor(repository)
    if case_type == "WEB":
        return WebCaseExecutor(repository)
    return AppCaseExecutor(repository, case_type)
