from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import yaml

from app.repositories.interfaces import ResourceRepository
from app.schemas.tasks import OpenApiImportJobPayload
from app.services.api_testing_service import ApiTestingService


MAX_OPENAPI_BYTES = 10 * 1024 * 1024


class OpenApiImportTaskService:
    """Manage OpenAPI import task records and execution rules.

    The scheduler layer owns task triggering. This service owns task status
    transitions, source loading, parsing, and persistence orchestration.
    """

    def __init__(self, repository: ResourceRepository) -> None:
        self.repository = repository

    def create_file_task(self, project_id: int, filename: str, overwrite: bool) -> dict[str, Any]:
        """Create a queued OpenAPI file import task."""

        return self._create_task(project_id, "file", filename, overwrite)

    def create_url_task(self, project_id: int, url: str, overwrite: bool) -> dict[str, Any]:
        """Create a queued OpenAPI URL import task."""

        self._validate_url(url)
        return self._create_task(project_id, "url", url, overwrite)

    def get_task(self, task_id: int) -> dict[str, Any]:
        """Return an import task or raise a domain-level validation error."""

        task = self.repository.get("api_import_tasks", task_id)
        if not task:
            raise ValueError("导入任务不存在")
        return task

    def run_task(self, task_id: int, payload: OpenApiImportJobPayload) -> None:
        """Execute a queued OpenAPI import task.

        Scheduler jobs call this method so all business work remains in the
        service layer instead of being embedded in the job trigger.
        """

        task = self.repository.get("api_import_tasks", task_id)
        if not task:
            return
        try:
            self._update_task(task, "running", "正在获取 OpenAPI 内容")
            task_data = task.get("data") if isinstance(task.get("data"), dict) else {}
            content = self._load_content(payload, str(task_data.get("source") or ""))
            task = self.repository.get("api_import_tasks", task_id) or task
            self._update_task(task, "running", "正在解析并保存接口和字段")
            result = ApiTestingService(self.repository).import_openapi(
                int(task["project_id"]),
                content,
                bool((task.get("data") or {}).get("overwrite", True)),
                source_url=payload.url,
                source_type=str(task_data.get("source_type") or "inline"),
                source_name=str(task_data.get("source") or ""),
            )
            task = self.repository.get("api_import_tasks", task_id) or task
            self._update_task(task, "success", "导入成功", result=result)
        except Exception as exc:
            task = self.repository.get("api_import_tasks", task_id)
            if task:
                self._update_task(task, "failed", "导入失败", error=str(exc))
            raise

    def _create_task(self, project_id: int, source_type: str, source: str, overwrite: bool) -> dict[str, Any]:
        return self.repository.create(
            "api_import_tasks",
            {
                "name": f"OpenAPI 导入 - {source}",
                "project_id": project_id,
                "status": "queued",
                "data": {
                    "source_type": source_type,
                    "source": source,
                    "overwrite": overwrite,
                    "progress": "等待执行",
                    "result": None,
                    "error": None,
                },
            },
        )

    def _update_task(
        self,
        task: dict[str, Any],
        status_text: str,
        progress: str,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        data = dict(task.get("data") or {})
        data["progress"] = progress
        if result is not None:
            data["result"] = result
            data["error"] = None
        if error is not None:
            data["error"] = error
        self.repository.update("api_import_tasks", int(task["id"]), {"status": status_text, "data": data})

    def _load_content(self, payload: OpenApiImportJobPayload, source: str = "") -> dict[str, Any]:
        if payload.url:
            return self._load_openapi_from_url(payload.url)
        return self._decode_openapi(payload.raw or b"", f"OpenAPI 文件解析失败：{source}" if source else "OpenAPI 文件解析失败")

    def _validate_url(self, url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("OpenAPI URL 仅支持 http/https")

    def _load_openapi_from_url(self, url: str) -> dict[str, Any]:
        self._validate_url(url)
        request = Request(url, headers={"User-Agent": "Autotest-OpenAPI-Importer/1.0"})
        try:
            with urlopen(request, timeout=30) as response:
                raw = response.read(MAX_OPENAPI_BYTES + 1)
        except HTTPError as exc:
            raise ValueError(f"OpenAPI URL 请求失败：HTTP {exc.code}") from exc
        except URLError as exc:
            raise ValueError(f"OpenAPI URL 请求失败：{exc.reason}") from exc
        except TimeoutError as exc:
            raise ValueError("OpenAPI URL 请求超时") from exc
        if len(raw) > MAX_OPENAPI_BYTES:
            raise ValueError("OpenAPI 内容超过 10 MB 限制")
        return self._decode_openapi(raw, "OpenAPI URL 返回内容不是合法 JSON/YAML")

    def _decode_openapi(self, raw: bytes, error_message: str) -> dict[str, Any]:
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ValueError(error_message) from exc
        try:
            content = json.loads(text)
        except json.JSONDecodeError:
            try:
                content = yaml.safe_load(text)
            except yaml.YAMLError as exc:
                raise ValueError(error_message) from exc
        if not isinstance(content, dict):
            raise ValueError("OpenAPI 内容必须是对象")
        return content
