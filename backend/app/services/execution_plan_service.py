"""CRUD and lifecycle rules for the execution_plans table."""

from __future__ import annotations

from app.core.exceptions import BusinessRuleError, ResourceNotFoundError
from app.enums.business import ExecutionPlanStatusEnum, ExecutionPlanTestTypeEnum
from app.models.execution_plan import ExecutionPlan, ExecutionPlanCase
from app.repositories.interfaces import ExecutionPlanRepository
from app.schemas.execution import (
    ExecutionPlanCreate,
    ExecutionPlanDetailOut,
    ExecutionPlanFeatureAddRequest,
    ExecutionPlanManualFeatureCreate,
    ExecutionPlanOut,
    ExecutionPlanUpdate,
)
from app.services.execution_plan_detail_service import ExecutionPlanDetailService
from app.services.execution_plan_presenter import (
    dict_value,
    execution_plan_out,
    int_list,
)


class ExecutionPlanService:
    """Own execution plan CRUD while delegating case-detail behavior."""

    def __init__(self, repository: ExecutionPlanRepository) -> None:
        self.repository = repository
        self.detail_service = ExecutionPlanDetailService(repository)

    def list(
        self,
        *,
        keyword: str | None,
        project_id: int | None,
        test_type: str | None,
        status: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[ExecutionPlanOut], int]:
        """Return paginated execution plans."""

        rows, total = self.repository.list(
            keyword=keyword,
            project_id=project_id,
            test_type=test_type,
            status=status,
            page=page,
            page_size=page_size,
        )
        return [execution_plan_out(row) for row in rows], total

    def get(self, plan_id: int) -> ExecutionPlanOut:
        """Return one plan or raise a stable business error."""

        return execution_plan_out(self._get_existing(plan_id))

    def create(self, payload: ExecutionPlanCreate) -> ExecutionPlanOut:
        """Create a plan with normalized domain and source selections."""

        test_type = self._resolve_test_type(
            payload.test_type,
            payload.api_ids,
            payload.web_feature_ids,
        )
        row = self.repository.create(
            {
                "name": payload.name,
                "project_id": payload.project_id,
                "test_rounds": payload.test_rounds,
                "test_type": test_type,
                "api_ids_json": payload.api_ids,
                "web_feature_ids_json": payload.web_feature_ids,
                "description": payload.description,
                "status": payload.status.code,
            }
        )
        return execution_plan_out(row)

    def update(self, plan_id: int, payload: ExecutionPlanUpdate) -> ExecutionPlanOut:
        """Edit a plan without exposing persistence details to routers."""

        current = self._get_existing(plan_id)
        update_data = payload.model_dump(exclude_unset=True)
        self._drop_hidden_empty_values(update_data)
        self._normalize_enum_codes(update_data)
        self._move_source_ids(update_data)
        api_ids = int_list(update_data.get("api_ids_json", current.api_ids_json))
        web_ids = int_list(
            update_data.get("web_feature_ids_json", current.web_feature_ids_json)
        )
        update_data["test_type"] = self._resolve_test_type(
            payload.test_type,
            api_ids,
            web_ids,
        )
        row = self.repository.update(plan_id, update_data)
        if row is None:
            raise ResourceNotFoundError("执行计划不存在")
        return execution_plan_out(row)

    def complete(self, plan_id: int) -> ExecutionPlanOut:
        """Mark a plan as completed."""

        row = self.repository.update(
            plan_id,
            {"status": ExecutionPlanStatusEnum.DONE.code},
        )
        if row is None:
            raise ResourceNotFoundError("执行计划不存在")
        return execution_plan_out(row)

    def record_generation(
        self,
        plan_id: int,
        metadata: dict[str, object],
    ) -> ExecutionPlanOut:
        """Persist auditable generation metadata owned by the plan."""

        row = self.repository.update(plan_id, {"generation_json": metadata})
        if row is None:
            raise ResourceNotFoundError("执行计划不存在")
        return execution_plan_out(row)

    def copy(self, plan_id: int) -> ExecutionPlanOut:
        """Copy a plan and its currently selected snapshots."""

        source = self._get_existing(plan_id)
        row = self.repository.create(
            {
                "name": self._copy_name(source.name),
                "project_id": source.project_id,
                "test_rounds": source.test_rounds,
                "test_type": source.test_type,
                "description": source.description,
                "requirement_title": source.requirement_title,
                "requirement_document": source.requirement_document,
                "generation_json": dict_value(source.generation_json),
                "api_ids_json": int_list(source.api_ids_json),
                "web_feature_ids_json": int_list(source.web_feature_ids_json),
                "status": ExecutionPlanStatusEnum.ACTIVE.code,
            }
        )
        self.detail_service.copy_plan_cases(source.id, row.id)
        return execution_plan_out(row)

    def detail(self, plan_id: int) -> ExecutionPlanDetailOut:
        """Return plan detail from the dedicated query service."""

        return self.detail_service.detail(plan_id)

    def add_features(
        self,
        plan_id: int,
        payload: ExecutionPlanFeatureAddRequest,
    ) -> ExecutionPlanDetailOut:
        """Delegate feature snapshot creation."""

        return self.detail_service.add_features(plan_id, payload)

    def add_manual_feature(
        self,
        plan_id: int,
        payload: ExecutionPlanManualFeatureCreate,
    ) -> ExecutionPlanDetailOut:
        """Delegate manual test-point creation."""

        return self.detail_service.add_manual_feature(plan_id, payload)

    def selected_plan_cases(self, plan_id: int) -> list[ExecutionPlanCase]:
        """Return snapshots included in current plan execution."""

        return self.detail_service.selected_plan_cases(plan_id)

    def delete(self, plan_id: int) -> bool:
        """Soft delete a plan."""

        if not self.repository.delete(plan_id):
            raise ResourceNotFoundError("执行计划不存在")
        return True

    def batch_delete(self, plan_ids: list[int]) -> dict[str, int]:
        """Soft delete multiple plans."""

        return {"deleted_count": self.repository.batch_delete(plan_ids)}

    def _get_existing(self, plan_id: int) -> ExecutionPlan:
        row = self.repository.get(plan_id)
        if row is None:
            raise ResourceNotFoundError("执行计划不存在")
        return row

    def _resolve_test_type(
        self,
        requested: ExecutionPlanTestTypeEnum | None,
        api_ids: list[int],
        web_feature_ids: list[int],
    ) -> str:
        if api_ids and web_feature_ids:
            return ExecutionPlanTestTypeEnum.ALL.code
        if api_ids:
            return ExecutionPlanTestTypeEnum.API.code
        if web_feature_ids:
            return ExecutionPlanTestTypeEnum.WEB.code
        if requested is not None:
            return requested.code
        raise BusinessRuleError("执行计划至少需要选择一个 API 或 Web 功能")

    def _normalize_enum_codes(self, data: dict[str, object]) -> None:
        test_type = data.get("test_type")
        if hasattr(test_type, "code"):
            data["test_type"] = test_type.code

    def _move_source_ids(self, data: dict[str, object]) -> None:
        for source_key, target_key in (
            ("api_ids", "api_ids_json"),
            ("web_feature_ids", "web_feature_ids_json"),
        ):
            if source_key in data:
                data[target_key] = data.pop(source_key)

    def _drop_hidden_empty_values(self, data: dict[str, object]) -> None:
        for key in ("project_id", "description"):
            if data.get(key) is None:
                data.pop(key, None)

    def _copy_name(self, name: str) -> str:
        suffix = " - 副本"
        return f"{name[: 128 - len(suffix)]}{suffix}"
