from __future__ import annotations

import unittest

from app.core.exceptions import BusinessRuleError
from app.schemas.system_users import (
    SystemUserCreate,
    SystemUserResetPassword,
    SystemUserUpdate,
)
from app.services.auth_service import USER_TABLE
from app.services.system_user_service import SystemUserService
from app.utils.security_utils import verify_password


class FakeResourceRepository:
    """In-memory repository that mimics the generic resource contract."""

    def __init__(self) -> None:
        self.rows: dict[int, dict[str, object]] = {}
        self.next_id = 1

    def list(
        self,
        table: str,
        keyword: str | None = None,
        project_id: int | None = None,
        page: int = 1,
        page_size: int = 20,
        data_filters: dict[str, object] | None = None,
    ) -> tuple[list[dict[str, object]], int]:
        del project_id
        rows = [row for row in self.rows.values() if row.get("table") == table]
        if keyword and keyword.strip():
            rows = [row for row in rows if keyword.strip().lower() in " ".join([
                str(row["data"].get("username") or ""),
                str(row["data"].get("real_name") or row["name"]),
                str(row["data"].get("phone") or ""),
            ]).lower()]
        if (data_filters or {}).get("status"):
            rows = [row for row in rows if row.get("status") == data_filters["status"]]
        start = (page - 1) * page_size
        return rows[start : start + page_size], len(rows)

    def get(self, table: str, item_id: int) -> dict[str, object] | None:
        row = self.rows.get(item_id)
        return row if row and row.get("table") == table else None

    def create(self, table: str, data: dict[str, object]) -> dict[str, object]:
        item = {
            "id": self.next_id,
            "table": table,
            "name": data.get("name") or "Untitled",
            "status": data.get("status", "active"),
            "data": data.get("data", {}),
            "created_at": "2026-01-01T00:00:00",
            "updated_at": "2026-01-01T00:00:00",
        }
        self.rows[self.next_id] = item
        self.next_id += 1
        return item

    def create_many(self, table: str, rows: list[dict[str, object]]) -> list[dict[str, object]]:
        return [self.create(table, row) for row in rows]

    def update(self, table: str, item_id: int, data: dict[str, object]) -> dict[str, object] | None:
        row = self.get(table, item_id)
        if row is None:
            return None
        row.update(data)
        return row

    def delete(self, table: str, item_id: int) -> bool:
        if self.get(table, item_id) is None:
            return False
        self.rows.pop(item_id)
        return True

    def batch_delete(self, table: str, ids: list[int]) -> int:
        return sum(1 for item_id in set(ids) if self.delete(table, item_id))

    def delete_by_project(self, table: str, project_id: int) -> int:
        del table, project_id
        return 0


class SystemUserServiceTest(unittest.TestCase):
    def test_create_user_hashes_password_and_masks_output(self) -> None:
        repository = FakeResourceRepository()
        service = SystemUserService(repository)

        user = service.create(
            SystemUserCreate(
                username="Tester",
                real_name="测试用户",
                phone="13800138000",
                password="Secret123",
            )
        )
        row = repository.get(USER_TABLE, user.id)
        data = row["data"] if isinstance(row, dict) else {}

        self.assertEqual(user.username, "tester")
        self.assertEqual(user.password_info, "已设置")
        self.assertNotIn("password_hash", user.model_dump())
        self.assertTrue(isinstance(data, dict) and verify_password("Secret123", str(data["password_hash"])))

    def test_duplicate_username_is_rejected_case_insensitively(self) -> None:
        service = SystemUserService(FakeResourceRepository())
        service.create(SystemUserCreate(username="tester", real_name="测试用户", password="Secret123"))

        with self.assertRaises(BusinessRuleError):
            service.create(SystemUserCreate(username="TESTER", real_name="重复用户", password="Secret123"))

    def test_reset_password_replaces_hash(self) -> None:
        repository = FakeResourceRepository()
        service = SystemUserService(repository)
        user = service.create(SystemUserCreate(username="tester", real_name="测试用户", password="Secret123"))

        service.reset_password(user.id, SystemUserResetPassword(password="NewSecret123").password)
        row = repository.get(USER_TABLE, user.id)
        data = row["data"] if isinstance(row, dict) else {}

        self.assertTrue(isinstance(data, dict) and verify_password("NewSecret123", str(data["password_hash"])))
        self.assertFalse(isinstance(data, dict) and verify_password("Secret123", str(data["password_hash"])))

    def test_update_username_checks_uniqueness(self) -> None:
        repository = FakeResourceRepository()
        service = SystemUserService(repository)
        service.create(SystemUserCreate(username="first", real_name="用户一", password="Secret123"))
        second = service.create(SystemUserCreate(username="second", real_name="用户二", password="Secret123"))

        with self.assertRaises(BusinessRuleError):
            service.update(second.id, SystemUserUpdate(username="FIRST"))


if __name__ == "__main__":
    unittest.main()
