"""Business service for platform user management."""

from __future__ import annotations

import time
from typing import Any

from app.core.exceptions import BusinessRuleError, ResourceNotFoundError
from app.enums.business import ResourceStatusEnum
from app.repositories.interfaces import ResourceRepository
from app.schemas.system_users import (
    SystemUserCreate,
    SystemUserOut,
    SystemUserUpdate,
)
from app.services.auth_service import USER_TABLE
from app.utils.security_utils import hash_password

DEFAULT_USER_ROLES = ["user"]


class SystemUserService:
    """Manage users stored in the generic resource repository.

    Keeping the user-specific invariants here avoids leaking password hashing,
    uniqueness checks, and ResourceRecord data-shape details into routers.
    """

    def __init__(self, repository: ResourceRepository) -> None:
        self.repository = repository

    def list(
        self,
        *,
        keyword: str | None,
        status: ResourceStatusEnum | None,
        page: int,
        page_size: int,
    ) -> tuple[list[SystemUserOut], int]:
        """Return paginated users after filtering business fields."""

        rows, total = self.repository.list(
            USER_TABLE, keyword=keyword, page=page, page_size=page_size,
            data_filters={"status": status.code} if status is not None else None,
        )
        return [self._to_output(row) for row in rows], total

    def get(self, user_id: int) -> SystemUserOut:
        """Return one user or raise a stable business error."""

        return self._to_output(self._get_existing(user_id))

    def create(self, payload: SystemUserCreate) -> SystemUserOut:
        """Create a user and store only the hashed password."""

        username = self._normalize_username(payload.username)
        self._ensure_unique_username(username)
        now = int(time.time())
        row = self.repository.create(
            USER_TABLE,
            {
                "name": payload.real_name,
                "status": payload.status.code,
                "description": None,
                "data": {
                    "username": username,
                    "real_name": payload.real_name,
                    "phone": payload.phone or "",
                    "password_hash": hash_password(payload.password),
                    "roles": DEFAULT_USER_ROLES,
                    "permissions": [],
                    "must_change_password": False,
                    "created_by": "system",
                    "created_at": now,
                },
            },
        )
        return self._to_output(row)

    def update(self, user_id: int, payload: SystemUserUpdate) -> SystemUserOut:
        """Update user profile fields without modifying password hashes."""

        row = self._get_existing(user_id)
        current_data = self._record_data(row)
        update_data = payload.model_dump(exclude_unset=True)
        username = current_data.get("username")
        if update_data.get("username"):
            username = self._normalize_username(str(update_data["username"]))
            self._ensure_unique_username(username, exclude_user_id=user_id)
        real_name = str(update_data.get("real_name") or current_data.get("real_name") or row.get("name") or username)
        merged_data = {
            **current_data,
            "username": str(username or ""),
            "real_name": real_name,
        }
        if "phone" in update_data:
            merged_data["phone"] = update_data["phone"] or ""
        status = update_data.get("status")
        row = self.repository.update(
            USER_TABLE,
            user_id,
            {
                "name": real_name,
                "status": status.code if isinstance(status, ResourceStatusEnum) else row.get("status"),
                "data": merged_data,
            },
        )
        if row is None:
            raise ResourceNotFoundError("用户不存在")
        return self._to_output(row)

    def reset_password(self, user_id: int, password: str) -> SystemUserOut:
        """Replace the user's password hash with a newly generated hash."""

        row = self._get_existing(user_id)
        data = {
            **self._record_data(row),
            "password_hash": hash_password(password),
            "password_reset_at": int(time.time()),
            "must_change_password": False,
        }
        updated = self.repository.update(USER_TABLE, user_id, {"data": data})
        if updated is None:
            raise ResourceNotFoundError("用户不存在")
        return self._to_output(updated)

    def delete(self, user_id: int) -> bool:
        """Soft delete a user record."""

        if not self.repository.delete(USER_TABLE, user_id):
            raise ResourceNotFoundError("用户不存在")
        return True

    def batch_delete(self, user_ids: list[int]) -> dict[str, int]:
        """Soft delete multiple user records."""

        return {"deleted_count": self.repository.batch_delete(USER_TABLE, user_ids)}

    def _get_existing(self, user_id: int) -> dict[str, Any]:
        row = self.repository.get(USER_TABLE, user_id)
        if row is None:
            raise ResourceNotFoundError("用户不存在")
        return row

    def _ensure_unique_username(self, username: str, exclude_user_id: int | None = None) -> None:
        rows, _ = self.repository.list(USER_TABLE, page=1, page_size=10_000)
        for row in rows:
            if exclude_user_id is not None and int(row.get("id") or 0) == exclude_user_id:
                continue
            data = self._record_data(row)
            if self._normalize_username(str(data.get("username") or "")) == username:
                raise BusinessRuleError("用户名已存在")

    def _to_output(self, row: dict[str, Any]) -> SystemUserOut:
        data = self._record_data(row)
        username = str(data.get("username") or row.get("name") or "")
        real_name = str(data.get("real_name") or row.get("name") or username)
        password_hash = str(data.get("password_hash") or "")
        return SystemUserOut(
            id=int(row["id"]),
            username=username,
            real_name=real_name,
            phone=str(data.get("phone") or "") or None,
            status=ResourceStatusEnum(str(row.get("status") or ResourceStatusEnum.ACTIVE.code)),
            roles=self._string_list(data.get("roles")),
            permissions=self._string_list(data.get("permissions")),
            password_info="已设置" if password_hash else "未设置",
            created_at=str(row.get("created_at") or ""),
            updated_at=str(row.get("updated_at") or ""),
            last_login_at=self._optional_int(data.get("last_login_at")),
        )

    def _record_data(self, row: dict[str, Any] | None) -> dict[str, Any]:
        data = row.get("data") if isinstance(row, dict) else None
        return data if isinstance(data, dict) else {}

    def _normalize_username(self, username: str) -> str:
        return username.strip().lower()

    def _string_list(self, value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(item) for item in value if str(item or "").strip()]

    def _optional_int(self, value: Any) -> int | None:
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None
