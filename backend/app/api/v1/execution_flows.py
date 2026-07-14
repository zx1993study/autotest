"""Execution flow resource endpoints."""

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


router = APIRouter(prefix="/execution/flows", tags=["execution-flows"])


def get_execution_flow_service(
    repository: ResourceRepository = Depends(get_resource_repository),
) -> ResourceService:
    """Provide the execution flow service for this router only."""

    return ResourceService("execution_flows", repository)


@router.get("")
def list_execution_flows(
    query: ResourceListQuery = Depends(),
    service: ResourceService = Depends(get_execution_flow_service),
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
def create_execution_flow(
    payload: ResourceCreate,
    service: ResourceService = Depends(get_execution_flow_service),
) -> dict[str, object]:
    return success(service.create(payload.model_dump()))


@router.post("/batch-delete")
def batch_delete_execution_flows(
    payload: BatchDeleteRequest,
    service: ResourceService = Depends(get_execution_flow_service),
) -> dict[str, object]:
    return success(service.batch_delete(payload.ids))


@router.get("/{item_id:int}")
def get_execution_flow(
    item_id: int,
    service: ResourceService = Depends(get_execution_flow_service),
) -> dict[str, object]:
    return success(service.get(item_id))


@router.put("/{item_id:int}")
def update_execution_flow(
    item_id: int,
    payload: ResourceUpdate,
    service: ResourceService = Depends(get_execution_flow_service),
) -> dict[str, object]:
    return success(service.update(item_id, payload.model_dump(exclude_unset=True)))


@router.delete("/{item_id:int}")
def delete_execution_flow(
    item_id: int,
    service: ResourceService = Depends(get_execution_flow_service),
) -> dict[str, object]:
    return success(service.delete(item_id))
