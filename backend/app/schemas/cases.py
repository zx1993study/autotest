from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.types import JsonObject, JsonValue
from app.enums.business import (
    CaseDraftStatusEnum,
    CaseTypeEnum,
    ExecutionModeEnum,
    ResourceStatusEnum,
)


class CaseListQuery(BaseModel):
    """Validated list query for drafts and formal test cases."""

    model_config = ConfigDict(populate_by_name=True)

    project_id: int | None = Field(default=None, ge=1)
    source_id: int | None = Field(default=None, ge=1)
    keyword: str | None = Field(default=None, max_length=128)
    status: CaseDraftStatusEnum | ResourceStatusEnum | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200, alias="pageSize")
    include_latest_execution: bool = False


class CaseExecutionSummary(BaseModel):
    """Small read-only summary of a formal case's latest execution."""

    record_id: int
    status: Literal["success", "failed", "exception", "queued", "running", "cancelled", "skipped"]
    response_code: JsonValue = None
    http_status: int | None = None
    executed_at: str | None = None
    error: str | None = None


class CaseDraftCreate(BaseModel):
    """Input DTO for a generated case draft."""

    project_id: int = Field(default=1, ge=1)
    case_type: CaseTypeEnum | None = None
    name: str = Field(min_length=1, max_length=128)
    source_id: int | None = Field(default=None, ge=1)
    description: str | None = Field(default=None, max_length=2000)
    status: CaseDraftStatusEnum = CaseDraftStatusEnum.DRAFT
    case_json: JsonObject = Field(default_factory=dict)
    data: JsonObject = Field(default_factory=dict)
    assertions: list[JsonObject] = Field(default_factory=list)
    strategy_ids: list[int] = Field(default_factory=list)


class CaseDraftBatchCreate(BaseModel):
    """Validated bounded batch of case drafts."""

    items: list[CaseDraftCreate] = Field(min_length=1, max_length=500)


class CaseDraftUpdate(BaseModel):
    """Input DTO for draft review and editing."""

    name: str | None = Field(default=None, max_length=128)
    project_id: int | None = Field(default=None, ge=1)
    description: str | None = Field(default=None, max_length=2000)
    case_json: JsonObject | None = None
    data: JsonObject | None = None
    assertions: list[JsonObject] | None = None
    strategy_ids: list[int] | None = None
    status: CaseDraftStatusEnum | None = None
    review_comment: str | None = Field(default=None, max_length=2000)


class TestCaseCreate(BaseModel):
    """Input DTO for an executable formal test case."""

    project_id: int = Field(default=1, ge=1)
    case_type: CaseTypeEnum | None = None
    name: str = Field(min_length=1, max_length=128)
    source_id: int | None = Field(default=None, ge=1)
    description: str | None = Field(default=None, max_length=2000)
    status: ResourceStatusEnum = ResourceStatusEnum.ACTIVE
    data: JsonObject = Field(default_factory=dict)
    steps: list[JsonObject] = Field(default_factory=list)
    assertions: list[JsonObject] = Field(default_factory=list)
    strategy_ids: list[int] = Field(default_factory=list)


class ExecuteRequest(BaseModel):
    """Input DTO for executing one or more formal test cases."""

    env_id: int | None = Field(default=None, ge=1)
    auth_id: int | None = Field(default=None, ge=1)
    mode: ExecutionModeEnum = ExecutionModeEnum.SERVER_HEADLESS
    node_id: str | None = Field(default=None, max_length=128)
    case_ids: list[int] = Field(default_factory=list, max_length=500)


class ApiCaseExecutionConfig(BaseModel):
    """Bounded API execution settings, retaining runtime request overrides."""

    model_config = ConfigDict(extra="allow")

    concurrency: int = Field(default=5, ge=1, le=10)
    timeout: int = Field(default=15, ge=1, le=300)


class ApiExecuteRequest(ExecuteRequest):
    config: ApiCaseExecutionConfig = Field(default_factory=ApiCaseExecutionConfig)
