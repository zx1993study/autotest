from app.core.exceptions import BusinessRuleError, ResourceNotFoundError
from app.repositories.interfaces import ApiModuleRepository
from app.schemas.api_module import ApiModuleSaveRequest
from app.services.api_testing_service import (
    UNGROUPED_MODULE_KEY,
    UNGROUPED_MODULE_LABEL,
)


class ApiModuleService:
    def __init__(self, repository: ApiModuleRepository) -> None:
        self.repository = repository

    def create(self, payload: ApiModuleSaveRequest) -> dict:
        self._validate(payload)
        result = self.repository.save_module(payload.project_id, None, payload.model_dump())
        if result is None:
            raise BusinessRuleError("当前项目已存在同名模块")
        return result

    def update(self, item_id: int, payload: ApiModuleSaveRequest) -> dict:
        self._editable(payload.project_id, item_id)
        self._validate(payload, item_id)
        result = self.repository.save_module(payload.project_id, item_id, payload.model_dump())
        if result is None:
            raise BusinessRuleError("模块已变更或当前项目已存在同名模块，请刷新后重试")
        return result

    def delete(self, project_id: int, item_id: int) -> bool:
        self._editable(project_id, item_id)
        count = self.repository.module_reference_count(item_id)
        if count:
            raise BusinessRuleError(f"该模块关联 {count} 个 API，请先调整接口所属模块后再删除")
        if not self.repository.delete_module(project_id, item_id):
            raise BusinessRuleError("模块已变更或新增了关联 API，请刷新后重试")
        return True

    def _editable(self, project_id: int, item_id: int) -> dict:
        module = self.repository.get("api_modules", item_id)
        if not module or module.get("project_id") != project_id:
            raise ResourceNotFoundError("API 模块不存在或不属于当前项目")
        data = module.get("data") or {}
        if data.get("is_ungrouped") or data.get("module_key") == UNGROUPED_MODULE_KEY:
            raise BusinessRuleError("系统未分组模块不能编辑或删除")
        return module

    def _validate(self, payload: ApiModuleSaveRequest, item_id: int | None = None) -> None:
        if not self.repository.get("projects", payload.project_id):
            raise ResourceNotFoundError("所属项目不存在")
        if payload.name in {UNGROUPED_MODULE_KEY, UNGROUPED_MODULE_LABEL}:
            raise BusinessRuleError("该名称为系统保留模块名称")
        page = 1
        while True:
            modules, total = self.repository.list("api_modules", project_id=payload.project_id, page=page, page_size=200)
            if any(row["id"] != item_id and str(row["name"]).strip().casefold() == payload.name.casefold() for row in modules):
                raise BusinessRuleError("当前项目已存在同名模块")
            if page * 200 >= total:
                break
            page += 1
