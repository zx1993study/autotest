"""System operation log resource endpoints."""

from fastapi import APIRouter, Depends

from app.api.dependencies import get_resource_repository
from app.core.response import page_result, success
from app.repositories.interfaces import ResourceRepository
from app.schemas.common import (
    BatchDeleteRequest,
    ResourceCreate,
    ResourceListQuery,
    ResourceUpdate,
)
from app.services.resource_service import ResourceService


router = APIRouter(prefix="/system/operation-logs", tags=["system-operation-logs"])


def get_operation_log_service(
    repository: ResourceRepository = Depends(get_resource_repository),
) -> ResourceService:
    """Provide the operation log service for this router only."""

    return ResourceService("system_operation_logs", repository)


@router.get("")
def list_operation_logs(
    query: ResourceListQuery = Depends(),
    service: ResourceService = Depends(get_operation_log_service),
) -> dict[str, object]:
    items, total = service.list(
        query.keyword,
        query.project_id,
        query.page,
        query.page_size,
        query.data_filters(),
    )
    return page_result(items, total, query.page, query.page_size)


@router.post("")
def create_operation_log(
    payload: ResourceCreate,
    service: ResourceService = Depends(get_operation_log_service),
) -> dict[str, object]:
    return success(service.create(payload.model_dump()))


@router.post("/batch-delete")
def batch_delete_operation_logs(
    payload: BatchDeleteRequest,
    service: ResourceService = Depends(get_operation_log_service),
) -> dict[str, object]:
    return success(service.batch_delete(payload.ids))


@router.get("/{item_id:int}")
def get_operation_log(
    item_id: int,
    service: ResourceService = Depends(get_operation_log_service),
) -> dict[str, object]:
    return success(service.get(item_id))


@router.put("/{item_id:int}")
def update_operation_log(
    item_id: int,
    payload: ResourceUpdate,
    service: ResourceService = Depends(get_operation_log_service),
) -> dict[str, object]:
    return success(service.update(item_id, payload.model_dump(exclude_unset=True)))


@router.delete("/{item_id:int}")
def delete_operation_log(
    item_id: int,
    service: ResourceService = Depends(get_operation_log_service),
) -> dict[str, object]:
    return success(service.delete(item_id))
