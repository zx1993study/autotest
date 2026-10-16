import unittest

from app.db.base import Base
from app.repositories.sqlalchemy_resource_repository import SqlAlchemyResourceRepository
from app.services.web_feature_testing_service import WebFeatureTestingService
from app.services.web_page_management_service import WebPageManagementService
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from web_automation.compiler import ExecutionPlanCompiler


class WebFeatureStorageTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.repo = SqlAlchemyResourceRepository(self.db)
        self.service = WebFeatureTestingService(self.repo)
        group = WebPageManagementService(self.repo).create_group({"name": "Customers", "project_id": 1, "url": "https://example.test/customers"})
        self.feature = self.service.save_feature(group["id"], {"name": "Add", "parameters": [{"key": "name", "label": "Name", "type": "text", "required": True}]})
        self.candidate = {"name": "Add", "input_info": {"name": "Default"}, "steps": [{"action": "fill", "locator_type": "label", "locator": "Name", "value": "{{name}}"}, {"action": "assert", "locator_type": "text", "locator": "Saved", "expected": "Saved"}]}
        self.version = self.service.save_version(self.feature["id"], self.candidate)

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_persisted_case_is_visible_and_compiles_with_its_inputs(self):
        saved = self.service.save_case(self.feature["id"], {"name": "Case", "input_info": {"name": "Customer"}})
        self.db.expire_all()
        detail = self.service.detail(self.feature["id"])
        self.assertEqual([saved["id"]], [c["id"] for c in detail["cases"]])
        self.assertEqual(self.version["id"], detail["versions"][0]["id"])
        compiled = ExecutionPlanCompiler().compile({"cases": detail["cases"]})
        self.assertEqual("Customer", compiled.cases[0].steps[0]["value"])
        self.assertEqual("https://example.test/customers", compiled.cases[0].target_url)

    def test_delete_does_not_leave_visible_case_or_version_rows(self):
        self.service.save_case(self.feature["id"], {"name": "Case", "input_info": {"name": "Customer"}})
        self.service.delete_feature(self.feature["id"])
        self.assertIsNone(self.repo.get("web_pages", self.feature["id"]))
        self.assertEqual(0, self.repo.list("web_test_cases", project_id=1)[1])
        self.assertEqual(0, self.repo.list("web_function_versions", project_id=1)[1])


if __name__ == "__main__":
    unittest.main()
