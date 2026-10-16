from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.types import JsonObject
from app.enums.business import ExecutionModeEnum, ExecutionPlanStatusEnum, ExecutionPlanTestTypeEnum


class ExecutionPlanListQuery(BaseModel):
    """Validated filters for execution plan list pages."""

    model_config = ConfigDict(populate_by_name=True)

    keyword: str | None = Field(default=None, max_length=128)
    project_id: int | None = Field(default=None, ge=1)
    test_type: ExecutionPlanTestTypeEnum | None = None
    status: ExecutionPlanStatusEnum | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200, alias="pageSize")


class ExecutionPlanCreate(BaseModel):
    """Input DTO for creating an execution plan."""

    name: str = Field(min_length=1, max_length=128)
    project_id: int | None = Field(default=None, ge=1)
    test_rounds: int = Field(default=1, ge=1, le=10000)
    test_type: ExecutionPlanTestTypeEnum | None = None
    api_ids: list[int] = Field(default_factory=list, max_length=500)
    web_feature_ids: list[int] = Field(default_factory=list, max_length=500)
    description: str | None = Field(default=None, max_length=2000)
    status: ExecutionPlanStatusEnum = ExecutionPlanStatusEnum.ACTIVE

    @field_validator("name", "description", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        """Trim user-entered text before business validation."""

        return value.strip() if isinstance(value, str) else value

    @field_validator("api_ids", "web_feature_ids")
    @classmethod
    def normalize_source_ids(cls, value: list[int]) -> list[int]:
        """Deduplicate source selections while retaining the user's order."""

        return list(dict.fromkeys(value))


class ExecutionPlanUpdate(BaseModel):
    """Input DTO for editing an execution plan."""

    name: str | None = Field(default=None, min_length=1, max_length=128)
    project_id: int | None = Field(default=None, ge=1)
    test_rounds: int | None = Field(default=None, ge=1, le=10000)
    test_type: ExecutionPlanTestTypeEnum | None = None
    api_ids: list[int] | None = Field(default=None, max_length=500)
    web_feature_ids: list[int] | None = Field(default=None, max_length=500)
    description: str | None = Field(default=None, max_length=2000)

    @field_validator("name", "description", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        """Trim optional text while preserving omitted fields."""

        return value.strip() if isinstance(value, str) else value

    @field_validator("api_ids", "web_feature_ids")
    @classmethod
    def normalize_source_ids(cls, value: list[int] | None) -> list[int] | None:
        """Normalize optional source selections before service validation."""

        return list(dict.fromkeys(value)) if value is not None else None


class ExecutionPlanOut(BaseModel):
    """Output VO consumed by the generic resource table component."""

    id: int
    name: str
    project_id: int | None = None
    test_rounds: int
    test_type: str
    api_ids: list[int] = Field(default_factory=list)
    web_feature_ids: list[int] = Field(default_factory=list)
    api_count: int = 0
    web_feature_count: int = 0
    description: str | None = None
    requirement_title: str | None = None
    requirement_document: str | None = None
    generation: JsonObject = Field(default_factory=dict)
    status: str
    data: JsonObject = Field(default_factory=dict)
    created_at: str
    updated_at: str


class ExecutionPlanCaseOut(BaseModel):
    """Case snapshot included by an execution plan."""

    id: int
    plan_id: int
    case_type: str
    feature_id: int | None = None
    feature_name: str
    case_id: int
    case_name: str
    case_version: str | None = None
    snapshot: JsonObject = Field(default_factory=dict)
    sort_order: int
    created_at: str
    updated_at: str


class ExecutionPlanRunOut(BaseModel):
    """One run batch under an execution plan."""

    id: int
    plan_id: int
    round_no: int
    status: str
    total_count: int
    success_count: int
    failed_count: int
    pass_rate: float
    started_at: str | None = None
    ended_at: str | None = None
    created_at: str
    updated_at: str


class ExecutionPlanRunItemOut(BaseModel):
    """Execution result for one case snapshot inside a run."""

    id: int
    run_id: int
    plan_case_id: int
    case_type: str
    case_id: int
    status: str
    duration_ms: int | None = None
    error_message: str | None = None
    report_record_id: int | None = None
    artifact: JsonObject = Field(default_factory=dict)
    executed_at: str | None = None
    created_at: str


class ExecutionPlanFeatureCaseOut(BaseModel):
    """Case plus its latest result for grouped detail rendering."""

    case_snapshot: ExecutionPlanCaseOut
    latest_result: ExecutionPlanRunItemOut | None = None


class ExecutionPlanFeatureOut(BaseModel):
    """Feature point grouped under WEB/API/APP tabs."""

    feature_id: int | None = None
    feature_name: str
    cases: list[ExecutionPlanFeatureCaseOut] = Field(default_factory=list)


class ExecutionPlanGroupOut(BaseModel):
    """Feature group for one test domain."""

    case_type: str
    label: str
    features: list[ExecutionPlanFeatureOut] = Field(default_factory=list)


class ExecutionPlanSummaryOut(BaseModel):
    """Aggregated detail metrics for the latest selected run."""

    feature_count: int
    case_count: int
    run_count: int
    executed_count: int
    success_count: int
    failed_count: int
    pass_rate: float


class ExecutionPlanDetailOut(BaseModel):
    """Detail VO for execution plan pages."""

    plan: ExecutionPlanOut
    summary: ExecutionPlanSummaryOut
    latest_run: ExecutionPlanRunOut | None = None
    runs: list[ExecutionPlanRunOut] = Field(default_factory=list)
    groups: list[ExecutionPlanGroupOut] = Field(default_factory=list)


class ExecutionPlanGenerationOut(BaseModel):
    """Result returned after regenerating executable plan cases."""

    plan_id: int
    knowledge_count: int
    api_case_count: int
    web_case_count: int
    generated_case_count: int
    detail: ExecutionPlanDetailOut


class ExecutionPlanFeatureAddRequest(BaseModel):
    """Input DTO for adding API/Web feature points to a plan detail."""

    case_type: Literal["API", "WEB"]
    feature_ids: list[int] = Field(min_length=1, max_length=500)


class ExecutionPlanManualFeatureCreate(BaseModel):
    """Input DTO for adding a manual-only test feature point."""

    feature_name: str = Field(min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=2000)

    @field_validator("feature_name", "description", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        """Normalize text so empty manual points are rejected early."""

        return value.strip() if isinstance(value, str) else value


class ExecutionPlanRunRequest(BaseModel):
    """Input DTO for running an execution plan."""

    round_no: int | None = Field(default=None, ge=1, le=10000)
    auth_id: int | None = Field(default=None, ge=1)
    mode: ExecutionModeEnum = ExecutionModeEnum.SERVER_HEADLESS
    node_id: str | None = Field(default=None, max_length=128)
    config: JsonObject = Field(default_factory=dict)


class ExecutionFlowCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    project_id: int
    steps: list[dict[str, Any]] = Field(default_factory=list)
    config: dict[str, Any] = Field(default_factory=dict)
