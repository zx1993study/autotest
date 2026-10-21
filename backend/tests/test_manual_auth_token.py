import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cryptography.fernet import Fernet
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.exception_handlers import register_exception_handlers
from app.api.v1.project_auth import router
from app.core.exceptions import BusinessRuleError, ResourceNotFoundError
from app.db.session import get_db
from app.models.resource_record import ResourceRecord
from app.repositories.sqlalchemy_resource_repository import SqlAlchemyResourceRepository
from app.services.auth_file_service import AuthFileService
from app.services.project_auth_resource_service import ProjectAuthResourceService
from app.services.project_auth_service import ProjectAuthService
from app.services.project_auth_token_service import ProjectAuthTokenService


class ManualAuthTokenTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.files = Path(self.temp.name) / "auth"
        self.files.mkdir()
        environment = patch.dict(os.environ, {"AUTOTEST_STORAGE_DIR": self.temp.name, "PROJECT_AUTH_ENCRYPTION_KEY": ""})
        environment.start()
        self.addCleanup(environment.stop)
        directory = patch("app.services.auth_file_service.AUTH_DIR", self.files)
        directory.start()
        self.addCleanup(directory.stop)
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        ResourceRecord.__table__.create(self.engine)
        self.session = sessionmaker(bind=self.engine)()
        self.addCleanup(self.engine.dispose)
        self.addCleanup(self.session.close)
        self.repository = SqlAlchemyResourceRepository(self.session)
        self.service = ProjectAuthResourceService(self.repository)

    def payload(self, token, **data):
        return {"name": "auth", "project_id": 1, "data": {"auth_type": "bearer", "token": token, **data}}

    def legacy_auth(self, filename="legacy.json", token="legacy-token"):
        AuthFileService().save_json(filename, {"token": token})
        return self.repository.create("project_auth", {"name": "legacy", "project_id": 1, "data": {"auth_type": "bearer", "token_file": filename}})

    def test_raw_and_prefixed_tokens_are_encrypted_without_json(self):
        for token in ("header.payload.signature", "Bearer header.payload.signature", "  bearer   header.payload.signature  "):
            auth = self.service.create(self.payload(token))
            raw = self.repository.get("project_auth", auth["id"])["data"]
            self.assertEqual(ProjectAuthService(self.repository).auth_headers(auth["id"]), {"Authorization": "Bearer header.payload.signature"})
            self.assertNotIn("header.payload.signature", json.dumps(raw))
            self.assertIn("token_encrypted", raw)
            self.assertNotIn("token_file", raw)
            self.assertNotIn("token_encrypted", auth["data"])
            self.assertNotIn("token", auth["data"])
            self.assertTrue(auth["data"]["token_saved"])
            self.assertEqual(auth["data"]["token_storage"], "database")
        self.assertFalse(list(self.files.iterdir()))

    def test_edit_and_blank_input_preserve_database_value(self):
        auth = self.service.create(self.payload("old-token", header_name="X-Token"))
        self.service.update(auth["id"], {"data": {"token": "Bearer new-token"}})
        self.assertEqual(ProjectAuthService(self.repository).auth_headers(auth["id"]), {"X-Token": "Bearer new-token"})
        previous = self.repository.get("project_auth", auth["id"])["data"]["token_encrypted"]
        self.service.update(auth["id"], {"description": "metadata only", "data": {"token": "", "token_encrypted": "injected"}})
        self.assertEqual(self.repository.get("project_auth", auth["id"])["data"]["token_encrypted"], previous)
        self.assertNotIn(previous, json.dumps(self.service.get(auth["id"])))
        self.assertNotIn(previous, json.dumps(self.service.list(None, None, 1, 20)[0]))

    def test_invalid_tokens_do_not_create_credentials(self):
        for token in ("Bearer", "Bearer token one", "first\nBearer second", "abc\r\nInjected: value", "a" * 16385):
            with self.subTest(length=len(token)), self.assertRaises(BusinessRuleError):
                self.service.create(self.payload(token))
        self.assertFalse(list(self.files.iterdir()))
        self.assertEqual(self.repository.list("project_auth")[1], 0)

    def test_edit_missing_auth_does_not_create_credentials(self):
        with self.assertRaises(ResourceNotFoundError):
            self.service.update(9999, self.payload("new-token"))
        self.assertFalse(list(self.files.iterdir()))

    def test_database_failure_preserves_legacy_file(self):
        auth = self.legacy_auth()
        previous = (self.files / "legacy.json").read_bytes()
        with patch.object(self.repository, "update", side_effect=RuntimeError("database failure")), self.assertRaises(RuntimeError):
            self.service.update(auth["id"], {"data": {"token": "new-token"}})
        self.assertEqual((self.files / "legacy.json").read_bytes(), previous)
        self.assertNotIn("token_encrypted", self.repository.get("project_auth", auth["id"])["data"])
        with patch.object(self.repository, "create", side_effect=RuntimeError("database failure")), self.assertRaises(RuntimeError):
            self.service.create(self.payload("new-token"))
        self.assertEqual(self.repository.list("project_auth")[1], 1)

    def test_legacy_migration_removes_only_unshared_file(self):
        auth = self.legacy_auth()
        self.service.update(auth["id"], {"data": {"token": "new-token"}})
        self.assertFalse((self.files / "legacy.json").exists())
        first = self.legacy_auth("shared.json")
        second = self.legacy_auth("shared.json")
        self.service.update(first["id"], {"data": {"token": "replacement"}})
        self.assertTrue((self.files / "shared.json").exists())
        self.assertEqual(ProjectAuthService(self.repository).auth_headers(second["id"]), {"Authorization": "Bearer legacy-token"})
        self.service.delete(second["id"])
        self.assertFalse((self.files / "shared.json").exists())

    def test_single_and_batch_delete_clean_unshared_files(self):
        first = self.legacy_auth()
        second = self.legacy_auth()
        self.service.delete(first["id"])
        self.assertTrue((self.files / "legacy.json").exists())
        third = self.legacy_auth("other.json")
        result = self.service.batch_delete([second["id"], third["id"], 9999])
        self.assertEqual(result["deleted_count"], 2)
        self.assertFalse(list(self.files.iterdir()))

    def test_delete_failure_preserves_file(self):
        auth = self.legacy_auth()
        with patch.object(self.repository, "delete", side_effect=RuntimeError("database failure")), self.assertRaises(RuntimeError):
            self.service.delete(auth["id"])
        self.assertTrue((self.files / "legacy.json").exists())

    def test_batch_cleanup_scans_references_once_and_keeps_shared_files(self):
        first = self.legacy_auth("first.json")
        second = self.legacy_auth("second.json")
        shared = self.legacy_auth("shared.json")
        keeper = self.legacy_auth("shared.json")
        with patch.object(self.repository, "list", wraps=self.repository.list) as list_items, patch.object(
            self.repository, "get", wraps=self.repository.get,
        ) as get_item:
            result = self.service.batch_delete([first["id"], second["id"], shared["id"], first["id"]])
        self.assertEqual(result, {"deleted_count": 3})
        self.assertEqual((list_items.call_count, get_item.call_count), (1, 0))
        self.assertEqual({file.name for file in self.files.iterdir()}, {"shared.json"})
        self.assertIsNotNone(self.repository.get("project_auth", keeper["id"]))

    def test_batch_delete_failure_preserves_all_files(self):
        first = self.legacy_auth("first.json")
        second = self.legacy_auth("second.json")
        with patch.object(self.repository, "batch_delete", side_effect=RuntimeError("database failure")), self.assertRaises(RuntimeError):
            self.service.batch_delete([first["id"], second["id"]])
        self.assertEqual({file.name for file in self.files.iterdir()}, {"first.json", "second.json"})

    def test_batch_cleanup_checks_later_pages_before_removing_shared_file(self):
        candidate = self.legacy_auth("shared.json")
        other = self.legacy_auth("unused.json")
        self.legacy_auth("shared.json")
        self.repository.create_many("project_auth", [{"name": f"New {key}", "data": {}} for key in range(200)])
        with patch.object(self.repository, "list", wraps=self.repository.list) as list_items:
            self.assertEqual(self.service.batch_delete([candidate["id"], other["id"]]), {"deleted_count": 2})
        self.assertEqual(list_items.call_count, 2)
        self.assertEqual({file.name for file in self.files.iterdir()}, {"shared.json"})

    def test_encrypted_auth_batch_does_not_scan_legacy_file_references(self):
        auth = self.service.create(self.payload("test-token"))
        with patch.object(self.repository, "list", wraps=self.repository.list) as list_items:
            self.assertEqual(self.service.batch_delete([auth["id"]]), {"deleted_count": 1})
        list_items.assert_not_called()

    def test_api_key_and_legacy_bearer_compatibility(self):
        auth = self.service.create(self.payload("key-value", auth_type="api_key", header_name="X-API-Key"))
        self.assertEqual(ProjectAuthService(self.repository).auth_headers(auth["id"]), {"X-API-Key": "key-value"})
        bearer = self.legacy_auth(token="bearer  legacy")
        self.assertEqual(ProjectAuthService(self.repository).auth_headers(bearer["id"]), {"Authorization": "Bearer legacy"})

    def test_wrong_or_missing_key_fails_closed(self):
        auth = self.service.create(self.payload("private-token"))
        with patch.dict(os.environ, {"PROJECT_AUTH_ENCRYPTION_KEY": Fernet.generate_key().decode()}), self.assertRaises(BusinessRuleError):
            ProjectAuthService(self.repository).auth_headers(auth["id"])
        (Path(self.temp.name) / "project-auth-secrets" / "key").unlink()
        with self.assertRaises(BusinessRuleError):
            ProjectAuthService(self.repository).auth_headers(auth["id"])

    def test_shared_environment_key_works_across_storage_roots(self):
        key = Fernet.generate_key().decode()
        with patch.dict(os.environ, {"PROJECT_AUTH_ENCRYPTION_KEY": key}):
            encrypted = ProjectAuthTokenService().encrypt("shared-token")
            with tempfile.TemporaryDirectory() as other, patch.dict(os.environ, {"AUTOTEST_STORAGE_DIR": other}):
                self.assertEqual(ProjectAuthTokenService().decrypt(encrypted), "shared-token")

    def test_login_token_generation_upserts_and_migrates(self):
        old = self.legacy_auth()
        service = ProjectAuthService(self.repository)
        payload = {"name": "legacy", "project_id": 1, "token": "login-token"}
        result = service.generate_token_auth(payload)
        self.assertEqual(result["id"], old["id"])
        self.assertFalse(list(self.files.iterdir()))
        self.assertEqual(service.auth_headers(old["id"]), {"Authorization": "Bearer login-token"})
        self.assertEqual(service.generate_token_auth({**payload, "token": "refreshed-token"})["id"], old["id"])
        self.assertEqual(self.repository.list("project_auth")[1], 1)
        self.assertNotIn("token_encrypted", result["data"])

    def test_api_create_edit_and_generate_never_return_secrets(self):
        app = FastAPI()
        register_exception_handlers(app)
        app.include_router(router, prefix="/api/v1")

        def database():
            yield self.session

        app.dependency_overrides[get_db] = database
        with TestClient(app) as client:
            response = client.post("/api/v1/project-auth", json=self.payload("Bearer mock-secret"))
            self.assertEqual(response.status_code, 200)
            self.assertNotIn("mock-secret", response.text)
            auth = response.json()["data"]
            response = client.put(f"/api/v1/project-auth/{auth['id']}", json={"data": {"token": "replacement-secret"}})
            self.assertEqual(response.status_code, 200)
            self.assertNotIn("replacement-secret", response.text)
            response = client.post("/api/v1/project-auth/generate-token", json={"name": "auth", "project_id": 1, "token": "generated-secret"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["data"]["id"], auth["id"])
            self.assertNotIn("generated-secret", response.text)
            self.assertNotIn("token_encrypted", response.text)
            self.assertFalse(list(self.files.iterdir()))
