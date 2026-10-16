from __future__ import annotations

from copy import deepcopy
import unittest

from app.constants.knowledge_principles import DEFAULT_KNOWLEDGE_ITEMS
from app.services.knowledge_seed_service import KnowledgeSeedService


class FakeResourceRepository:
    """In-memory resource store for knowledge synchronization tests."""

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
        del keyword, page, page_size, data_filters
        rows = [
            row
            for row in self.rows.values()
            if row["table"] == table and row.get("project_id") == project_id
        ]
        return rows, len(rows)

    def get(self, table: str, item_id: int) -> dict[str, object] | None:
        row = self.rows.get(item_id)
        return row if row and row["table"] == table else None

    def create(self, table: str, data: dict[str, object]) -> dict[str, object]:
        row = {"id": self.next_id, "table": table, **deepcopy(data)}
        self.rows[self.next_id] = row
        self.next_id += 1
        return row

    def update(
        self,
        table: str,
        item_id: int,
        data: dict[str, object],
    ) -> dict[str, object] | None:
        row = self.get(table, item_id)
        if row is None:
            return None
        row.update(deepcopy(data))
        return row

    def delete(self, table: str, item_id: int) -> bool:
        if self.get(table, item_id) is None:
            return False
        self.rows.pop(item_id)
        return True


class KnowledgeSeedServiceTest(unittest.TestCase):
    def test_seed_should_create_exactly_eight_test_principles(self) -> None:
        repository = FakeResourceRepository()
        service = KnowledgeSeedService(repository)

        result = service.seed_defaults(project_id=8)

        self.assertEqual(result["inserted_count"], 8)
        self.assertEqual(result["total_count"], 8)
        self.assertEqual(len(repository.rows), len(DEFAULT_KNOWLEDGE_ITEMS))
        self.assertTrue(
            all(
                isinstance(row.get("data"), dict)
                and row["data"].get("kind") == "test_principle"
                for row in repository.rows.values()
            )
        )

    def test_seed_should_update_managed_items_and_remove_legacy_defaults(self) -> None:
        repository = FakeResourceRepository()
        service = KnowledgeSeedService(repository)
        service.seed_defaults(project_id=8)
        first = next(iter(repository.rows.values()))
        first["description"] = "outdated system principle"
        repository.create(
            "project_knowledge",
            {
                "name": "旧模板",
                "project_id": 8,
                "status": "active",
                "data": {"knowledge_key": "template.web.form_success"},
            },
        )
        custom = repository.create(
            "project_knowledge",
            {
                "name": "自定义原则",
                "project_id": 8,
                "status": "active",
                "data": {"knowledge_key": "custom.project_rule"},
            },
        )

        result = service.seed_defaults(project_id=8)

        self.assertEqual(result["updated_count"], 1)
        self.assertEqual(result["skipped_count"], 7)
        self.assertEqual(result["deleted_count"], 1)
        self.assertIsNotNone(repository.get("project_knowledge", int(custom["id"])))

    def test_unchanged_defaults_should_not_write_on_repeated_startup(self) -> None:
        repository = FakeResourceRepository()
        service = KnowledgeSeedService(repository)
        service.seed_defaults(project_id=8)

        result = service.seed_defaults(project_id=8)

        self.assertEqual(result["updated_count"], 0)
        self.assertEqual(result["inserted_count"], 0)
        self.assertEqual(result["skipped_count"], 8)

    def test_explicit_overwrite_should_still_refresh_all_defaults(self) -> None:
        repository = FakeResourceRepository()
        service = KnowledgeSeedService(repository)
        service.seed_defaults(project_id=8)

        result = service.seed_defaults(project_id=8, overwrite=True)

        self.assertEqual(result["updated_count"], 8)


if __name__ == "__main__":
    unittest.main()
