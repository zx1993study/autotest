from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.api.dependencies import get_resource_repository
from app.api.v1.agent import _agent_bearer_token
from app.core.response import success
from app.repositories.interfaces import ResourceRepository
from app.schemas.browser_window import BrowserWindowExchangeRequest
from app.services.agent_node_service import AgentNodeService
from app.services.browser_window_service import BrowserWindowService

RepositoryDependency = Annotated[ResourceRepository, Depends(get_resource_repository)]
router = APIRouter(tags=["browser-windows"])


@router.get("/agent/tasks/{task_id:int}/browser-window")
def get_window(task_id: int, repository: RepositoryDependency):
    return success(BrowserWindowService(repository).get(task_id))


@router.post("/agent/tasks/{task_id:int}/browser-window/show")
def show_window(task_id: int, repository: RepositoryDependency):
    return success(BrowserWindowService(repository).request_show(task_id))


@router.post("/agent/runtime/tasks/{task_id:int}/browser-window")
def exchange(task_id: int, request: Request, payload: BrowserWindowExchangeRequest, repository: RepositoryDependency):
    AgentNodeService(repository).verify_token(payload.node_key, _agent_bearer_token(request))
    return success(BrowserWindowService(repository).exchange(task_id, payload))
