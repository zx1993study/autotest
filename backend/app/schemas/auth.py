from __future__ import annotations

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Input DTO for platform user login."""

    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=6, max_length=128)


class UserProfile(BaseModel):
    """Safe current-user profile returned to the frontend."""

    id: int
    username: str
    display_name: str
    roles: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)


class LoginResponse(BaseModel):
    """Login result containing the bearer token and user profile."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserProfile


class BootstrapAuthInfo(BaseModel):
    """Public bootstrap data used by the login page."""

    default_username: str
    password_policy: str
