import unittest

from app.models.resource_record import ResourceRecord
from app.repositories.sqlalchemy_resource_repository import SqlAlchemyResourceRepository
from app.services.api_testing_service import ApiTestingService
from app.services.project_auth_service import ProjectAuthService
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


class ApiInterfaceProjectAuthTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        ResourceRecord.__table__.create(self.engine)
        self.session = sessionmaker(bind=self.engine)()
        self.addCleanup(self.engine.dispose)
        self.addCleanup(self.session.close)
        self.repository = SqlAlchemyResourceRepository(self.session)
        self.service = ApiTestingService(self.repository)
        self.module = self.repository.create("api_modules", {"name": "Customers", "project_id": 1, "data": {"module_key": "Customers"}})
        self.other_module = self.repository.create("api_modules", {"name": "Other", "project_id": 2, "data": {"module_key": "Other"}})
        self.auth = self.auth_record(1, "API")
        self.other_auth = self.auth_record(2, "API")
        self.web_auth = self.auth_record(1, "WEB")

    def auth_record(self, project_id, case_type):
        return self.repository.create("project_auth", {"name": "auth", "project_id": project_id, "data": {"login_case_type": case_type}})

    def payload(self, auth_id):
        return {"name": "customer", "project_id": 1, "data": {"module_id": self.module["id"], "auth_id": auth_id, "path": "/customers"}}

    def test_same_project_auth_and_explicit_empty_auth_are_allowed(self):
        saved = self.service.create_interface(self.payload(str(self.auth["id"])))
        self.assertEqual(saved["data"]["auth_id"], self.auth["id"])
        self.assertEqual(saved["data"]["module_id"], self.module["id"])
        self.assertIsNone(self.service.create_interface(self.payload(None))["data"]["auth_id"])

    def test_missing_cross_project_and_non_api_auth_are_rejected_before_creation(self):
        for auth_id in (9999, self.other_auth["id"], self.web_auth["id"], "invalid"):
            with self.subTest(auth_id=auth_id), self.assertRaises(ValueError):
                self.service.create_interface(self.payload(auth_id))
        self.assertEqual(self.repository.list("api_interfaces")[1], 0)

    def test_edit_preserves_valid_auth_and_blocks_project_change_until_reselected(self):
        saved = self.service.create_interface(self.payload(self.auth["id"]))
        updated = self.service.update_interface(saved["id"], {"name": "edited", "data": {"path": "/customers/new"}})
        self.assertEqual(updated["data"]["auth_id"], self.auth["id"])
        move = {"project_id": 2, "data": {"module_id": self.other_module["id"]}}
        with self.assertRaises(ValueError):
            self.service.update_interface(saved["id"], move)
        self.assertEqual(self.repository.get("api_interfaces", saved["id"])["project_id"], 1)
        move["data"]["auth_id"] = self.other_auth["id"]
        moved = self.service.update_interface(saved["id"], move)
        self.assertEqual(moved["project_id"], 2)
        self.assertEqual(moved["data"]["auth_id"], self.other_auth["id"])

    def test_options_filter_by_project_and_api_type(self):
        options = ProjectAuthService(self.repository).list_options(1, "API")
        self.assertEqual([item["id"] for item in options], [self.auth["id"]])
