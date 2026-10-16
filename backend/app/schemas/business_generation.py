import base64
import struct
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class ReferenceScreenshot(BaseModel):
    description: str = Field(min_length=1, max_length=2000)
    image_base64: str = Field(max_length=5_600_000)

    @field_validator("image_base64")
    @classmethod
    def png_only(cls, value):
        raw = base64.b64decode(value, validate=True)
        if len(raw) < 24 or len(raw) > 4 * 1024 * 1024 or not raw.startswith(b"\x89PNG\r\n\x1a\n"):
            raise ValueError("截图必须为不超过 4MB 的 PNG")
        width, height = struct.unpack(">II", raw[16:24])
        if not width or not height or width * height > 20_000_000:
            raise ValueError("截图尺寸超出限制")
        return value


class GenerationRequest(BaseModel):
    source_id: int = Field(gt=0)
    prompt: str = Field(min_length=1, max_length=12000)
    model_id: int | None = Field(default=None, gt=0)
    include_knowledge: bool = True
    screenshots: list[ReferenceScreenshot] = Field(default_factory=list, max_length=6)
    parent_task_id: int | None = Field(default=None, gt=0)
    previous_candidate: dict[str, Any] | None = None

    @model_validator(mode="after")
    def total_size(self):
        if sum(len(s.image_base64) for s in self.screenshots) > 11_200_000:
            raise ValueError("截图总大小不能超过 8MB")
        if not self.prompt.strip():
            raise ValueError("需求不能为空")
        return self


class CandidateRequest(BaseModel):
    candidate: dict[str, Any]


class ReplayRequest(CandidateRequest):
    node_key: str = Field(min_length=3, max_length=128)
    wait_for_login: bool = True
    approve_side_effects: bool = False


class GenerationControlRequest(BaseModel):
    action: Literal["continue", "cancel"]


class ReplayStateRequest(BaseModel):
    node_key: str = Field(min_length=3, max_length=128)
    lease_token: str | None = None
    phase: Literal["state", "waiting_login", "running"] = "state"
