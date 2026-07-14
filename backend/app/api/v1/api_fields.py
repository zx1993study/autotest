"""API field resource and synchronization endpoints."""

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
from app.schemas.testing import SyncFieldsRequest
from app.services.api_testing_service import ApiTestingService
from app.services.resource_service import ResourceService


router = APIRouter(prefix="/api-testing/fields", tags=["api-fields"])


def get_api_field_resource_service(
    repository: ResourceRepository = Depends(get_resource_repository),
) -> ResourceService:
    """Provide API field CRUD behavior."""

    return ResourceService("api_fields", repository)


def get_api_testing_service(
    repository: ResourceRepository = Depends(get_resource_repository),
) -> ApiTestingService:
    """Provide API field synchronization behavior."""

    return ApiTestingService(repository)


@router.post("/sync")
def sync_fields(
    payload: SyncFieldsRequest,
    service: ApiTestingService = Depends(get_api_testing_service),
) -> dict[str, object]:
    return success(service.sync_fields(payload.project_id, payload.interface_ids))


@router.get("")
def list_api_fields(
    query: ResourceListQuery = Depends(),
    service: ResourceService = Depends(get_api_field_resource_service),
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
def create_api_field(
    payload: ResourceCreate,
    service: ResourceService = Depends(get_api_field_resource_service),
) -> dict[str, object]:
    return success(service.create(payload.model_dump()))


@router.post("/batch-delete")
def batch_delete_api_fields(
    payload: BatchDeleteRequest,
    service: ResourceService = Depends(get_api_field_resource_service),
) -> dict[str, object]:
    return success(service.batch_delete(payload.ids))


@router.get("/{item_id:int}")
def get_api_field(
    item_id: int,
    service: ResourceService = Depends(get_api_field_resource_service),
) -> dict[str, object]:
    return success(service.get(item_id))


@router.put("/{item_id:int}")
def update_api_field(
    item_id: int,
    payload: ResourceUpdate,
    service: ResourceService = Depends(get_api_field_resource_service),
) -> dict[str, object]:
    return success(service.update(item_id, payload.model_dump(exclude_unset=True)))


@router.delete("/{item_id:int}")
def delete_api_field(
    item_id: int,
    service: ResourceService = Depends(get_api_field_resource_service),
) -> dict[str, object]:
    return success(service.delete(item_id))
