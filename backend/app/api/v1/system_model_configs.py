from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.api.dependencies import get_resource_repository
from app.core.response import page_result, success
from app.repositories.interfaces import ResourceRepository
from app.schemas.common import BatchDeleteRequest, ResourceCreate, ResourceUpdate
from app.services.ai_model_service import AiModelResourceService

RepositoryDependency = Annotated[ResourceRepository, Depends(get_resource_repository)]
router = APIRouter(prefix="/system/model-configs", tags=["system-model-configs"])

def get_ai_model_service(repository: RepositoryDependency):
    return AiModelResourceService(repository)

@router.get("")
def list_models(
    service: Annotated[AiModelResourceService, Depends(get_ai_model_service)],
    keyword: str | None = None,
    page: int = 1,
    pageSize: int = 20,
) -> dict[str, Any]:
    items, total = service.list(keyword, None, page, pageSize)
    return page_result(items, total, page, pageSize)


@router.get("/options")
def list_model_options(
    service: Annotated[AiModelResourceService, Depends(get_ai_model_service)],
) -> dict[str, Any]:
    items, _ = service.list(None, None, 1, 1000)
    return success(
        [
            {"id": item["id"], "name": item["name"], "model": item.get("data", {}).get("model")}
            for item in items
            if item.get("status") == "active"
        ]
    )


@router.get("/current")
def get_current_model(
    service: Annotated[AiModelResourceService, Depends(get_ai_model_service)],
) -> dict[str, Any]:
    return success(service.current_model_safe())


@router.post("")
def create_model(
    payload: ResourceCreate,
    service: Annotated[AiModelResourceService, Depends(get_ai_model_service)],
) -> dict[str, Any]:
    return success(service.create(payload.model_dump()))


@router.post("/{item_id:int}/set-current")
def set_current_model(
    item_id: int,
    service: Annotated[AiModelResourceService, Depends(get_ai_model_service)],
) -> dict[str, Any]:
    return success(service.set_current(item_id))


@router.post("/batch-delete")
def batch_delete_models(
    payload: BatchDeleteRequest,
    service: Annotated[AiModelResourceService, Depends(get_ai_model_service)],
) -> dict[str, Any]:
    return success(service.batch_delete(payload.ids))


@router.get("/{item_id:int}")
def get_model(
    item_id: int,
    service: Annotated[AiModelResourceService, Depends(get_ai_model_service)],
) -> dict[str, Any]:
    return success(service.get(item_id))


@router.put("/{item_id:int}")
def update_model(
    item_id: int,
    payload: ResourceUpdate,
    service: Annotated[AiModelResourceService, Depends(get_ai_model_service)],
) -> dict[str, Any]:
    return success(service.update(item_id, payload.model_dump(exclude_unset=True)))


@router.delete("/{item_id:int}")
def delete_model(
    item_id: int,
    service: Annotated[AiModelResourceService, Depends(get_ai_model_service)],
) -> dict[str, Any]:
    return success(service.delete(item_id))
