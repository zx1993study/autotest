from __future__ import annotations

import time
import unittest

from app.services.auth_service import AuthService, USER_TABLE
from app.utils.security_utils import create_access_token, hash_password, verify_access_token, verify_password


class FakeResourceRepository:
    """Small in-memory repository for auth service tests."""

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
        del keyword, project_id, data_filters
        rows = [row for row in self.rows.values() if row.get("table") == table]
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


class SecurityUtilsTest(unittest.TestCase):
    def test_password_hash_verification(self) -> None:
        password_hash = hash_password("Admin@123456")

        self.assertTrue(verify_password("Admin@123456", password_hash))
        self.assertFalse(verify_password("wrong-password", password_hash))

    def test_access_token_validation(self) -> None:
        token = create_access_token({"sub": "1"}, "secret", 60)

        self.assertEqual(verify_access_token(token, "secret")["sub"], "1")
        with self.assertRaises(ValueError):
            verify_access_token(token, "other-secret")

    def test_access_token_expiration(self) -> None:
        token = create_access_token({"sub": "1"}, "secret", -1)
        time.sleep(0.01)

        with self.assertRaises(ValueError):
            verify_access_token(token, "secret")


class AuthServiceTest(unittest.TestCase):
    def test_default_admin_can_login(self) -> None:
        repository = FakeResourceRepository()
        service = AuthService(repository)

        service.ensure_default_admin()
        response = service.login("admin", "Admin@123456")
        users, total = repository.list(USER_TABLE, page=1, page_size=10)

        self.assertEqual(total, 1)
        self.assertEqual(users[0]["status"], "active")
        self.assertTrue(response.access_token)
        self.assertEqual(response.user.username, "admin")
        self.assertIn("admin", response.user.roles)


if __name__ == "__main__":
    unittest.main()
