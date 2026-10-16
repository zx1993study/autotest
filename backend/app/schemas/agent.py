from __future__ import annotations

from pydantic import BaseModel, Field, ConfigDict

from app.core.types import JsonObject
from app.enums.business import AgentNodeStatusEnum, AgentTaskStatusEnum, AgentTaskTypeEnum


class AgentRegisterRequest(BaseModel):
    """Input DTO for registering an installed local execution agent."""

    node_key: str = Field(min_length=3, max_length=128)
    name: str = Field(min_length=1, max_length=128)
    version: str | None = Field(default=None, max_length=64)
    capabilities: list[str] = Field(default_factory=list, max_length=50)
    system: JsonObject = Field(default_factory=dict)


class AgentTokenProvisionRequest(BaseModel):
    """Input DTO for provisioning a node-specific Agent access token.

    The plaintext token is returned once by the API, so callers can write it
    into the local Agent config without exposing a reusable user login token.
    """

    node_key: str = Field(min_length=3, max_length=128)
    name: str = Field(min_length=1, max_length=128)
    version: str | None = Field(default=None, max_length=64)
    capabilities: list[str] = Field(default_factory=list, max_length=50)
    system: JsonObject = Field(default_factory=dict)


class AgentHeartbeatRequest(BaseModel):
    """Input DTO for keeping an agent node online."""

    status: AgentNodeStatusEnum = AgentNodeStatusEnum.ONLINE
    version: str | None = Field(default=None, max_length=64)
    capabilities: list[str] | None = Field(default=None, max_length=50)
    current_task_id: int | None = Field(default=None, ge=1)
    system: JsonObject | None = None


class AgentTaskClaimRequest(BaseModel):
    """Input DTO for an agent polling its next executable task."""

    node_key: str = Field(min_length=3, max_length=128)
    capabilities: list[str] = Field(default_factory=list, max_length=50)


class AgentTaskCreateRequest(BaseModel):
    """Input DTO for creating a task that should be handled by an agent."""

    task_type: AgentTaskTypeEnum
    node_key: str | None = Field(default=None, max_length=128)
    payload: JsonObject = Field(default_factory=dict)


class AgentTaskReportRequest(BaseModel):
    """Input DTO for reporting an agent task result back to the platform."""

    node_key: str = Field(min_length=3, max_length=128)
    status: AgentTaskStatusEnum
    result: JsonObject = Field(default_factory=dict)
    error: str | None = Field(default=None, max_length=5000)
    lease_token: str | None = Field(default=None, max_length=128)


class AgentTaskRenewRequest(BaseModel):
    node_key: str = Field(min_length=3, max_length=128)
    lease_token: str | None = Field(default=None, max_length=128)


class AgentModelCompletionRequest(BaseModel):
    model_config = ConfigDict(extra="allow")
    messages: list[JsonObject] = Field(min_length=1, max_length=100)
    stream: bool = False


class AgentTaskAuthContextRequest(BaseModel):
    """Input DTO for consuming a task-scoped auth snapshot."""

    node_key: str = Field(min_length=3, max_length=128)
    snapshot_id: str | None = Field(default=None, max_length=128)


class AgentTaskAiModelContextRequest(BaseModel):
    """Input DTO for consuming a task-scoped AI model secret snapshot."""

    node_key: str = Field(min_length=3, max_length=128)
    snapshot_id: str | None = Field(default=None, max_length=128)
