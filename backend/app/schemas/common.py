from pydantic import BaseModel, ConfigDict, Field

from app.core.types import JsonObject
from app.enums.business import ResourceStatusEnum


class PageQuery(BaseModel):
    """Validated pagination and keyword filters."""

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)
    keyword: str | None = Field(default=None, max_length=128)


class ResourceListQuery(BaseModel):
    """Query DTO shared by explicit resource list endpoints."""

    model_config = ConfigDict(populate_by_name=True)

    project_id: int | None = Field(default=None, ge=1)
    keyword: str | None = Field(default=None, max_length=128)
    interface_id: int | None = Field(default=None, ge=1)
    page_id: int | None = Field(default=None, ge=1)
    case_id: int | None = Field(default=None, ge=1)
    case_type: str | None = Field(default=None, max_length=32)
    feature_type: str | None = Field(default=None, max_length=64)
    domain: str | None = Field(default=None, max_length=32)
    kind: str | None = Field(default=None, max_length=64)
    category: str | None = Field(default=None, max_length=64)
    platform: str | None = Field(default=None, max_length=32)
    method: str | None = Field(default=None, max_length=16)
    path: str | None = Field(default=None, max_length=512)
    module: str | None = Field(default=None, max_length=128)
    module_id: int | None = Field(default=None, ge=1)
    status: str | None = Field(default=None, max_length=32)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200, alias="pageSize")

    def data_filters(self) -> dict[str, object]:
        """Return only business data filters supplied by the client."""

        filters: dict[str, object] = {}
        for key in (
            "interface_id",
            "page_id",
            "case_id",
            "case_type",
            "feature_type",
            "domain",
            "kind",
            "category",
            "platform",
            "method",
            "path",
            "module",
            "module_id",
            "status",
        ):
            value = getattr(self, key)
            if value is not None and value != "":
                filters[key] = value
        return filters


class ResourceCreate(BaseModel):
    """Input DTO for creating a generic resource."""

    name: str = Field(min_length=1, max_length=128)
    project_id: int | None = Field(default=None, ge=1)
    description: str | None = Field(default=None, max_length=2000)
    status: ResourceStatusEnum = ResourceStatusEnum.ACTIVE
    data: JsonObject = Field(default_factory=dict)


class ResourceUpdate(BaseModel):
    """Input DTO for partially updating a generic resource."""

    name: str | None = Field(default=None, max_length=128)
    project_id: int | None = Field(default=None, ge=1)
    description: str | None = Field(default=None, max_length=2000)
    data: JsonObject | None = None
    status: ResourceStatusEnum | None = None


class ResourceOut(BaseModel):
    """Output VO for the generic resource contract."""

    id: int
    name: str
    project_id: int | None = None
    description: str | None = None
    status: ResourceStatusEnum
    data: JsonObject
    created_at: str
    updated_at: str


class BatchDeleteRequest(BaseModel):
    """Validated batch deletion request."""

    ids: list[int] = Field(min_length=1, max_length=500)


class ImportPayload(BaseModel):
    """Validated structured import request."""

    project_id: int = Field(ge=1)
    source_type: str = Field(default="json", min_length=1, max_length=32)
    content: JsonObject | list[JsonObject]
    overwrite: bool = True


class ImportUrlPayload(BaseModel):
    """Validated remote OpenAPI import request."""

    project_id: int = Field(ge=1)
    url: str = Field(min_length=1, max_length=2048)
    overwrite: bool = True
