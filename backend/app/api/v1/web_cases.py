from fastapi import APIRouter, Depends

from app.api.dependencies import get_resource_repository
from app.core.response import page_result, success
from app.repositories.interfaces import ResourceRepository
from app.schemas.cases import CaseListQuery, ExecuteRequest, TestCaseCreate
from app.schemas.common import BatchDeleteRequest
from app.schemas.testing import ExecuteCasesRequest
from app.scheduler.jobs.case_execution_jobs import run_case_execution_job
from app.services.project_auth_service import ProjectAuthService
from app.services.test_case_service import TestCaseService

router = APIRouter(prefix="/web-testing/cases", tags=["web-cases"])


def get_web_test_case_service(
    repository: ResourceRepository = Depends(get_resource_repository),
) -> TestCaseService:
    """Provide web test case CRUD behavior."""

    return TestCaseService("WEB", repository)


def get_web_auth_service(
    repository: ResourceRepository = Depends(get_resource_repository),
) -> ProjectAuthService:
    """Provide web login-case option behavior."""

    return ProjectAuthService(repository)


@router.post("/run")
def run_cases(
    payload: ExecuteCasesRequest,
    repository: ResourceRepository = Depends(get_resource_repository),
) -> dict[str, object]:
    return success(run_case_execution_job("WEB", payload.model_dump(), repository))


@router.get("/login-options")
def list_login_case_options(
    project_id: int | None = None,
    service: ProjectAuthService = Depends(get_web_auth_service),
) -> dict[str, object]:
    return success(service.list_web_login_case_options(project_id))


@router.get("")
def list_web_cases(
    query: CaseListQuery = Depends(),
    service: TestCaseService = Depends(get_web_test_case_service),
) -> dict[str, object]:
    items, total = service.list(query.keyword, query.project_id, query.page, query.page_size)
    return page_result(items, total, query.page, query.page_size)


@router.post("")
def create_web_case(
    payload: TestCaseCreate,
    service: TestCaseService = Depends(get_web_test_case_service),
) -> dict[str, object]:
    return success(service.create(payload.model_dump()))


@router.post("/execute")
def execute_web_cases(
    payload: ExecuteRequest,
    repository: ResourceRepository = Depends(get_resource_repository),
) -> dict[str, object]:
    return success(run_case_execution_job("WEB", payload.model_dump(), repository))


@router.post("/batch-delete")
def batch_delete_web_cases(
    payload: BatchDeleteRequest,
    service: TestCaseService = Depends(get_web_test_case_service),
) -> dict[str, object]:
    return success(service.batch_delete(payload.ids))


@router.get("/{case_id:int}")
def get_web_case(
    case_id: int,
    service: TestCaseService = Depends(get_web_test_case_service),
) -> dict[str, object]:
    return success(service.get(case_id))


@router.put("/{case_id:int}")
def update_web_case(
    case_id: int,
    payload: TestCaseCreate,
    service: TestCaseService = Depends(get_web_test_case_service),
) -> dict[str, object]:
    return success(service.update(case_id, payload.model_dump(exclude_unset=True)))


@router.delete("/{case_id:int}")
def delete_web_case(
    case_id: int,
    service: TestCaseService = Depends(get_web_test_case_service),
) -> dict[str, object]:
    return success(service.delete(case_id))
