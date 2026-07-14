from typing import Any

from pydantic import BaseModel, Field


class ExecutionPlanCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    project_id: int
    cron: str | None = None
    case_ids: list[int] = Field(default_factory=list)
    config: dict[str, Any] = Field(default_factory=dict)


class ExecutionFlowCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    project_id: int
    steps: list[dict[str, Any]] = Field(default_factory=list)
    config: dict[str, Any] = Field(default_factory=dict)
