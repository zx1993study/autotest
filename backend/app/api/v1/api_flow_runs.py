from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import get_resource_repository
from app.core.response import success
from app.repositories.interfaces import ResourceRepository
from app.schemas.api_flow_run import ApiFlowRunRequest
from app.services.api_flow_run_service import ApiFlowRunService

router = APIRouter(prefix="/execution/flows/{flow_id:int}/runs", tags=["api-flow-runs"])


def get_service(repository: Annotated[ResourceRepository, Depends(get_resource_repository)]) -> ApiFlowRunService:
    return ApiFlowRunService(repository)


RunService = Annotated[ApiFlowRunService, Depends(get_service)]


@router.get("")
def list_runs(flow_id: int, service: RunService):
    return success(service.list_for_flow(flow_id))


@router.post("")
def create_run(flow_id: int, payload: ApiFlowRunRequest, service: RunService):
    return success(service.create_batch(flow_id, payload.model_dump()))


@router.get("/{batch_id:int}")
def get_run(flow_id: int, batch_id: int, service: RunService):
    return success(service.get_for_flow(flow_id, batch_id))


@router.post("/{batch_id:int}/cancel")
def cancel_run(flow_id: int, batch_id: int, service: RunService):
    return success(service.cancel(flow_id, batch_id))
