from __future__ import annotations

import json
import time
from typing import Any
from urllib.error import HTTPError
from urllib.parse import quote, urlencode, urlparse
from urllib.request import Request, urlopen

from app.repositories.interfaces import ResourceRepository
from app.scheduler.jobs.case_execution_base import CaseExecutionBase
from app.services.project_auth_service import ProjectAuthService


class ApiCaseExecutor(CaseExecutionBase):
    """Execute API test cases and persist execution records."""

    def __init__(self, repository: ResourceRepository) -> None:
        super().__init__("API", repository)

    def execute(self, case: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        started_at = time.perf_counter()
        request_info: dict[str, Any] = {}
        response_status: int | None = None
        response_headers: dict[str, str] = {}
        response_body = ""
        assertion_results: list[dict[str, Any]] = []
        error_message: str | None = None

        try:
            request_info = self._build_api_request(case, payload)
            response_status, response_headers, response_body = self._send_http_request(request_info)
            duration_ms = self.duration_ms(started_at)
            assertion_results = self._assert_response(
                self.case_assertions(case),
                response_status,
                duration_ms,
                response_body,
            )
            passed = all(item.get("passed") for item in assertion_results)
            record_status = "success" if passed else "failed"
            description = "执行通过" if passed else "断言失败"
        except Exception as exc:  # noqa: BLE001 - execution records must capture runtime failures.
            duration_ms = self.duration_ms(started_at)
            record_status = "failed"
            error_message = str(exc)
            description = error_message

        return self.repository.create(
            "execution_records",
            {
                "name": f"API 用例执行 - {case['name']}",
                "project_id": case.get("project_id") or payload.get("project_id"),
                "description": description,
                "status": record_status,
                "data": {
                    "case_id": case["id"],
                    "case_type": self.case_type,
                    "mode": payload.get("mode", "local_headless"),
                    "request": request_info,
                    "response_status": response_status,
                    "response_headers": response_headers,
                    "response_body": self._truncate(response_body),
                    "duration_ms": duration_ms,
                    "assertions": assertion_results,
                    "error": error_message,
                },
            },
        )

    def _build_api_request(self, case: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        case_data = self.case_data(case)
        legacy_request = case_data.get("request") if isinstance(case_data.get("request"), dict) else {}
        request_spec = {**legacy_request, **case_data}
        request_spec.pop("request", None)
        self._apply_runtime_overrides(request_spec, payload)
        interface = self._interface(case.get("source_id"))
        interface_data = interface.get("data", {}) if interface else {}

        project_id = case.get("project_id") or payload.get("project_id")
        base_url = self.project_base_url(project_id)
        if not base_url:
            raise ValueError("项目未配置项目地址，无法执行 API 用例")

        method = str(request_spec.get("method") or interface_data.get("method") or "GET").upper()
        path = str(request_spec.get("path") or interface_data.get("path") or case.get("name") or "")
        if not path:
            raise ValueError("用例缺少接口路径")

        headers = self._as_string_map(request_spec.get("headers"))
        query = self._as_dict(request_spec.get("query"))
        body = self._as_dict(request_spec.get("body"))
        content_type = str(request_spec.get("content_type") or interface_data.get("content_type") or "").strip()
        if content_type and not self._has_header(headers, "content-type"):
            headers["Content-Type"] = content_type

        path_params: dict[str, Any] = {}
        cookies: dict[str, Any] = {}
        self._apply_params(
            request_spec.get("params"),
            case.get("source_id"),
            project_id,
            method,
            query,
            body,
            headers,
            path_params,
            cookies,
        )
        self._apply_auth(
            payload.get("auth_id") or request_spec.get("auth_id") or interface_data.get("auth_id"),
            headers,
            query,
        )

        if cookies:
            cookie_value = "; ".join(f"{key}={value}" for key, value in cookies.items())
            headers["Cookie"] = "; ".join(filter(None, [headers.get("Cookie"), cookie_value]))

        resolved_path = self._fill_path_params(path, path_params)
        api_base_path = (
            request_spec.get("api_base_path")
            or interface_data.get("api_base_path")
            or self._project_api_base_path(project_id)
            or self._latest_import_api_base_path(project_id)
            or ""
        )
        url = self.join_url(base_url, resolved_path, str(api_base_path))
        if query:
            url = f"{url}{'&' if '?' in url else '?'}{urlencode(self._query_values(query), doseq=True)}"

        return {
            "method": method,
            "url": url,
            "base_url": base_url,
            "api_base_path": api_base_path,
            "path": resolved_path,
            "headers": headers,
            "query": query,
            "body": body,
            "timeout": int(payload.get("config", {}).get("timeout", 15))
            if isinstance(payload.get("config"), dict)
            else 15,
        }

    def _apply_runtime_overrides(self, request_spec: dict[str, Any], payload: dict[str, Any]) -> None:
        """Apply execution-only request overrides from dashboard payloads.

        The execution dashboard lets users edit a parameter JSON before running
        a formal case. Keeping the override in ``config`` avoids mutating the
        saved formal case while still reusing the normal scheduler executor.
        """

        config = payload.get("config")
        if not isinstance(config, dict):
            return

        params = config.get("params")
        if isinstance(params, dict):
            request_spec["params"] = params

        for key in ("headers", "query", "body"):
            value = config.get(key)
            if isinstance(value, dict):
                request_spec[key] = value

    def _apply_params(
        self,
        params: Any,
        interface_id: Any,
        project_id: Any,
        method: str,
        query: dict[str, Any],
        body: dict[str, Any],
        headers: dict[str, str],
        path_params: dict[str, Any],
        cookies: dict[str, Any],
    ) -> None:
        if not isinstance(params, dict):
            return

        fields = self._fields_for_interface(interface_id, project_id)
        field_locations = {
            str((field.get("data") or {}).get("name") or field.get("name")): str(
                (field.get("data") or {}).get("location") or "body"
            )
            for field in fields
        }
        default_location = "query" if method in {"GET", "DELETE"} else "body"
        for name, value in params.items():
            location = field_locations.get(str(name), default_location)
            if location == "query":
                query[name] = value
            elif location == "header":
                headers[str(name)] = str(value)
            elif location == "path":
                path_params[str(name)] = value
            elif location == "cookie":
                cookies[str(name)] = value
            else:
                body[str(name)] = value

    def _apply_auth(self, auth_id: Any, headers: dict[str, str], query: dict[str, Any]) -> None:
        if not auth_id:
            return
        auth_headers = ProjectAuthService(self.repository).auth_headers(auth_id)
        if auth_headers:
            headers.update(auth_headers)
            return
        auth = self.repository.get("project_auth", int(auth_id))
        data = auth.get("data") if auth else {}
        token = (data or {}).get("token") or (data or {}).get("access_token") or (data or {}).get("value")
        if token and not (data or {}).get("header_name"):
            query["api_key"] = token

    def _send_http_request(self, request_info: dict[str, Any]) -> tuple[int, dict[str, str], str]:
        method = str(request_info["method"]).upper()
        headers = dict(request_info.get("headers") or {})
        body = request_info.get("body")
        data = self._body_bytes(method, headers, body)
        request_info["headers"] = headers
        request = Request(str(request_info["url"]), data=data, headers=headers, method=method)
        try:
            with urlopen(request, timeout=int(request_info.get("timeout") or 15)) as response:
                return (
                    int(response.status),
                    dict(response.headers.items()),
                    self._decode_body(response.read(), response.headers.get_content_charset()),
                )
        except HTTPError as exc:
            charset = exc.headers.get_content_charset() if exc.headers else None
            return int(exc.code), dict(exc.headers.items()), self._decode_body(exc.read(), charset)

    def _body_bytes(self, method: str, headers: dict[str, str], body: Any) -> bytes | None:
        if method in {"GET", "HEAD"}:
            return None
        if body in (None, ""):
            return None
        content_type = next(
            (value for key, value in headers.items() if key.lower() == "content-type"),
            "application/json",
        )
        if not any(key.lower() == "content-type" for key in headers):
            headers["Content-Type"] = content_type
        if isinstance(body, bytes):
            return body
        if "application/x-www-form-urlencoded" in content_type and isinstance(body, dict):
            return urlencode(self._query_values(body), doseq=True).encode("utf-8")
        if isinstance(body, (dict, list)):
            return json.dumps(body, ensure_ascii=False).encode("utf-8")
        return str(body).encode("utf-8")

    def _assert_response(
        self,
        assertions: list[dict[str, Any]],
        response_status: int | None,
        duration_ms: int,
        response_body: str,
    ) -> list[dict[str, Any]]:
        if not assertions:
            passed = response_status is not None and 200 <= response_status < 400
            return [{"type": "http_status", "passed": passed, "actual": response_status, "expected": "2xx/3xx"}]

        results: list[dict[str, Any]] = []
        for assertion in assertions:
            assertion_type = str(assertion.get("type") or "unknown")
            if assertion_type == "status":
                expected = self.to_int(assertion.get("expected"))
                passed = response_status == expected
                results.append({"type": assertion_type, "passed": passed, "actual": response_status, "expected": expected})
            elif assertion_type in {"response_time", "duration"}:
                operator = str(assertion.get("operator") or "<=")
                expected = self.to_int(assertion.get("expected"), 3000)
                passed = self._compare(duration_ms, operator, expected)
                results.append({"type": assertion_type, "passed": passed, "actual": duration_ms, "expected": expected})
            elif assertion_type in {"body_contains", "message_contains"}:
                expected = str(assertion.get("expected") or "")
                passed = expected in response_body
                results.append({"type": assertion_type, "passed": passed, "expected": expected})
            else:
                results.append({"type": assertion_type, "passed": True, "message": "当前断言类型暂按通过记录"})
        return results

    def _interface(self, source_id: Any) -> dict[str, Any] | None:
        if not source_id:
            return None
        return self.repository.get("api_interfaces", int(source_id))

    def _fields_for_interface(self, interface_id: Any, project_id: Any) -> list[dict[str, Any]]:
        if not interface_id:
            return []
        rows, _ = self.repository.list("api_fields", project_id=project_id, page_size=10000)
        return [
            item
            for item in rows
            if str((item.get("data") or {}).get("interface_id")) == str(interface_id)
        ]

    def _project_api_base_path(self, project_id: Any) -> str:
        if not project_id:
            return ""
        project = self.repository.get("projects", int(project_id))
        data = project.get("data") if project else {}
        return str((data or {}).get("api_base_path") or "").strip()

    def _latest_import_api_base_path(self, project_id: Any) -> str:
        if not project_id:
            return ""
        tasks, _ = self.repository.list("api_import_tasks", project_id=int(project_id), page_size=20)
        for task in tasks:
            data = task.get("data") or {}
            source = data.get("source")
            if data.get("source_type") != "url" or not isinstance(source, str):
                continue
            parsed = urlparse(source)
            parent = parsed.path.rsplit("/", 1)[0].strip("/")
            if parent:
                return f"/{parent}"
        return ""

    def _fill_path_params(self, path: str, values: dict[str, Any]) -> str:
        result = path
        for key, value in values.items():
            encoded = quote(str(value), safe="")
            result = result.replace(f"{{{key}}}", encoded).replace(f":{key}", encoded)
        return result

    def _as_dict(self, value: Any) -> dict[str, Any]:
        return dict(value) if isinstance(value, dict) else {}

    def _as_string_map(self, value: Any) -> dict[str, str]:
        return {str(key): str(item) for key, item in value.items()} if isinstance(value, dict) else {}

    def _has_header(self, headers: dict[str, str], name: str) -> bool:
        return any(key.lower() == name.lower() for key in headers)

    def _query_values(self, values: dict[str, Any]) -> dict[str, Any]:
        normalized: dict[str, Any] = {}
        for key, value in values.items():
            if isinstance(value, bool):
                normalized[key] = "true" if value else "false"
            elif isinstance(value, (dict, list)):
                normalized[key] = json.dumps(value, ensure_ascii=False)
            else:
                normalized[key] = value
        return normalized

    def _decode_body(self, raw: bytes, charset: str | None) -> str:
        return raw.decode(charset or "utf-8", errors="replace")

    def _truncate(self, value: str, limit: int = 8000) -> str:
        return value if len(value) <= limit else f"{value[:limit]}...<truncated>"

    def _compare(self, actual: int, operator: str, expected: int | None) -> bool:
        if expected is None:
            return True
        if operator == "<":
            return actual < expected
        if operator == ">":
            return actual > expected
        if operator == ">=":
            return actual >= expected
        if operator == "==":
            return actual == expected
        return actual <= expected
