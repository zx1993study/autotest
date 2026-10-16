from fastapi import APIRouter, Depends, Request

from app.api.dependencies import get_resource_repository
from app.api.v1.agent import _agent_bearer_token
from app.core.response import success
from app.repositories.interfaces import ResourceRepository
from app.schemas.app_exploration import (AppExplorationStart, AppExplorationControl,
    AppExplorationAccept, AppRuntimeState, AppObservation, AppActionReport, AppConnectionReport)
from app.services.app_exploration_service import AppExplorationService
from app.services.app_exploration_control_service import AppExplorationControlService
from app.services.app_exploration_runtime_service import AppExplorationRuntimeService
from app.services.agent_node_service import AgentNodeService
from app.scheduler.jobs.app_exploration_jobs import plan_device_step

router = APIRouter(tags=['app-features'])


@router.post('/app-testing/features/{feature_id:int}/exploration')
def start(feature_id:int,payload:AppExplorationStart,repository:ResourceRepository=Depends(get_resource_repository)):
    return success(AppExplorationService(repository).start(feature_id,payload))


@router.get('/app-testing/features/{feature_id:int}/exploration/active')
def active(feature_id:int,repository:ResourceRepository=Depends(get_resource_repository)):
    return success(AppExplorationService(repository).active(feature_id))


@router.get('/app-testing/features/{feature_id:int}/exploration/{task_id:int}')
def detail(feature_id:int,task_id:int,repository:ResourceRepository=Depends(get_resource_repository)):
    service = AppExplorationService(repository)
    return success(service.public(service.get(task_id,feature_id)))


@router.post('/app-testing/features/{feature_id:int}/exploration/{task_id:int}/control')
def control(feature_id:int,task_id:int,payload:AppExplorationControl,repository:ResourceRepository=Depends(get_resource_repository)):
    return success(AppExplorationControlService(repository).control(task_id,feature_id,payload))


@router.post('/app-testing/features/{feature_id:int}/exploration/{task_id:int}/accept')
def accept(feature_id:int,task_id:int,payload:AppExplorationAccept,repository:ResourceRepository=Depends(get_resource_repository)):
    return success(AppExplorationService(repository).accept(task_id,feature_id,payload))


def runtime(repository,payload,request):
    AgentNodeService(repository).verify_token(payload.node_key,_agent_bearer_token(request))
    return AppExplorationRuntimeService(repository)


@router.post('/agent/runtime/tasks/{task_id:int}/app-state')
def state(task_id:int,request:Request,payload:AppRuntimeState,repository:ResourceRepository=Depends(get_resource_repository)):
    return success(runtime(repository,payload,request).state(task_id,payload))


@router.post('/agent/runtime/tasks/{task_id:int}/app-observation')
def observation(task_id:int,request:Request,payload:AppObservation,repository:ResourceRepository=Depends(get_resource_repository)):
    result = runtime(repository,payload,request).observe(task_id,payload)
    if result['planning']:
        plan_device_step(task_id,result['revision'])
    return success(result)


@router.post('/agent/runtime/tasks/{task_id:int}/app-connection')
def connection(task_id:int,request:Request,payload:AppConnectionReport,repository:ResourceRepository=Depends(get_resource_repository)):
    return success(runtime(repository,payload,request).connection(task_id,payload))


@router.post('/agent/runtime/tasks/{task_id:int}/app-action')
def action(task_id:int,request:Request,payload:AppActionReport,repository:ResourceRepository=Depends(get_resource_repository)):
    return success(runtime(repository,payload,request).action(task_id,payload))
