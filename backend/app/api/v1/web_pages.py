from typing import Any

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
from app.services.ui_testing_service import UiTestingService
from app.services.web_page_service import WebPageResourceService

router = APIRouter(prefix="/web-testing/pages", tags=["web-pages"])
def get_web_page_resource_service(
    repository: ResourceRepository = Depends(get_resource_repository),
) -> WebPageResourceService:
    """Provide web page CRUD and option behavior."""

    return WebPageResourceService(repository)


def get_web_page_scan_service(
    repository: ResourceRepository = Depends(get_resource_repository),
) -> UiTestingService:
    """Provide Web element discovery persistence behavior."""

    return UiTestingService("web_pages", "web_elements", repository)


@router.get("/options")
def list_page_options(
    project_id: int | None = None,
    service: WebPageResourceService = Depends(get_web_page_resource_service),
) -> dict[str, Any]:
    return success(service.list_options(project_id))


@router.post("/scan")
def scan_page(
    payload: ScanRequest,
    service: UiTestingService = Depends(get_web_page_scan_service),
) -> dict[str, object]:
    return success(
        service.scan_elements(
            payload.project_id,
            payload.page_id,
            payload.target_url,
            payload.feature,
            payload.source,
            payload.existing_element_strategy,
        )
    )


@router.get("")
def list_web_pages(
    query: ResourceListQuery = Depends(),
    service: WebPageResourceService = Depends(get_web_page_resource_service),
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
def create_web_page(
    payload: ResourceCreate,
    service: WebPageResourceService = Depends(get_web_page_resource_service),
) -> dict[str, object]:
    return success(service.create(payload.model_dump()))


@router.post("/batch-delete")
def batch_delete_web_pages(
    payload: BatchDeleteRequest,
    service: WebPageResourceService = Depends(get_web_page_resource_service),
) -> dict[str, object]:
    return success(service.batch_delete(payload.ids))


@router.get("/{item_id:int}")
def get_web_page(
    item_id: int,
    service: WebPageResourceService = Depends(get_web_page_resource_service),
) -> dict[str, object]:
    return success(service.get(item_id))


@router.put("/{item_id:int}")
def update_web_page(
    item_id: int,
    payload: ResourceUpdate,
    service: WebPageResourceService = Depends(get_web_page_resource_service),
) -> dict[str, object]:
    return success(service.update(item_id, payload.model_dump(exclude_unset=True)))


@router.delete("/{item_id:int}")
def delete_web_page(
    item_id: int,
    service: WebPageResourceService = Depends(get_web_page_resource_service),
) -> dict[str, object]:
    return success(service.delete(item_id))
