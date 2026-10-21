from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ReportKind = Literal["api", "flow"]


class ApiReportQuery(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    project_id: int | None = Field(default=None, ge=1)
    kind: ReportKind | None = None
    status: str | None = Field(default=None, max_length=32)
    keyword: str | None = Field(default=None, max_length=200)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100, alias="pageSize")


class ApiReportRow(BaseModel):
    key: str
    kind: ReportKind
    record_id: int
    project_id: int | None
    flow_id: int | None = None
    case_id: int | None = None
    scenario_id: int | None = None
    source_name: str
    method: str = ""
    field_or_scene: str
    test_point: str
    status: str
    passed: bool | None = None
    executed_at: str
