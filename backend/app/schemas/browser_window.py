from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.agent import AgentTaskRenewRequest


class BrowserWindowState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    window_id: str = Field(min_length=16, max_length=64)
    revision: int = Field(gt=0, le=9223372036854775807)
    status: Literal["opening", "open", "closed", "unavailable"]
    browser_name: str = Field(default="", max_length=80)
    label: str = Field(default="", max_length=200)
    phase: Literal["starting", "waiting_login", "waiting_input", "recording", "analyzing", "running", "finished"] = "starting"
    focus: Literal["idle", "active", "blocked", "failed"] = "idle"
    command_id: str = Field(default="", max_length=64)


class BrowserWindowExchangeRequest(AgentTaskRenewRequest):
    window: BrowserWindowState
