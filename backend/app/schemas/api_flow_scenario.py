from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.execution_flow import (
    FlowBinding,
    FlowCondition,
    FlowExtract,
    RequestRemovalPath,
)


class ScenarioNode(BaseModel):
    case_id: int | None = Field(default=None, gt=0)
    mode: Literal["always", "skip", "condition"] = "always"
    condition: FlowCondition | None = None
    params: dict[str, Any] = Field(default_factory=dict)
    request: dict[str, Any] = Field(default_factory=dict)
    request_removals: list[RequestRemovalPath] = Field(default_factory=list, max_length=1000)
    assertions: list[dict[str, Any]] | None = None
    bindings: list[FlowBinding] | None = None
    extracts: list[FlowExtract] | None = None


class ScenarioDefinition(BaseModel):
    flow_id: int = 0
    template_version: int = 0
    inputs: dict[str, Any] = Field(default_factory=dict)
    nodes: dict[str, ScenarioNode] = Field(default_factory=dict)
    failure_policy: Literal["stop", "continue"] = "stop"
    expected_end: str = "auto"


class ApiFlowScenarioCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    status: Literal["active", "disabled"] = "active"
    data: ScenarioDefinition = Field(default_factory=ScenarioDefinition)


class ApiFlowScenarioUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    status: Literal["active", "disabled"] | None = None
    data: ScenarioDefinition | None = None
