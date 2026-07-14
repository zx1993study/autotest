from __future__ import annotations

import time
from typing import Any

from app.core.exceptions import BusinessRuleError, ResourceNotFoundError
from app.repositories.interfaces import ResourceRepository
from app.services.auth_file_service import AuthFileService


class ProjectAuthService:
    def __init__(self, repository: ResourceRepository) -> None:
        self.repository = repository

    def list_options(self, project_id: int | None = None, login_case_type: str | None = None) -> list[dict[str, Any]]:
        rows, _ = self.repository.list("project_auth", project_id=project_id, page_size=500)
        login_case_type_text = str(login_case_type or "").strip().upper()
        if login_case_type_text:
            rows = [
                item
                for item in rows
                if str(self._record_data(item).get("login_case_type") or "").upper() == login_case_type_text
            ]
        return [
            {
                "id": item["id"],
                "name": item["name"],
            }
            for item in rows
        ]

    def list_web_login_case_options(self, project_id: int | None = None) -> list[dict[str, Any]]:
        """Return active web cases that can be used as login auth sources."""

        from app.services.test_case_service import TestCaseService

        rows, _ = TestCaseService("WEB", self.repository).list(keyword=None, project_id=project_id, page=1, page_size=1000)
        result: list[dict[str, Any]] = []
        for item in rows:
            if item.get("status") != "active":
                continue
            if not self.is_web_login_case(item):
                continue
            result.append(
                {
                    "id": item["id"],
                    "name": item["name"],
                    "project_id": item.get("project_id"),
                }
            )
        return result

    def generate_cookie_auth(self, payload: dict[str, Any]) -> dict[str, Any]:
        name = str(payload.get("name") or "").strip()
        if not name:
            raise BusinessRuleError("请输入鉴权名称")

        record_id = self._to_int(payload.get("record_id"))
        if not record_id:
            raise BusinessRuleError("请选择执行记录")

        record = self.repository.get("execution_records", record_id)
        if not record:
            raise ResourceNotFoundError("未找到执行记录")

        record_data = self._record_data(record)
        if str(record_data.get("case_type") or record.get("case_type") or "").upper() != "WEB":
            raise BusinessRuleError("只有 Web 用例支持生成 Cookie 鉴权")

        cookies = record_data.get("cookies")
        if not isinstance(cookies, list) or not cookies:
            auth_saved = record_data.get("auth_saved") if isinstance(record_data.get("auth_saved"), dict) else {}
            cookie_file = auth_saved.get("token_file")
            if cookie_file:
                cookies = AuthFileService().load_json(str(cookie_file)).get("cookies")
        if not isinstance(cookies, list) or not cookies:
            raise BusinessRuleError("执行记录中未找到 Cookie，请先重新执行登录用例")

        case_id = self._to_int(payload.get("case_id") or record_data.get("case_id") or record.get("case_id"))
        if not case_id:
            raise BusinessRuleError("执行记录缺少用例 ID")

        case = self.repository.get("web_test_cases", case_id)
        if not case:
            raise ResourceNotFoundError("未找到 Web 正式用例")
        if not self.is_web_login_case(case):
            raise BusinessRuleError("只有功能类型为登录的用例支持生成 Cookie")

        case = dict(case)
        case["project_id"] = case.get("project_id") or record.get("project_id") or record_data.get("project_id")
        return self.save_web_cookie_auth(
            case=case,
            cookies=cookies,
            auth_name=name,
            metadata={
                "source_record_id": record.get("id"),
                "url": record_data.get("url") or record_data.get("final_url"),
            },
            refresh_strategy="manual",
            description="从 Web 正式用例查看生成 Cookie",
            stable_filename=False,
        )

    def generate_token_auth(self, payload: dict[str, Any]) -> dict[str, Any]:
        name = str(payload.get("name") or "").strip()
        token = str(payload.get("token") or "").strip()
        if not name:
            raise BusinessRuleError("请输入鉴权名称")
        if not token:
            raise BusinessRuleError("请输入 Token")

        project_id = self._to_int(payload.get("project_id"))
        source_record_id = self._to_int(payload.get("source_record_id"))
        login_case_id = self._to_int(payload.get("login_case_id"))
        header_name = str(payload.get("header_name") or "Authorization")
        auth_type = str(payload.get("auth_type") or "bearer")
        login_case_type = str(payload.get("login_case_type") or "API").upper()
        target_auth_id = self._to_int(payload.get("target_auth_id"))
        existing = self._find_auth_for_case(
            project_id=project_id,
            login_case_type=login_case_type,
            login_case_id=login_case_id,
            auth_name=name,
            target_auth_id=target_auth_id,
        )
        existing_data = self._record_data(existing)
        filename = str(existing_data.get("token_file") or "")
        if not filename:
            filename = f"{self._safe_file_stem(name)}-{source_record_id or login_case_id or int(time.time())}.json"
        saved_at = int(time.time())
        filename = AuthFileService().save_json(
            filename,
            {
                "type": auth_type,
                "token": token,
                "project_id": project_id,
                "auth_name": str(existing.get("name") or name) if existing else name,
                "header_name": header_name,
                "source_record_id": source_record_id,
                "login_case_id": login_case_id,
                "saved_at": saved_at,
                "updated_at": saved_at,
            },
        )
        data = {
            **existing_data,
            "auth_type": auth_type,
            "login_case_type": login_case_type,
            "login_case_id": login_case_id,
            "source_record_id": source_record_id,
            "token_file": filename,
            "header_name": header_name,
            "token_source": "api_response",
            "refresh_strategy": str(
                payload.get("refresh_strategy") or existing_data.get("refresh_strategy") or "manual"
            ),
        }
        payload_data = {
            "name": str(existing.get("name") or name) if target_auth_id and existing else name,
            "project_id": project_id,
            "description": str(
                payload.get("description") or (existing or {}).get("description") or "从 API 响应 Token 保存"
            ),
            "status": "active",
            "data": data,
        }
        if existing:
            updated = self.repository.update("project_auth", int(existing["id"]), payload_data)
            return self._hide_token(updated or existing)
        return self._hide_token(self.repository.create("project_auth", payload_data))

    def auth_headers(self, auth_id: Any) -> dict[str, str]:
        auth = self._auth(auth_id)
        if not auth:
            return {}
        data = self._record_data(auth)
        auth_type = str(data.get("auth_type") or "").lower()
        header_name = str(data.get("header_name") or "Authorization")
        token = data.get("token") or data.get("access_token") or data.get("value")
        if not token and data.get("token_file"):
            token = self._token_from_file(str(data["token_file"]))

        if auth_type == "bearer" and token:
            token_text = str(token)
            return {header_name: token_text if token_text.lower().startswith("bearer ") else f"Bearer {token_text}"}
        if auth_type == "api_key" and token and header_name:
            return {header_name: str(token)}
        if auth_type == "cookie":
            cookie_header = self.cookie_header(auth_id)
            return {"Cookie": cookie_header} if cookie_header else {}
        if token and header_name:
            return {header_name: str(token)}
        return {}

    def web_cookies(self, auth_id: Any) -> list[dict[str, Any]]:
        auth = self._auth(auth_id)
        if not auth:
            return []
        data = self._record_data(auth)
        cookies = data.get("cookies")
        if not isinstance(cookies, list) and data.get("token_file"):
            cookies = AuthFileService().load_json(str(data["token_file"])).get("cookies")
        if not isinstance(cookies, list):
            return []
        return [item for item in cookies if isinstance(item, dict) and item.get("name") is not None]

    def cookie_header(self, auth_id: Any) -> str:
        cookies = self.web_cookies(auth_id)
        if cookies:
            return "; ".join(f"{item.get('name')}={item.get('value', '')}" for item in cookies)
        auth = self._auth(auth_id)
        data = self._record_data(auth)
        token = data.get("token") or data.get("value")
        return str(token) if token else ""

    def save_web_cookie_auth(
        self,
        case: dict[str, Any],
        cookies: list[Any],
        auth_name: str,
        metadata: dict[str, Any] | None = None,
        refresh_strategy: str = "manual",
        description: str = "Web 登录 Cookie 鉴权",
        stable_filename: bool = False,
    ) -> dict[str, Any]:
        if not cookies:
            return {}
        metadata = metadata or {}
        name = str(auth_name or "").strip()
        if not name:
            raise BusinessRuleError("请输入鉴权名称")

        target_auth_id = self._to_int(metadata.get("target_auth_id"))
        preserve_existing_name = bool(metadata.get("preserve_existing_name"))
        existing = self._find_auth_for_case(
            project_id=self._to_int(case.get("project_id")),
            login_case_type="WEB",
            login_case_id=self._to_int(case.get("id")),
            auth_name=name,
            target_auth_id=target_auth_id,
            auth_type="cookie",
        )
        existing_data = self._record_data(existing)
        resource_name = str(existing.get("name") or name) if existing and preserve_existing_name else name
        filename = str(existing_data.get("token_file") or "")
        filename_stem = self._safe_file_stem(name)
        if not filename and stable_filename:
            filename_stem = f"{filename_stem}-{case.get('id') or 'case'}"
        elif not filename:
            filename_stem = f"{filename_stem}-{case.get('id') or 'case'}-{int(time.time())}"
            filename = f"{filename_stem}.json"
        elif not AuthFileService().exists(filename):
            filename = AuthFileService().safe_filename(filename)

        saved_at = int(time.time())
        filename = AuthFileService().save_json(
            filename or f"{filename_stem}.json",
            {
                "type": "cookie",
                "case_id": case.get("id"),
                "project_id": case.get("project_id"),
                "auth_name": resource_name,
                "url": metadata.get("url"),
                "cookies": cookies,
                "source_record_id": metadata.get("source_record_id"),
                "saved_at": saved_at,
                "updated_at": saved_at,
            },
        )
        auth = self._upsert_cookie_auth(
            case=case,
            auth_name=resource_name,
            filename=filename,
            refresh_strategy=refresh_strategy,
            description=description,
            source_record_id=metadata.get("source_record_id"),
            existing=existing,
        )
        return {"auth_id": auth.get("id"), "name": resource_name, "token_file": filename}

    def is_web_login_case(self, case: dict[str, Any]) -> bool:
        page = self._source_page(case)
        page_data = self._record_data(page) if page else {}
        case_data = self._record_data(case)
        request = case_data.get("request") if isinstance(case_data.get("request"), dict) else {}
        markers = [
            page_data.get("feature_type"),
            page.get("name") if page else None,
            case.get("name"),
            case_data.get("feature_type"),
            request.get("feature_type") if isinstance(request, dict) else None,
        ]
        return any(str(item or "").lower() == "login" or "登录" in str(item or "") for item in markers)

    def _upsert_cookie_auth(
        self,
        case: dict[str, Any],
        auth_name: str,
        filename: str,
        refresh_strategy: str,
        description: str,
        source_record_id: Any = None,
        existing: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        project_id = case.get("project_id")
        existing = existing or self._find_auth_for_case(
            project_id=self._to_int(project_id),
            login_case_type="WEB",
            login_case_id=self._to_int(case.get("id")),
            auth_name=auth_name,
            auth_type="cookie",
        )
        existing_data = self._record_data(existing)
        data = {
            **existing_data,
            "auth_type": "cookie",
            "login_case_type": "WEB",
            "login_case_id": case.get("id"),
            "source_record_id": source_record_id,
            "token_file": filename,
            "token": "",
            "refresh_strategy": refresh_strategy,
        }
        payload = {
            "name": auth_name,
            "project_id": project_id,
            "description": description,
            "status": "active",
            "data": data,
        }
        if existing:
            updated = self.repository.update("project_auth", int(existing["id"]), payload)
            return updated or existing
        return self.repository.create("project_auth", payload)

    def _find_auth_for_case(
        self,
        project_id: int | None,
        login_case_type: str,
        login_case_id: int | None,
        auth_name: str,
        target_auth_id: int | None = None,
        auth_type: str | None = None,
    ) -> dict[str, Any] | None:
        """Find the auth row that should be updated before creating a new one.

        Refresh jobs pass ``target_auth_id`` so the selected row is updated
        directly. Manual saves fall back to the same login case, then the
        legacy name-based match to avoid creating duplicate auth resources.
        """

        normalized_type = str(login_case_type or "").upper()
        normalized_auth_type = str(auth_type or "").lower()
        if target_auth_id:
            target = self._auth(target_auth_id)
            if target and self._auth_matches(target, project_id, normalized_type, login_case_id, normalized_auth_type):
                return target

        rows, _ = self.repository.list("project_auth", project_id=project_id, page_size=500)
        if login_case_id and normalized_type:
            for row in rows:
                if self._auth_matches(row, project_id, normalized_type, login_case_id, normalized_auth_type):
                    return row

        name = str(auth_name or "").strip()
        for row in rows:
            if row.get("name") == name and self._to_int(row.get("project_id")) == project_id:
                return row
        return None

    def _auth_matches(
        self,
        auth: dict[str, Any],
        project_id: int | None,
        login_case_type: str,
        login_case_id: int | None,
        auth_type: str,
    ) -> bool:
        data = self._record_data(auth)
        if self._to_int(auth.get("project_id")) != project_id:
            return False
        if login_case_type and str(data.get("login_case_type") or "").upper() != login_case_type:
            return False
        if login_case_id and self._to_int(data.get("login_case_id")) != login_case_id:
            return False
        return not auth_type or str(data.get("auth_type") or "").lower() == auth_type

    def _source_page(self, case: dict[str, Any]) -> dict[str, Any] | None:
        source_id = self._to_int(case.get("source_id"))
        if not source_id:
            return None
        return self.repository.get("web_pages", source_id)

    def _auth(self, auth_id: Any) -> dict[str, Any] | None:
        auth_id_value = self._to_int(auth_id)
        if not auth_id_value:
            return None
        return self.repository.get("project_auth", auth_id_value)

    def _token_from_file(self, filename: str) -> str:
        data = AuthFileService().load_json(filename)
        for key in ("token", "access_token", "accessToken", "value"):
            value = data.get(key)
            if value:
                return str(value)
        return ""

    def _record_data(self, record: dict[str, Any] | None) -> dict[str, Any]:
        if not record:
            return {}
        data = record.get("data")
        return data if isinstance(data, dict) else {}

    def _hide_token(self, auth: dict[str, Any]) -> dict[str, Any]:
        result = dict(auth)
        data = result.get("data")
        if isinstance(data, dict):
            clean_data = dict(data)
            for key in ("token", "access_token", "accessToken", "value"):
                clean_data.pop(key, None)
            result["data"] = clean_data
        return result

    def _to_int(self, value: Any) -> int | None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _safe_file_stem(self, value: str) -> str:
        normalized = "".join(char if char.isalnum() or char in {"-", "_", "."} else "_" for char in value.strip())
        return normalized.strip("._") or "auth"
