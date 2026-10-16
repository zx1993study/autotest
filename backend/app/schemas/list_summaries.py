from typing import Any, TypedDict

from pydantic import BaseModel

from app.core.types import JsonValue


class AppFeatureSummary(TypedDict):
    scenario_count: int
    last_run: dict[str, Any] | None


class WebFeatureCounts(TypedDict):
    element_count: int
    case_count: int


class GenerationTaskSummary(BaseModel):
    domain: str | None = None
    source_id: int | None = None
    task_type: str | None = None
    progress: JsonValue = None
    model_http_calls: int = 0
    error: str | None = None
