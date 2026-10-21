"""Shared completion checks for server and Agent Web execution."""

from typing import Any


def active_steps(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [s for s in steps if str(s.get("skip", s.get("是否跳过", False))).lower() not in {"true", "1", "yes"}]


def verification_error(steps: list[dict[str, Any]]) -> str | None:
    active = active_steps(steps)
    assertions = [i for i, s in enumerate(active) if s.get("action") == "assert" and s.get("expected") is not None and str(s["expected"]).strip()]
    if not assertions:
        return "脚本缺少有效的业务结果断言，不能将操作结束判定为功能成功"
    actions = [i for i, s in enumerate(active) if s.get("action") not in {"assert", "wait", "hover"} and not s.get("cleanup")]
    if actions and max(assertions) < max(actions):
        return "最后一次业务操作后没有结果断言，请补充功能完成校验（清理步骤需标记 cleanup）"
    return None


def outcome_metadata(steps: list[dict[str, Any]], completed: int, status: str) -> dict[str, Any]:
    active = active_steps(steps)
    assertions = [i for i, s in enumerate(active) if s.get("action") == "assert" and s.get("expected") is not None and str(s["expected"]).strip()]
    configured = verification_error(steps) is None
    passed = status == "success" and completed == len(active) and configured
    business = "passed" if passed else "not_configured" if not configured else "failed" if completed in assertions else "not_run"
    return {
        "operation_result": "completed" if status == "success" and completed == len(active) else status,
        "business_result": business,
        "assertion_count": len(assertions),
        "result_label": "操作及业务验证通过" if passed else "业务结果未验证" if status == "success" else "操作或业务验证未通过",
    }
