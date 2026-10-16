"""Pure strategy metadata helpers shared by API and Web case builders."""

from __future__ import annotations

from typing import Any


def with_strategy_meta(
    case_json: dict[str, Any],
    strategy_id: int,
    knowledge_key_value: str | None,
) -> dict[str, Any]:
    """Attach normalized knowledge references to one generated case."""

    case_json["strategy_ids"] = [strategy_id]
    if knowledge_key_value:
        case_json["knowledge_keys"] = [knowledge_key_value]
    return case_json


def strategy_category(strategy: dict[str, Any]) -> str:
    """Map free-form knowledge metadata to a stable generation category."""

    data = strategy.get("data") if isinstance(strategy.get("data"), dict) else {}
    raw = " ".join(
        str(item or "").lower()
        for item in (
            data.get("category"),
            data.get("knowledge_key"),
            strategy.get("name"),
            strategy.get("description"),
            data.get("content"),
        )
    )
    category_markers = (
        ("normal", ("normal", "success", "正常")),
        ("required_empty", ("required", "empty", "必填", "为空")),
        ("boundary", ("boundary", "边界")),
        ("delete_confirm", ("delete", "删除")),
        ("security", ("auth", "permission", "security", "鉴权", "权限", "安全")),
        ("invalid", ("abnormal", "invalid", "exception", "异常")),
    )
    for category, markers in category_markers:
        if any(marker in raw for marker in markers):
            return category
    return "strategy"


def category_label(category: str) -> str:
    """Return the Chinese label used in generated case names."""

    labels = {
        "boundary": "边界场景",
        "required_empty": "必填为空",
        "delete_confirm": "删除确认",
        "security": "安全校验",
        "auth": "鉴权校验",
        "invalid": "异常场景",
        "strategy": "策略场景",
    }
    return labels.get(category, "策略场景")


def is_auth_strategy(strategy: dict[str, Any]) -> bool:
    """Identify knowledge that specifically requests unauthenticated tests."""

    data = strategy.get("data") if isinstance(strategy.get("data"), dict) else {}
    raw = " ".join(
        str(item or "").lower()
        for item in (
            data.get("knowledge_key"),
            strategy.get("name"),
            strategy.get("description"),
            data.get("content"),
        )
    )
    return any(
        marker in raw
        for marker in ("auth", "token", "cookie", "unauthorized", "401", "未登录", "鉴权")
    )


def knowledge_key(strategy: dict[str, Any]) -> str | None:
    """Read one optional stable knowledge key."""

    data = strategy.get("data") if isinstance(strategy.get("data"), dict) else {}
    value = data.get("knowledge_key")
    return str(value) if value else None


def knowledge_keys(
    strategies: list[dict[str, Any]],
    category: str,
) -> list[str]:
    """Collect unique keys for one generation category."""

    return [
        key
        for key in (
            knowledge_key(item)
            for item in strategies
            if strategy_category(item) == category
        )
        if key
    ]


def case_json(
    case_type: str,
    name: str,
    category: str,
    request: dict[str, Any],
    expected_status: int,
) -> dict[str, Any]:
    """Build the common generated-case envelope."""

    return {
        "name": name,
        "case_type": case_type,
        "category": category,
        **request,
        "assertions": [{"type": "status", "expected": expected_status}],
    }
