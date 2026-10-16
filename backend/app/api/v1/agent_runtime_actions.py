from fastapi import APIRouter, Depends, Request, Query

from app.api.dependencies import get_resource_repository
from app.api.v1.agent import _agent_bearer_token
from app.core.response import success
from app.repositories.interfaces import ResourceRepository
from app.schemas.agent import AgentTaskRenewRequest, AgentModelCompletionRequest
from app.services.agent_artifact_service import AgentArtifactService
from app.services.agent_node_service import AgentNodeService
from app.services.agent_task_lease_service import AgentTaskLeaseService
from app.services.agent_model_proxy_service import AgentModelProxyService
from app.schemas.web_operation import WebOperationState, WebOperationControl
from app.services.web_operation_service import WebOperationService
from app.services.web_case_secret_service import WebCaseSecretService


router = APIRouter(prefix="/agent/runtime/tasks", tags=["agent-runtime"])


@router.post("/{task_id:int}/renew")
def renew_task(task_id: int, request: Request, payload: AgentTaskRenewRequest, repository: ResourceRepository = Depends(get_resource_repository)):
    AgentNodeService(repository).verify_token(payload.node_key, _agent_bearer_token(request))
    return success(AgentTaskLeaseService(repository).renew(task_id, payload))


@router.post("/{task_id:int}/video")
async def upload_video(task_id: int, request: Request, node_key: str = Query(min_length=3, max_length=128), sha256: str = Query(min_length=64, max_length=64), repository: ResourceRepository = Depends(get_resource_repository)):
    AgentNodeService(repository).verify_token(node_key, _agent_bearer_token(request))
    return success(await AgentArtifactService(repository).save_video(task_id, node_key, sha256, request.stream()))


@router.post("/{task_id:int}/model/v1/chat/completions")
def model_completion(task_id: int, request: Request, payload: AgentModelCompletionRequest, repository: ResourceRepository = Depends(get_resource_repository)):
    service = AgentModelProxyService(repository)
    service.authorize(task_id, _agent_bearer_token(request))
    return service.completion(task_id, payload)


@router.post('/{task_id:int}/web-state')
def web_state(task_id: int, request: Request, payload: WebOperationState, repository: ResourceRepository = Depends(get_resource_repository)):
    AgentNodeService(repository).verify_token(payload.node_key, _agent_bearer_token(request))
    return success(WebOperationService(repository).state(task_id, payload))


controls = APIRouter(prefix='/agent/tasks', tags=['web-operation'])


@router.post('/{task_id:int}/case-inputs')
def case_inputs(task_id: int, request: Request, payload: AgentTaskRenewRequest, repository: ResourceRepository = Depends(get_resource_repository)):
    AgentNodeService(repository).verify_token(payload.node_key, _agent_bearer_token(request))
    from fastapi.responses import JSONResponse
    return JSONResponse(success(WebCaseSecretService(repository).task_inputs(task_id, payload.node_key, payload.lease_token)), headers={'Cache-Control':'no-store'})


@controls.post('/{task_id:int}/web-control')
def web_control(task_id: int, payload: WebOperationControl, repository: ResourceRepository = Depends(get_resource_repository)):
    return success(WebOperationService(repository).control(task_id, payload))
