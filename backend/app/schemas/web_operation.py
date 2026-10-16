from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.agent import AgentTaskRenewRequest


class WebOperationState(AgentTaskRenewRequest):
    phase: Literal['state', 'waiting_input'] = 'state'
    case_id: int | None = None
    step: int = Field(default=0, ge=0, le=60)


class WebOperationControl(BaseModel):
    action: Literal['continue', 'cancel', 'stop']
    nonce: str = Field(default='', max_length=128)


class WebRecordingStart(BaseModel):
    node_key: str = Field(min_length=3, max_length=128)
    approve_side_effects: bool = False


class WebRecordingAccept(BaseModel):
    task_id: int = Field(gt=0)
    candidate: dict
