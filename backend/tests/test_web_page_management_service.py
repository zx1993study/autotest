from __future__ import annotations

import unittest
from collections import Counter
from typing import Any

from app.services.web_page_management_service import WebPageManagementService


class FakeResourceRepository:
    def web_feature_counts(self, feature_ids):
        return {key: {
            "element_count": sum(row.get("data", {}).get("page_id") == key for row in self.rows["web_elements"]),
            "case_count": sum(row.get("source_id") == key for row in self.rows["web_test_cases"]),
        } for key in feature_ids}

    def __init__(self) -> None:
        self.next_id = 100
        self.list_calls: Counter[str] = Counter()
        self.rows: dict[str, list[dict[str, Any]]] = {
            "web_pages": [
                {
                    "id": 10,
                    "name": "仓库管理页面",
                    "project_id": 1,
                    "status": "active",
                    "description": None,
                    "data": {
                        "route": "/warehouse/warehouse",
                        "url": "https://example.test/warehouse/warehouse",
                        "feature_type": "page",
                    },
                    "updated_at": "2026-09-01T10:00:00",
                },
                {
                    "id": 11,
                    "name": "新增仓库",
                    "project_id": 1,
                    "status": "active",
                    "description": None,
                    "data": {
                        "route": "/warehouse/warehouse?tab=basic",
                        "url": "https://example.test/warehouse/warehouse?tab=basic",
                        "feature_type": "add",
                        "related_interface_ids": [50],
                    },
                    "updated_at": "2026-09-02T10:00:00",
                },
                {
                    "id": 12,
                    "name": "删除仓库",
                    "project_id": 1,
                    "status": "active",
                    "description": None,
                    "data": {
                        "route": "https://example.test/warehouse/warehouse?tab=danger#confirm",
                        "url": "https://example.test/warehouse/warehouse?tab=danger",
                        "feature_type": "delete",
                    },
                    "updated_at": "2026-09-03T10:00:00",
                },
            ],
            "web_page_groups": [],
            "web_page_api_relations": [],
            "web_elements": [
                {"id": 40, "project_id": 1, "data": {"page_id": 11}},
                {"id": 41, "project_id": 1, "data": {"page_id": 11}},
            ],
            "web_test_cases": [{"id": 42, "project_id": 1, "source_id": 11, "data": {}}],
            "api_interfaces": [
                {
                    "id": 50,
                    "name": "Create Warehouse",
                    "project_id": 1,
                    "status": "active",
                    "data": {"method": "POST", "path": "/warehouse", "module": "仓库"},
                },
                {
                    "id": 51,
                    "name": "Delete Warehouse",
                    "project_id": 1,
                    "status": "active",
                    "data": {"method": "DELETE", "path": "/warehouse/{id}", "module": "仓库"},
                },
            ],
            "project_auth": [],
        }

    def list(self, table: str, keyword=None, project_id=None, page=1, page_size=20, data_filters=None):
        self.list_calls[table] += 1
        rows = [dict(item) for item in self.rows.get(table, [])]
        if project_id is not None:
            rows = [item for item in rows if item.get("project_id") == project_id]
        if keyword:
            needle = str(keyword).casefold()
            rows = [item for item in rows if needle in str(item.get("name") or "").casefold()]
        for key, value in (data_filters or {}).items():
            rows = [item for item in rows if (item.get("data") or {}).get(key) == value]
        start = (page - 1) * page_size
        return rows[start : start + page_size], len(rows)

    def get(self, table: str, item_id: int):
        return next((item for item in self.rows.get(table, []) if item.get("id") == item_id), None)

    def create(self, table: str, data: dict[str, Any]):
        self.next_id += 1
        row = {
            "id": self.next_id,
            "description": None,
            "status": "active",
            "data": {},
            "created_at": "2026-09-04T10:00:00",
            "updated_at": "2026-09-04T10:00:00",
            **data,
        }
        self.rows.setdefault(table, []).append(row)
        return row

    def create_many(self, table: str, rows: list[dict[str, Any]]):
        return [self.create(table, row) for row in rows]

    def update(self, table: str, item_id: int, data: dict[str, Any]):
        row = self.get(table, item_id)
        if row is None:
            return None
        row.update({key: value for key, value in data.items() if key != "data"})
        if "data" in data:
            row["data"] = dict(data["data"])
        return row

    def update_many(self, table: str, rows: list[tuple[int, dict[str, Any]]]):
        return [updated for item_id, data in rows if (updated := self.update(table, item_id, data))]

    def delete(self, table: str, item_id: int):
        before = len(self.rows.get(table, []))
        self.rows[table] = [item for item in self.rows.get(table, []) if item.get("id") != item_id]
        return len(self.rows[table]) != before

    def batch_delete(self, table: str, ids: list[int]):
        return sum(1 for item_id in ids if self.delete(table, item_id))

    def delete_by_project(self, table: str, project_id: int):
        return 0


class WebPageManagementServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = FakeResourceRepository()
        self.service = WebPageManagementService(self.repository)

    def test_synchronizes_route_variants_without_replacing_feature_ids(self) -> None:
        rows, total = self.service.list_groups(1, None, None, 1, 20)

        self.assertEqual(1, total)
        self.assertEqual("仓库管理页面", rows[0]["name"])
        self.assertEqual("/warehouse/warehouse", rows[0]["data"]["route"])
        self.assertEqual(3, rows[0]["feature_count"])
        self.assertEqual([10, 11, 12], [item["id"] for item in self.repository.rows["web_pages"]])
        group_id = rows[0]["id"]
        self.assertTrue(all(item["data"]["page_group_id"] == group_id for item in self.repository.rows["web_pages"]))

        second = self.service.synchronize_project(1)
        self.assertEqual(0, second["created_groups"])
        self.assertEqual(0, second["linked_features"])

    def test_exposes_counts_and_filters_interfaces_by_feature(self) -> None:
        group = self.service.list_groups(1, None, None, 1, 20)[0][0]
        group_id = int(group["id"])
        features, total = self.service.list_features(group_id, "新增", None, 1, 20)
        self.assertEqual(1, total)
        self.assertEqual(2, features[0]["element_count"])
        self.assertEqual(1, features[0]["case_count"])

        result = self.service.create_relations(group_id, [51], 12, "manual")
        self.assertEqual(1, result["created_count"])
        page_interfaces, _ = self.service.list_interfaces(group_id, None, None, None, 1, 20)
        self.assertEqual({50, 51}, {item["id"] for item in page_interfaces})
        feature_interfaces, _ = self.service.list_interfaces(group_id, 12, None, "DELETE", 1, 20)
        self.assertEqual([51], [item["id"] for item in feature_interfaces])
        self.assertEqual("删除仓库", feature_interfaces[0]["relation_feature_name"])

    def test_stable_page_list_skips_full_project_synchronization(self) -> None:
        self.service.list_groups(1, None, None, 1, 20)
        self.repository.list_calls.clear()

        rows, total = self.service.list_groups(1, None, None, 1, 20)

        self.assertEqual(1, total)
        self.assertEqual(3, rows[0]["feature_count"])
        self.assertEqual(1, self.repository.list_calls["web_page_groups"])
        self.assertEqual(1, self.repository.list_calls["web_pages"])
        self.assertEqual(1, self.repository.list_calls["web_page_api_relations"])
        self.assertEqual(0, self.repository.list_calls["api_interfaces"])

    def test_creates_page_group_with_compatible_page_feature(self) -> None:
        created = self.service.create_group(
            {
                "name": "客户管理页面",
                "project_id": 1,
                "route": "/customer/list",
                "url": "https://example.test/customer/list",
                "status": "active",
            }
        )
        self.assertEqual(1, created["feature_count"])
        feature = self.repository.rows["web_pages"][-1]
        self.assertEqual(created["id"], feature["data"]["page_group_id"])
        self.assertEqual("page", feature["data"]["feature_type"])


if __name__ == "__main__":
    unittest.main()
