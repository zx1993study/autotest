from fastapi import APIRouter, Depends

from app.api.dependencies import get_resource_repository
from app.core.response import page_result, success
from app.repositories.interfaces import ResourceRepository
from app.schemas.cases import ApiExecuteRequest, CaseListQuery, TestCaseCreate
from app.schemas.common import BatchDeleteRequest
from app.schemas.testing import ApiExecuteCasesRequest
from app.services.case_execution_dispatcher import CaseExecutionDispatcher
from app.services.test_case_service import TestCaseService

router = APIRouter(prefix="/api-testing/cases", tags=["api-cases"])


def get_api_test_case_service(
    repository: ResourceRepository = Depends(get_resource_repository),
) -> TestCaseService:
    """Provide API test case CRUD behavior."""

    return TestCaseService("API", repository)


@router.post("/run")
def run_cases(
    payload: ApiExecuteCasesRequest,
    repository: ResourceRepository = Depends(get_resource_repository),
) -> dict[str, object]:
    return success(CaseExecutionDispatcher(repository).execute("API", payload.model_dump()))


@router.get("")
def list_api_cases(
    query: CaseListQuery = Depends(),
    service: TestCaseService = Depends(get_api_test_case_service),
) -> dict[str, object]:
    items, total = service.list(
        query.keyword,
        query.project_id,
        query.page,
        query.page_size,
        source_id=query.source_id,
        status=query.status,
        include_latest_execution=query.include_latest_execution,
    )
    return page_result(items, total, query.page, query.page_size)


@router.post("")
def create_api_case(
    payload: TestCaseCreate,
    service: TestCaseService = Depends(get_api_test_case_service),
) -> dict[str, object]:
    return success(service.create(payload.model_dump()))


@router.post("/execute")
def execute_api_cases(
    payload: ApiExecuteRequest,
    repository: ResourceRepository = Depends(get_resource_repository),
) -> dict[str, object]:
    return success(CaseExecutionDispatcher(repository).execute("API", payload.model_dump()))


@router.post("/batch-delete")
def batch_delete_api_cases(
    payload: BatchDeleteRequest,
    service: TestCaseService = Depends(get_api_test_case_service),
) -> dict[str, object]:
    return success(service.batch_delete(payload.ids))


@router.get("/{case_id:int}")
def get_api_case(
    case_id: int,
    service: TestCaseService = Depends(get_api_test_case_service),
) -> dict[str, object]:
    return success(service.get(case_id))


@router.put("/{case_id:int}")
def update_api_case(
    case_id: int,
    payload: TestCaseCreate,
    service: TestCaseService = Depends(get_api_test_case_service),
) -> dict[str, object]:
    return success(service.update(case_id, payload.model_dump(exclude_unset=True)))


@router.delete("/{case_id:int}")
def delete_api_case(
    case_id: int,
    service: TestCaseService = Depends(get_api_test_case_service),
) -> dict[str, object]:
    return success(service.delete(case_id))
