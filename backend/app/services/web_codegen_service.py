"""Business orchestration for Playwright codegen sessions."""

from __future__ import annotations

from urllib.parse import urljoin

from app.core.exceptions import (
    AutomationEngineError,
    BusinessRuleError,
    ResourceNotFoundError,
)
from app.repositories.interfaces import ResourceRepository
from app.services.project_auth_service import ProjectAuthService
from app.utils.playwright_codegen_runner import PlaywrightCodegenRunner


def resolve_codegen_target_url(
    repository: ResourceRepository,
    page: dict[str, object],
    target_url: str,
) -> str:
    """Resolve a relative page route against the owning project's base URL."""

    raw_page_data = page.get("data")
    page_data = raw_page_data if isinstance(raw_page_data, dict) else {}
    raw_url = str(target_url or page_data.get("url") or page_data.get("route") or "").strip()
    if not raw_url:
        raise BusinessRuleError("页面地址为空，无法启动 codegen")
    if raw_url.startswith(("http://", "https://")):
        return raw_url

    project_id = page.get("project_id")
    project = repository.get("projects", int(project_id)) if project_id else None
    raw_project_data = project.get("data") if project else {}
    project_data = raw_project_data if isinstance(raw_project_data, dict) else {}
    base_url = str(
        project_data.get("base_url") or (project or {}).get("description") or ""
    ).strip()
    if not base_url:
        raise BusinessRuleError("页面地址不是完整 URL，且项目未配置 base_url")
    return urljoin(base_url.rstrip("/") + "/", raw_url.lstrip("/"))


class WebCodegenService:
    """Validate page ownership and coordinate codegen session lifecycle."""

    def __init__(self, runner: PlaywrightCodegenRunner | None = None) -> None:
        self.runner = runner or PlaywrightCodegenRunner()

    def start(
        self,
        repository: ResourceRepository,
        *,
        page_id: int,
        target_url: str,
        project_id: int | None,
        feature_type: str | None,
        feature_name: str | None,
    ) -> dict[str, object]:
        """Start a codegen session for a validated page resource."""

        page = repository.get("web_pages", page_id)
        if not page:
            raise ResourceNotFoundError("页面功能不存在")
        page_project_id = page.get("project_id")
        if project_id and page_project_id and int(page_project_id) != project_id:
            raise BusinessRuleError("页面功能不属于当前项目")

        raw_page_data = page.get("data")
        page_data = raw_page_data if isinstance(raw_page_data, dict) else {}
        auth_id = page_data.get("auth_id")
        cookies = ProjectAuthService(repository).web_cookies(auth_id)
        resolved_target_url = resolve_codegen_target_url(repository, page, target_url)
        metadata = {
            "project_id": page_project_id or project_id,
            "page_id": page_id,
            "page_name": feature_name or page.get("name"),
            "feature_type": feature_type or page_data.get("feature_type"),
            "target_url": resolved_target_url,
        }
        try:
            return self.runner.start(resolved_target_url, cookies, metadata)
        except (RuntimeError, OSError) as exc:
            raise AutomationEngineError(str(exc)) from exc

    def status(self, session_id: str) -> dict[str, object]:
        """Return current codegen state or a domain-level missing error."""

        try:
            return self.runner.status(session_id)
        except ValueError as exc:
            raise ResourceNotFoundError(str(exc)) from exc

    def stop(self, session_id: str) -> dict[str, object]:
        """Stop a codegen session or report that it does not exist."""

        try:
            return self.runner.stop(session_id)
        except ValueError as exc:
            raise ResourceNotFoundError(str(exc)) from exc
