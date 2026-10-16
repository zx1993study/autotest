from __future__ import annotations

from urllib.parse import urljoin, urlsplit, urlunsplit

from app.core.exceptions import BusinessRuleError
from app.repositories.interfaces import ResourceRepository


def resolve_web_target_url(
    repository: ResourceRepository,
    page: dict[str, object],
    target_url: str = "",
) -> str:
    """Resolve a page route against the owning project's base URL."""

    raw_page_data = page.get("data")
    page_data = raw_page_data if isinstance(raw_page_data, dict) else {}
    raw_url = str(target_url or page_data.get("url") or page_data.get("route") or "").strip()
    if not raw_url:
        raise BusinessRuleError("页面地址为空，无法打开目标页面")
    if raw_url.startswith(("http://", "https://")):
        location = urlsplit(raw_url)
        route = str(page_data.get("route") or "").strip()
        if not target_url and route.startswith("/") and route != "/" and location.path in {"", "/"} and not location.fragment:
            rows, _ = repository.list("web_page_groups", project_id=page.get("project_id"), page_size=10000)
            hash_router = any(
                urlsplit(str((row.get("data") or {}).get("url") or "")).netloc == location.netloc
                and urlsplit(str((row.get("data") or {}).get("url") or "")).fragment.startswith("/")
                for row in rows
            )
            return urlunsplit((location.scheme, location.netloc, location.path or "/", "", route)) if hash_router else urljoin(raw_url, route)
        return raw_url

    project_id = page.get("project_id")
    project = repository.get("projects", int(project_id)) if project_id else None
    raw_project_data = project.get("data") if project else {}
    project_data = raw_project_data if isinstance(raw_project_data, dict) else {}
    base_url = str(
        project_data.get("base_url")
        or project_data.get("project_url")
        or project_data.get("url")
        or ""
    ).strip()
    if not base_url:
        raise BusinessRuleError("页面地址不是完整 URL，且项目未配置 base_url")
    return urljoin(f"{base_url.rstrip('/')}/", raw_url.lstrip("/"))

