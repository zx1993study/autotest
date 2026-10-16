from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from pathlib import Path
import http.client
from urllib.parse import urlsplit


class AgentApiError(RuntimeError):
    """Raised when the remote platform rejects an Agent request."""


class AgentApiClient:
    """Small JSON client for Autotest platform APIs."""

    def __init__(self, server_url: str, token: str, timeout_sec: int = 30) -> None:
        normalized_url = server_url.rstrip("/")
        self.base_url = normalized_url if normalized_url.endswith("/api/v1") else f"{normalized_url}/api/v1"
        self.token = token
        self.timeout_sec = timeout_sec

    def get(self, path: str) -> Any:
        return self._request("GET", path)

    def post(self, path: str, payload: dict[str, Any]) -> Any:
        return self._request("POST", path, payload)

    def upload(self, path: str, filename: str, artifacts_dir: Path) -> dict:
        source = Path(filename).resolve()
        if not source.is_relative_to(artifacts_dir.resolve()) or source.suffix.lower() not in {".mp4", ".webm"}:
            raise AgentApiError("Invalid recording path")
        size = source.stat().st_size
        if not 0 < size <= 200 * 1024 * 1024:
            raise AgentApiError("Recording exceeds upload limit")
        import hashlib

        digest = hashlib.sha256()
        with source.open("rb") as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(chunk)
        url = urlsplit(f"{self.base_url}{path}&sha256={digest.hexdigest()}")
        cls = http.client.HTTPSConnection if url.scheme == "https" else http.client.HTTPConnection
        connection = cls(url.hostname, url.port, timeout=120)
        try:
            connection.putrequest("POST", f"{url.path}?{url.query}")
            connection.putheader("Authorization", f"Bearer {self.token}")
            connection.putheader("Content-Type", "video/webm" if source.suffix.lower() == ".webm" else "video/mp4")
            connection.putheader("Content-Length", str(size))
            connection.endheaders()
            with source.open("rb") as file:
                for chunk in iter(lambda: file.read(1024 * 1024), b""):
                    connection.send(chunk)
            response = connection.getresponse()
            value = json.loads(response.read())
            if response.status != 200 or value.get("code") not in (None, 0):
                raise AgentApiError(f"Artifact upload failed: HTTP {response.status}")
            return value["data"]
        finally:
            connection.close()

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
        url = f"{self.base_url}{path if path.startswith('/') else '/' + path}"
        body = json.dumps(payload or {}, ensure_ascii=False).encode("utf-8") if payload is not None else None
        request = Request(
            url,
            data=body,
            method=method,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        try:
            with urlopen(request, timeout=self.timeout_sec) as response:
                raw = response.read().decode("utf-8")
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise AgentApiError(f"平台请求失败 HTTP {exc.code}: {detail}") from exc
        except URLError as exc:
            raise AgentApiError(f"无法连接远程平台: {exc}") from exc
        data = json.loads(raw) if raw else {}
        if isinstance(data, dict) and data.get("code") not in (None, 0):
            raise AgentApiError(str(data.get("message") or "平台接口返回失败"))
        return data.get("data") if isinstance(data, dict) and "data" in data else data
