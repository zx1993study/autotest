from pydantic import BaseModel, ConfigDict, Field

from app.core.types import JsonObject
from app.enums.business import ExecutionModeEnum
from app.schemas.cases import ApiCaseExecutionConfig


class GenerateDraftRequest(BaseModel):
    """Input DTO for rule-based test draft generation."""

    project_id: int = Field(ge=1)
    source_ids: list[int] = Field(default_factory=list, max_length=500)
    strategy: str = Field(default="basic", min_length=1, max_length=64)
    strategy_ids: list[int] = Field(default_factory=list, max_length=500)


class AppScenarioGenerateRequest(BaseModel):
    """Input DTO for generating an App scenario draft from user intent."""

    project_id: int = Field(ge=1)
    prompt: str = Field(min_length=1, max_length=8000)
    model_id: int | None = Field(default=None, ge=1)
    entry_id: int | None = Field(default=None, ge=1)
    source_id: int | None = Field(default=None, ge=1)
    target_platforms: list[str] = Field(default_factory=list, max_length=4)
    target_device_form_factors: list[str] = Field(default_factory=list, max_length=4)
    include_knowledge: bool = True
    knowledge_ids: list[int] = Field(default_factory=list, max_length=100)
    start_from_current_screen: bool = True
    record_video: bool = True
    save_draft: bool = True
    dry_run: bool = False
    allow_rule_fallback: bool = True


class AppScenarioEventTraceRequest(BaseModel):
    """Input DTO for generating an App scenario draft from recorded events."""

    project_id: int = Field(ge=1)
    name: str | None = Field(default=None, max_length=128)
    entry_id: int | None = Field(default=None, ge=1)
    source_id: int | None = Field(default=None, ge=1)
    events: list[JsonObject] = Field(min_length=1, max_length=1000)
    start_from_current_screen: bool = True
    record_video: bool = True
    save_draft: bool = True


class AppFeatureListQuery(BaseModel):
    """Query DTO for the new App feature testing hierarchy."""

    model_config = ConfigDict(populate_by_name=True)

    project_id: int | None = Field(default=None, ge=1)
    device_id: int | None = Field(default=None, ge=1)
    keyword: str | None = Field(default=None, max_length=128)
    status: str | None = Field(default=None, max_length=32)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200, alias="pageSize")


class AppFeatureScenarioListQuery(BaseModel):
    """Query DTO for listing scenarios under one App feature."""

    model_config = ConfigDict(populate_by_name=True)

    device_id: int | None = Field(default=None, ge=1)
    keyword: str | None = Field(default=None, max_length=128)
    status: str | None = Field(default=None, max_length=32)
    source_type: str | None = Field(default=None, max_length=32)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200, alias="pageSize")


class AppFeatureScenarioCreateRequest(BaseModel):
    """Create or update a feature scenario and its editable script parts."""

    name: str = Field(min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=2000)
    status: str = Field(default="active", max_length=32)
    source_type: str = Field(default="manual", max_length=32)
    device_id: int | None = Field(default=None, ge=1)
    entry_id: int | None = Field(default=None, ge=1)
    record_video: bool = True
    start_from_current_screen: bool = True
    operation_steps: list[JsonObject] = Field(default_factory=list, max_length=1000)
    input_info: JsonObject = Field(default_factory=dict)
    variables: JsonObject = Field(default_factory=dict)
    assertions: list[JsonObject] = Field(default_factory=list, max_length=500)


class AppFeatureScenarioUpdateRequest(BaseModel):
    """Partial update for a feature scenario."""

    name: str | None = Field(default=None, max_length=128)
    description: str | None = Field(default=None, max_length=2000)
    status: str | None = Field(default=None, max_length=32)
    device_id: int | None = Field(default=None, ge=1)
    entry_id: int | None = Field(default=None, ge=1)
    record_video: bool | None = None
    start_from_current_screen: bool | None = None
    operation_steps: list[JsonObject] | None = Field(default=None, max_length=1000)
    input_info: JsonObject | None = None
    variables: JsonObject | None = None
    assertions: list[JsonObject] | None = Field(default=None, max_length=500)


class AppFeatureScenarioTextGenerateRequest(BaseModel):
    """Generate a feature scenario script from natural language."""

    name: str | None = Field(default=None, max_length=128)
    prompt: str = Field(min_length=1, max_length=8000)
    model_id: int | None = Field(default=None, ge=1)
    device_id: int | None = Field(default=None, ge=1)
    entry_id: int | None = Field(default=None, ge=1)
    include_knowledge: bool = True
    knowledge_ids: list[int] = Field(default_factory=list, max_length=100)
    record_video: bool = True
    start_from_current_screen: bool = True
    dry_run: bool = False
    allow_rule_fallback: bool = True


class AppFeatureScenarioRecordingRequest(BaseModel):
    """Generate a scenario from a recorded event trace."""

    name: str = Field(min_length=1, max_length=128)
    device_id: int | None = Field(default=None, ge=1)
    entry_id: int | None = Field(default=None, ge=1)
    events: list[JsonObject] = Field(default_factory=list, max_length=1000)
    record_video: bool = True
    start_from_current_screen: bool = True


class AppScenarioInputInfoUpdateRequest(BaseModel):
    """Update only the variable input part of a scenario script."""

    input_info: JsonObject = Field(default_factory=dict)


class AppScenarioRunRequest(BaseModel):
    """Execute a scenario against one selected or default device."""

    device_id: int | None = Field(default=None, ge=1)
    node_id: str | None = Field(default=None, min_length=3, max_length=128)
    input_info: JsonObject = Field(default_factory=dict)
    variables: JsonObject | None = None
    record_video: bool | None = None
    mode: str = Field(default="local_appium", max_length=64)


class ApiModuleListQuery(BaseModel):
    """Paginate API modules derived from one project's interface metadata."""

    model_config = ConfigDict(populate_by_name=True)

    project_id: int = Field(ge=1)
    keyword: str | None = Field(default=None, max_length=128)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200, alias="pageSize")


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
    mode: ExecutionModeEnum = ExecutionModeEnum.SERVER_HEADLESS
    node_id: str | None = Field(default=None, max_length=128)
    case_ids: list[int] = Field(default_factory=list, max_length=500)
    config: JsonObject = Field(default_factory=dict)


class ApiExecuteCasesRequest(ExecuteCasesRequest):
    config: ApiCaseExecutionConfig = Field(default_factory=ApiCaseExecutionConfig)
