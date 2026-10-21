from fastapi import APIRouter, Depends

from app.api.dependencies import get_resource_repository
from app.core.response import page_result, success
from app.repositories.interfaces import ResourceRepository
from app.schemas.common import BatchDeleteRequest, ResourceCreate, ResourceUpdate
from app.schemas.testing import (
    AppFeatureListQuery,
    AppFeatureScenarioCreateRequest,
    AppFeatureScenarioListQuery,
    AppFeatureScenarioRecordingRequest,
    AppFeatureScenarioTextGenerateRequest,
    AppFeatureScenarioUpdateRequest,
    AppScenarioInputInfoUpdateRequest,
    AppScenarioRunRequest,
)
from app.services.app_feature_testing_service import AppFeatureTestingService
from app.services.resource_option_service import ResourceOptionService


router = APIRouter(prefix="/app-testing/features", tags=["app-features"])
runs_router = APIRouter(prefix="/app-testing/scenario-runs", tags=["app-scenario-runs"])
scenarios_router = APIRouter(prefix="/app-testing/scenarios", tags=["app-feature-scenarios"])


def get_app_feature_testing_service(
    repository: ResourceRepository = Depends(get_resource_repository),
) -> AppFeatureTestingService:
    return AppFeatureTestingService(repository)


def get_app_feature_option_service(
    repository: ResourceRepository = Depends(get_resource_repository),
) -> ResourceOptionService:
    return ResourceOptionService("app_features", repository)


@router.get("/options")
def list_app_feature_options(
    project_id: int | None = None,
    service: ResourceOptionService = Depends(get_app_feature_option_service),
) -> dict[str, object]:
    return success(service.list_options(project_id))


@router.get("")
def list_app_features(
    query: AppFeatureListQuery = Depends(),
    service: AppFeatureTestingService = Depends(get_app_feature_testing_service),
) -> dict[str, object]:
    items, total = service.list_features(
        project_id=query.project_id,
        device_id=query.device_id,
        keyword=query.keyword,
        status=query.status,
        page=query.page,
        page_size=query.page_size,
    )
    return page_result(items, total, query.page, query.page_size)


@router.post("")
def create_app_feature(
    payload: ResourceCreate,
    service: AppFeatureTestingService = Depends(get_app_feature_testing_service),
) -> dict[str, object]:
    return success(service.create_feature(payload.model_dump()))


@router.post("/batch-delete")
def batch_delete_app_features(
    payload: BatchDeleteRequest,
    service: AppFeatureTestingService = Depends(get_app_feature_testing_service),
) -> dict[str, object]:
    return success(service.batch_delete_features(payload.ids))


@router.get("/{feature_id:int}")
def get_app_feature(
    feature_id: int,
    service: AppFeatureTestingService = Depends(get_app_feature_testing_service),
) -> dict[str, object]:
    return success(service.get_feature(feature_id))


@router.put("/{feature_id:int}")
def update_app_feature(
    feature_id: int,
    payload: ResourceUpdate,
    service: AppFeatureTestingService = Depends(get_app_feature_testing_service),
) -> dict[str, object]:
    return success(service.update_feature(feature_id, payload.model_dump(exclude_unset=True)))


@router.delete("/{feature_id:int}")
def delete_app_feature(
    feature_id: int,
    service: AppFeatureTestingService = Depends(get_app_feature_testing_service),
) -> dict[str, object]:
    return success(service.delete_feature(feature_id))


@router.get("/{feature_id:int}/scenarios")
def list_app_feature_scenarios(
    feature_id: int,
    query: AppFeatureScenarioListQuery = Depends(),
    service: AppFeatureTestingService = Depends(get_app_feature_testing_service),
) -> dict[str, object]:
    items, total = service.list_scenarios(
        feature_id,
        device_id=query.device_id,
        keyword=query.keyword,
        status=query.status,
        source_type=query.source_type,
        page=query.page,
        page_size=query.page_size,
    )
    return page_result(items, total, query.page, query.page_size)


@router.post("/{feature_id:int}/scenarios")
def create_app_feature_scenario(
    feature_id: int,
    payload: AppFeatureScenarioCreateRequest,
    service: AppFeatureTestingService = Depends(get_app_feature_testing_service),
) -> dict[str, object]:
    return success(service.create_scenario(feature_id, payload.model_dump()))


@router.post("/{feature_id:int}/scenarios/generate-from-text")
def generate_app_feature_scenario_from_text(
    feature_id: int,
    payload: AppFeatureScenarioTextGenerateRequest,
    service: AppFeatureTestingService = Depends(get_app_feature_testing_service),
) -> dict[str, object]:
    return success(service.generate_scenario_from_text(feature_id, payload.model_dump()))


@router.post("/{feature_id:int}/scenarios/generate-from-recording")
def generate_app_feature_scenario_from_recording(
    feature_id: int,
    payload: AppFeatureScenarioRecordingRequest,
    service: AppFeatureTestingService = Depends(get_app_feature_testing_service),
) -> dict[str, object]:
    return success(service.generate_scenario_from_recording(feature_id, payload.model_dump()))


@scenarios_router.get("/{scenario_id:int}")
def get_app_feature_scenario(
    scenario_id: int,
    service: AppFeatureTestingService = Depends(get_app_feature_testing_service),
) -> dict[str, object]:
    return success(service.get_scenario(scenario_id))


@scenarios_router.put("/{scenario_id:int}")
def update_app_feature_scenario(
    scenario_id: int,
    payload: AppFeatureScenarioUpdateRequest,
    service: AppFeatureTestingService = Depends(get_app_feature_testing_service),
) -> dict[str, object]:
    return success(service.update_scenario(scenario_id, payload.model_dump(exclude_unset=True)))


@scenarios_router.put("/{scenario_id:int}/input-info")
def update_app_feature_scenario_input_info(
    scenario_id: int,
    payload: AppScenarioInputInfoUpdateRequest,
    service: AppFeatureTestingService = Depends(get_app_feature_testing_service),
) -> dict[str, object]:
    return success(service.update_input_info(scenario_id, payload.input_info))


@scenarios_router.post("/{scenario_id:int}/run")
def run_app_feature_scenario(
    scenario_id: int,
    payload: AppScenarioRunRequest,
    service: AppFeatureTestingService = Depends(get_app_feature_testing_service),
) -> dict[str, object]:
    return success(service.run_scenario(scenario_id, payload.model_dump()))


@scenarios_router.get("/{scenario_id:int}/runs")
def list_app_feature_scenario_runs(
    scenario_id: int,
    page: int = 1,
    pageSize: int = 20,
    service: AppFeatureTestingService = Depends(get_app_feature_testing_service),
) -> dict[str, object]:
    items, total = service.list_runs(scenario_id, page=page, page_size=pageSize)
    return page_result(items, total, page, pageSize)


@runs_router.get("/{run_id:int}")
def get_app_feature_scenario_run(
    run_id: int,
    service: AppFeatureTestingService = Depends(get_app_feature_testing_service),
) -> dict[str, object]:
    return success(service.get_run(run_id))
