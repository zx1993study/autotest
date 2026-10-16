import unittest

from app.models.resource_record import ResourceRecord
from app.models.test_case_record import ApiTestCaseRecord
from app.repositories.sqlalchemy_resource_repository import SqlAlchemyResourceRepository
from app.services.test_case_service import TestCaseService
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session


class CaseListBatchEnrichmentTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        ResourceRecord.__table__.create(self.engine)
        ApiTestCaseRecord.__table__.create(self.engine)
        self.db = Session(self.engine)
        self.repo = SqlAlchemyResourceRepository(self.db)
        self.service = TestCaseService("API", self.repo)
        self.db.add_all([
            ResourceRecord(id=1, table_name="projects", name="Project", data_json={}),
            ResourceRecord(id=2, table_name="api_interfaces", name="Create", project_id=1,
                           data_json={"data": {"method": "POST", "path": "/items"}}),
            ResourceRecord(id=3, table_name="project_knowledge", name="Strategy",
                           data_json={"data": {"knowledge_key": "required", "domain": "API"}}),
            ResourceRecord(id=4, table_name="project_knowledge", name="Deleted", deleted=True),
        ])
        self.db.add_all([
            ApiTestCaseRecord(name=f"Case {index}", project_id=1, source_id=2, status="active",
                              data_json={"params": {"name": "value"}}, strategy_ids_json=[3, 3, 4, 999])
            for index in range(20)
        ])
        self.db.commit()
        self.statements = []
        event.listen(self.engine, "before_cursor_execute", self.capture)

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def capture(self, connection, cursor, statement, parameters, context, many):
        self.statements.append(statement)

    def test_related_queries_are_bounded_and_keep_existing_fields(self):
        rows, total = self.service.list(None, 1, 1, 20, include_latest_execution=True)
        self.assertEqual((len(rows), total, len(self.statements)), (20, 20, 6))
        for row in rows:
            self.assertEqual(row["data"]["project_name"], "Project")
            self.assertEqual(row["data"]["api_method"], "POST")
            self.assertEqual(row["data"]["api_path"], "/items")
            self.assertEqual(row["data"]["params"], {"name": "value"})
            self.assertEqual(row["strategy_ids"], [3, 4, 999])
            self.assertEqual([item["id"] for item in row["strategies"]], [3])
            self.assertIsNone(row["latest_execution"])
        self.statements.clear()
        self.service.list(None, 1, 1, 1, include_latest_execution=True)
        self.assertEqual(len(self.statements), 6)

    def test_missing_references_and_empty_pages_do_not_trigger_individual_reads(self):
        self.db.query(ResourceRecord).filter(ResourceRecord.id.in_([1, 2])).delete()
        self.db.commit()
        rows, _ = self.service.list(None, 1, 1, 20)
        self.assertEqual(len(self.statements), 6)  # Delete plus five bounded reads.
        self.assertEqual(rows[0]["data"]["project_name"], "")
        self.assertEqual(rows[0]["data"]["api_path"], "")
        self.statements.clear()
        self.assertEqual(self.service.list(None, 1, 2, 20), ([], 20))
        self.assertEqual(len(self.statements), 2)

    def test_get_many_scopes_namespace_and_soft_deletion(self):
        self.assertEqual([row["id"] for row in self.repo.get_many("project_knowledge", [2, 3, 3, 4])], [3])
        self.assertEqual(len(self.statements), 1)
        self.statements.clear()
        self.assertEqual(self.repo.get_many("projects", []), [])
        self.assertEqual(self.statements, [])
        case_id = self.db.query(ApiTestCaseRecord.id).first()[0]
        self.assertEqual(self.repo.get_many("api_test_cases", [case_id])[0]["source_id"], 2)


if __name__ == "__main__":
    unittest.main()
