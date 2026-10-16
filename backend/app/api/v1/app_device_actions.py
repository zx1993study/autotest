from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_resource_repository
from app.core.response import success
from app.repositories.interfaces import ResourceRepository
from app.schemas.app_device import (
    DeviceBatchConnectionCheckRequest,
    DeviceConnectionCheckRequest,
    DiscoveredDeviceImportRequest,
)
from app.services.agent_device_discovery_service import AgentDeviceDiscoveryService
from app.services.app_device_import_service import AppDeviceImportService

router = APIRouter(prefix="/app-testing/devices", tags=["app-devices"])


def get_discovery(repository: Annotated[ResourceRepository, Depends(get_resource_repository)]):
    return AgentDeviceDiscoveryService(repository)


def get_import(repository: Annotated[ResourceRepository, Depends(get_resource_repository)]):
    return AppDeviceImportService(repository)


@router.get("/discover")
def discover(service: Annotated[AgentDeviceDiscoveryService, Depends(get_discovery)], node_id: str | None = None):
    return success(service.queue(node_id))


@router.get("/wda/discover")
def discover_wda(service: Annotated[AgentDeviceDiscoveryService, Depends(get_discovery)], subnet: str | None = None, port: Annotated[list[int] | None, Query()] = None, node_id: str | None = None):
    return success(service.queue(node_id, subnet, port))


@router.post("/import-discovered")
def import_devices(payload: DiscoveredDeviceImportRequest, service: Annotated[AppDeviceImportService, Depends(get_import)]):
    return success(service.import_discovered(payload))


@router.post("/check")
@router.post("/wda/check")
def check(payload: DeviceConnectionCheckRequest, service: Annotated[AgentDeviceDiscoveryService, Depends(get_discovery)]):
    return success(service.queue_check([payload.id]))


@router.post("/batch-check")
def batch_check(payload: DeviceBatchConnectionCheckRequest, service: Annotated[AgentDeviceDiscoveryService, Depends(get_discovery)]):
    return success(service.queue_check(payload.ids))


@router.post("/{item_id:int}/refresh")
def refresh(item_id: int, service: Annotated[AgentDeviceDiscoveryService, Depends(get_discovery)]):
    return success(service.queue_check([item_id]))
