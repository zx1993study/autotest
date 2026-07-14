from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin, urlparse

from app.constants.ai_generation import SENSITIVE_MARKERS


def project_context(item: dict[str, Any]) -> dict[str, Any]:
    """Build a safe project summary for AI prompts."""

    data = item.get("data") if isinstance(item.get("data"), dict) else {}
    return {
        "id": item.get("id"),
        "name": item.get("name"),
        "description": item.get("description"),
        "base_url": data.get("base_url") or data.get("project_url") or data.get("url"),
        "api_base_path": data.get("api_base_path"),
        "default_env": data.get("default_env"),
    }


def page_context(item: dict[str, Any]) -> dict[str, Any]:
    """Build a compact Web page/function summary for model context."""

    data = item.get("data") if isinstance(item.get("data"), dict) else {}
    return {
        "id": item.get("id"),
        "name": short_text(item.get("name"), 80),
        "route": data.get("route"),
        "url": data.get("url"),
        "feature_type": data.get("feature_type"),
        "module": short_text(data.get("module"), 80),
    }


def interface_context(item: dict[str, Any]) -> dict[str, Any]:
    """Build a compact API interface summary for model context."""

    data = item.get("data") if isinstance(item.get("data"), dict) else {}
    raw = data.get("raw") if isinstance(data.get("raw"), dict) else {}
    return {
        "id": item.get("id"),
        "name": short_text(item.get("name"), 100),
        "method": data.get("method"),
        "path": data.get("path"),
        "module": short_text(data.get("module") or first(raw.get("tags")), 80),
        "summary": short_text(raw.get("summary") or item.get("description"), 160),
    }


def knowledge_context(item: dict[str, Any]) -> dict[str, Any]:
    """Build a compact knowledge item summary for model context."""

    data = item.get("data") if isinstance(item.get("data"), dict) else {}
    return {
        "id": item.get("id"),
        "name": item.get("name"),
        "kind": data.get("kind"),
        "domain": data.get("domain"),
        "category": data.get("category"),
        "priority": data.get("priority"),
        "content": short_text(data.get("content"), 200),
    }


def interface_module_summary(interfaces: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Aggregate interfaces by module so prompts can see API distribution."""

    summary: dict[str, dict[str, Any]] = {}
    for item in interfaces:
        data = item.get("data") if isinstance(item.get("data"), dict) else {}
        raw = data.get("raw") if isinstance(data.get("raw"), dict) else {}
        module = str(data.get("module") or first(raw.get("tags")) or "未分组")
        method = str(data.get("method") or "").upper()
        row = summary.setdefault(module, {"module": module, "count": 0, "methods": {}})
        row["count"] += 1
        row["methods"][method] = row["methods"].get(method, 0) + 1
    return list(summary.values())


def resource_context(item: dict[str, Any]) -> dict[str, Any]:
    """Expose the common resource fields used by AI case generation."""

    return {
        "id": item.get("id"),
        "name": item.get("name"),
        "project_id": item.get("project_id"),
        "description": item.get("description"),
        "status": item.get("status"),
        "data": item.get("data") if isinstance(item.get("data"), dict) else {},
    }


def raw_page_keys(page: dict[str, Any]) -> list[str]:
    route = page.get("route")
    url = page.get("url")
    feature_type = normalize_feature_type(page.get("feature_type"))
    key_value = page_identity_key(None, route, url, feature_type)
    return [key_value] if key_value else []


def normalize_feature_type(value: Any) -> str:
    text = str(value or "page").strip().lower()
    aliases = {
        "list": "page",
        "search": "query",
        "create": "add",
        "new": "add",
        "update": "edit",
        "remove": "delete",
        "view": "detail",
        "info": "detail",
        "upload": "import",
        "download": "export",
    }
    return aliases.get(text, text)


def feature_key(prefix: str, *values: Any) -> str | None:
    parts: list[str] = []
    for value in values:
        if value is None:
            return None
        text = str(value).strip()
        if not text or text.lower() == "none":
            return None
        parts.append(text.lower())
    return f"{prefix}:{'|'.join(parts)}"


def page_identity_key(project_id: Any, route: Any, url: Any, feature_type: Any) -> str | None:
    normalized_route = normalize_identity_route(route)
    normalized_url = normalize_identity_url(url)
    normalized_feature_type = normalize_feature_type(feature_type)
    if not normalized_route or not normalized_url or not normalized_feature_type:
        return None
    parts = ["page_identity"]
    if project_id is not None:
        parts.append(str(project_id).strip())
    parts.extend([normalized_route, normalized_url, normalized_feature_type])
    return ":".join(parts)


def normalize_identity_route(value: Any) -> str:
    text = str(value or "").strip()
    if not text or text.lower() == "none":
        return ""
    if text.startswith("http://") or text.startswith("https://"):
        text = route_from_url(text)
    text = text.strip()
    if len(text) > 1:
        text = text.rstrip("/")
    return text.lower()


def normalize_identity_url(value: Any) -> str:
    text = str(value or "").strip()
    if not text or text.lower() == "none":
        return ""
    parsed = urlparse(text)
    if parsed.scheme and parsed.netloc:
        path = parsed.path.rstrip("/") if parsed.path and parsed.path != "/" else parsed.path
        return parsed._replace(scheme=parsed.scheme.lower(), netloc=parsed.netloc.lower(), path=path).geturl().lower()
    if len(text) > 1:
        text = text.rstrip("/")
    return text.lower()


def is_login_page_identity(route: Any, url: Any, feature_type: Any) -> bool:
    if normalize_feature_type(feature_type) == "login":
        return True
    for value in (route, url):
        text = str(value or "").strip().lower()
        if not text:
            continue
        parsed = urlparse(text)
        path = parsed.path.lower() if parsed.scheme else text.split("?", 1)[0]
        clean_path = path.strip("/")
        segments = [segment for segment in clean_path.split("/") if segment]
        last_segment = segments[-1] if segments else clean_path
        if clean_path in {"login", "signin", "sign-in", "登录"} or last_segment in {
            "login",
            "signin",
            "sign-in",
            "登录",
        }:
            return True
    return False


def key(prefix: str, value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() == "none":
        return None
    return f"{prefix}:{text}".lower()


def batch_user_prompt(user_prompt: str | None, index: int, total: int) -> str:
    suffix = (
        f"\n当前是第 {index}/{total} 个页面。"
        "请只分析 context.current_page 中这个页面对应的截图、页面文字、按钮入口和 api_calls，"
        "不要生成其他页面的功能。"
    )
    return f"{user_prompt or '请按默认策略生成。'}{suffix}"


def chunks(rows: list[dict[str, Any]], size: int) -> list[list[dict[str, Any]]]:
    if not rows:
        return []
    return [rows[index : index + size] for index in range(0, len(rows), size)]


def first(value: Any) -> Any:
    return value[0] if isinstance(value, list) and value else None


def is_strategy_for_web(row: dict[str, Any]) -> bool:
    data = row.get("data") if isinstance(row.get("data"), dict) else {}
    domain = str(data.get("domain") or "").upper()
    kind = str(data.get("kind") or "")
    return domain in {"WEB", "COMMON", ""} and kind in {"design_strategy", "case_template", ""}


def sanitize_ai_value(value: Any) -> Any:
    """Mask secrets before data is persisted or sent to the model."""

    if isinstance(value, dict):
        result = {}
        for key_name, item in value.items():
            lower_key = str(key_name).lower()
            if any(marker in lower_key for marker in SENSITIVE_MARKERS):
                result[key_name] = "***"
            else:
                result[key_name] = sanitize_ai_value(item)
        return result
    if isinstance(value, list):
        return [sanitize_ai_value(item) for item in value]
    if isinstance(value, str):
        return sanitize_text(value)
    return value


def sanitize_text(value: str) -> str:
    text = value
    for marker in SENSITIVE_MARKERS:
        text = re.sub(
            rf"({re.escape(marker)}\s*[:=]\s*)([^,\s;，；]+)",
            rf"\1***",
            text,
            flags=re.I,
        )
    if len(text) > 4000:
        return f"{text[:4000]}...<truncated>"
    return text


def preview_prompt(prompt: dict[str, str]) -> dict[str, str]:
    return {
        "system": prompt["system"],
        "user": prompt["user"][:12000],
    }


def list_dicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def strategy_ids(value: Any) -> list[int]:
    values = value if isinstance(value, list) else [value]
    result: list[int] = []
    for item in values:
        try:
            result.append(int(item))
        except (TypeError, ValueError):
            continue
    return result


def int_or_default(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def bool_or_default(value: Any, default: bool) -> bool:
    if value in (None, ""):
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return default


def optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def int_list(value: Any) -> list[int]:
    if value in (None, ""):
        return []
    raw_items = value if isinstance(value, list) else [value]
    result: list[int] = []
    for item in raw_items:
        try:
            numeric = int(item)
        except (TypeError, ValueError):
            continue
        if numeric > 0 and numeric not in result:
            result.append(numeric)
    return result


def exception_message(exc: Exception) -> str:
    detail = getattr(exc, "detail", None)
    if detail:
        return str(detail)
    text = str(exc)
    return text if text else exc.__class__.__name__


def short_text(value: Any, limit: int) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if len(text) <= limit:
        return text
    return f"{text[:limit]}..."


def route_from_url(url: str) -> str:
    match = re.match(r"^https?://[^/]+(?P<path>/.*)$", url)
    return match.group("path") if match else url


def looks_like_api_path(value: Any) -> bool:
    text = str(value or "").strip().lower()
    if not text:
        return False
    parsed = urlparse(text)
    path = parsed.path.lower() if parsed.scheme else text.split("?", 1)[0]
    return any(marker in path for marker in ("/api/", "/dev-api/", "/prod-api/", "/openapi", "/graphql"))


def join_url(base_url: str, route: str) -> str:
    if not base_url:
        return route
    if route.startswith("http://") or route.startswith("https://"):
        return route
    return urljoin(base_url.rstrip("/") + "/", route.lstrip("/"))
