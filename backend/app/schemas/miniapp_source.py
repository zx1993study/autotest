from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class SourceIdentity(BaseModel):
    repository: str = Field(pattern=r"^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/?$", max_length=300)
    revision: str = Field(pattern=r"^[a-f0-9]{40}$")


class SourceMetadata(BaseModel):
    model_config = ConfigDict(extra="allow")
    schema_version: Literal[1]
    source: SourceIdentity


class SourceOperation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal["visible", "input", "click", "disabled", "password_mode", "toast"]
    selector: str | None = Field(default=None, max_length=500)
    value: str = Field(default="", max_length=500)
    text: str | None = Field(default=None, max_length=500)
    masked: bool = True

    @model_validator(mode="after")
    def check_target(self):
        if not (self.text if self.action == "toast" else self.selector):
            raise ValueError("Operation target is required")
        return self


class SourceCase(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str = Field(min_length=1, max_length=128)
    title: str = Field(min_length=1, max_length=128)
    route: str = Field(min_length=1, max_length=300, pattern=r"^[A-Za-z0-9_/-]+$")
    platforms: list[Literal["h5", "mp-weixin", "mp-weixin-real-device"]] = Field(min_length=1, max_length=3)
    category: Literal["render", "query", "validation", "client_guard", "business"]
    automation: Literal["scripted", "manual", "manual_native"]
    verification: Literal["not_executed"] = "not_executed"
    requires_auth: bool
    requires_fixture: bool
    risk: Literal["read", "write", "session", "native"]
    steps: list[str] = Field(min_length=1, max_length=100)
    expected: list[str] = Field(min_length=1, max_length=100)
    preconditions: list[str] = Field(default_factory=list, max_length=100)
    operations: list[SourceOperation] = Field(default_factory=list, max_length=100)

    @field_validator("steps", "expected", "preconditions")
    @classmethod
    def bound_text(cls, values):
        if any(not value.strip() or len(value) > 2000 for value in values):
            raise ValueError("Invalid step text")
        return values

    @field_validator("route")
    @classmethod
    def relative_route(cls, value):
        if value.startswith("/") or "//" in value:
            raise ValueError("Expected relative miniapp route")
        return value

    @model_validator(mode="after")
    def require_script(self):
        if self.automation == "scripted" and not self.operations:
            raise ValueError("Scripted cases require operations")
        return self


class SourceCatalogImport(BaseModel):
    project_id: int = Field(ge=1)
    metadata: SourceMetadata
    cases: list[SourceCase] = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def unique_ids(self):
        if len({case.id for case in self.cases}) != len(self.cases):
            raise ValueError("Duplicate source case IDs")
        return self


class SourceRunRequest(BaseModel):
    project_id: int = Field(ge=1)
    case_ids: list[int] = Field(min_length=1, max_length=500)
    platform: Literal["h5", "mp-weixin"] = "mp-weixin"


class SourceBusinessBinding(BaseModel):
    flow_id: int = Field(ge=1)
    scenario_id: int = Field(ge=1)
