from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import get_resource_repository
from app.core.response import page_result, success
from app.repositories.interfaces import ResourceRepository
from app.schemas.app_device import DeviceOptionsQuery
from app.schemas.common import (
    BatchDeleteRequest,
    ResourceCreate,
    ResourceListQuery,
    ResourceUpdate,
)
from app.services.app_device_option_service import AppDeviceOptionService
from app.services.resource_service import ResourceService

router = APIRouter(prefix="/app-testing/devices", tags=["app-devices"])


def get_service(repository: Annotated[ResourceRepository, Depends(get_resource_repository)]):
    return ResourceService("app_devices", repository)


def get_options(repository: Annotated[ResourceRepository, Depends(get_resource_repository)]):
    return AppDeviceOptionService(repository)


@router.get("/options")
def options(query: Annotated[DeviceOptionsQuery, Depends()], service: Annotated[AppDeviceOptionService, Depends(get_options)]):
    return success(service.list_options(query))


@router.get("")
def list_devices(query: Annotated[ResourceListQuery, Depends()], service: Annotated[ResourceService, Depends(get_service)]):
    items, total = service.list(query.keyword, query.project_id, query.page, query.page_size, query.data_filters())
    return page_result(items, total, query.page, query.page_size)


@router.post("")
def create(payload: ResourceCreate, service: Annotated[ResourceService, Depends(get_service)]):
    return success(service.create(payload.model_dump()))


@router.post("/batch-delete")
def batch_delete(payload: BatchDeleteRequest, service: Annotated[ResourceService, Depends(get_service)]):
    return success(service.batch_delete(payload.ids))


@router.get("/{item_id:int}")
def get(item_id: int, service: Annotated[ResourceService, Depends(get_service)]):
    return success(service.get(item_id))


@router.put("/{item_id:int}")
def update(item_id: int, payload: ResourceUpdate, service: Annotated[ResourceService, Depends(get_service)]):
    return success(service.update(item_id, payload.model_dump(exclude_unset=True)))


@router.delete("/{item_id:int}")
def delete(item_id: int, service: Annotated[ResourceService, Depends(get_service)]):
    return success(service.delete(item_id))
