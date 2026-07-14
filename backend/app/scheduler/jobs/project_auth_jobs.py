from __future__ import annotations

import json
from typing import Any

from app.core.exceptions import BusinessRuleError, ResourceNotFoundError
from app.repositories.interfaces import ResourceRepository
from app.scheduler.jobs.case_execution_jobs import run_case_execution_job
from app.services.project_auth_service import ProjectAuthService


TOKEN_KEYS = {"token", "access_token", "accessToken", "id_token", "idToken", "jwt"}


def refresh_project_auth_job(
    auth_id: int,
    payload: dict[str, Any],
    repository: ResourceRepository,
) -> dict[str, Any]:
    """Refresh a project auth resource by executing its bound login case.

    Routers should call this scheduler job instead of composing executors in
    the API layer. The job owns execution orchestration and delegates auth file
    upserts back to ``ProjectAuthService`` so CRUD concerns remain centralized.
    """

    auth = repository.get("project_auth", auth_id)
    if not auth:
        raise ResourceNotFoundError("未找到鉴权信息")

    data = _record_data(auth)
    login_case_type = str(data.get("login_case_type") or "").upper()
    login_case_id = _to_int(data.get("login_case_id"))
    if not login_case_type or not login_case_id:
        raise BusinessRuleError("鉴权信息未绑定登录用例，无法刷新")

    if login_case_type == "WEB":
        return _refresh_web_auth(auth_id, auth, payload, repository)
    if login_case_type == "API":
        return _refresh_api_auth(auth_id, auth, payload, repository)
    raise BusinessRuleError(f"暂不支持刷新 {login_case_type} 类型鉴权")


def _refresh_web_auth(
    auth_id: int,
    auth: dict[str, Any],
    payload: dict[str, Any],
    repository: ResourceRepository,
) -> dict[str, Any]:
    data = _record_data(auth)
    execution = run_case_execution_job(
        "WEB",
        {
            "case_ids": [int(data["login_case_id"])],
            "project_id": auth.get("project_id"),
            "mode": payload.get("mode") or "local_headless",
            "config": payload.get("config") if isinstance(payload.get("config"), dict) else {},
            "refresh_auth_id": auth_id,
            "skip_auth": True,
        },
        repository,
    )
    record = _first_record(execution)
    if record.get("status") != "success":
        raise BusinessRuleError(_execution_error(record) or "登录用例执行失败，鉴权信息未刷新")

    auth_saved = _record_data(record).get("auth_saved")
    if not isinstance(auth_saved, dict) or not auth_saved.get("auth_id"):
        raise BusinessRuleError("登录用例执行成功，但未采集到可保存的 Cookie")

    return {
        "auth_id": auth_saved.get("auth_id") or auth_id,
        "record_id": record.get("id"),
        "status": record.get("status"),
        "token_file": auth_saved.get("token_file"),
        "message": "鉴权信息已刷新",
    }


def _refresh_api_auth(
    auth_id: int,
    auth: dict[str, Any],
    payload: dict[str, Any],
    repository: ResourceRepository,
) -> dict[str, Any]:
    data = _record_data(auth)
    execution = run_case_execution_job(
        "API",
        {
            "case_ids": [int(data["login_case_id"])],
            "project_id": auth.get("project_id"),
            "mode": payload.get("mode") or "local_headless",
            "config": payload.get("config") if isinstance(payload.get("config"), dict) else {},
        },
        repository,
    )
    record = _first_record(execution)
    if record.get("status") != "success":
        raise BusinessRuleError(_execution_error(record) or "登录用例执行失败，鉴权信息未刷新")

    record_data = _record_data(record)
    token = _extract_token(record_data.get("response_body"))
    if not token:
        raise BusinessRuleError("登录用例执行成功，但响应中未识别到 token")

    auth_type = str(data.get("auth_type") or "bearer").lower()
    if auth_type == "cookie":
        raise BusinessRuleError("API Cookie 鉴权请使用 Web Cookie 登录用例刷新")

    updated = ProjectAuthService(repository).generate_token_auth(
        {
            "target_auth_id": auth_id,
            "name": auth.get("name") or "API Token",
            "project_id": auth.get("project_id"),
            "description": auth.get("description"),
            "auth_type": auth_type,
            "token": token,
            "header_name": data.get("header_name") or "Authorization",
            "login_case_type": "API",
            "login_case_id": int(data["login_case_id"]),
            "source_record_id": record.get("id"),
            "refresh_strategy": data.get("refresh_strategy") or "manual",
        }
    )
    updated_data = _record_data(updated)
    return {
        "auth_id": updated.get("id") or auth_id,
        "record_id": record.get("id"),
        "status": record.get("status"),
        "token_file": updated_data.get("token_file"),
        "message": "鉴权信息已刷新",
    }


def _first_record(execution: dict[str, Any]) -> dict[str, Any]:
    records = execution.get("records")
    if not isinstance(records, list) or not records:
        raise BusinessRuleError("未生成登录用例执行记录")
    record = records[0]
    if not isinstance(record, dict):
        raise BusinessRuleError("登录用例执行记录格式异常")
    return record


def _extract_token(response_body: Any) -> str:
    if isinstance(response_body, str):
        try:
            response_body = json.loads(response_body)
        except json.JSONDecodeError:
            return ""
    return _find_token_value(response_body)


def _find_token_value(value: Any) -> str:
    if isinstance(value, list):
        for item in value:
            token = _find_token_value(item)
            if token:
                return token
        return ""
    if not isinstance(value, dict):
        return ""
    for key, item in value.items():
        if key in TOKEN_KEYS and isinstance(item, str) and item.strip():
            return item.strip()
    for item in value.values():
        token = _find_token_value(item)
        if token:
            return token
    return ""


def _execution_error(record: dict[str, Any]) -> str:
    data = _record_data(record)
    return str(data.get("error") or record.get("description") or "").strip()


def _record_data(record: dict[str, Any] | None) -> dict[str, Any]:
    data = record.get("data") if isinstance(record, dict) else None
    return data if isinstance(data, dict) else {}


def _to_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
