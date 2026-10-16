"""Execution flow resource endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import get_resource_repository
from app.core.response import page_result, success
from app.repositories.interfaces import ResourceRepository
from app.schemas.common import (
    BatchDeleteRequest,
    ResourceListQuery,
)
from app.schemas.execution_flow import ExecutionFlowCreate, ExecutionFlowUpdate
from app.services.execution_flow_service import ExecutionFlowService

router = APIRouter(prefix="/execution/flows", tags=["execution-flows"])


def get_execution_flow_service(
    repository: Annotated[ResourceRepository, Depends(get_resource_repository)],
) -> ExecutionFlowService:
    """Provide the execution flow service for this router only."""

    return ExecutionFlowService(repository)


FlowService = Annotated[ExecutionFlowService, Depends(get_execution_flow_service)]


@router.get("")
def list_execution_flows(
    query: Annotated[ResourceListQuery, Depends()],
    service: FlowService,
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
    payload: ExecutionFlowCreate,
    service: FlowService,
) -> dict[str, object]:
    return success(service.create(payload.model_dump()))


@router.post("/batch-delete")
def batch_delete_execution_flows(
    payload: BatchDeleteRequest,
    service: FlowService,
) -> dict[str, object]:
    return success(service.batch_delete(payload.ids))


@router.get("/{item_id:int}")
def get_execution_flow(
    item_id: int,
    service: FlowService,
) -> dict[str, object]:
    return success(service.get(item_id))


@router.put("/{item_id:int}")
def update_execution_flow(
    item_id: int,
    payload: ExecutionFlowUpdate,
    service: FlowService,
) -> dict[str, object]:
    return success(service.update(item_id, payload.model_dump(exclude_unset=True)))


@router.delete("/{item_id:int}")
def delete_execution_flow(
    item_id: int,
    service: FlowService,
) -> dict[str, object]:
    return success(service.delete(item_id))


@router.post("/{item_id:int}/copy")
def copy_execution_flow(item_id: int, service: FlowService):
    return success(service.copy(item_id))
