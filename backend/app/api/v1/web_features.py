from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import get_resource_repository
from app.core.response import success
from app.repositories.interfaces import ResourceRepository
from app.scheduler.jobs.business_generation_jobs import submit_generation_job
from app.schemas.web_features import (
    WebFeatureRepair,
    WebFeatureRun,
    WebFeatureSave,
    WebInputCaseSave,
    WebVersionSelect,
)
from app.services.web_feature_testing_service import WebFeatureTestingService
from app.services.web_recording_service import WebRecordingService
from app.schemas.web_operation import WebRecordingStart, WebRecordingAccept
from app.services.web_script_export_service import WebScriptExportService
from app.schemas.web_execution_summary import WebExecutionSummaryQuery
from app.services.web_execution_summary_service import WebExecutionSummaryService

Repository = Annotated[ResourceRepository, Depends(get_resource_repository)]
router = APIRouter(prefix="/web-testing", tags=["web-functions"])


@router.post('/execution-summaries')
def execution_summaries(payload: WebExecutionSummaryQuery, repository: Repository):
    return success(WebExecutionSummaryService(repository).summarize(payload).model_dump(mode="json"))


@router.post("/page-groups/{group_id:int}/features")
def create_feature(group_id: int, payload: WebFeatureSave, repository: Repository):
    return success(WebFeatureTestingService(repository).save_feature(group_id, payload.model_dump()))


@router.get("/features/{feature_id:int}")
def feature_detail(feature_id: int, repository: Repository):
    return success(WebFeatureTestingService(repository).detail(feature_id))


@router.put("/page-groups/{group_id:int}/features/{feature_id:int}")
def update_feature(group_id: int, feature_id: int, payload: WebFeatureSave, repository: Repository):
    return success(WebFeatureTestingService(repository).save_feature(group_id, payload.model_dump(), feature_id))


@router.delete("/features/{feature_id:int}")
def delete_feature(feature_id: int, repository: Repository):
    return success(WebFeatureTestingService(repository).delete_feature(feature_id))


@router.post("/features/{feature_id:int}/discovery/accept")
def accept_discovery(feature_id: int, repository: Repository):
    return success(WebFeatureTestingService(repository).accept_discovery(feature_id))


@router.post("/features/{feature_id:int}/versions/select")
def select_version(feature_id: int, payload: WebVersionSelect, repository: Repository):
    return success(WebFeatureTestingService(repository).activate_version(feature_id, payload.version_id))


@router.post("/features/{feature_id:int}/input-cases")
def create_case(feature_id: int, payload: WebInputCaseSave, repository: Repository):
    return success(WebFeatureTestingService(repository).save_case(feature_id, payload.model_dump()))


@router.put("/features/{feature_id:int}/input-cases/{case_id:int}")
def update_case(feature_id: int, case_id: int, payload: WebInputCaseSave, repository: Repository):
    return success(WebFeatureTestingService(repository).save_case(feature_id, payload.model_dump(), case_id))


@router.delete("/features/{feature_id:int}/input-cases/{case_id:int}")
def delete_case(feature_id: int, case_id: int, repository: Repository):
    return success(WebFeatureTestingService(repository).delete_case(feature_id, case_id))


@router.post("/features/{feature_id:int}/import-drafts/{draft_id:int}")
def import_draft(feature_id: int, draft_id: int, repository: Repository):
    return success(WebFeatureTestingService(repository).import_draft(feature_id, draft_id))


@router.post("/features/{feature_id:int}/run")
def run(feature_id: int, payload: WebFeatureRun, repository: Repository):
    return success(WebFeatureTestingService(repository).run(feature_id, payload.model_dump()))


@router.post("/features/{feature_id:int}/repair")
def repair(feature_id: int, payload: WebFeatureRepair, repository: Repository):
    queued = WebFeatureTestingService(repository).repair(feature_id, payload.model_dump())
    submit_generation_job(queued["task_id"])
    return success(queued)


@router.post('/features/{feature_id:int}/recording')
def recording(feature_id: int, payload: WebRecordingStart, repository: Repository):
    return success(WebRecordingService(repository).start(feature_id, payload))


@router.post('/features/{feature_id:int}/recording/accept')
def accept_recording(feature_id: int, payload: WebRecordingAccept, repository: Repository):
    return success(WebRecordingService(repository).accept(feature_id, payload))


@router.get('/features/{feature_id:int}/script')
def export_script(feature_id: int, repository: Repository, version_id: int | None = None):
    return success(WebScriptExportService(repository).feature(feature_id, version_id))
