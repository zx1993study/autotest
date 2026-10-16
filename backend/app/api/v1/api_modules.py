from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_api_module_repository
from app.core.response import success
from app.repositories.interfaces import ApiModuleRepository
from app.schemas.api_module import ApiModuleSaveRequest
from app.services.api_module_service import ApiModuleService

router = APIRouter(prefix="/api-testing/interfaces/modules", tags=["api-modules"])


def get_service(repository: ApiModuleRepository = Depends(get_api_module_repository)) -> ApiModuleService:
    return ApiModuleService(repository)


@router.post("")
def create_module(payload: ApiModuleSaveRequest, service: ApiModuleService = Depends(get_service)):
    return success(service.create(payload))


@router.put("/{module_id:int}")
def update_module(module_id: int, payload: ApiModuleSaveRequest, service: ApiModuleService = Depends(get_service)):
    return success(service.update(module_id, payload))


@router.delete("/{module_id:int}")
def delete_module(module_id: int, project_id: int = Query(ge=1), service: ApiModuleService = Depends(get_service)):
    return success(service.delete(project_id, module_id))
