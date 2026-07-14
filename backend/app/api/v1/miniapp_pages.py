from fastapi import APIRouter, Depends

from app.api.dependencies import get_resource_repository
from app.core.response import page_result, success
from app.repositories.interfaces import ResourceRepository
from app.schemas.common import (
    BatchDeleteRequest,
    ResourceCreate,
    ResourceListQuery,
    ResourceUpdate,
)
from app.schemas.testing import ScanRequest
from app.services.resource_service import ResourceService
from app.services.ui_testing_service import UiTestingService

router = APIRouter(prefix="/miniapp-testing/pages", tags=["miniapp-pages"])


def get_miniapp_page_resource_service(
    repository: ResourceRepository = Depends(get_resource_repository),
) -> ResourceService:
    """Provide MiniApp page CRUD behavior without exposing persistence details."""

    return ResourceService("miniapp_pages", repository)


def get_miniapp_page_scan_service(
    repository: ResourceRepository = Depends(get_resource_repository),
) -> UiTestingService:
    """Provide MiniApp page scan behavior through the UI testing domain service."""

    return UiTestingService("miniapp_pages", "miniapp_elements", repository)


@router.post("/scan")
def scan_page(
    payload: ScanRequest,
    service: UiTestingService = Depends(get_miniapp_page_scan_service),
) -> dict[str, object]:
    return success(
        service.scan_elements(
            payload.project_id,
            payload.page_id,
            payload.target_url,
            payload.feature,
            payload.source,
        )
    )


@router.get("")
def list_miniapp_pages(
    query: ResourceListQuery = Depends(),
    service: ResourceService = Depends(get_miniapp_page_resource_service),
) -> dict[str, object]:
    items, total = service.list(
        query.keyword,
        query.project_id,
        query.page,
        query.page_size,
        query.data_filters(),
    )
    return page_result(items, total, query.page, query.page_size)


@router.post("")
def create_miniapp_page(
    payload: ResourceCreate,
    service: ResourceService = Depends(get_miniapp_page_resource_service),
) -> dict[str, object]:
    return success(service.create(payload.model_dump()))


@router.post("/batch-delete")
def batch_delete_miniapp_pages(
    payload: BatchDeleteRequest,
    service: ResourceService = Depends(get_miniapp_page_resource_service),
) -> dict[str, object]:
    return success(service.batch_delete(payload.ids))


@router.get("/{item_id:int}")
def get_miniapp_page(
    item_id: int,
    service: ResourceService = Depends(get_miniapp_page_resource_service),
) -> dict[str, object]:
    return success(service.get(item_id))


@router.put("/{item_id:int}")
def update_miniapp_page(
    item_id: int,
    payload: ResourceUpdate,
    service: ResourceService = Depends(get_miniapp_page_resource_service),
) -> dict[str, object]:
    return success(service.update(item_id, payload.model_dump(exclude_unset=True)))


@router.delete("/{item_id:int}")
def delete_miniapp_page(
    item_id: int,
    service: ResourceService = Depends(get_miniapp_page_resource_service),
) -> dict[str, object]:
    return success(service.delete(item_id))
