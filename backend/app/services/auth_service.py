from __future__ import annotations

import time
from typing import Any

from app.core.config import settings
from app.core.exceptions import BusinessRuleError, ResourceNotFoundError
from app.repositories.interfaces import ResourceRepository
from app.schemas.auth import BootstrapAuthInfo, LoginResponse, UserProfile
from app.utils.security_utils import create_access_token, hash_password, verify_access_token, verify_password


USER_TABLE = "system_users"
DEFAULT_PERMISSIONS = ["*"]


class AuthService:
    """Application authentication business rules.

    Users are stored as generic resources to fit the current repository layer
    without introducing direct ORM access into services or routers.
    """

    def __init__(self, repository: ResourceRepository) -> None:
        self.repository = repository

    def bootstrap_info(self) -> BootstrapAuthInfo:
        """Return public login bootstrap metadata."""

        return BootstrapAuthInfo(
            default_username=settings.default_admin_username,
            password_policy="至少 6 位，建议包含大小写字母、数字和符号。",
        )

    def ensure_default_admin(self) -> None:
        """Create the default administrator when no platform user exists."""

        users, total = self.repository.list(USER_TABLE, page=1, page_size=1)
        if total or users:
            return
        username = settings.default_admin_username.strip()
        password = settings.default_admin_password
        self.repository.create(
            USER_TABLE,
            {
                "name": "系统管理员",
                "status": "active",
                "description": "系统初始化默认管理员",
                "data": {
                    "username": username,
                    "password_hash": hash_password(password),
                    "roles": ["admin"],
                    "permissions": DEFAULT_PERMISSIONS,
                    "must_change_password": True,
                    "created_by": "system",
                    "created_at": int(time.time()),
                },
            },
        )

    def login(self, username: str, password: str) -> LoginResponse:
        """Authenticate a platform user and issue a bearer token."""

        user = self._user_by_username(username)
        if not user or user.get("status") != "active":
            raise BusinessRuleError("账号或密码错误")
        data = self._record_data(user)
        password_hash = str(data.get("password_hash") or "")
        if not password_hash or not verify_password(password, password_hash):
            raise BusinessRuleError("账号或密码错误")

        now = int(time.time())
        self.repository.update(
            USER_TABLE,
            int(user["id"]),
            {"data": {**data, "last_login_at": now}},
        )
        profile = self._profile({**user, "data": {**data, "last_login_at": now}})
        token = create_access_token(
            {
                "sub": str(profile.id),
                "username": profile.username,
                "roles": profile.roles,
            },
            settings.auth_secret_key,
            settings.auth_access_token_expire_minutes * 60,
        )
        return LoginResponse(
            access_token=token,
            expires_in=settings.auth_access_token_expire_minutes * 60,
            user=profile,
        )

    def current_user_from_token(self, token: str) -> UserProfile:
        """Resolve and validate the current user from a bearer token."""

        try:
            claims = verify_access_token(token, settings.auth_secret_key)
            user_id = int(str(claims.get("sub") or ""))
        except (TypeError, ValueError) as exc:
            raise BusinessRuleError("登录状态已失效，请重新登录") from exc
        user = self.repository.get(USER_TABLE, user_id)
        if not user or user.get("status") != "active":
            raise ResourceNotFoundError("用户不存在或已停用")
        return self._profile(user)

    def _user_by_username(self, username: str) -> dict[str, Any] | None:
        normalized = username.strip().lower()
        rows, _ = self.repository.list(USER_TABLE, page=1, page_size=1000)
        for row in rows:
            data = self._record_data(row)
            if str(data.get("username") or "").strip().lower() == normalized:
                return row
        return None

    def _profile(self, user: dict[str, Any]) -> UserProfile:
        data = self._record_data(user)
        roles = self._string_list(data.get("roles"))
        permissions = self._string_list(data.get("permissions"))
        return UserProfile(
            id=int(user["id"]),
            username=str(data.get("username") or user.get("name") or ""),
            display_name=str(user.get("name") or data.get("display_name") or data.get("username") or ""),
            roles=roles,
            permissions=permissions,
        )

    def _record_data(self, record: dict[str, Any] | None) -> dict[str, Any]:
        data = record.get("data") if isinstance(record, dict) else None
        return data if isinstance(data, dict) else {}

    def _string_list(self, value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(item) for item in value if str(item or "").strip()]
