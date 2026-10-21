from datetime import datetime
from typing import Annotated, Literal, TypedDict

from pydantic import BaseModel, Field


class WebExecutionSummaryQuery(BaseModel):
    project_id: int = Field(gt=0)
    scope: Literal["page", "feature", "case"]
    ids: list[Annotated[int, Field(gt=0)]] = Field(min_length=1, max_length=200)


class WebExecutionSnapshot(TypedDict):
    case_id: int
    feature_id: int
    page_id: int | None
    record_id: int | None
    status: str | None
    business_result: str | None
    assertion_count: int | None
    executed_at: datetime | None


class WebExecutionSummary(BaseModel):
    id: int
    status: Literal["success", "failed", "not_run", "partial", "unverified", "running", "canceled", "empty"] = "empty"
    total_count: int = 0
    success_count: int = 0
    failed_count: int = 0
    not_run_count: int = 0
    unverified_count: int = 0
    running_count: int = 0
    canceled_count: int = 0
    executed_at: datetime | None = None
    record_id: int | None = None


class WebExecutionSummaries(BaseModel):
    items: list[WebExecutionSummary]
