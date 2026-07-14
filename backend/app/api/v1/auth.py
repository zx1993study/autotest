from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request

from app.api.dependencies import get_resource_repository
from app.core.exceptions import BusinessRuleError
from app.core.response import success
from app.repositories.interfaces import ResourceRepository
from app.schemas.auth import LoginRequest
from app.services.auth_service import AuthService


router = APIRouter(prefix="/auth", tags=["auth"])


def get_auth_service(
    repository: ResourceRepository = Depends(get_resource_repository),
) -> AuthService:
    """Provide authentication behavior without exposing persistence details."""

    return AuthService(repository)


@router.get("/bootstrap")
def auth_bootstrap(service: AuthService = Depends(get_auth_service)) -> dict[str, Any]:
    return success(service.bootstrap_info().model_dump())


@router.post("/login")
def login(payload: LoginRequest, service: AuthService = Depends(get_auth_service)) -> dict[str, Any]:
    return success(service.login(payload.username, payload.password).model_dump())


@router.get("/me")
def current_user(request: Request) -> dict[str, Any]:
    user = getattr(request.state, "current_user", None)
    if user is None:
        raise BusinessRuleError("登录状态已失效，请重新登录")
    return success(user.model_dump())


@router.post("/logout")
def logout() -> dict[str, Any]:
    return success({"logged_out": True})
