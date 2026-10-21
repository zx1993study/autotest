from __future__ import annotations

import unittest
from datetime import datetime

from app.db.base import Base
from app.models.resource_record import ResourceRecord
from app.models.test_case_record import WebTestCaseRecord
from app.repositories.sqlalchemy_resource_repository import SqlAlchemyResourceRepository
from app.services.api_testing_service import ApiTestingService
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


class ResourceRepositorySortingTest(unittest.TestCase):
    """Verify resource-specific ordering and list filters."""

    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.session = sessionmaker(bind=self.engine)()
        self.repository = SqlAlchemyResourceRepository(self.session)

    def tearDown(self) -> None:
        self.session.close()
        self.engine.dispose()

    def test_generic_resources_sort_by_updated_at_then_id_desc(self) -> None:
        older = datetime(2026, 7, 10, 9, 0, 0)
        newer = datetime(2026, 7, 11, 9, 0, 0)
        self.session.add_all(
            [
                ResourceRecord(
                    table_name="projects",
                    name="old",
                    data_json={},
                    updated_at=older,
                    created_at=older,
                ),
                ResourceRecord(
                    table_name="projects",
                    name="new-a",
                    data_json={},
                    updated_at=newer,
                    created_at=newer,
                ),
                ResourceRecord(
                    table_name="projects",
                    name="new-b",
                    data_json={},
                    updated_at=newer,
                    created_at=newer,
                ),
            ]
        )
        self.session.commit()

        rows, total = self.repository.list("projects", page=1, page_size=20)

        self.assertEqual(total, 3)
        self.assertEqual([row["name"] for row in rows], ["new-b", "new-a", "old"])

    def test_test_cases_sort_by_id_desc(self) -> None:
        older = datetime(2026, 7, 10, 9, 0, 0)
        newer = datetime(2026, 7, 11, 9, 0, 0)
        self.session.add_all(
            [
                WebTestCaseRecord(
                    name="old",
                    data_json={},
                    steps_json=[],
                    assertions_json=[],
                    strategy_ids_json=[],
                    updated_at=older,
                    created_at=older,
                ),
                WebTestCaseRecord(
                    name="new-a",
                    data_json={},
                    steps_json=[],
                    assertions_json=[],
                    strategy_ids_json=[],
                    updated_at=newer,
                    created_at=newer,
                ),
                WebTestCaseRecord(
                    name="new-b",
                    data_json={},
                    steps_json=[],
                    assertions_json=[],
                    strategy_ids_json=[],
                    updated_at=newer,
                    created_at=newer,
                ),
            ]
        )
        self.session.commit()

        rows, total = self.repository.list("web_test_cases", page=1, page_size=20)

        self.assertEqual(total, 3)
        self.assertEqual([row["name"] for row in rows], ["new-b", "new-a", "old"])

    def test_web_elements_sort_by_element_id_ascending(self) -> None:
        older = datetime(2026, 7, 10, 9, 0, 0)
        newer = datetime(2026, 7, 11, 9, 0, 0)
        self.session.add_all(
            [
                ResourceRecord(
                    table_name="web_elements",
                    name="first-id",
                    data_json={},
                    updated_at=older,
                    created_at=older,
                ),
                ResourceRecord(
                    table_name="web_elements",
                    name="second-id",
                    data_json={},
                    updated_at=newer,
                    created_at=newer,
                ),
            ]
        )
        self.session.commit()

        rows, total = self.repository.list("web_elements", page=1, page_size=20)

        self.assertEqual(total, 2)
        self.assertEqual([row["name"] for row in rows], ["first-id", "second-id"])

    def test_api_interfaces_filter_by_method_and_path_fragment(self) -> None:
        now = datetime(2026, 7, 12, 9, 0, 0)
        self.session.add_all(
            [
                ResourceRecord(
                    table_name="api_interfaces",
                    name="list warehouses",
                    data_json={"data": {"method": "GET", "path": "/api/warehouses"}},
                    updated_at=now,
                    created_at=now,
                ),
                ResourceRecord(
                    table_name="api_interfaces",
                    name="create warehouse",
                    data_json={"data": {"method": "POST", "path": "/api/warehouses"}},
                    updated_at=now,
                    created_at=now,
                ),
                ResourceRecord(
                    table_name="api_interfaces",
                    name="create customer",
                    data_json={"data": {"method": "POST", "path": "/api/customers"}},
                    updated_at=now,
                    created_at=now,
                ),
            ]
        )
        self.session.commit()

        rows, total = self.repository.list(
            "api_interfaces",
            page=1,
            page_size=20,
            data_filters={"method": "POST", "path": "warehouse"},
        )

        self.assertEqual(total, 1)
        self.assertEqual(rows[0]["name"], "create warehouse")

    def test_api_interfaces_filter_by_module_and_ungrouped(self) -> None:
        now = datetime(2026, 7, 12, 9, 0, 0)
        self.session.add_all(
            [
                ResourceRecord(
                    table_name="api_interfaces",
                    name="user api",
                    project_id=1,
                    data_json={"data": {"module": "Users"}},
                    updated_at=now,
                    created_at=now,
                ),
                ResourceRecord(
                    table_name="api_interfaces",
                    name="empty module",
                    project_id=1,
                    data_json={"data": {"module": ""}},
                    updated_at=now,
                    created_at=now,
                ),
                ResourceRecord(
                    table_name="api_interfaces",
                    name="missing module",
                    project_id=1,
                    data_json={"data": {}},
                    updated_at=now,
                    created_at=now,
                ),
            ]
        )
        self.session.commit()

        module_rows, module_total = self.repository.list(
            "api_interfaces",
            project_id=1,
            page_size=20,
            data_filters={"module": "Users"},
        )
        ungrouped_rows, ungrouped_total = self.repository.list(
            "api_interfaces",
            project_id=1,
            page_size=20,
            data_filters={"module": "__ungrouped__"},
        )

        self.assertEqual(module_total, 1)
        self.assertEqual(module_rows[0]["name"], "user api")
        self.assertEqual(ungrouped_total, 2)
        self.assertEqual({row["name"] for row in ungrouped_rows}, {"empty module", "missing module"})

    def test_api_module_summary_is_project_scoped_and_ungrouped_is_last(self) -> None:
        now = datetime(2026, 7, 12, 9, 0, 0)
        self.session.add_all(
            [
                ResourceRecord(
                    table_name="api_interfaces",
                    name="list users",
                    project_id=1,
                    data_json={"data": {"module": "Users", "method": "GET"}},
                    updated_at=now,
                    created_at=now,
                ),
                ResourceRecord(
                    table_name="api_interfaces",
                    name="create user",
                    project_id=1,
                    data_json={"data": {"module": "Users", "method": "POST", "deprecated": True}},
                    updated_at=now,
                    created_at=now,
                ),
                ResourceRecord(
                    table_name="api_interfaces",
                    name="health",
                    project_id=1,
                    status="disabled",
                    data_json={"data": {"method": "GET"}},
                    updated_at=now,
                    created_at=now,
                ),
                ResourceRecord(
                    table_name="api_interfaces",
                    name="other project",
                    project_id=2,
                    data_json={"data": {"module": "Users", "method": "DELETE"}},
                    updated_at=now,
                    created_at=now,
                ),
            ]
        )
        self.session.commit()

        rows, total = ApiTestingService(self.repository).list_modules(1, None, 1, 20)

        self.assertEqual(total, 2)
        self.assertEqual([row["key"] for row in rows], ["Users", "__ungrouped__"])
        self.assertEqual(rows[0]["method_counts"], {"GET": 1, "POST": 1})
        self.assertEqual(rows[0]["deprecated_count"], 1)
        self.assertEqual(rows[1]["disabled_count"], 1)
        linked_rows, linked_total = self.repository.list(
            "api_interfaces",
            project_id=1,
            page_size=20,
            data_filters={"module_id": rows[0]["id"]},
        )
        self.assertEqual(linked_total, 2)
        self.assertEqual({row["name"] for row in linked_rows}, {"list users", "create user"})

    def test_api_module_sync_keeps_existing_module_id_as_source_of_truth(self) -> None:
        module = self.repository.create(
            "api_modules",
            {
                "name": "Accounts",
                "project_id": 1,
                "data": {"module_key": "Accounts"},
            },
        )
        interface = self.repository.create(
            "api_interfaces",
            {
                "name": "list accounts",
                "project_id": 1,
                "data": {"module_id": module["id"], "module": "Old name", "method": "GET"},
            },
        )

        rows, total = ApiTestingService(self.repository).list_modules(1, None, 1, 20)
        synchronized = self.repository.get("api_interfaces", interface["id"])

        self.assertEqual(total, 1)
        self.assertEqual([row["name"] for row in rows], ["Accounts"])
        self.assertEqual(synchronized["data"]["module_id"], module["id"])
        self.assertEqual(synchronized["data"]["module"], "Accounts")

    def test_empty_project_module_queries_do_not_create_default_records(self) -> None:
        service = ApiTestingService(self.repository)
        for _ in range(2):
            self.assertEqual(service.list_modules(1, None, 1, 20), ([], 0))
            self.assertEqual(service.list_module_options(1), [])
        self.assertEqual(self.repository.list("api_modules", project_id=1)[1], 0)

    def test_named_interface_creation_does_not_create_an_empty_default_module(self) -> None:
        ApiTestingService(self.repository).create_interface({"name": "list users", "project_id": 1, "data": {"module": "Users", "method": "GET", "path": "/users"}})
        modules, total = self.repository.list("api_modules", project_id=1)
        self.assertEqual(total, 1)
        self.assertEqual(modules[0]["name"], "Users")

    def test_deleted_empty_default_is_not_recreated_by_reading_modules(self) -> None:
        module = self.repository.create("api_modules", {"name": "未分组", "project_id": 1, "data": {"module_key": "__ungrouped__", "is_ungrouped": True}})
        self.repository.delete("api_modules", module["id"])
        self.assertEqual(ApiTestingService(self.repository).list_module_options(1), [])
        self.assertEqual(self.repository.list("api_modules", project_id=1)[1], 0)

    def test_execution_records_filter_by_case_id_and_case_type(self) -> None:
        now = datetime(2026, 7, 12, 10, 0, 0)
        self.session.add_all(
            [
                ResourceRecord(
                    table_name="execution_records",
                    name="web run",
                    data_json={"data": {"case_id": 21, "case_type": "WEB"}},
                    updated_at=now,
                    created_at=now,
                ),
                ResourceRecord(
                    table_name="execution_records",
                    name="api run with same id",
                    data_json={"data": {"case_id": 21, "case_type": "API"}},
                    updated_at=now,
                    created_at=now,
                ),
            ]
        )
        self.session.commit()

        rows, total = self.repository.list(
            "execution_records",
            page=1,
            page_size=20,
            data_filters={"case_id": 21, "case_type": "WEB"},
        )

        self.assertEqual(total, 1)
        self.assertEqual(rows[0]["name"], "web run")


if __name__ == "__main__":
    unittest.main()
