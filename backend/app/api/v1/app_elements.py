"""App element resource endpoints."""

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


router = APIRouter(prefix="/app-testing/elements", tags=["app-elements"])


def get_app_element_service(
    repository: ResourceRepository = Depends(get_resource_repository),
) -> ResourceService:
    """Provide the App element service for this router only."""

    return ResourceService("app_elements", repository)


@router.get("")
def list_app_elements(
    query: ResourceListQuery = Depends(),
    service: ResourceService = Depends(get_app_element_service),
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
def create_app_element(
    payload: ResourceCreate,
    service: ResourceService = Depends(get_app_element_service),
) -> dict[str, object]:
    return success(service.create(payload.model_dump()))


@router.post("/batch-delete")
def batch_delete_app_elements(
    payload: BatchDeleteRequest,
    service: ResourceService = Depends(get_app_element_service),
) -> dict[str, object]:
    return success(service.batch_delete(payload.ids))


@router.get("/{item_id:int}")
def get_app_element(
    item_id: int,
    service: ResourceService = Depends(get_app_element_service),
) -> dict[str, object]:
    return success(service.get(item_id))


@router.put("/{item_id:int}")
def update_app_element(
    item_id: int,
    payload: ResourceUpdate,
    service: ResourceService = Depends(get_app_element_service),
) -> dict[str, object]:
    return success(service.update(item_id, payload.model_dump(exclude_unset=True)))


@router.delete("/{item_id:int}")
def delete_app_element(
    item_id: int,
    service: ResourceService = Depends(get_app_element_service),
) -> dict[str, object]:
    return success(service.delete(item_id))
