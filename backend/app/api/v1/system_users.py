"""System user management endpoints."""

from fastapi import APIRouter, Depends

from app.api.dependencies import get_resource_repository
from app.core.response import page_result, success
from app.repositories.interfaces import ResourceRepository
from app.schemas.common import BatchDeleteRequest
from app.schemas.system_users import (
    SystemUserCreate,
    SystemUserListQuery,
    SystemUserResetPassword,
    SystemUserUpdate,
)
from app.services.system_user_service import SystemUserService


router = APIRouter(prefix="/system/users", tags=["system-users"])


def get_system_user_service(
    repository: ResourceRepository = Depends(get_resource_repository),
) -> SystemUserService:
    """Provide user management behavior without exposing persistence details."""

    return SystemUserService(repository)


@router.get("")
def list_users(
    query: SystemUserListQuery = Depends(),
    service: SystemUserService = Depends(get_system_user_service),
) -> dict[str, object]:
    items, total = service.list(
        keyword=query.keyword,
        status=query.status,
        page=query.page,
        page_size=query.page_size,
    )
    return page_result([item.model_dump(mode="json") for item in items], total, query.page, query.page_size)


@router.post("")
def create_user(
    payload: SystemUserCreate,
    service: SystemUserService = Depends(get_system_user_service),
) -> dict[str, object]:
    return success(service.create(payload).model_dump(mode="json"))


@router.post("/batch-delete")
def batch_delete_users(
    payload: BatchDeleteRequest,
    service: SystemUserService = Depends(get_system_user_service),
) -> dict[str, object]:
    return success(service.batch_delete(payload.ids))


@router.get("/{user_id:int}")
def get_user(
    user_id: int,
    service: SystemUserService = Depends(get_system_user_service),
) -> dict[str, object]:
    return success(service.get(user_id).model_dump(mode="json"))


@router.put("/{user_id:int}")
def update_user(
    user_id: int,
    payload: SystemUserUpdate,
    service: SystemUserService = Depends(get_system_user_service),
) -> dict[str, object]:
    return success(service.update(user_id, payload).model_dump(mode="json"))


@router.post("/{user_id:int}/reset-password")
def reset_user_password(
    user_id: int,
    payload: SystemUserResetPassword,
    service: SystemUserService = Depends(get_system_user_service),
) -> dict[str, object]:
    return success(service.reset_password(user_id, payload.password).model_dump(mode="json"))


@router.delete("/{user_id:int}")
def delete_user(
    user_id: int,
    service: SystemUserService = Depends(get_system_user_service),
) -> dict[str, object]:
    return success(service.delete(user_id))
