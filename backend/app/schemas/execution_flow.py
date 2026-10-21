"""Typed API flow templates stored in the existing resource namespace."""

from typing import Annotated, Any, Literal, TypedDict

from jsonpointer import JsonPointer, JsonPointerException
from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.common import ResourceCreate, ResourceUpdate

RequestRemovalPath = Annotated[str, Field(pattern=r"^/(params|headers|query)/[^/]+$|^/(body|method|path|content_type|api_base_path)$")]


class ExecutionFlowSummary(TypedDict):
    scenario_count: int
    latest_status: str | None


class FlowValue(BaseModel):
    source: str = "global"
    name: str = Field(min_length=1, max_length=100)


class FlowCondition(FlowValue):
    operator: Literal["eq", "ne", "gt", "ge", "lt", "le", "contains", "exists"] = "eq"
    value: Any = None


class FlowRowSelection(BaseModel):
    path: str
    non_empty: list[str] = Field(default_factory=list, max_length=100)
    equals: dict[str, Any] = Field(default_factory=dict, max_length=100)

    @model_validator(mode="after")
    def validate_selection(self):
        if not self.non_empty and not self.equals:
            raise ValueError("Row selection needs an explicit filter")
        try:
            for path in [self.path, *self.non_empty, *self.equals]:
                JsonPointer(path)
        except JsonPointerException as exc:
            raise ValueError("Invalid row selection JSON Pointer") from exc
        return self


class FlowExtract(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    source: Literal["body", "header", "status"] = "body"
    path: str = ""
    mode: Literal["single", "array"] = "single"
    paths: list[str] = Field(default_factory=list, max_length=100)
    required: bool = True
    sensitive: bool = False
    selection: FlowRowSelection | None = None

    @model_validator(mode="after")
    def validate_paths(self):
        if self.selection and self.source != "body":
            raise ValueError("Row selection only supports response bodies")
        if self.mode == "array" and (self.source == "status" or not self.paths):
            raise ValueError("数组提取必须配置至少一条 Body 或 Header 精确路径")
        if self.mode == "array" and any(not path for path in self.paths):
            raise ValueError("数组提取路径不能为空")
        return self


class FlowBinding(FlowValue):
    target: Literal["auto", "params", "headers", "query", "body", "variables"] = "params"
    path: str = ""
    target_name: str = Field(default="", max_length=200)
    prefix: str = ""

    @model_validator(mode="after")
    def validate_target(self):
        if self.target == "auto":
            self.target_name = self.target_name.strip()
            if not self.target_name:
                raise ValueError("目的变量名不能为空")
        elif not self.path.startswith("/"):
            raise ValueError("参数目标路径必须以 / 开头")
        return self


class FlowRoute(BaseModel):
    source: Literal["body", "header", "status"] = "body"
    path: str = "/code"
    operator: Literal["eq", "ne", "gt", "ge", "lt", "le", "contains", "exists"] = "eq"
    value: Any = 0
    target: str = "end"


class FlowNode(BaseModel):
    key: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_\-]{0,63}$")
    name: str = Field(min_length=1, max_length=200)
    api_id: int = Field(gt=0)
    case_id: int | None = Field(default=None, gt=0)
    auth_id: int | None = Field(default=None, gt=0)
    params: dict[str, Any] = Field(default_factory=dict)
    request: dict[str, Any] = Field(default_factory=dict)
    request_removals: list[RequestRemovalPath] = Field(default_factory=list, max_length=1000)
    bindings: list[FlowBinding] = Field(default_factory=list, max_length=100)
    extracts: list[FlowExtract] = Field(default_factory=list, max_length=100)
    routes: list[FlowRoute] = Field(default_factory=list, max_length=100)
    next: str = "auto"

    @field_validator("key")
    @classmethod
    def reserved_keys(cls, value: str) -> str:
        if value in {"global", "end", "auto"}:
            raise ValueError("节点标识不能使用 global、end、auto")
        return value


class FlowDefinition(BaseModel):
    version: int = 1
    inputs: dict[str, Any] = Field(default_factory=dict)
    nodes: list[FlowNode] = Field(default_factory=list, max_length=100)


class ExecutionFlowCreate(ResourceCreate):
    pass


class ExecutionFlowUpdate(ResourceUpdate):
    pass
