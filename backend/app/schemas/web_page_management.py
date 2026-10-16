from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.enums.business import ResourceStatusEnum


class WebPageGroupListQuery(BaseModel):
    """Filters for the page-level Web asset directory."""

    model_config = ConfigDict(populate_by_name=True)

    project_id: int = Field(ge=1)
    keyword: str | None = Field(default=None, max_length=256)
    status: str | None = Field(default=None, max_length=32)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200, alias="pageSize")


class WebPageGroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    project_id: int = Field(ge=1)
    route: str | None = Field(default=None, max_length=2048)
    url: str | None = Field(default=None, max_length=2048)
    auth_id: int | None = Field(default=None, ge=1)
    description: str | None = Field(default=None, max_length=2000)
    status: ResourceStatusEnum = ResourceStatusEnum.ACTIVE


class WebPageGroupUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    route: str | None = Field(default=None, max_length=2048)
    url: str | None = Field(default=None, max_length=2048)
    auth_id: int | None = Field(default=None, ge=1)
    description: str | None = Field(default=None, max_length=2000)
    status: ResourceStatusEnum | None = None


class WebPageFeatureListQuery(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    keyword: str | None = Field(default=None, max_length=128)
    status: str | None = Field(default=None, max_length=32)
    feature_type: str | None = Field(default=None, max_length=64)
    script_status: str | None = Field(default=None, max_length=32)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200, alias="pageSize")


class WebPageInterfaceListQuery(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    feature_id: int | None = Field(default=None, ge=1)
    keyword: str | None = Field(default=None, max_length=256)
    method: str | None = Field(default=None, max_length=16)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200, alias="pageSize")


class WebPageApiRelationCreate(BaseModel):
    interface_ids: list[int] = Field(min_length=1, max_length=500)
    feature_id: int | None = Field(default=None, ge=1)
    source: str = Field(default="manual", pattern="^(manual|network|ai)$")

