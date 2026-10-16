"""Schemas for system user management endpoints."""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.enums.business import ResourceStatusEnum


class SystemUserListQuery(BaseModel):
    """Validated query DTO for listing platform users."""

    model_config = ConfigDict(populate_by_name=True)

    keyword: str | None = Field(default=None, max_length=128)
    status: ResourceStatusEnum | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200, alias="pageSize")


class SystemUserCreate(BaseModel):
    """Input DTO for creating a user with a one-time plaintext password."""

    username: str = Field(min_length=3, max_length=64, pattern=r"^[A-Za-z0-9_.@-]+$")
    real_name: str = Field(min_length=1, max_length=64)
    phone: str | None = Field(default=None, max_length=32)
    password: str = Field(min_length=6, max_length=128)
    status: ResourceStatusEnum = ResourceStatusEnum.ACTIVE

    @field_validator("username", "real_name", "phone", "password", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        """Normalize surrounding whitespace before business validation."""

        return value.strip() if isinstance(value, str) else value


class SystemUserUpdate(BaseModel):
    """Input DTO for editing user profile data without touching passwords."""

    username: str | None = Field(default=None, min_length=3, max_length=64, pattern=r"^[A-Za-z0-9_.@-]+$")
    real_name: str | None = Field(default=None, min_length=1, max_length=64)
    phone: str | None = Field(default=None, max_length=32)
    status: ResourceStatusEnum | None = None

    @field_validator("username", "real_name", "phone", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        """Normalize optional text fields while preserving omitted fields."""

        return value.strip() if isinstance(value, str) else value


class SystemUserResetPassword(BaseModel):
    """Input DTO for resetting a user's login password."""

    password: str = Field(min_length=6, max_length=128)


class SystemUserOut(BaseModel):
    """Output VO that intentionally hides password hashes."""

    id: int
    username: str
    real_name: str
    phone: str | None = None
    status: ResourceStatusEnum
    roles: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    password_info: str
    created_at: str
    updated_at: str
    last_login_at: int | None = None
