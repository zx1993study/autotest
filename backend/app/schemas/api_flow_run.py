from typing import Any, Literal

from pydantic import BaseModel, Field


class ApiFlowRunRequest(BaseModel):
    scenario_ids: list[int] = Field(min_length=1, max_length=100)
    mode: Literal["serial", "parallel"] = "serial"
    concurrency: int = Field(default=2, ge=1, le=4)
    inputs: dict[str, Any] = Field(default_factory=dict)
