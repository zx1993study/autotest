"""Unit tests for the architecture foundation introduced by the refactor."""

from __future__ import annotations

import json
import unittest

from pydantic import ValidationError

from app.core.exceptions import ResourceNotFoundError
from app.enums.business import ExecutionModeEnum, ResourceStatusEnum
from app.schemas.cases import ExecuteRequest
from app.schemas.common import ResourceOut
from app.services.resource_service import ResourceService


class FakeResourceRepository:
    """In-memory repository used to isolate service business behavior."""

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
        del table, keyword, project_id, page, page_size, data_filters
        rows = list(self.rows.values())
        return rows, len(rows)

    def get(self, table: str, item_id: int) -> dict[str, object] | None:
        del table
        return self.rows.get(item_id)

    def create(self, table: str, data: dict[str, object]) -> dict[str, object]:
        del table
        item = {
            "id": self.next_id,
            "name": data["name"],
            "status": data.get("status", "active"),
            "data": data.get("data", {}),
        }
        self.rows[self.next_id] = item
        self.next_id += 1
        return item

    def create_many(
        self,
        table: str,
        rows: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        return [self.create(table, row) for row in rows]

    def update(
        self,
        table: str,
        item_id: int,
        data: dict[str, object],
    ) -> dict[str, object] | None:
        del table
        item = self.rows.get(item_id)
        if item is None:
            return None
        item.update(data)
        return item

    def delete(self, table: str, item_id: int) -> bool:
        del table
        return self.rows.pop(item_id, None) is not None

    def batch_delete(self, table: str, ids: list[int]) -> int:
        return sum(1 for item_id in set(ids) if self.delete(table, item_id))

    def delete_by_project(self, table: str, project_id: int) -> int:
        del table, project_id
        return 0


class EnumContractTest(unittest.TestCase):
    """Verify code validation and description serialization remain synchronized."""

    def test_execution_mode_accepts_declared_code(self) -> None:
        request = ExecuteRequest(mode=ExecutionModeEnum.LOCAL_APPIUM.code)

        self.assertEqual(request.mode, ExecutionModeEnum.LOCAL_APPIUM)

    def test_execution_mode_rejects_unknown_code(self) -> None:
        with self.assertRaises(ValidationError):
            ExecuteRequest(mode="unknown-mode")

    def test_output_schema_serializes_enum_description(self) -> None:
        output = ResourceOut(
            id=1,
            name="演示资源",
            status=ResourceStatusEnum.ACTIVE,
            data={},
            created_at="2026-07-10T00:00:00",
            updated_at="2026-07-10T00:00:00",
        )

        payload = json.loads(output.model_dump_json())

        self.assertEqual(payload["status"], ResourceStatusEnum.ACTIVE.desc)


class ResourceServiceTest(unittest.TestCase):
    """Verify services expose domain exceptions rather than HTTP exceptions."""

    def setUp(self) -> None:
        self.repository = FakeResourceRepository()
        self.service = ResourceService("projects", self.repository)

    def test_create_applies_resource_defaults(self) -> None:
        item = self.service.create({"name": "项目 A"})

        self.assertEqual(item["status"], "active")
        self.assertEqual(item["data"], {})

    def test_get_missing_resource_raises_domain_exception(self) -> None:
        with self.assertRaises(ResourceNotFoundError):
            self.service.get(999)


if __name__ == "__main__":
    unittest.main()
