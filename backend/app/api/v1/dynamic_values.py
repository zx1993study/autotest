from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field
from web_automation.dynamic_values import DynamicValueError, prepare_dynamic_execution

from app.core.exceptions import BusinessRuleError
from app.core.response import success


router = APIRouter(prefix="/testing/dynamic-values", tags=["dynamic-values"])


class DynamicValuePreview(BaseModel):
    value: Any
    variables: dict[str, Any] = Field(default_factory=dict)


@router.post("/preview")
def preview_dynamic_value(payload: DynamicValuePreview) -> dict[str, object]:
    try:
        case, _, context = prepare_dynamic_execution({"data": {"variables": payload.variables, "value": payload.value}}, {})
        resolved = case["data"]["value"]
    except DynamicValueError as exc:
        raise BusinessRuleError(str(exc)) from exc
    return success({"resolved": resolved, "dynamic_values": context.snapshot()})
