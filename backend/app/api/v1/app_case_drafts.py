from fastapi import APIRouter, Depends

from app.api.dependencies import get_resource_repository
from app.core.response import page_result, success
from app.repositories.interfaces import ResourceRepository
from app.schemas.cases import CaseDraftBatchCreate, CaseDraftCreate, CaseDraftUpdate, CaseListQuery
from app.schemas.common import BatchDeleteRequest
from app.schemas.testing import GenerateDraftRequest
from app.services.case_draft_service import CaseDraftService
from app.services.test_generation_service import TestGenerationService

router = APIRouter(prefix="/app-testing/case-drafts", tags=["app-case-drafts"])


def get_app_case_draft_service(
    repository: ResourceRepository = Depends(get_resource_repository),
) -> CaseDraftService:
    """Provide APP draft CRUD and review behavior."""

    return CaseDraftService("APP", repository)


def get_app_case_generation_service(
    repository: ResourceRepository = Depends(get_resource_repository),
) -> TestGenerationService:
    """Provide APP draft generation behavior."""

    return TestGenerationService(repository)


@router.post("/generate")
def generate_drafts(
    payload: GenerateDraftRequest,
    service: TestGenerationService = Depends(get_app_case_generation_service),
) -> dict[str, object]:
    return success(
        service.generate_asset_drafts(
            "APP",
            "app_pages",
            "app_elements",
            payload.project_id,
            payload.source_ids,
            payload.strategy,
        )
    )


@router.get("")
def list_app_case_drafts(
    query: CaseListQuery = Depends(),
    service: CaseDraftService = Depends(get_app_case_draft_service),
) -> dict[str, object]:
    items, total = service.list(query.project_id, query.keyword, query.page, query.page_size)
    return page_result(items, total, query.page, query.page_size)


@router.post("")
def create_app_case_draft(
    payload: CaseDraftCreate,
    service: CaseDraftService = Depends(get_app_case_draft_service),
) -> dict[str, object]:
    return success(service.create(payload.model_dump()))


@router.post("/batch-create")
def batch_create_app_case_drafts(
    payload: CaseDraftBatchCreate,
    service: CaseDraftService = Depends(get_app_case_draft_service),
) -> dict[str, object]:
    rows = [item.model_dump() for item in payload.items]
    return success(service.create_many(rows))


@router.post("/accept")
def accept_app_case_drafts(
    payload: BatchDeleteRequest,
    service: CaseDraftService = Depends(get_app_case_draft_service),
) -> dict[str, object]:
    return success(service.accept_many(payload.ids))


@router.post("/batch-delete")
def batch_delete_app_case_drafts(
    payload: BatchDeleteRequest,
    service: CaseDraftService = Depends(get_app_case_draft_service),
) -> dict[str, object]:
    return success(service.batch_delete(payload.ids))


@router.put("/{draft_id:int}")
def update_app_case_draft(
    draft_id: int,
    payload: CaseDraftUpdate,
    service: CaseDraftService = Depends(get_app_case_draft_service),
) -> dict[str, object]:
    return success(service.update(draft_id, payload.model_dump(exclude_unset=True)))


@router.post("/{draft_id:int}/accept")
def accept_app_case_draft(
    draft_id: int,
    service: CaseDraftService = Depends(get_app_case_draft_service),
) -> dict[str, object]:
    return success(service.accept(draft_id))


@router.post("/{draft_id:int}/reject")
def reject_app_case_draft(
    draft_id: int,
    payload: CaseDraftUpdate,
    service: CaseDraftService = Depends(get_app_case_draft_service),
) -> dict[str, object]:
    return success(service.reject(draft_id, payload.review_comment))


@router.delete("/{draft_id:int}")
def delete_app_case_draft(
    draft_id: int,
    service: CaseDraftService = Depends(get_app_case_draft_service),
) -> dict[str, object]:
    return success(service.delete(draft_id))
