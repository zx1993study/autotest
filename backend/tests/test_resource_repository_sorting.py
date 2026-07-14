from __future__ import annotations

import unittest
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.resource_record import ResourceRecord
from app.models.test_case_record import WebTestCaseRecord
from app.repositories.sqlalchemy_resource_repository import SqlAlchemyResourceRepository


class ResourceRepositorySortingTest(unittest.TestCase):
    """Verify management lists show recently updated rows first."""

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

    def test_test_cases_sort_by_updated_at_then_id_desc(self) -> None:
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
