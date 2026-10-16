import math
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class WebInputParameter(BaseModel):
    key: str = Field(pattern=r"^[A-Za-z_][A-Za-z0-9_]*$", max_length=80)
    label: str = Field(min_length=1, max_length=128)
    type: Literal["text", "password", "textarea", "number", "select", "multiselect", "date", "datetime", "boolean", "json", "manual"] = "text"
    required: bool = False
    options: list[Any] = Field(default_factory=list, max_length=200)
    default_value: Any = None
    condition: dict[str, Any] = Field(default_factory=dict)
    validation: dict[str, Any] = Field(default_factory=dict)
    locator_type: str = "label"
    locator: str = ""
    confirmed: bool = False
    required_known: bool = True
    frame_selector: str = ""

    @model_validator(mode="after")
    def valid_rules(self):
        if self.condition and (set(self.condition) != {"key", "equals"} or not isinstance(self.condition["key"], str)):
            raise ValueError("显示条件须包含 key 和 equals")
        if set(self.validation) - {"min", "max", "min_length", "max_length"}:
            raise ValueError("校验规则只支持 min、max、min_length 和 max_length")
        for key, value in self.validation.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError("校验规则须为有限数字")
            if key.endswith("length") and (not isinstance(value, int) or value < 0):
                raise ValueError("长度校验须为非负整数")
        for lower, upper in (("min", "max"), ("min_length", "max_length")):
            if lower in self.validation and upper in self.validation and self.validation[lower] > self.validation[upper]:
                raise ValueError("校验下限不能大于上限")
        return self


class WebFeatureSave(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    feature_type: Literal["page", "login", "query", "add", "edit", "delete", "detail", "import", "export", "audit", "submit", "other"] = "query"
    description: str = Field(default="", max_length=2000)
    status: Literal["active", "disabled"] = "active"
    auth_id: int | None = Field(default=None, gt=0)
    parameters: list[WebInputParameter] = Field(default_factory=list, max_length=100)
    candidate: dict[str, Any] | None = None
    expected_revision: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def unique_parameters(self):
        if len({p.key for p in self.parameters}) != len(self.parameters):
            raise ValueError("参数标识不能重复")
        keys = {p.key for p in self.parameters}
        for parameter in self.parameters:
            if parameter.condition and parameter.condition.get("key") not in keys - {parameter.key}:
                raise ValueError("条件依赖必须指向其他已定义参数")
            if parameter.type in {"manual", "password"} and parameter.default_value not in (None, ""):
                raise ValueError("密码和人工输入不能保存默认值，请在用例中设置密码")
        return self


class WebInputCaseSave(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    input_info: dict[str, Any] = Field(default_factory=dict)
    expected_steps: list[dict[str, Any]] = Field(default_factory=list, max_length=60)
    priority: Literal["P0", "P1", "P2", "P3"] = "P2"
    status: Literal["active", "disabled"] = "active"
    allow_invalid_inputs: bool = False
    script_version: int | None = Field(default=None, gt=0)
    copy_from_case_id: int | None = Field(default=None, gt=0)


class WebFeatureRun(BaseModel):
    case_ids: list[int] = Field(min_length=1, max_length=50)
    headless: bool = True
    node_key: str = Field(min_length=3, max_length=128)
    approve_side_effects: bool = False
    record_video: bool = True


class WebFeatureRepair(BaseModel):
    agent_task_id: int = Field(gt=0)
    case_id: int = Field(gt=0)


class WebVersionSelect(BaseModel):
    version_id: int = Field(gt=0)
