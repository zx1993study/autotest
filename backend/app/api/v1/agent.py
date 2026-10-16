from fastapi import APIRouter, Depends, Request

from app.api.dependencies import get_resource_repository
from app.core.response import page_result, success
from app.repositories.interfaces import ResourceRepository
from app.schemas.agent import (
    AgentHeartbeatRequest,
    AgentRegisterRequest,
    AgentTaskAiModelContextRequest,
    AgentTaskAuthContextRequest,
    AgentTaskClaimRequest,
    AgentTaskCreateRequest,
    AgentTaskReportRequest,
    AgentTokenProvisionRequest,
)
from app.schemas.common import PageQuery
from app.services.agent_node_service import AgentNodeService
from app.services.agent_task_service import AgentTaskService

router = APIRouter(prefix="/agent", tags=["agent"])


def get_agent_node_service(
    repository: ResourceRepository = Depends(get_resource_repository),
) -> AgentNodeService:
    """Provide local agent node management behavior."""

    return AgentNodeService(repository)


def get_agent_task_service(
    repository: ResourceRepository = Depends(get_resource_repository),
) -> AgentTaskService:
    """Provide local agent task dispatch behavior."""

    return AgentTaskService(repository)


@router.get("/nodes")
def list_agent_nodes(
    query: PageQuery = Depends(),
    service: AgentNodeService = Depends(get_agent_node_service),
) -> dict[str, object]:
    rows, total = service.list_nodes(query.page, query.page_size)
    return page_result(rows, total, query.page, query.page_size)


@router.post("/nodes/provision-token")
def provision_agent_node_token(
    payload: AgentTokenProvisionRequest,
    service: AgentNodeService = Depends(get_agent_node_service),
) -> dict[str, object]:
    return success(service.provision_token(payload))


@router.get("/nodes/options")
def node_options(service: AgentNodeService = Depends(get_agent_node_service)):
    return success(service.list_options())


@router.post("/nodes/register")
def register_agent_node(
    payload: AgentRegisterRequest,
    service: AgentNodeService = Depends(get_agent_node_service),
) -> dict[str, object]:
    return success(service.register(payload))


@router.post("/runtime/register")
def runtime_register_agent_node(
    request: Request,
    payload: AgentRegisterRequest,
    service: AgentNodeService = Depends(get_agent_node_service),
) -> dict[str, object]:
    service.verify_token(payload.node_key, _agent_bearer_token(request))
    return success(service.register(payload))


@router.post("/nodes/{node_key}/heartbeat")
def heartbeat_agent_node(
    node_key: str,
    payload: AgentHeartbeatRequest,
    service: AgentNodeService = Depends(get_agent_node_service),
) -> dict[str, object]:
    return success(service.heartbeat(node_key, payload))


@router.post("/runtime/nodes/{node_key}/heartbeat")
def runtime_heartbeat_agent_node(
    request: Request,
    node_key: str,
    payload: AgentHeartbeatRequest,
    service: AgentNodeService = Depends(get_agent_node_service),
) -> dict[str, object]:
    service.verify_token(node_key, _agent_bearer_token(request))
    return success(service.heartbeat(node_key, payload))


@router.post("/nodes/{node_id:int}/default-local-headed")
def set_default_local_headed_node(
    node_id: int,
    service: AgentNodeService = Depends(get_agent_node_service),
) -> dict[str, object]:
    return success(service.set_default_local_headed(node_id))


@router.post("/nodes/{node_id:int}/token/reset")
def reset_agent_node_token(
    node_id: int,
    service: AgentNodeService = Depends(get_agent_node_service),
) -> dict[str, object]:
    return success(service.reset_token(node_id))


@router.get("/tasks")
def list_agent_tasks(
    query: PageQuery = Depends(),
    service: AgentTaskService = Depends(get_agent_task_service),
) -> dict[str, object]:
    rows, total = service.list_tasks(query.page, query.page_size)
    return page_result(rows, total, query.page, query.page_size)


@router.get("/tasks/{task_id:int}")
def get_agent_task(task_id: int, service: AgentTaskService = Depends(get_agent_task_service)):
    return success(service.get_task(task_id))


@router.post("/tasks")
def create_agent_task(
    payload: AgentTaskCreateRequest,
    service: AgentTaskService = Depends(get_agent_task_service),
) -> dict[str, object]:
    return success(service.create(payload))


@router.post("/tasks/claim")
def claim_agent_task(
    payload: AgentTaskClaimRequest,
    service: AgentTaskService = Depends(get_agent_task_service),
) -> dict[str, object]:
    return success(service.claim_next(payload.node_key, payload.capabilities))


@router.post("/runtime/tasks/claim")
def runtime_claim_agent_task(
    request: Request,
    payload: AgentTaskClaimRequest,
    node_service: AgentNodeService = Depends(get_agent_node_service),
    task_service: AgentTaskService = Depends(get_agent_task_service),
) -> dict[str, object]:
    node_service.verify_token(payload.node_key, _agent_bearer_token(request))
    return success(task_service.claim_next(payload.node_key, payload.capabilities))


@router.post("/tasks/{task_id:int}/report")
def report_agent_task(
    task_id: int,
    payload: AgentTaskReportRequest,
    service: AgentTaskService = Depends(get_agent_task_service),
) -> dict[str, object]:
    return success(service.report(task_id, payload))


@router.post("/runtime/tasks/{task_id:int}/report")
def runtime_report_agent_task(
    request: Request,
    task_id: int,
    payload: AgentTaskReportRequest,
    node_service: AgentNodeService = Depends(get_agent_node_service),
    task_service: AgentTaskService = Depends(get_agent_task_service),
) -> dict[str, object]:
    node_service.verify_token(payload.node_key, _agent_bearer_token(request))
    return success(task_service.report(task_id, payload))


@router.post("/tasks/{task_id:int}/auth-context")
def consume_agent_task_auth_context(
    task_id: int,
    payload: AgentTaskAuthContextRequest,
    service: AgentTaskService = Depends(get_agent_task_service),
) -> dict[str, object]:
    return success(service.consume_auth_context(task_id, payload.node_key, payload.snapshot_id))


@router.post("/runtime/tasks/{task_id:int}/auth-context")
def runtime_consume_agent_task_auth_context(
    request: Request,
    task_id: int,
    payload: AgentTaskAuthContextRequest,
    node_service: AgentNodeService = Depends(get_agent_node_service),
    task_service: AgentTaskService = Depends(get_agent_task_service),
) -> dict[str, object]:
    node_service.verify_token(payload.node_key, _agent_bearer_token(request))
    return success(task_service.consume_auth_context(task_id, payload.node_key, payload.snapshot_id))


@router.post("/runtime/tasks/{task_id:int}/ai-model-context")
def runtime_consume_agent_task_ai_model_context(
    request: Request,
    task_id: int,
    payload: AgentTaskAiModelContextRequest,
    node_service: AgentNodeService = Depends(get_agent_node_service),
    task_service: AgentTaskService = Depends(get_agent_task_service),
) -> dict[str, object]:
    node_service.verify_token(payload.node_key, _agent_bearer_token(request))
    return success(task_service.consume_ai_model_context(task_id, payload.node_key, payload.snapshot_id))


def _agent_bearer_token(request: Request) -> str:
    """Extract the Agent token without coupling runtime APIs to user JWT."""

    header_value = request.headers.get("Authorization", "")
    prefix = "Bearer "
    if header_value.startswith(prefix):
        return header_value[len(prefix) :].strip()
    return request.headers.get("X-Agent-Token", "").strip()
