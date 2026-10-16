"""Configure execution plan sources across plan and resource boundaries."""

from __future__ import annotations

from app.core.exceptions import BusinessRuleError
from app.repositories.interfaces import ExecutionPlanRepository, ResourceRepository
from app.schemas.execution import ExecutionPlanCreate, ExecutionPlanOut, ExecutionPlanUpdate
from app.services.execution_plan_service import ExecutionPlanService


class ExecutionPlanConfigurationService:
    """Validate project-owned API/Web selections before plan CRUD writes."""

    def __init__(
        self,
        plan_repository: ExecutionPlanRepository,
        resource_repository: ResourceRepository,
    ) -> None:
        self.plan_repository = plan_repository
        self.resource_repository = resource_repository
        self.plan_service = ExecutionPlanService(plan_repository)

    def create(self, payload: ExecutionPlanCreate) -> ExecutionPlanOut:
        """Create a configured plan whose sources belong to one project."""

        project_id = self._required_project_id(payload.project_id)
        self._validate_selections(
            project_id,
            payload.api_ids,
            payload.web_feature_ids,
        )
        return self.plan_service.create(payload)

    def update(
        self,
        plan_id: int,
        payload: ExecutionPlanUpdate,
    ) -> ExecutionPlanOut:
        """Update source scope and hide snapshots removed from that scope."""

        current = self.plan_service.get(plan_id)
        project_id = self._required_project_id(
            payload.project_id
            if "project_id" in payload.model_fields_set
            else current.project_id
        )
        api_ids = payload.api_ids if payload.api_ids is not None else current.api_ids
        web_feature_ids = (
            payload.web_feature_ids
            if payload.web_feature_ids is not None
            else current.web_feature_ids
        )
        self._validate_selections(project_id, api_ids, web_feature_ids)
        normalized = self._normalized_update(
            payload,
            project_id,
            api_ids,
            web_feature_ids,
        )
        result = self.plan_service.update(plan_id, normalized)
        self.plan_repository.replace_plan_feature_selection(
            plan_id,
            "API",
            set(api_ids),
        )
        self.plan_repository.replace_plan_feature_selection(
            plan_id,
            "WEB",
            set(web_feature_ids),
        )
        return result

    def _validate_selections(
        self,
        project_id: int,
        api_ids: list[int],
        web_feature_ids: list[int],
    ) -> None:
        if not api_ids and not web_feature_ids:
            raise BusinessRuleError("执行计划至少需要选择一个 API 或 Web 功能")
        self._validate_resource_ids("api_interfaces", "API", project_id, api_ids)
        self._validate_resource_ids("web_pages", "Web 功能", project_id, web_feature_ids)

    def _validate_resource_ids(
        self,
        table: str,
        label: str,
        project_id: int,
        selected_ids: list[int],
    ) -> None:
        if not selected_ids:
            return
        rows, _ = self.resource_repository.list(
            table,
            project_id=project_id,
            page=1,
            page_size=10000,
        )
        valid_ids = {
            int(item["id"])
            for item in rows
            if item.get("status") == "active" and isinstance(item.get("id"), int)
        }
        invalid_ids = [item for item in selected_ids if item not in valid_ids]
        if invalid_ids:
            values = ", ".join(str(item) for item in invalid_ids[:10])
            raise BusinessRuleError(f"{label} 不属于当前项目或已停用：{values}")

    def _required_project_id(self, value: int | None) -> int:
        if value is None:
            raise BusinessRuleError("执行计划必须归属项目")
        project = self.resource_repository.get("projects", value)
        if project is None or project.get("status") != "active":
            raise BusinessRuleError("项目不存在或已停用")
        return value

    def _normalized_update(
        self,
        payload: ExecutionPlanUpdate,
        project_id: int,
        api_ids: list[int],
        web_feature_ids: list[int],
    ) -> ExecutionPlanUpdate:
        changes: dict[str, object] = {
            "project_id": project_id,
            "api_ids": api_ids,
            "web_feature_ids": web_feature_ids,
        }
        if "description" in payload.model_fields_set and payload.description is None:
            changes["description"] = ""
        return payload.model_copy(update=changes)
