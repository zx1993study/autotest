"""Web element resource endpoints."""

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
from app.services.resource_service import ResourceService
from app.services.web_element_service import WebElementService


router = APIRouter(prefix="/web-testing/elements", tags=["web-elements"])


def get_web_element_service(
    repository: ResourceRepository = Depends(get_resource_repository),
) -> WebElementService:
    """Provide the Web element service for this router only."""

    return WebElementService(repository)


@router.get("")
def list_web_elements(
    query: ResourceListQuery = Depends(),
    service: WebElementService = Depends(get_web_element_service),
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
def create_web_element(
    payload: ResourceCreate,
    service: ResourceService = Depends(get_web_element_service),
) -> dict[str, object]:
    return success(service.create(payload.model_dump()))


@router.post("/batch-delete")
def batch_delete_web_elements(
    payload: BatchDeleteRequest,
    service: ResourceService = Depends(get_web_element_service),
) -> dict[str, object]:
    return success(service.batch_delete(payload.ids))


@router.get("/{item_id:int}")
def get_web_element(
    item_id: int,
    service: ResourceService = Depends(get_web_element_service),
) -> dict[str, object]:
    return success(service.get(item_id))


@router.put("/{item_id:int}")
def update_web_element(
    item_id: int,
    payload: ResourceUpdate,
    service: ResourceService = Depends(get_web_element_service),
) -> dict[str, object]:
    return success(service.update(item_id, payload.model_dump(exclude_unset=True)))


@router.delete("/{item_id:int}")
def delete_web_element(
    item_id: int,
    service: ResourceService = Depends(get_web_element_service),
) -> dict[str, object]:
    return success(service.delete(item_id))
