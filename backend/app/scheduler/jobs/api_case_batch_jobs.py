"""Parallel API requests with database access confined to the calling thread."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from typing import Any

from pydantic import ValidationError

from app.core.exceptions import BusinessRuleError
from app.repositories.api_flow_snapshot_repository import ApiFlowSnapshotRepository
from app.repositories.interfaces import ResourceRepository
from app.scheduler.jobs.api_case_executor import ApiCaseExecutor
from app.schemas.cases import ApiCaseExecutionConfig


class _BatchApiCaseExecutor(ApiCaseExecutor):
    def __init__(self, tables: dict[str, list[dict[str, Any]]], preparation_lock: Any):
        super().__init__(ApiFlowSnapshotRepository(tables))
        self.preparation_lock = preparation_lock

    def prepare_execution(self, case, payload):
        # Dynamic phone reservations are shared across the batch, not HTTP calls.
        with self.preparation_lock:
            return super().prepare_execution(case, payload)


def run_api_case_batch(cases: list[dict[str, Any]], payload: dict[str, Any],
                       repository: ResourceRepository) -> list[dict[str, Any]]:
    try:
        config = ApiCaseExecutionConfig.model_validate(payload.get("config") or {})
    except ValidationError as exc:
        raise BusinessRuleError("API 执行配置无效：并发数应为 1-10，超时应为 1-300 秒") from exc
    execution_payload = {**payload, "config": config.model_dump(), "_dynamic_phone_reservations": set()}
    workers = min(config.concurrency, len(cases))
    if workers <= 1:
        executor = ApiCaseExecutor(repository)
        return [executor.execute(case, execution_payload) for case in cases]

    tables = _load_references(cases, execution_payload, repository)
    preparation_lock = Lock()
    ordered_records: list[dict[str, Any] | None] = [None] * len(cases)
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="api-case") as pool:
        futures = {
            pool.submit(_execute_snapshot, case, execution_payload, tables, preparation_lock): index
            for index, case in enumerate(cases)
        }
        for future in as_completed(futures):
            index = futures[future]
            try:
                record = future.result()
            except Exception as exc:  # noqa: BLE001 - preserve failed worker evidence and finish the batch.
                record = _failed_record(cases[index], execution_payload, exc)
            ordered_records[index] = repository.create("execution_records", record)
    return [record for record in ordered_records if record is not None]


def _execute_snapshot(case, payload, tables, preparation_lock):
    return _BatchApiCaseExecutor(tables, preparation_lock).execute(case, payload, persist_record=False)


def _load_references(cases, payload, repository):
    references: dict[str, dict[int, dict[str, Any]]] = {
        table: {} for table in ("projects", "api_interfaces", "project_auth", "api_fields", "api_import_tasks")
    }
    loaded: set[tuple[str, int]] = set()
    field_queries: set[tuple[int | None, int]] = set()
    for case in cases:
        project_id = case.get("project_id") or payload.get("project_id")
        interface_id = case.get("source_id")
        project = _load_one("projects", project_id, repository, references, loaded)
        interface = _load_one("api_interfaces", interface_id, repository, references, loaded)
        interface_data = (interface or {}).get("data") or {}
        data = case.get("data") or {}
        legacy = data.get("request") if isinstance(data.get("request"), dict) else {}
        request = {**legacy, **data}
        if not request.get("skip_auth"):
            auth_id = payload.get("auth_id") or request.get("auth_id") or interface_data.get("auth_id")
            _load_one("project_auth", auth_id, repository, references, loaded)
        if interface_id and (project_id, interface_id) not in field_queries:
            field_queries.add((project_id, interface_id))
            rows, _ = repository.list("api_fields", project_id=project_id, page_size=10000,
                                      data_filters={"interface_id": interface_id})
            references["api_fields"].update({row["id"]: row for row in rows})
        needs_import = not (request.get("api_base_path") or interface_data.get("api_base_path")
                            or ((project or {}).get("data") or {}).get("api_base_path"))
        if project_id and needs_import and ("api_import_tasks", project_id) not in loaded:
            loaded.add(("api_import_tasks", project_id))
            rows, _ = repository.list("api_import_tasks", project_id=project_id, page_size=20)
            references["api_import_tasks"].update({row["id"]: row for row in rows})
    return {table: list(rows.values()) for table, rows in references.items()}


def _load_one(table, item_id, repository, references, loaded):
    if not item_id:
        return None
    try:
        item_id = int(item_id)
    except (TypeError, ValueError):
        # The executor records an invalid reference as a per-case failure.
        return None
    key = (table, item_id)
    if key not in loaded:
        loaded.add(key)
        row = repository.get(table, item_id)
        if row:
            references[table][item_id] = row
    return references[table].get(item_id)


def _failed_record(case, payload, error):
    return {
        "name": f"API 用例执行 - {case['name']}",
        "project_id": case.get("project_id") or payload.get("project_id"),
        "description": str(error), "status": "failed",
        "data": {"case_id": case["id"], "case_type": "API", "mode": payload.get("mode", "local_headless"),
                 "error": str(error), "response_status": None, "duration_ms": 0},
    }
