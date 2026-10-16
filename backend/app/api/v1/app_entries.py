from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.dependencies import get_resource_repository
from app.core.response import page_result, success
from app.repositories.interfaces import ResourceRepository
from app.schemas.common import BatchDeleteRequest, ResourceCreate, ResourceListQuery, ResourceUpdate
from app.services.resource_option_service import ResourceOptionService
from app.services.resource_service import ResourceService


router = APIRouter(prefix="/app-testing/entries", tags=["app-entries"])


def get_app_entry_service(
    repository: ResourceRepository = Depends(get_resource_repository),
) -> ResourceService:
    return ResourceService("app_entries", repository)


def get_app_entry_option_service(
    repository: ResourceRepository = Depends(get_resource_repository),
) -> ResourceOptionService:
    return ResourceOptionService("app_entries", repository)


@router.get("/options")
def list_app_entry_options(
    project_id: int | None = None,
    service: ResourceOptionService = Depends(get_app_entry_option_service),
) -> dict[str, object]:
    return success(service.list_options(project_id))


@router.get("")
def list_app_entries(
    query: ResourceListQuery = Depends(),
    service: ResourceService = Depends(get_app_entry_service),
) -> dict[str, object]:
    items, total = service.list(query.keyword, query.project_id, query.page, query.page_size, query.data_filters())
    return page_result(items, total, query.page, query.page_size)


@router.post("")
def create_app_entry(
    payload: ResourceCreate,
    service: ResourceService = Depends(get_app_entry_service),
) -> dict[str, object]:
    return success(service.create(payload.model_dump()))


@router.post("/batch-delete")
def batch_delete_app_entries(
    payload: BatchDeleteRequest,
    service: ResourceService = Depends(get_app_entry_service),
) -> dict[str, object]:
    return success(service.batch_delete(payload.ids))


@router.get("/{item_id:int}")
def get_app_entry(
    item_id: int,
    service: ResourceService = Depends(get_app_entry_service),
) -> dict[str, object]:
    return success(service.get(item_id))


@router.put("/{item_id:int}")
def update_app_entry(
    item_id: int,
    payload: ResourceUpdate,
    service: ResourceService = Depends(get_app_entry_service),
) -> dict[str, object]:
    return success(service.update(item_id, payload.model_dump(exclude_unset=True)))


@router.delete("/{item_id:int}")
def delete_app_entry(
    item_id: int,
    service: ResourceService = Depends(get_app_entry_service),
) -> dict[str, object]:
    return success(service.delete(item_id))
