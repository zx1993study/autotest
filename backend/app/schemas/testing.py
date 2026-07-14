from pydantic import BaseModel, Field

from app.core.types import JsonObject
from app.enums.business import ExecutionModeEnum


class GenerateDraftRequest(BaseModel):
    """Input DTO for rule-based test draft generation."""

    project_id: int = Field(ge=1)
    source_ids: list[int] = Field(default_factory=list, max_length=500)
    strategy: str = Field(default="basic", min_length=1, max_length=64)


class ScanRequest(BaseModel):
    """Input DTO for UI page or element discovery."""

    project_id: int = Field(ge=1)
    page_id: int | None = Field(default=None, ge=1)
    target_url: str | None = Field(default=None, max_length=2048)
    cookies: str | None = Field(default=None, max_length=100_000)
    feature: str | None = Field(default=None, max_length=128)
    source: JsonObject = Field(default_factory=dict)
    existing_element_strategy: str = Field(default="update", pattern="^(update|skip|replace)$")


class SyncFieldsRequest(BaseModel):
    """Input DTO for synchronizing fields from API definitions."""

    project_id: int = Field(ge=1)
    interface_ids: list[int] = Field(default_factory=list, max_length=500)


class ExecuteCasesRequest(BaseModel):
    """Compatibility DTO used by domain-specific execution endpoints."""

    project_id: int | None = Field(default=None, ge=1)
    env_id: int | None = Field(default=None, ge=1)
    auth_id: int | None = Field(default=None, ge=1)
    mode: ExecutionModeEnum = ExecutionModeEnum.LOCAL_HEADLESS
    node_id: str | None = Field(default=None, max_length=128)
    case_ids: list[int] = Field(default_factory=list, max_length=500)
    config: JsonObject = Field(default_factory=dict)
