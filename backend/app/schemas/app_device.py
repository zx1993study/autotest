from typing import Any, Literal

from pydantic import BaseModel, Field


class DeviceOptionsQuery(BaseModel):
    project_id: int | None = Field(default=None, ge=1)
    scope: Literal["project", "pool"] = "project"


class DeviceConnectionCheckRequest(BaseModel):
    id: int = Field(ge=1)


class DeviceBatchConnectionCheckRequest(BaseModel):
    ids: list[int] = Field(default_factory=list, max_length=500)


class DiscoveredDeviceImportRequest(BaseModel):
    project_id: int | None = Field(default=None, ge=1)
    tags: str | None = Field(default=None, max_length=512)
    update_existing: bool = True
    items: list[dict[str, Any]] = Field(min_length=1, max_length=200)
