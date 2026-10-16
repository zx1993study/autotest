import unittest
from datetime import datetime

from app.models.resource_record import ResourceRecord
from app.models.test_case_record import WebTestCaseRecord
from app.repositories.sqlalchemy_resource_repository import SqlAlchemyResourceRepository
from app.services.app_feature_testing_service import AppFeatureTestingService
from app.services.web_page_management_service import WebPageManagementService
from sqlalchemy import create_engine, event, insert
from sqlalchemy.orm import Session


class FeatureListQueriesTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        ResourceRecord.__table__.create(self.engine)
        WebTestCaseRecord.__table__.create(self.engine)
        self.db = Session(self.engine)
        self.repo = SqlAlchemyResourceRepository(self.db)
        self.app = AppFeatureTestingService(self.repo)
        self.web = WebPageManagementService(self.repo)
        self.statements = []
        event.listen(self.engine, "before_cursor_execute", self.capture)

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def capture(self, connection, cursor, statement, parameters, context, many):
        self.statements.append(statement)

    def resource(self, table, key, project=1, deleted=False, **data):
        row = ResourceRecord(id=key, table_name=table, name=f"Item {key}", project_id=project,
                             status="active", deleted=deleted, data_json={"data": data},
                             updated_at=datetime(2026, 10, 15))
        self.db.add(row)
        return row

    def features(self, **kwargs):
        return self.app.list_features(project_id=1, device_id=kwargs.get("device_id"), keyword=None,
                                      status=None, page=kwargs.get("page", 1), page_size=kwargs.get("page_size", 20))

    def test_app_pagination_has_no_ten_thousand_limit_or_per_feature_queries(self):
        self.db.execute(insert(ResourceRecord), [
            {"table_name": "app_features", "name": f"Item {key}", "project_id": 1,
             "status": "active", "data_json": {"data": {}}, "updated_at": datetime(2026, 10, 15)}
            for key in range(10005)
        ])
        self.db.commit()
        self.statements.clear()
        rows, total = self.features(page=501)
        self.assertEqual((len(rows), total, len(self.statements)), (5, 10005, 4))
        self.assertEqual(rows[0]["scenario_count"], 0)
        self.assertEqual(self.features(page=502), ([], 10005))

    def test_app_device_filter_and_summary_are_project_scoped(self):
        self.resource("app_features", 1, default_device_id=30)
        self.resource("app_features", 2)
        self.resource("app_features", 3)
        self.resource("app_feature_scenarios", 10, feature_id=2, device_id="30",
                      operation_steps=[{"action": "click", "evidence": "x" * 100000}],
                      last_run={"status": "failed", "updated_at": "2026-10-14"})
        self.resource("app_feature_scenarios", 11, feature_id=2, device_id=40,
                      last_run={"status": "success", "updated_at": "2026-10-15"})
        self.resource("app_feature_scenarios", 12, project=2, feature_id=3, device_id=30)
        self.resource("app_feature_scenarios", 13, deleted=True, feature_id=3, device_id=30)
        self.db.commit()
        self.statements.clear()
        rows, total = self.features(device_id=30)
        self.assertEqual((total, len(self.statements)), (2, 4))
        self.assertEqual([row["id"] for row in rows], [2, 1])
        self.assertEqual(rows[0]["scenario_count"], 2)
        self.assertEqual(rows[0]["last_run_status"], "success")
        self.assertNotIn("operation_steps", self.statements[-1])

    def test_app_scenario_device_filter_keeps_unassigned_scenarios(self):
        self.resource("app_features", 1)
        for key, device in [(10, None), (11, 30), (12, 40), (13, 0)]:
            self.resource("app_feature_scenarios", key, feature_id=1, device_id=device)
        self.resource("app_feature_scenarios", 14, feature_id=2, device_id=30)
        self.db.commit()
        rows, total = self.app.list_scenarios(1, device_id=30, keyword=None, status=None,
                                             source_type=None, page=2, page_size=2)
        self.assertEqual((total, [row["id"] for row in rows]), (3, [10]))

    def test_device_filters_do_not_treat_malformed_strings_as_device_ids(self):
        self.resource("app_features", 1, default_device_id="30junk")
        self.resource("app_features", 2, default_device_id="  +30 ")
        for key, device in [(10, "30junk"), (11, "30.5"), (12, 30.5), (13, "invalid")]:
            self.resource("app_feature_scenarios", key, feature_id=1, device_id=device)
        self.db.commit()
        self.assertEqual([row["id"] for row in self.features(device_id=30)[0]], [2, 1])
        rows, total = self.app.list_scenarios(1, device_id=40, keyword=None, status=None,
                                             source_type=None, page=1, page_size=20)
        self.assertEqual((total, [row["id"] for row in rows]), (3, [13, 11, 10]))
        self.db.query(ResourceRecord).filter(ResourceRecord.id == 12).delete()
        self.db.commit()
        self.assertEqual([row["id"] for row in self.features(device_id=30)[0]], [2])

    def test_web_filtering_counts_and_pagination_use_only_current_feature_ids(self):
        self.resource("web_page_groups", 1)
        self.resource("web_pages", 2, page_group_id=1, feature_type="add", parameters=[{}])
        self.resource("web_pages", 3, page_group_id=1, feature_type="query", script_status="verified")
        self.resource("web_pages", 4, page_group_id=1, feature_type="add")
        self.resource("web_pages", 5, project=2, page_group_id=1, feature_type="add")
        self.resource("web_elements", 10, page_id=2)
        self.resource("web_elements", 11, project=2, page_id=2)
        self.db.add_all([
            WebTestCaseRecord(name="Current", project_id=1, source_id=2),
            WebTestCaseRecord(name="Other project", project_id=2, source_id=4),
            WebTestCaseRecord(name="Deleted", project_id=1, source_id=4, deleted=True),
        ])
        self.db.commit()
        self.statements.clear()
        rows, total = self.web.list_features(1, None, None, 2, 1, feature_type="add")
        self.assertEqual((total, len(self.statements)), (2, 6))
        self.assertEqual((rows[0]["id"], rows[0]["element_count"], rows[0]["case_count"]), (2, 1, 1))
        self.assertEqual((rows[0]["script_status"], rows[0]["parameter_count"]), ("legacy", 1))
        legacy, _ = self.web.list_features(1, None, None, 1, 20, script_status="legacy")
        missing, _ = self.web.list_features(1, None, None, 1, 20, script_status="missing")
        self.assertEqual([row["id"] for row in legacy], [2])
        self.assertEqual([row["id"] for row in missing], [4])


if __name__ == "__main__":
    unittest.main()
