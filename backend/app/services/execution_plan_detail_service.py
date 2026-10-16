"""Execution plan detail, feature snapshot and result grouping behavior."""

from __future__ import annotations

from datetime import UTC, datetime

from app.core.exceptions import ResourceNotFoundError
from app.enums.business import ExecutionPlanTestTypeEnum
from app.models.execution_plan import (
    ExecutionPlan,
    ExecutionPlanCase,
    ExecutionPlanRun,
    ExecutionPlanRunItem,
)
from app.repositories.interfaces import ExecutionPlanRepository
from app.schemas.execution import (
    ExecutionPlanDetailOut,
    ExecutionPlanFeatureAddRequest,
    ExecutionPlanFeatureCaseOut,
    ExecutionPlanFeatureOut,
    ExecutionPlanGroupOut,
    ExecutionPlanManualFeatureCreate,
    ExecutionPlanSummaryOut,
)
from app.services.execution_plan_presenter import (
    dict_value,
    execution_plan_case_out,
    execution_plan_out,
    execution_plan_run_item_out,
    execution_plan_run_out,
    format_time,
    int_list,
)


PLAN_CASE_TYPES = ("WEB", "API", "APP")
DETAIL_EXTRA_CASE_TYPES = ("MANUAL",)
CASE_TYPE_LABELS = {"WEB": "Web", "API": "API", "APP": "App", "MANUAL": "手动"}
PLAN_FEATURE_SELECTED_FLAG = "plan_feature_selected"


class ExecutionPlanDetailService:
    """Own plan detail reads and plan-case snapshot mutations."""

    def __init__(self, repository: ExecutionPlanRepository) -> None:
        self.repository = repository

    def detail(self, plan_id: int) -> ExecutionPlanDetailOut:
        """Return grouped snapshots and their latest selected run results."""

        plan = self._get_plan(plan_id)
        cases = self.selected_plan_cases(plan_id)
        runs = self.repository.list_runs(plan_id)
        selected_runs, items_by_run = self._selected_runs_and_items(runs, cases)
        latest_run = selected_runs[0] if selected_runs else None
        latest_items = items_by_run.get(latest_run.id, []) if latest_run else []
        latest_item_map = {item.plan_case_id: item for item in latest_items}
        return ExecutionPlanDetailOut(
            plan=execution_plan_out(plan),
            summary=self._summary(cases, selected_runs, latest_items),
            latest_run=execution_plan_run_out(latest_run) if latest_run else None,
            runs=[execution_plan_run_out(item) for item in selected_runs],
            groups=self._groups(plan, cases, latest_item_map),
        )

    def add_features(
        self,
        plan_id: int,
        payload: ExecutionPlanFeatureAddRequest,
    ) -> ExecutionPlanDetailOut:
        """Add source features and snapshot their active formal cases."""

        plan = self._get_plan(plan_id)
        selected_ids = set(self._normalized_ids(payload.feature_ids))
        self.repository.mark_plan_feature_cases_selected(
            plan.id,
            payload.case_type,
            selected_ids,
        )
        rows = self._feature_snapshot_rows(plan, payload.case_type, payload.feature_ids)
        if rows:
            self.repository.create_plan_cases(rows)
        return self.detail(plan_id)

    def add_manual_feature(
        self,
        plan_id: int,
        payload: ExecutionPlanManualFeatureCreate,
    ) -> ExecutionPlanDetailOut:
        """Add a skipped pseudo-case for a manually verified feature point."""

        plan = self._get_plan(plan_id)
        sort_order = self._next_sort_order(plan.id)
        self.repository.create_plan_cases(
            [
                {
                    "plan_id": plan.id,
                    "case_type": "MANUAL",
                    "feature_id": None,
                    "feature_name": payload.feature_name,
                    "case_id": -sort_order,
                    "case_name": "手动测试",
                    "case_version": format_time(datetime.now(UTC)),
                    "snapshot_json": {
                        "case_type": "MANUAL",
                        "manual": True,
                        "description": payload.description or "",
                    },
                    "sort_order": sort_order,
                }
            ]
        )
        return self.detail(plan_id)

    def selected_plan_cases(self, plan_id: int) -> list[ExecutionPlanCase]:
        """Return snapshots explicitly selected for current plan execution."""

        return [
            item
            for item in self.repository.list_plan_cases(plan_id)
            if self._is_selected(item)
        ]

    def copy_plan_cases(
        self,
        source_plan_id: int,
        target_plan_id: int,
    ) -> list[ExecutionPlanCase]:
        """Copy selected snapshots while preserving their immutable payload."""

        rows = [
            {
                "plan_id": target_plan_id,
                "case_type": item.case_type,
                "feature_id": item.feature_id,
                "feature_name": item.feature_name,
                "case_id": item.case_id,
                "case_name": item.case_name,
                "case_version": item.case_version,
                "snapshot_json": dict(item.snapshot_json or {}),
                "sort_order": item.sort_order,
            }
            for item in self.selected_plan_cases(source_plan_id)
        ]
        return self.repository.create_plan_cases(rows)

    def _feature_snapshot_rows(
        self,
        plan: ExecutionPlan,
        case_type: str,
        feature_ids: list[int],
    ) -> list[dict[str, object]]:
        normalized_ids = self._normalized_ids(feature_ids)
        selected_ids = set(normalized_ids)
        test_cases = [
            case
            for case in self.repository.list_test_cases(case_type, plan.project_id)
            if self._optional_int(getattr(case, "source_id", None)) in selected_ids
        ]
        names = self.repository.feature_names(case_type, selected_ids)
        existing_ids = {
            item.case_id
            for item in self.repository.list_plan_cases(plan.id)
            if item.case_type == case_type and item.case_id > 0
        }
        return self._new_snapshot_rows(
            plan,
            case_type,
            normalized_ids,
            test_cases,
            names,
            existing_ids,
        )

    def _new_snapshot_rows(
        self,
        plan: ExecutionPlan,
        case_type: str,
        feature_ids: list[int],
        test_cases: list[object],
        feature_names: dict[int, str],
        existing_ids: set[int],
    ) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        sort_order = self._next_sort_order(plan.id)
        for feature_id in feature_ids:
            for case in test_cases:
                if self._optional_int(getattr(case, "source_id", None)) != feature_id:
                    continue
                case_id = int(getattr(case, "id"))
                if case_id in existing_ids:
                    continue
                rows.append(
                    self._snapshot_row(
                        plan.id,
                        case_type,
                        feature_id,
                        feature_names.get(feature_id) or "未命名功能点",
                        case,
                        sort_order + len(rows),
                    )
                )
                existing_ids.add(case_id)
        return rows

    def _snapshot_row(
        self,
        plan_id: int,
        case_type: str,
        feature_id: int,
        feature_name: str,
        case: object,
        sort_order: int,
    ) -> dict[str, object]:
        return {
            "plan_id": plan_id,
            "case_type": case_type,
            "feature_id": feature_id,
            "feature_name": feature_name,
            "case_id": int(getattr(case, "id")),
            "case_name": str(getattr(case, "name") or "-"),
            "case_version": format_time(getattr(case, "updated_at", None)),
            "snapshot_json": self._case_snapshot(case, case_type, feature_id),
            "sort_order": sort_order,
        }

    def _case_snapshot(
        self,
        case: object,
        case_type: str,
        feature_id: int,
    ) -> dict[str, object]:
        return {
            "case_type": case_type,
            "source_id": feature_id,
            PLAN_FEATURE_SELECTED_FLAG: True,
            "description": str(getattr(case, "description", "") or ""),
            "status": str(getattr(case, "status", "") or ""),
            "data": dict_value(getattr(case, "data_json", None)),
            "steps": self._dict_list(getattr(case, "steps_json", None)),
            "assertions": self._dict_list(getattr(case, "assertions_json", None)),
            "strategy_ids": int_list(getattr(case, "strategy_ids_json", None)),
        }

    def _selected_runs_and_items(
        self,
        runs: list[ExecutionPlanRun],
        cases: list[ExecutionPlanCase],
    ) -> tuple[list[ExecutionPlanRun], dict[int, list[ExecutionPlanRunItem]]]:
        selected_ids = {item.id for item in cases}
        selected_runs: list[ExecutionPlanRun] = []
        items_by_run: dict[int, list[ExecutionPlanRunItem]] = {}
        for run in runs:
            items = [
                item
                for item in self.repository.list_run_items(run.id)
                if item.plan_case_id in selected_ids
            ]
            if items:
                selected_runs.append(run)
                items_by_run[run.id] = items
        return selected_runs, items_by_run

    def _summary(
        self,
        cases: list[ExecutionPlanCase],
        runs: list[ExecutionPlanRun],
        latest_items: list[ExecutionPlanRunItem],
    ) -> ExecutionPlanSummaryOut:
        success = sum(item.status == "success" for item in latest_items)
        failed = sum(item.status == "failed" for item in latest_items)
        executed = sum(item.status not in {"queued", "running"} for item in latest_items)
        features = {(item.case_type, item.feature_id, item.feature_name) for item in cases}
        return ExecutionPlanSummaryOut(
            feature_count=len(features),
            case_count=len(cases),
            run_count=len(runs),
            executed_count=executed,
            success_count=success,
            failed_count=failed,
            pass_rate=self._percent(success, success + failed),
        )

    def _groups(
        self,
        plan: ExecutionPlan,
        cases: list[ExecutionPlanCase],
        latest_items: dict[int, ExecutionPlanRunItem],
    ) -> list[ExecutionPlanGroupOut]:
        return [
            ExecutionPlanGroupOut(
                case_type=case_type,
                label=CASE_TYPE_LABELS.get(case_type, case_type),
                features=self._features(case_type, cases, latest_items),
            )
            for case_type in self._detail_case_types(plan, cases)
        ]

    def _features(
        self,
        case_type: str,
        cases: list[ExecutionPlanCase],
        latest_items: dict[int, ExecutionPlanRunItem],
    ) -> list[ExecutionPlanFeatureOut]:
        grouped: dict[tuple[int | None, str], list[ExecutionPlanFeatureCaseOut]] = {}
        for item in (case for case in cases if case.case_type == case_type):
            key = (item.feature_id, item.feature_name)
            grouped.setdefault(key, []).append(
                ExecutionPlanFeatureCaseOut(
                    case_snapshot=execution_plan_case_out(item),
                    latest_result=execution_plan_run_item_out(latest_items[item.id])
                    if item.id in latest_items
                    else None,
                )
            )
        return [
            ExecutionPlanFeatureOut(
                feature_id=feature_id,
                feature_name=feature_name,
                cases=items,
            )
            for (feature_id, feature_name), items in grouped.items()
        ]

    def _detail_case_types(
        self,
        plan: ExecutionPlan,
        cases: list[ExecutionPlanCase],
    ) -> tuple[str, ...]:
        initial = (
            list(PLAN_CASE_TYPES)
            if plan.test_type == ExecutionPlanTestTypeEnum.ALL.code
            else [plan.test_type]
        )
        for case_type in (*PLAN_CASE_TYPES, *DETAIL_EXTRA_CASE_TYPES):
            if any(item.case_type == case_type for item in cases) and case_type not in initial:
                initial.append(case_type)
        return tuple(initial)

    def _get_plan(self, plan_id: int) -> ExecutionPlan:
        plan = self.repository.get(plan_id)
        if plan is None:
            raise ResourceNotFoundError("执行计划不存在")
        return plan

    def _is_selected(self, item: ExecutionPlanCase) -> bool:
        snapshot = dict_value(item.snapshot_json)
        return item.case_type == "MANUAL" or snapshot.get("manual") is True or snapshot.get(PLAN_FEATURE_SELECTED_FLAG) is True

    def _next_sort_order(self, plan_id: int) -> int:
        return max(
            (item.sort_order for item in self.repository.list_plan_cases(plan_id)),
            default=0,
        ) + 1

    def _normalized_ids(self, values: list[int]) -> list[int]:
        return list(dict.fromkeys(item for item in values if item > 0))

    def _optional_int(self, value: object) -> int | None:
        try:
            parsed = int(value) if value is not None else 0
        except (TypeError, ValueError):
            return None
        return parsed if parsed > 0 else None

    def _dict_list(self, value: object) -> list[dict[str, object]]:
        if not isinstance(value, list):
            return []
        return [item for item in value if isinstance(item, dict)]

    def _percent(self, numerator: int, denominator: int) -> float:
        return round((numerator / denominator) * 100, 1) if denominator > 0 else 0.0
