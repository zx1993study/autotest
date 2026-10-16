from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any

from app.core.exceptions import BusinessRuleError, ResourceNotFoundError
from app.enums.business import ExecutionPlanStatusEnum, ExecutionRunItemStatusEnum, ExecutionRunStatusEnum
from app.models.execution_plan import ExecutionPlan, ExecutionPlanCase, ExecutionPlanRunItem
from app.repositories.interfaces import ExecutionPlanRepository, ResourceRepository
from app.schemas.execution import ExecutionPlanDetailOut, ExecutionPlanRunRequest
from app.services.case_execution_dispatcher import CaseExecutionDispatcher
from app.services.execution_plan_service import ExecutionPlanService


class ExecutionPlanRunService:
    """Run execution plans and persist batch-level results.

    The actual Web/API/App execution remains owned by ``CaseExecutionDispatcher``.
    This service only orchestrates plan snapshots and records the relationship
    between a plan run, each snapshot case, and the generated execution record.
    """

    def __init__(
        self,
        plan_repository: ExecutionPlanRepository,
        resource_repository: ResourceRepository,
        dispatcher: CaseExecutionDispatcher | None = None,
    ) -> None:
        self.plan_repository = plan_repository
        self.resource_repository = resource_repository
        self.dispatcher = dispatcher or CaseExecutionDispatcher(resource_repository)
        self.plan_service = ExecutionPlanService(plan_repository)

    def run(self, plan_id: int, payload: ExecutionPlanRunRequest) -> ExecutionPlanDetailOut:
        """Run the next plan round and return refreshed detail data."""

        plan = self._get_existing(plan_id)
        if plan.status == ExecutionPlanStatusEnum.DONE.code:
            raise BusinessRuleError("执行计划已完成，不能继续执行")
        plan_cases = self.plan_service.selected_plan_cases(plan_id)
        if not plan_cases:
            raise BusinessRuleError("执行计划暂无测试项，请先在详情页添加 API 信息或 Web 功能")

        round_no = self._next_round_no(plan, payload.round_no, plan_cases)
        started_at = datetime.now()
        run = self.plan_repository.create_run(
            {
                "plan_id": plan.id,
                "round_no": round_no,
                "status": ExecutionRunStatusEnum.RUNNING.code,
                "total_count": len(plan_cases),
                "started_at": started_at,
            }
        )
        item_rows = self._execute_plan_cases(run.id, plan, plan_cases, payload)
        run_items = self.plan_repository.create_run_items(item_rows)
        summary = self._run_summary(run_items)
        self.plan_repository.update_run(
            run.id,
            {
                **summary,
                "ended_at": datetime.now(),
            },
        )
        return self.plan_service.detail(plan_id)

    def _get_existing(self, plan_id: int) -> ExecutionPlan:
        plan = self.plan_repository.get(plan_id)
        if plan is None:
            raise ResourceNotFoundError("执行计划不存在")
        return plan

    def _next_round_no(
        self,
        plan: ExecutionPlan,
        requested_round_no: int | None,
        plan_cases: list[ExecutionPlanCase],
    ) -> int:
        if requested_round_no is not None:
            if requested_round_no > plan.test_rounds:
                raise BusinessRuleError("执行轮次不能超过测试轮数")
            return requested_round_no
        runs = self.plan_repository.list_runs(plan.id)
        selected_case_ids = {item.id for item in plan_cases}
        latest_round = max(
            (
                run.round_no
                for run in runs
                if any(item.plan_case_id in selected_case_ids for item in self.plan_repository.list_run_items(run.id))
            ),
            default=0,
        )
        next_round = latest_round + 1
        if next_round > plan.test_rounds:
            raise BusinessRuleError("执行计划已达到测试轮数，请复制计划后继续执行")
        return next_round

    def _execute_plan_cases(
        self,
        run_id: int,
        plan: ExecutionPlan,
        plan_cases: list[ExecutionPlanCase],
        payload: ExecutionPlanRunRequest,
    ) -> list[dict[str, object]]:
        item_rows: list[dict[str, object]] = []
        cases_by_type: dict[str, list[ExecutionPlanCase]] = defaultdict(list)
        for plan_case in plan_cases:
            if not self._is_executable_case(plan_case):
                item_rows.append(self._skipped_item_row(run_id, plan_case, "手动测试功能点不支持自动执行"))
                continue
            cases_by_type[plan_case.case_type].append(plan_case)
        for case_type, items in cases_by_type.items():
            item_rows.extend(self._execute_case_group(run_id, plan, case_type, items, payload))
        return item_rows

    def _execute_case_group(
        self,
        run_id: int,
        plan: ExecutionPlan,
        case_type: str,
        plan_cases: list[ExecutionPlanCase],
        payload: ExecutionPlanRunRequest,
    ) -> list[dict[str, object]]:
        case_ids = [item.case_id for item in plan_cases]
        try:
            result = self.dispatcher.execute(
                case_type,
                {
                    "project_id": plan.project_id,
                    "auth_id": payload.auth_id,
                    "mode": payload.mode.code,
                    "node_id": payload.node_id,
                    "case_ids": case_ids,
                    "config": payload.config,
                },
            )
        except Exception as exc:  # noqa: BLE001 - plan runs must persist per-case failures.
            return [
                self._failed_item_row(run_id, plan_case, str(exc))
                for plan_case in plan_cases
            ]
        record_map = self._records_by_case_id(result)
        queued_artifact = self._queued_artifact(result)
        return [
            self._item_row_from_record(
                run_id,
                plan_case,
                record_map.get(plan_case.case_id),
                queued_artifact,
            )
            for plan_case in plan_cases
        ]

    def _records_by_case_id(self, result: dict[str, Any]) -> dict[int, dict[str, Any]]:
        records = result.get("records")
        if not isinstance(records, list):
            return {}
        mapped: dict[int, dict[str, Any]] = {}
        for record in records:
            if not isinstance(record, dict):
                continue
            data = self._record_data(record)
            case_id = self._optional_int(data.get("case_id"))
            if case_id is not None:
                mapped[case_id] = record
        return mapped

    def _item_row_from_record(
        self,
        run_id: int,
        plan_case: ExecutionPlanCase,
        record: dict[str, Any] | None,
        queued_artifact: dict[str, object],
    ) -> dict[str, object]:
        if record is None:
            return {
                "run_id": run_id,
                "plan_case_id": plan_case.id,
                "case_type": plan_case.case_type,
                "case_id": plan_case.case_id,
                "status": ExecutionRunItemStatusEnum.QUEUED.code,
                "artifact_json": queued_artifact,
            }
        data = self._record_data(record)
        status = str(record.get("status") or ExecutionRunItemStatusEnum.FAILED.code)
        return {
            "run_id": run_id,
            "plan_case_id": plan_case.id,
            "case_type": plan_case.case_type,
            "case_id": plan_case.case_id,
            "status": status,
            "duration_ms": self._optional_int(data.get("duration_ms")),
            "error_message": self._record_error(record, data),
            "report_record_id": self._optional_int(record.get("id")),
            "artifact_json": self._record_artifact(record, data),
            "executed_at": datetime.now(),
        }

    def _failed_item_row(self, run_id: int, plan_case: ExecutionPlanCase, error: str) -> dict[str, object]:
        return {
            "run_id": run_id,
            "plan_case_id": plan_case.id,
            "case_type": plan_case.case_type,
            "case_id": plan_case.case_id,
            "status": ExecutionRunItemStatusEnum.FAILED.code,
            "error_message": error,
            "artifact_json": {"error": error},
            "executed_at": datetime.now(),
        }

    def _skipped_item_row(self, run_id: int, plan_case: ExecutionPlanCase, reason: str) -> dict[str, object]:
        return {
            "run_id": run_id,
            "plan_case_id": plan_case.id,
            "case_type": plan_case.case_type,
            "case_id": plan_case.case_id,
            "status": ExecutionRunItemStatusEnum.SKIPPED.code,
            "error_message": reason,
            "artifact_json": {"reason": reason},
            "executed_at": datetime.now(),
        }

    def _is_executable_case(self, plan_case: ExecutionPlanCase) -> bool:
        snapshot = plan_case.snapshot_json if isinstance(plan_case.snapshot_json, dict) else {}
        if snapshot.get("manual") or snapshot.get("placeholder"):
            return False
        return plan_case.case_type in {"WEB", "API", "APP"} and plan_case.case_id > 0

    def _run_summary(self, run_items: list[ExecutionPlanRunItem]) -> dict[str, object]:
        success_count = sum(1 for item in run_items if item.status == ExecutionRunItemStatusEnum.SUCCESS.code)
        failed_count = sum(1 for item in run_items if item.status == ExecutionRunItemStatusEnum.FAILED.code)
        queued_count = sum(1 for item in run_items if item.status == ExecutionRunItemStatusEnum.QUEUED.code)
        total_count = len(run_items)
        if failed_count and success_count:
            status = ExecutionRunStatusEnum.PARTIAL.code
        elif failed_count:
            status = ExecutionRunStatusEnum.FAILED.code
        elif queued_count:
            status = ExecutionRunStatusEnum.QUEUED.code
        else:
            status = ExecutionRunStatusEnum.SUCCESS.code
        return {
            "status": status,
            "total_count": total_count,
            "success_count": success_count,
            "failed_count": failed_count,
            "pass_rate": self._percent(success_count, success_count + failed_count),
        }

    def _queued_artifact(self, result: dict[str, Any]) -> dict[str, object]:
        artifact: dict[str, object] = {}
        agent_task = result.get("agent_task")
        if isinstance(agent_task, dict):
            artifact["agent_task"] = {
                "id": agent_task.get("id"),
                "node_id": agent_task.get("node_id"),
                "status": agent_task.get("status"),
            }
        return artifact

    def _record_artifact(self, record: dict[str, Any], data: dict[str, Any]) -> dict[str, object]:
        keys = (
            "mode",
            "node_id",
            "response_status",
            "screenshot_url",
            "screenshot_file",
            "screenshot_error",
            "step_count",
            "url",
        )
        artifact = {key: data[key] for key in keys if key in data}
        artifact["record_name"] = str(record.get("name") or "")
        return artifact

    def _record_error(self, record: dict[str, Any], data: dict[str, Any]) -> str | None:
        error = data.get("error") or record.get("description")
        return str(error) if error else None

    def _record_data(self, record: dict[str, Any]) -> dict[str, Any]:
        data = record.get("data")
        return data if isinstance(data, dict) else {}

    def _optional_int(self, value: object) -> int | None:
        try:
            parsed = int(value) if value is not None else 0
        except (TypeError, ValueError):
            return None
        return parsed if parsed > 0 else None

    def _percent(self, numerator: int, denominator: int) -> float:
        if denominator <= 0:
            return 0.0
        return round((numerator / denominator) * 100, 1)
