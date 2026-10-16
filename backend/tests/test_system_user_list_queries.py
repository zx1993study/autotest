import unittest
from datetime import datetime

from app.enums.business import ResourceStatusEnum
from app.models.resource_record import ResourceRecord
from app.repositories.sqlalchemy_resource_repository import SqlAlchemyResourceRepository
from app.services.system_user_service import SystemUserService
from sqlalchemy import create_engine, insert
from sqlalchemy.orm import Session


class SystemUserListQueriesTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        ResourceRecord.__table__.create(self.engine)
        self.db = Session(self.engine)
        self.service = SystemUserService(SqlAlchemyResourceRepository(self.db))

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_pagination_and_username_search_do_not_have_a_ten_thousand_limit(self):
        self.db.execute(insert(ResourceRecord), [
            {"table_name": "system_users", "name": "Real name", "status": "active",
             "updated_at": datetime(2026, 10, 15), "data_json": {"data": {"username": f"tester{key}", "password_hash": "hash"}}}
            for key in range(10005)
        ])
        self.db.commit()
        rows, total = self.service.list(keyword=None, status=None, page=501, page_size=20)
        self.assertEqual((len(rows), total), (5, 10005))
        rows, total = self.service.list(keyword="TESTER0", status=ResourceStatusEnum.ACTIVE, page=1, page_size=20)
        self.assertEqual((total, rows[0].username), (1, "tester0"))
        self.assertNotIn("password_hash", rows[0].model_dump())

    def test_search_preserves_cross_field_matching_and_literal_wildcards(self):
        self.db.add_all([
            ResourceRecord(table_name="system_users", name="Fallback", status="disabled",
                           data_json={"data": {"username": "alice", "real_name": "Bob", "phone": "100_20%"}}),
            ResourceRecord(table_name="system_users", name="Other", status="active", data_json={"data": {"username": "other"}}),
        ])
        self.db.commit()
        rows, total = self.service.list(keyword="ALICE BOB", status=None, page=1, page_size=20)
        self.assertEqual(total, 1)
        self.assertEqual(rows[0].username, "alice")
        self.assertEqual(self.service.list(keyword="_20%", status=None, page=1, page_size=20)[1], 1)
        self.assertEqual(self.service.list(keyword="alice", status=ResourceStatusEnum.ACTIVE, page=1, page_size=20)[1], 0)


if __name__ == "__main__":
    unittest.main()
