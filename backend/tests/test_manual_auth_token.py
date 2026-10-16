import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.api.exception_handlers import register_exception_handlers
from app.api.v1.project_auth import router
from app.core.exceptions import BusinessRuleError, ResourceNotFoundError
from app.db.session import get_db
from app.models.resource_record import ResourceRecord
from app.repositories.sqlalchemy_resource_repository import SqlAlchemyResourceRepository
from app.services.auth_file_service import AuthFileService
from app.services.project_auth_resource_service import ProjectAuthResourceService
from app.services.project_auth_service import ProjectAuthService
from app.utils.auth_token import normalize_auth_token
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


class ManualAuthTokenTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.files = Path(self.temp.name)
        self.auth_dir_patch = patch("app.services.auth_file_service.AUTH_DIR", self.files)
        self.auth_dir_patch.start()
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        ResourceRecord.__table__.create(self.engine)
        self.session = sessionmaker(bind=self.engine)()
        self.repository = SqlAlchemyResourceRepository(self.session)
        self.service = ProjectAuthResourceService(self.repository)

    def tearDown(self):
        self.session.close()
        self.engine.dispose()
        self.auth_dir_patch.stop()
        self.temp.cleanup()

    def payload(self, token, **data):
        return {"name": "auth", "project_id": 1, "data": {"auth_type": "bearer", "token": token, **data}}

    def test_raw_and_prefixed_token_are_normalized_without_duplicate_bearer(self):
        for token in ("header.payload.signature", "Bearer header.payload.signature", "  bearer   header.payload.signature  "):
            with self.subTest(format=token.split()[0]):
                auth = self.service.create(self.payload(token))
                filename = auth["data"]["token_file"]
                self.assertEqual(AuthFileService().load_json(filename)["token"], "header.payload.signature")
                self.assertEqual(ProjectAuthService(self.repository).auth_headers(auth["id"]), {"Authorization": "Bearer header.payload.signature"})
                self.assertNotIn("token", self.repository.get("project_auth", auth["id"])["data"])
                self.assertNotIn("header.payload.signature", json.dumps(auth))
        self.assertEqual(len(list(self.files.glob("*.json"))), 3)

    def test_edit_updates_original_file_and_blank_input_preserves_value(self):
        auth = self.service.create(self.payload("old-token", token_file="auth/original.json", header_name="X-Token"))
        filename = auth["data"]["token_file"]
        changed = self.service.update(auth["id"], {"data": {"token": "Bearer new-token"}})
        self.assertEqual(changed["data"]["token_file"], filename)
        self.assertEqual(AuthFileService().load_json(filename)["token"], "new-token")
        self.assertEqual(ProjectAuthService(self.repository).auth_headers(auth["id"]), {"X-Token": "Bearer new-token"})
        previous = (self.files / filename).read_bytes()
        self.service.update(auth["id"], {"description": "metadata only", "data": {"token": ""}})
        self.assertEqual((self.files / filename).read_bytes(), previous)
        self.assertNotIn("token", self.service.get(auth["id"])["data"])
        self.assertNotIn("token", self.service.list(None, None, 1, 20)[0][0]["data"])

    def test_invalid_or_multiple_tokens_do_not_create_files(self):
        for token in ("Bearer", "Bearer token one", "first\nBearer second", "abc\r\nInjected: value", "a" * 16385):
            with self.subTest(length=len(token)), self.assertRaises(BusinessRuleError):
                self.service.create(self.payload(token))
        self.assertFalse(list(self.files.iterdir()))

    def test_edit_missing_auth_does_not_touch_file(self):
        with self.assertRaises(ResourceNotFoundError):
            self.service.update(9999, self.payload("new-token", token_file="missing.json"))
        self.assertFalse(list(self.files.iterdir()))

    def test_database_failure_restores_original_token_file(self):
        auth = self.service.create(self.payload("old-token", token_file="original.json"))
        previous = (self.files / "original.json").read_bytes()
        with patch.object(self.repository, "update", side_effect=RuntimeError("database failure")), self.assertRaises(RuntimeError):
            self.service.update(auth["id"], {"data": {"token": "new-token"}})
        self.assertEqual((self.files / "original.json").read_bytes(), previous)
        with patch.object(self.repository, "create", side_effect=RuntimeError("database failure")), self.assertRaises(RuntimeError):
            self.service.create(self.payload("new-token", token_file="new.json"))
        self.assertFalse((self.files / "new.json").exists())
        self.assertFalse(list(self.files.glob(".auth-*")))

    def test_another_auth_cannot_overwrite_shared_filename(self):
        self.service.create(self.payload("old-token", token_file="original.json"))
        with self.assertRaises(BusinessRuleError):
            self.service.create(self.payload("new-token", token_file="auth/original.json"))
        self.assertEqual(AuthFileService().load_json("original.json")["token"], "old-token")

    def test_api_key_and_legacy_bearer_file_compatibility(self):
        auth = self.service.create(self.payload("key-value", auth_type="api_key", header_name="X-API-Key"))
        self.assertEqual(ProjectAuthService(self.repository).auth_headers(auth["id"]), {"X-API-Key": "key-value"})
        bearer = self.service.create(self.payload("raw"))
        AuthFileService().save_json(bearer["data"]["token_file"], {"token": "bearer  legacy"})
        self.assertEqual(ProjectAuthService(self.repository).auth_headers(bearer["id"]), {"Authorization": "Bearer legacy"})
        self.assertEqual(normalize_auth_token(""), "")

    def test_api_create_edit_writes_file_without_returning_secret(self):
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
            self.assertEqual(AuthFileService().load_json(auth["data"]["token_file"])["token"], "replacement-secret")
