from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import get_resource_repository
from app.core.response import success
from app.repositories.interfaces import ResourceRepository
from app.schemas.api_flow_scenario import ApiFlowScenarioCreate, ApiFlowScenarioUpdate
from app.services.api_flow_scenario_service import ApiFlowScenarioService

router = APIRouter(prefix="/execution/flows/{flow_id:int}/scenarios", tags=["api-flow-scenarios"])


def get_service(repository: Annotated[ResourceRepository, Depends(get_resource_repository)]) -> ApiFlowScenarioService:
    return ApiFlowScenarioService(repository)


ScenarioService = Annotated[ApiFlowScenarioService, Depends(get_service)]


@router.get("")
def list_scenarios(flow_id: int, service: ScenarioService):
    return success(service.list_for_flow(flow_id))


@router.post("")
def create_scenario(flow_id: int, payload: ApiFlowScenarioCreate, service: ScenarioService):
    return success(service.create_for_flow(flow_id, payload.model_dump()))


@router.put("/{scene_id:int}")
def update_scenario(flow_id: int, scene_id: int, payload: ApiFlowScenarioUpdate, service: ScenarioService):
    return success(service.update_for_flow(flow_id, scene_id, payload.model_dump(exclude_unset=True)))


@router.delete("/{scene_id:int}")
def delete_scenario(flow_id: int, scene_id: int, service: ScenarioService):
    return success(service.delete_for_flow(flow_id, scene_id))


@router.post("/{scene_id:int}/copy")
def copy_scenario(flow_id: int, scene_id: int, service: ScenarioService):
    return success(service.copy_for_flow(flow_id, scene_id))


@router.post("/{scene_id:int}/sync")
def sync_scenario(flow_id: int, scene_id: int, service: ScenarioService):
    return success(service.sync(flow_id, scene_id))
