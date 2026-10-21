import json
import tempfile
import unittest
from email import policy
from email.parser import BytesParser
from pathlib import Path
from threading import Event
from unittest.mock import patch

from app.api.dependencies import get_resource_repository
from app.api.v1.api_cases import router
from app.scheduler.jobs.api_case_executor import ApiCaseExecutor
from app.services.api_flow_runner import ApiFlowRunner
from app.services.api_request_file_service import ApiRequestFileService
from app.utils.api_multipart import multipart_bytes, request_files
from app.utils.api_number_delta import assert_number_delta
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError
from tests import test_api_flows as fixtures


class ApiRequestFilesTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.patch = patch("app.services.api_request_file_service.storage_path",
                           side_effect=lambda *parts: Path(self.directory.name).joinpath(*parts))
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.repo = fixtures.MemoryRepository()
        self.project = self.repo.create("projects", {"name": "Test"})["id"]
        self.files = ApiRequestFileService(self.repo)
        self.ref = self.files.save(self.project, "meeting.docx", "application/octet-stream", b"fixture-content")

    def test_multipart_is_real_file_and_boundary_replaces_stale_headers(self):
        headers = {"content-type": "multipart/form-data; boundary=old", "Content-Length": "1"}
        request = {"method": "POST", "project_id": self.project, "files": [self.ref],
                   "body": {"title": "测试早会", "enabled": True}}
        encoded = multipart_bytes(self.repo, request, headers)
        message = BytesParser(policy=policy.default).parsebytes(
            f"Content-Type: {headers['Content-Type']}\r\n\r\n".encode() + encoded)
        parts = {part.get_param("name", header="content-disposition"): part for part in message.iter_parts()}
        self.assertEqual(parts["file"].get_filename(), "meeting.docx")
        self.assertEqual(parts["file"].get_payload(decode=True), b"fixture-content")
        self.assertEqual(parts["title"].get_payload(decode=True).decode(), "测试早会")
        self.assertNotIn("Content-Length", headers)
        self.assertNotIn("old", headers["Content-Type"])

    def test_missing_cross_project_and_tampered_files_fail_closed(self):
        request = {"method": "POST", "project_id": self.project, "files": [self.ref]}
        other = self.repo.create("projects", {"name": "Other"})["id"]
        with self.assertRaises(ValueError):
            multipart_bytes(self.repo, {**request, "project_id": other}, {})
        path = Path(self.directory.name, "api-request-files", str(self.project), self.ref["sha256"])
        path.write_bytes(b"corrupt-content")
        with self.assertRaises(ValueError):
            multipart_bytes(self.repo, request, {})

    def test_paths_header_injection_and_unbounded_uploads_are_rejected(self):
        for changed in ({"filename": "../secret"}, {"sha256": "../secret"},
                        {"content_type": "text/plain\r\nInjected: yes"}, {"size": 0}, {"path": "C:/secret"}):
            with self.subTest(changed=changed), self.assertRaises(ValidationError):
                request_files([{**self.ref, **changed}])
        with self.assertRaises(ValueError):
            request_files([self.ref] * 5)
        for method, body in (("GET", {}), ("POST", {"nested": {"x": 1}})):
            with self.subTest(method=method), self.assertRaises(ValueError):
                multipart_bytes(self.repo, {"method": method, "body": body, "files": [self.ref]}, {})

    def test_upload_api_returns_reference_only_and_validates_empty_file(self):
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_resource_repository] = lambda: self.repo
        with TestClient(app) as client:
            response = client.post("/api-testing/cases/files", data={"project_id": self.project},
                                   files={"file": ("meeting.docx", b"fixture", "application/octet-stream")})
            self.assertEqual(response.status_code, 200)
            self.assertNotIn("fixture", response.text)
            response = client.post("/api-testing/cases/files", data={"project_id": self.project},
                                   files={"file": ("meeting.docx", b"", "application/octet-stream")})
            self.assertEqual(response.status_code, 422)


class MultipartFlowTest(unittest.TestCase):
    setUpClass = classmethod(fixtures.ApiFlowsTest.setUpClass.__func__)
    tearDownClass = classmethod(fixtures.ApiFlowsTest.tearDownClass.__func__)
    setUp = fixtures.ApiFlowsTest.setUp
    snapshot = fixtures.ApiFlowsTest.snapshot

    def test_actual_flow_sends_file_and_preserves_json_evidence(self):
        captured = []
        original = self.server.RequestHandlerClass.do_POST

        def receive(handler):
            if "multipart/form-data" not in handler.headers.get("Content-Type", ""):
                return original(handler)
            content = handler.rfile.read(int(handler.headers["Content-Length"]))
            captured.append(content)
            handler.send_json(200, {"code": 0, "data": {"id": 123}})

        with tempfile.TemporaryDirectory() as directory, patch(
            "app.services.api_request_file_service.storage_path", side_effect=lambda *parts: Path(directory).joinpath(*parts)
        ), patch.object(self.server.RequestHandlerClass, "do_POST", receive):
            ref = ApiRequestFileService(self.repo).save(self.project["id"], "meeting.docx", "application/octet-stream", b"file-only-bytes")
            snapshot = self.snapshot({"nodes": {"create": {"request": {"files": [ref]}}}})
            result = ApiFlowRunner(snapshot, Event()).run()
            self.assertEqual(result["status"], "success", result)
            self.assertIn(b"file-only-bytes", captured[0])
            self.assertNotIn("file-only-bytes", json.dumps(result))
            self.assertEqual(result["nodes"][1]["request"]["files"][0]["sha256"], ref["sha256"])

    def test_existing_json_and_urlencoded_requests_are_unchanged(self):
        executor = ApiCaseExecutor(self.repo)
        self.assertEqual(executor._body_bytes("POST", {}, {"name": "x"}), b'{"name": "x"}')
        self.assertEqual(executor._body_bytes("POST", {"Content-Type": "application/x-www-form-urlencoded"}, {"name": "x"}), b"name=x")

    def test_assertion_only_binding_does_not_add_request_parameters(self):
        snapshot = self.snapshot({"nodes": {"delete": {
            "bindings": [{"source": "create", "name": "id", "target": "variables", "path": "/baseline"}],
            "assertions": [{"type": "json_number_delta", "path": "/data/id", "baseline": "{{bound_id}}", "expected": 0}],
        }}})
        result = ApiFlowRunner(snapshot, Event()).run()
        self.assertEqual(result["status"], "success", result)
        self.assertNotIn("baseline", result["nodes"][2]["request"]["body"])


class NumberDeltaTest(unittest.TestCase):
    def test_decimal_balance_delta_and_invalid_values(self):
        spec = {"path": "/balance", "baseline": "500.10", "expected": "-500.00"}
        self.assertTrue(assert_number_delta('{"balance":"0.10"}', spec)["passed"])
        for actual in ("0.11", "NaN", "Infinity", True, None):
            self.assertFalse(assert_number_delta(json.dumps({"balance": actual}), spec)["passed"])
        self.assertFalse(assert_number_delta("{}", spec)["passed"])
