import unittest
from unittest.mock import patch

from app.api.dependencies import get_api_module_repository
from app.api.exception_handlers import register_exception_handlers
from app.api.v1.api_modules import router
from app.core.exceptions import BusinessRuleError, ResourceNotFoundError
from app.models.resource_record import ResourceRecord
from app.repositories.sqlalchemy_api_module_repository import (
    SqlAlchemyApiModuleRepository,
)
from app.schemas.api_module import ApiModuleSaveRequest
from app.services.api_module_service import ApiModuleService
from app.services.api_testing_service import ApiTestingService
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


class ApiModuleServiceTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        ResourceRecord.__table__.create(self.engine)
        self.session = sessionmaker(bind=self.engine)()
        self.repository = SqlAlchemyApiModuleRepository(self.session)
        self.service = ApiModuleService(self.repository)
        self.project = self.repository.create("projects", {"name": "project"})["id"]
        self.other_project = self.repository.create("projects", {"name": "other"})["id"]

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def payload(self, name, project_id=None):
        return ApiModuleSaveRequest(project_id=project_id or self.project, name=name, description="description")

    def test_create_trimmed_module_and_duplicate_name(self):
        module = self.service.create(self.payload("  Customers  "))
        self.assertEqual(module["name"], "Customers")
        self.assertEqual(module["data"]["module_key"], "Customers")
        with self.assertRaises(BusinessRuleError):
            self.service.create(self.payload("customers"))
        self.assertEqual(self.service.create(self.payload("Customers", self.other_project))["project_id"], self.other_project)

    def test_schema_rejects_empty_name_invalid_project_and_extra_fields(self):
        for values in ({"name": " "}, {"project_id": 0}, {"name": "a" * 129}, {"unexpected": True}):
            with self.subTest(values=values), self.assertRaises(ValidationError):
                ApiModuleSaveRequest(**{"project_id": self.project, "name": "valid", **values})

    def test_missing_project_and_cross_project_edit_rejected(self):
        with self.assertRaises(ResourceNotFoundError):
            self.service.create(self.payload("module", 99999))
        module = self.service.create(self.payload("module"))
        with self.assertRaises(ResourceNotFoundError):
            self.service.update(module["id"], self.payload("renamed", self.other_project))
        with self.assertRaises(ResourceNotFoundError):
            self.service.delete(self.other_project, module["id"])

    def test_reserved_module_cannot_be_created_edited_or_deleted(self):
        for name in ("__ungrouped__", "未分组"):
            with self.subTest(name=name), self.assertRaises(BusinessRuleError):
                self.service.create(self.payload(name))
        ungrouped = self.repository.create("api_modules", {"name": "未分组", "project_id": self.project, "data": {"module_key": "__ungrouped__", "is_ungrouped": True}})
        with self.assertRaises(BusinessRuleError):
            self.service.update(ungrouped["id"], self.payload("rename"))
        with self.assertRaises(BusinessRuleError):
            self.service.delete(self.project, ungrouped["id"])

    def test_rename_preserves_id_and_updates_linked_and_legacy_interfaces(self):
        module = self.service.create(self.payload("old"))
        linked = self.repository.create("api_interfaces", {"name": "linked", "project_id": self.project, "data": {"module_id": module["id"], "module": "old", "path": "/customers"}})
        legacy = self.repository.create("api_interfaces", {"name": "legacy", "project_id": self.project, "data": {"module": "old", "method": "POST"}})
        renamed = self.service.update(module["id"], self.payload("new"))
        self.assertEqual(renamed["id"], module["id"])
        for item in (linked, legacy):
            data = self.repository.get("api_interfaces", item["id"])["data"]
            self.assertEqual(data["module"], "new")
            self.assertEqual(data["module_id"], module["id"])
        self.assertEqual(self.repository.get("api_interfaces", linked["id"])["data"]["path"], "/customers")
        names = [item["name"] for item in ApiTestingService(self.repository).list_module_options(self.project)]
        self.assertIn("new", names)
        self.assertNotIn("old", names)

    def test_used_module_cannot_be_deleted_and_no_interface_is_removed(self):
        module = self.service.create(self.payload("used"))
        interface = self.repository.create("api_interfaces", {"name": "api", "project_id": self.project, "data": {"module_id": module["id"]}})
        with self.assertRaisesRegex(BusinessRuleError, "1 个 API"):
            self.service.delete(self.project, module["id"])
        self.assertIsNotNone(self.repository.get("api_modules", module["id"]))
        self.assertIsNotNone(self.repository.get("api_interfaces", interface["id"]))

    def test_legacy_reference_also_prevents_deletion(self):
        module = self.service.create(self.payload("legacy"))
        self.repository.create("api_interfaces", {"name": "api", "project_id": self.project, "data": {"module": "legacy"}})
        with self.assertRaises(BusinessRuleError):
            self.service.delete(self.project, module["id"])

    def test_empty_module_can_be_deleted(self):
        module = self.service.create(self.payload("empty"))
        self.assertTrue(self.service.delete(self.project, module["id"]))
        self.assertIsNone(self.repository.get("api_modules", module["id"]))
        self.assertNotIn(module["id"], [item["id"] for item in ApiTestingService(self.repository).list_module_options(self.project)])

    def test_rename_rolls_back_module_and_interface_on_commit_failure(self):
        module = self.service.create(self.payload("old"))
        interface = self.repository.create("api_interfaces", {"name": "api", "project_id": self.project, "data": {"module_id": module["id"], "module": "old"}})
        with patch.object(self.session, "commit", side_effect=RuntimeError("database failure")), self.assertRaises(RuntimeError):
            self.service.update(module["id"], self.payload("new"))
        self.assertEqual(self.repository.get("api_modules", module["id"])["name"], "old")
        self.assertEqual(self.repository.get("api_interfaces", interface["id"])["data"]["module"], "old")

    def test_api_create_update_delete_and_validation_error_contract(self):
        app = FastAPI()
        register_exception_handlers(app)
        app.include_router(router, prefix="/api/v1")
        app.dependency_overrides[get_api_module_repository] = lambda: self.repository
        with TestClient(app) as client:
            path = "/api/v1/api-testing/interfaces/modules"
            created = client.post(path, json=self.payload("api module").model_dump())
            self.assertEqual(created.status_code, 200)
            item_id = created.json()["data"]["id"]
            edited = client.put(f"{path}/{item_id}", json=self.payload("renamed").model_dump())
            self.assertEqual(edited.json()["data"]["name"], "renamed")
            duplicate = client.post(path, json=self.payload("renamed").model_dump())
            self.assertEqual(duplicate.status_code, 400)
            self.assertEqual(client.post(path, json={"project_id": 0, "name": "bad"}).status_code, 422)
            self.assertEqual(client.delete(f"{path}/{item_id}", params={"project_id": self.other_project}).status_code, 404)
            self.assertTrue(client.delete(f"{path}/{item_id}", params={"project_id": self.project}).json()["data"])
