from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class AppExplorationStart(BaseModel):
    device_id: int = Field(gt=0)
    entry_id: int = Field(gt=0)
    prompt: str = Field(min_length=1, max_length=12000)
    request_id: str = Field(min_length=16, max_length=80)
    model_id: int | None = Field(default=None, gt=0)
    approve_effects: bool = False
    start_from_current_screen: bool = False
    record_video: bool = True

    @field_validator('prompt')
    @classmethod
    def not_blank(cls, value):
        if not value.strip():
            raise ValueError('请输入操作目标')
        return value


class AppExplorationControl(BaseModel):
    action: Literal['message', 'pause', 'resume', 'cancel', 'finish', 'approve', 'manual_done', 'confirm_not_executed', 'check_app', 'confirm_app']
    message: str = Field(default='', max_length=12000)
    nonce: str = Field(default='', max_length=80)
    request_id: str = Field(min_length=16, max_length=80)


class AppExplorationAccept(BaseModel):
    name: str = Field(min_length=1, max_length=160)


class AppRuntimeState(BaseModel):
    node_key: str = Field(min_length=3, max_length=128)
    lease_token: str = Field(min_length=8, max_length=128)


class AppObservation(AppRuntimeState):
    observation_id: str = Field(min_length=16, max_length=80)
    screen: dict[str, Any]
    screenshot_base64: str | None = Field(default=None, max_length=5_600_000)
    session_reused: bool = False


class AppConnectionReport(AppRuntimeState):
    status: Literal['connected', 'identified', 'waiting_app']
    wda_url: str = Field(default='', max_length=500)
    reported_udid: str = Field(default='', max_length=128)
    bundle_id: str = Field(default='', max_length=240)
    app_name: str = Field(default='', max_length=240)


class AppActionReport(AppRuntimeState):
    nonce: str = Field(min_length=16, max_length=80)
    status: Literal['begin', 'success', 'failed', 'stale']
    error: str = Field(default='', max_length=500)
    duration_ms: int = Field(default=0, ge=0)
    input_value: str | None = Field(default=None, max_length=2000)
