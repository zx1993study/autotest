from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.agent import AgentTaskRenewRequest


class VisionCapture(BaseModel):
    feature_id: str = Field(max_length=64)
    feature_name: str = Field(max_length=200)
    screenshot_base64: str = Field(max_length=7 * 1024 * 1024)
    entry_element: dict | None = None
    requests: list[dict[str, str]] = Field(default_factory=list, max_length=100)
    dom: list[dict] = Field(default_factory=list, max_length=200)


class VisionStepRequest(AgentTaskRenewRequest):
    phase: Literal["waiting_login", "overview", "captures"]
    login_retry: bool = False
    screenshot_base64: str | None = Field(default=None, max_length=7 * 1024 * 1024)
    page_url: str = Field(default="", max_length=4096)
    dom: list[dict] = Field(default_factory=list, max_length=200)
    captures: list[VisionCapture] = Field(default_factory=list, max_length=30)
    feature_errors: list[dict] = Field(default_factory=list, max_length=30)


class VisionLoginRequest(BaseModel):
    action: Literal["continue", "cancel"]


class VisionModelCheckRequest(BaseModel):
    model_id: int | None = Field(default=None, gt=0)
