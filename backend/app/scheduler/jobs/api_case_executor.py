from __future__ import annotations

import json
import time
from typing import Any
from urllib.error import HTTPError
from urllib.parse import quote, urlencode, urlparse
from urllib.request import Request, urlopen

from jsonpointer import JsonPointerException, resolve_pointer

from app.repositories.interfaces import ResourceRepository
from app.scheduler.jobs.case_execution_base import CaseExecutionBase
from app.services.project_auth_service import ProjectAuthService
from app.utils.api_query_assertion import assert_query_result
from app.utils.api_rejection import assert_api_rejection
from app.utils.api_response import extract_response_code


class ApiCaseExecutor(CaseExecutionBase):
    """Execute API test cases and persist execution records."""

    def __init__(self, repository: ResourceRepository) -> None:
        super().__init__("API", repository)

    def execute(self, case: dict[str, Any], payload: dict[str, Any], *,
                response_capture: dict[str, Any] | None = None, persist_record: bool = True) -> dict[str, Any]:
        started_at = time.perf_counter()
        request_info: dict[str, Any] = {}
        response_status: int | None = None
        response_headers: dict[str, str] = {}
        response_body = ""
        assertion_results: list[dict[str, Any]] = []
        error_message: str | None = None

        try:
            case, payload = self.prepare_execution(case, payload)
            request_info = self._build_api_request(case, payload)
            response_status, response_headers, response_body = self._send_http_request(request_info)
            duration_ms = self.duration_ms(started_at)
            assertion_results = self._assert_response(
                self.case_assertions(case),
                response_status,
                response_headers,
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

        if response_capture is not None:
            response_capture.update(status=response_status, headers=response_headers, body=response_body)
        record = {
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
                    "response_code": extract_response_code(response_body),
                    "duration_ms": duration_ms,
                    "assertions": assertion_results,
                    "dynamic_values": case.get("_dynamic_values", {}),
                    "error": error_message,
                },
            }
        return self.repository.create("execution_records", record) if persist_record else record

    def _build_api_request(self, case: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        case_data = self.case_data(case)
        legacy_request = case_data.get("request") if isinstance(case_data.get("request"), dict) else {}
        request_spec = {**legacy_request, **case_data}
        request_spec.pop("request", None)
        self._apply_runtime_overrides(request_spec, payload)
        self._validate_dynamic_params(case, request_spec)
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
        body = request_spec.get("body")
        if body is None:
            body = {}
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
        if not bool(request_spec.get("skip_auth")):
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

        for key in ("headers", "query"):
            value = config.get(key)
            if isinstance(value, dict):
                request_spec[key] = value
        if "body" in config:
            request_spec["body"] = config.get("body")

    def _validate_dynamic_params(self, case: dict[str, Any], request_spec: dict[str, Any]) -> None:
        snapshot = case.get("_dynamic_values") or {}
        paths = snapshot.get("templates") or {}
        params = request_spec.get("params")
        if not paths or not isinstance(params, dict):
            return
        for field in self._fields_for_interface(case.get("source_id"), case.get("project_id")):
            data = field.get("data") or {}
            name = str(data.get("name") or field.get("name"))
            if name not in params or not any(path in paths for path in (f"$.data.params.{name}", f"$.data.request.params.{name}", f"$.config.params.{name}")):
                continue
            schema = data.get("schema") if isinstance(data.get("schema"), dict) else {}
            field_type = str(data.get("field_type") or data.get("type") or schema.get("type") or "string")
            value = params[name]
            if field_type in {"integer", "number", "boolean"} and isinstance(value, str):
                raise ValueError(f"Dynamic value for {name} is text but the field type is {field_type}")
            maximum = data.get("maxLength", schema.get("maxLength"))
            if maximum is not None and isinstance(value, str) and len(value) > int(maximum):
                raise ValueError(f"Dynamic value for {name} exceeds maxLength {maximum}")

    def _apply_params(
        self,
        params: Any,
        interface_id: Any,
        project_id: Any,
        method: str,
        query: dict[str, Any],
        body: Any,
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
            elif isinstance(body, dict):
                body[str(name)] = value

    def _apply_auth(self, auth_id: Any, headers: dict[str, str], query: dict[str, Any]) -> None:
        if not auth_id:
            return
        auth = self.repository.get("project_auth", int(auth_id))
        if not auth:
            raise ValueError("所选 API 认证配置不存在，请重新选择 Token")
        auth_headers = ProjectAuthService(self.repository).auth_headers(auth_id)
        if auth_headers:
            for name, value in auth_headers.items():
                for existing in list(headers):
                    if existing.lower() == name.lower():
                        del headers[existing]
                headers[name] = value
            return
        data = auth.get("data") or {}
        token = (data or {}).get("token") or (data or {}).get("access_token") or (data or {}).get("value")
        if token and not (data or {}).get("header_name"):
            query["api_key"] = token
            return
        raise ValueError("所选 API 认证没有有效的 Token 或 Cookie，请刷新认证信息")

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
        response_headers: dict[str, str],
        duration_ms: int,
        response_body: str,
    ) -> list[dict[str, Any]]:
        if not assertions:
            passed = response_status is not None and 200 <= response_status < 400
            return [{"type": "http_status", "passed": passed, "actual": response_status, "expected": "2xx/3xx"}]

        results: list[dict[str, Any]] = []
        for assertion in assertions:
            assertion_type = str(assertion.get("type") or "unknown")
            if assertion_type == "api_rejection":
                results.append(assert_api_rejection(response_status, response_body, assertion.get("expected"),
                                                    assertion.get("allowed_business_errors")))
            elif assertion_type == "json_query_result":
                results.append(assert_query_result(response_body, assertion))
            elif assertion_type == "status":
                expected = self.to_int(assertion.get("expected"))
                passed = response_status == expected
                results.append({"type": assertion_type, "passed": passed, "actual": response_status, "expected": expected})
            elif assertion_type == "status_not_5xx":
                passed = response_status is not None and response_status < 500
                results.append({"type": assertion_type, "passed": passed, "actual": response_status, "expected": "not 5xx"})
            elif assertion_type in {"status_in", "status_class"}:
                raw_expected = assertion.get("expected")
                expected_values = raw_expected if isinstance(raw_expected, list) else [raw_expected]
                passed = response_status is not None and any(
                    self._status_matches(response_status, value) for value in expected_values
                )
                results.append({"type": assertion_type, "passed": passed, "actual": response_status, "expected": raw_expected})
            elif assertion_type in {"response_time", "duration"}:
                operator = str(assertion.get("operator") or "<=")
                expected = self.to_int(assertion.get("expected"), 3000)
                passed = self._compare(duration_ms, operator, expected)
                results.append({"type": assertion_type, "passed": passed, "actual": duration_ms, "expected": expected})
            elif assertion_type in {"body_contains", "message_contains"}:
                expected = str(assertion.get("expected") or "")
                passed = expected in response_body
                results.append({"type": assertion_type, "passed": passed, "expected": expected})
            elif assertion_type in {"json_equals", "json_pointer"}:
                expected, actual, passed = assertion.get("expected"), None, False
                try:
                    actual = json.loads(response_body)
                    if assertion_type == "json_pointer":
                        actual = resolve_pointer(actual, str(assertion.get("path") or ""))
                    else:
                        path = str(assertion.get("path") or "").removeprefix("$.")
                        for part in path.split(".") if path else []:
                            actual = actual[int(part)] if isinstance(actual, list) else actual[part]
                    passed = actual == expected
                except (ValueError, KeyError, IndexError, TypeError, JsonPointerException):
                    pass
                results.append({"type": assertion_type, "passed": passed, "actual": actual, "expected": expected})
            elif assertion_type == "content_type_in":
                actual = next(
                    (value for key, value in response_headers.items() if key.lower() == "content-type"),
                    "",
                ).split(";", 1)[0].strip().lower()
                raw_expected = assertion.get("expected")
                expected_values = raw_expected if isinstance(raw_expected, list) else [raw_expected]
                normalized = [str(item).split(";", 1)[0].strip().lower() for item in expected_values if item]
                passed = bool(actual) and actual in normalized
                results.append({"type": assertion_type, "passed": passed, "actual": actual, "expected": raw_expected})
            elif assertion_type == "response_header":
                name = str(assertion.get("name") or assertion.get("expected") or "")
                actual = next((value for key, value in response_headers.items() if key.lower() == name.lower()), None)
                passed = actual is not None
                results.append({"type": assertion_type, "passed": passed, "actual": actual, "expected": name})
            else:
                results.append({"type": assertion_type, "passed": False, "message": "不支持的断言类型"})
        return results

    def _status_matches(self, actual: int, expected: Any) -> bool:
        text = str(expected or "").strip().upper()
        if text.isdigit():
            return actual == int(text)
        if len(text) == 3 and text[0].isdigit() and text[1:] == "XX":
            return actual // 100 == int(text[0])
        if len(text) == 3 and text.endswith("X") and text[:2].isdigit():
            return actual // 10 == int(text[:2])
        if text == "DEFAULT":
            return True
        return False

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
