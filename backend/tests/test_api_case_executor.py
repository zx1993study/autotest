from __future__ import annotations

import unittest
from typing import Any

from app.scheduler.jobs.api_case_executor import ApiCaseExecutor


class FakeResourceRepository:
    """Repository double that captures execution records for API executor tests."""

    def __init__(self) -> None:
        self.records: list[dict[str, Any]] = []
        self.items: dict[str, dict[int, dict[str, Any]]] = {
            "projects": {
                1: {
                    "id": 1,
                    "name": "演示项目",
                    "data": {"base_url": "https://example.test"},
                }
            },
            "api_interfaces": {
                10: {
                    "id": 10,
                    "name": "创建仓库",
                    "project_id": 1,
                    "data": {"method": "POST", "path": "/warehouses", "content_type": "application/json"},
                }
            },
        }
        self.fields = [
            {"id": 1, "name": "name", "project_id": 1, "data": {"interface_id": 10, "name": "name", "location": "body"}},
            {"id": 2, "name": "type", "project_id": 1, "data": {"interface_id": 10, "name": "type", "location": "body"}},
        ]

    def list(
        self,
        table: str,
        keyword: str | None = None,
        project_id: int | None = None,
        page: int = 1,
        page_size: int = 20,
        data_filters: dict[str, Any] | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        del keyword, page, page_size, data_filters
        if table == "api_fields":
            rows = [item for item in self.fields if project_id is None or item.get("project_id") == project_id]
            return rows, len(rows)
        rows = list(self.items.get(table, {}).values())
        if project_id is not None:
            rows = [item for item in rows if item.get("project_id") == project_id]
        return rows, len(rows)

    def get(self, table: str, item_id: int) -> dict[str, Any] | None:
        return self.items.get(table, {}).get(item_id)

    def create(self, table: str, data: dict[str, Any]) -> dict[str, Any]:
        self.records.append({"table": table, **data})
        return {"id": len(self.records), **data}

    def create_many(self, table: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [self.create(table, row) for row in rows]

    def update(self, table: str, item_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
        raise NotImplementedError

    def delete(self, table: str, item_id: int) -> bool:
        raise NotImplementedError

    def batch_delete(self, table: str, ids: list[int]) -> int:
        raise NotImplementedError

    def delete_by_project(self, table: str, project_id: int) -> int:
        raise NotImplementedError


class StubApiCaseExecutor(ApiCaseExecutor):
    """Avoid real HTTP while still exercising request assembly."""

    def _send_http_request(self, request_info: dict[str, Any]) -> tuple[int, dict[str, str], str]:
        return 200, {"Content-Type": "application/json"}, '{"ok": true}'


class ApiCaseExecutorTest(unittest.TestCase):
    def test_config_params_override_saved_case_params(self) -> None:
        repository = FakeResourceRepository()
        executor = StubApiCaseExecutor(repository)
        case = {
            "id": 99,
            "name": "创建仓库成功",
            "project_id": 1,
            "source_id": 10,
            "data": {
                "method": "POST",
                "path": "/warehouses",
                "params": {"name": "旧名称", "type": "old"},
            },
            "assertions": [{"type": "status", "expected": 200}],
        }

        record = executor.execute(
            case,
            {
                "project_id": 1,
                "case_ids": [99],
                "config": {"params": {"name": "新名称", "type": "normal"}},
            },
        )

        request_body = record["data"]["request"]["body"]
        self.assertEqual(request_body, {"name": "新名称", "type": "normal"})


if __name__ == "__main__":
    unittest.main()
