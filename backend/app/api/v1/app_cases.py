from fastapi import APIRouter, Depends

from app.api.dependencies import get_resource_repository
from app.core.response import page_result, success
from app.repositories.interfaces import ResourceRepository
from app.schemas.cases import CaseListQuery, ExecuteRequest, TestCaseCreate
from app.schemas.common import BatchDeleteRequest
from app.schemas.testing import ExecuteCasesRequest
from app.scheduler.jobs.case_execution_jobs import run_case_execution_job
from app.services.test_case_service import TestCaseService

router = APIRouter(prefix="/app-testing/cases", tags=["app-cases"])


def get_app_test_case_service(
    repository: ResourceRepository = Depends(get_resource_repository),
) -> TestCaseService:
    """Provide APP test case CRUD behavior."""

    return TestCaseService("APP", repository)


@router.post("/run")
def run_cases(
    payload: ExecuteCasesRequest,
    repository: ResourceRepository = Depends(get_resource_repository),
) -> dict[str, object]:
    return success(run_case_execution_job("APP", payload.model_dump(), repository))


@router.get("")
def list_app_cases(
    query: CaseListQuery = Depends(),
    service: TestCaseService = Depends(get_app_test_case_service),
) -> dict[str, object]:
    items, total = service.list(query.keyword, query.project_id, query.page, query.page_size)
    return page_result(items, total, query.page, query.page_size)


@router.post("")
def create_app_case(
    payload: TestCaseCreate,
    service: TestCaseService = Depends(get_app_test_case_service),
) -> dict[str, object]:
    return success(service.create(payload.model_dump()))


@router.post("/execute")
def execute_app_cases(
    payload: ExecuteRequest,
    repository: ResourceRepository = Depends(get_resource_repository),
) -> dict[str, object]:
    return success(run_case_execution_job("APP", payload.model_dump(), repository))


@router.post("/batch-delete")
def batch_delete_app_cases(
    payload: BatchDeleteRequest,
    service: TestCaseService = Depends(get_app_test_case_service),
) -> dict[str, object]:
    return success(service.batch_delete(payload.ids))


@router.get("/{case_id:int}")
def get_app_case(
    case_id: int,
    service: TestCaseService = Depends(get_app_test_case_service),
) -> dict[str, object]:
    return success(service.get(case_id))


@router.put("/{case_id:int}")
def update_app_case(
    case_id: int,
    payload: TestCaseCreate,
    service: TestCaseService = Depends(get_app_test_case_service),
) -> dict[str, object]:
    return success(service.update(case_id, payload.model_dump(exclude_unset=True)))


@router.delete("/{case_id:int}")
def delete_app_case(
    case_id: int,
    service: TestCaseService = Depends(get_app_test_case_service),
) -> dict[str, object]:
    return success(service.delete(case_id))
