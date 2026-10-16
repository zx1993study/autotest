from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.api.dependencies import get_resource_repository
from app.api.v1.agent import _agent_bearer_token
from app.core.response import page_result, success
from app.repositories.interfaces import ResourceRepository
from app.scheduler.jobs.business_generation_jobs import submit_generation_job
from app.schemas.business_generation import (
    CandidateRequest,
    GenerationControlRequest,
    ReplayRequest,
    ReplayStateRequest,
)
from app.services.agent_node_service import AgentNodeService
from app.services.business_generation_service import BusinessGenerationService
from app.services.generation_repair_service import GenerationRepairService
from app.services.generation_script_service import GenerationScriptService
from app.services.generation_task_query_service import GenerationTaskQueryService
from app.services.web_replay_service import WebReplayService

RepositoryDependency = Annotated[ResourceRepository, Depends(get_resource_repository)]
router = APIRouter(tags=["generation-records"])
PATH = "/execution/generation-tasks"


@router.get(PATH)
def list_tasks(repository: RepositoryDependency, project_id: int | None = None, page: int = 1, pageSize: int = 20):
    page, pageSize = max(1, page), min(100, max(1, pageSize))
    rows, total = GenerationTaskQueryService(repository).list(project_id, page, pageSize)
    return page_result(rows, total, page, pageSize)


@router.get(PATH + "/{task_id:int}")
def get_task(task_id: int, repository: RepositoryDependency):
    return success(GenerationTaskQueryService(repository).get(task_id))


@router.post(PATH + "/{task_id:int}/accept")
def accept(task_id: int, payload: CandidateRequest, repository: RepositoryDependency):
    return success(BusinessGenerationService(repository).accept(task_id, payload.candidate))


@router.post(PATH + "/{task_id:int}/verify")
def verify(task_id: int, payload: ReplayRequest, repository: RepositoryDependency):
    return success(WebReplayService(repository).queue(task_id, payload))


@router.post(PATH + "/{task_id:int}/control")
def control(task_id: int, payload: GenerationControlRequest, repository: RepositoryDependency):
    WebReplayService(repository).control(task_id, payload.action)
    return success({"accepted": True})


@router.get(PATH + "/{task_id:int}/script")
def script(task_id: int, repository: RepositoryDependency):
    return success(GenerationScriptService(repository).export(task_id))


@router.post(PATH + "/{task_id:int}/repair")
def repair(task_id: int, repository: RepositoryDependency):
    queued = GenerationRepairService(repository).submit(task_id)
    submit_generation_job(queued["task_id"])
    return success(queued)


@router.post("/agent/runtime/tasks/{task_id:int}/replay/state")
def replay_state(task_id: int, request: Request, payload: ReplayStateRequest, repository: RepositoryDependency):
    AgentNodeService(repository).verify_token(payload.node_key, _agent_bearer_token(request))
    return success(WebReplayService(repository).state(task_id, payload))
