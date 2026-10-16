from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from app.api.dependencies import get_resource_repository
from app.api.v1.agent import _agent_bearer_token
from app.core.response import success
from app.repositories.interfaces import ResourceRepository
from app.scheduler.jobs.web_vision_jobs import submit_vision_step
from app.schemas.agent import AgentTaskRenewRequest
from app.schemas.web_vision_agent import (
    VisionLoginRequest,
    VisionModelCheckRequest,
    VisionStepRequest,
)
from app.services.agent_node_service import AgentNodeService
from app.services.vision_model_check_service import VisionModelCheckService
from app.services.web_vision_agent_service import WebVisionAgentService
from app.services.web_vision_control_service import WebVisionControlService
from app.services.web_vision_step_service import WebVisionStepService

router = APIRouter(tags=["web-vision-discovery"])
RepositoryDependency = Annotated[ResourceRepository, Depends(get_resource_repository)]


@router.get("/web-testing/vision-discovery/active")
def active(repository: RepositoryDependency, project_id: int = Query(gt=0), page_id: int = Query(gt=0)):
    return success(WebVisionAgentService(repository).active(project_id, page_id))


@router.post("/web-testing/vision-discovery/model-check")
def model_check(payload: VisionModelCheckRequest, repository: RepositoryDependency):
    return success(VisionModelCheckService(repository).check(payload.model_id))


@router.post("/web-testing/vision-discovery/tasks/{task_id:int}/login")
def login_action(task_id: int, payload: VisionLoginRequest, repository: RepositoryDependency):
    return success(WebVisionAgentService(repository).interact(task_id, payload.action))


@router.post("/web-testing/vision-discovery/{task_id:int}/cancel")
def cancel(task_id: int, repository: RepositoryDependency):
    return success(WebVisionControlService(repository).cancel(task_id))


@router.post("/agent/runtime/tasks/{task_id:int}/vision/state")
def state(task_id: int, request: Request, payload: AgentTaskRenewRequest, repository: RepositoryDependency):
    AgentNodeService(repository).verify_token(payload.node_key, _agent_bearer_token(request))
    return success(WebVisionAgentService(repository).state(task_id, payload))


@router.post("/agent/runtime/tasks/{task_id:int}/vision/step")
def step(task_id: int, request: Request, payload: VisionStepRequest, repository: RepositoryDependency):
    AgentNodeService(repository).verify_token(payload.node_key, _agent_bearer_token(request))
    result, job_id = WebVisionStepService(repository).begin(task_id, payload)
    if job_id:
        submit_vision_step(task_id, payload, job_id)
    return success(result)


@router.post("/agent/runtime/tasks/{task_id:int}/vision/cancel")
def cancel_owned(task_id: int, request: Request, payload: AgentTaskRenewRequest, repository: RepositoryDependency):
    AgentNodeService(repository).verify_token(payload.node_key, _agent_bearer_token(request))
    return success(WebVisionAgentService(repository).cancel_owned(task_id, payload))
