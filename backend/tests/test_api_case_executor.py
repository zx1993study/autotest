from __future__ import annotations

import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from typing import Any
from unittest.mock import patch

from app.scheduler.jobs.api_case_executor import ApiCaseExecutor


class FakeResourceRepository:
    """Repository double that captures execution records for API executor tests."""

    def __init__(self) -> None:
        self.records: list[dict[str, Any]] = []
        self.items: dict[str, dict[int, dict[str, Any]]] = {
            "projects": {
                1: {
                    "id": 1,
                    "name": "演示项目",
                    "data": {"base_url": "https://example.test"},
                }
            },
            "api_interfaces": {
                10: {
                    "id": 10,
                    "name": "创建仓库",
                    "project_id": 1,
                    "data": {"method": "POST", "path": "/warehouses", "content_type": "application/json"},
                }
            },
        }
        self.fields = [
            {"id": 1, "name": "name", "project_id": 1, "data": {"interface_id": 10, "name": "name", "location": "body"}},
            {"id": 2, "name": "type", "project_id": 1, "data": {"interface_id": 10, "name": "type", "location": "body"}},
        ]

    def list(
        self,
        table: str,
        keyword: str | None = None,
        project_id: int | None = None,
        page: int = 1,
        page_size: int = 20,
        data_filters: dict[str, Any] | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        del keyword, page, page_size, data_filters
        if table == "api_fields":
            rows = [item for item in self.fields if project_id is None or item.get("project_id") == project_id]
            return rows, len(rows)
        rows = list(self.items.get(table, {}).values())
        if project_id is not None:
            rows = [item for item in rows if item.get("project_id") == project_id]
        return rows, len(rows)

    def get(self, table: str, item_id: int) -> dict[str, Any] | None:
        return self.items.get(table, {}).get(item_id)

    def create(self, table: str, data: dict[str, Any]) -> dict[str, Any]:
        self.records.append({"table": table, **data})
        return {"id": len(self.records), **data}

    def create_many(self, table: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [self.create(table, row) for row in rows]

    def update(self, table: str, item_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
        raise NotImplementedError

    def delete(self, table: str, item_id: int) -> bool:
        raise NotImplementedError

    def batch_delete(self, table: str, ids: list[int]) -> int:
        raise NotImplementedError

    def delete_by_project(self, table: str, project_id: int) -> int:
        raise NotImplementedError


class StubApiCaseExecutor(ApiCaseExecutor):
    """Avoid real HTTP while still exercising request assembly."""

    def _send_http_request(self, request_info: dict[str, Any]) -> tuple[int, dict[str, str], str]:
        return 200, {"Content-Type": "application/json"}, '{"ok": true}'


class ApiCaseExecutorTest(unittest.TestCase):
    def authenticated_fixture(self) -> tuple[FakeResourceRepository, dict[str, Any]]:
        repository = FakeResourceRepository()
        repository.items["project_auth"] = {
            101: {"id": 101, "project_id": 1, "data": {"auth_type": "bearer", "token": "interface-token"}},
            102: {"id": 102, "project_id": 1, "data": {"auth_type": "bearer", "token": "case-token"}},
            103: {"id": 103, "project_id": 1, "data": {"auth_type": "api_key", "header_name": "X-Token", "token": "runtime-token"}},
        }
        repository.items["api_interfaces"][10]["data"]["auth_id"] = 101
        case = {
            "id": 99, "name": "认证场景", "project_id": 1, "source_id": 10,
            "data": {"params": {"name": "test"}}, "assertions": [{"type": "status", "expected": 200}],
        }
        return repository, case

    def test_inherits_interface_token(self) -> None:
        repository, case = self.authenticated_fixture()
        request = StubApiCaseExecutor(repository)._build_api_request(case, {})
        self.assertEqual(request["headers"]["Authorization"], "Bearer interface-token")

    def test_selected_case_token_overrides_interface_and_manual_header(self) -> None:
        repository, case = self.authenticated_fixture()
        case["data"].update({"auth_id": 102, "headers": {"authorization": "Bearer outdated"}})
        request = StubApiCaseExecutor(repository)._build_api_request(case, {})
        self.assertEqual(request["headers"]["Authorization"], "Bearer case-token")
        self.assertNotIn("authorization", request["headers"])

    def test_runtime_auth_overrides_selected_case_token(self) -> None:
        repository, case = self.authenticated_fixture()
        case["data"]["auth_id"] = 102
        request = StubApiCaseExecutor(repository)._build_api_request(case, {"auth_id": 103})
        self.assertEqual(request["headers"]["X-Token"], "runtime-token")
        self.assertNotIn("Authorization", request["headers"])

    def test_explicit_no_auth_skips_case_interface_and_runtime_tokens(self) -> None:
        repository, case = self.authenticated_fixture()
        case["data"].update({"auth_id": 102, "skip_auth": True})
        request = StubApiCaseExecutor(repository)._build_api_request(case, {"auth_id": 103})
        self.assertNotIn("Authorization", request["headers"])
        self.assertNotIn("X-Token", request["headers"])

    def test_inherit_selection_clears_legacy_case_auth(self) -> None:
        repository, case = self.authenticated_fixture()
        case["data"].update({"request": {"auth_id": 102, "skip_auth": True}, "auth_id": None, "skip_auth": False})
        request = StubApiCaseExecutor(repository)._build_api_request(case, {})
        self.assertEqual(request["headers"]["Authorization"], "Bearer interface-token")

    def test_selected_token_is_loaded_from_auth_file(self) -> None:
        repository, case = self.authenticated_fixture()
        repository.items["project_auth"][102]["data"] = {"auth_type": "bearer", "token_file": "test-auth.json"}
        case["data"]["auth_id"] = 102
        with patch("app.services.project_auth_service.AuthFileService.load_json", return_value={"token": "Bearer file-token"}):
            request = StubApiCaseExecutor(repository)._build_api_request(case, {})
        self.assertEqual(request["headers"]["Authorization"], "Bearer file-token")

    def test_missing_or_empty_selected_auth_fails_before_sending(self) -> None:
        for auth_id in (999, 102):
            with self.subTest(auth_id=auth_id):
                repository, case = self.authenticated_fixture()
                repository.items["project_auth"][102]["data"] = {"auth_type": "bearer"}
                case["data"]["auth_id"] = auth_id
                executor = StubApiCaseExecutor(repository)
                with patch.object(executor, "_send_http_request") as send:
                    record = executor.execute(case, {})
                send.assert_not_called()
                self.assertEqual(record["status"], "failed")
                self.assertIn("认证", record["data"]["error"])

    def test_selected_token_authenticates_actual_http_request(self) -> None:
        received: list[str | None] = []

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                self.rfile.read(int(self.headers.get("Content-Length", "0")))
                token = self.headers.get("Authorization")
                received.append(token)
                self.send_response(200 if token == "Bearer case-token" else 401)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"ok": true}')

            def log_message(self, format: str, *args: Any) -> None:
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        worker = Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            repository, case = self.authenticated_fixture()
            repository.items["projects"][1]["data"]["base_url"] = f"http://127.0.0.1:{server.server_port}"
            case["data"].update({"auth_id": 102, "skip_auth": False})
            executor = ApiCaseExecutor(repository)
            record = executor.execute(case, {})
            self.assertEqual(record["status"], "success")
            self.assertEqual(record["data"]["response_status"], 200)
            self.assertEqual(received, ["Bearer case-token"])
            case["data"]["skip_auth"] = True
            unauthenticated = executor.execute(case, {})
            self.assertEqual(unauthenticated["data"]["response_status"], 401, unauthenticated["data"].get("error"))
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=2)

    def test_config_params_override_saved_case_params(self) -> None:
        repository = FakeResourceRepository()
        executor = StubApiCaseExecutor(repository)
        case = {
            "id": 99,
            "name": "创建仓库成功",
            "project_id": 1,
            "source_id": 10,
            "data": {
                "method": "POST",
                "path": "/warehouses",
                "params": {"name": "旧名称", "type": "old"},
            },
            "assertions": [{"type": "status", "expected": 200}],
        }

        record = executor.execute(
            case,
            {
                "project_id": 1,
                "case_ids": [99],
                "config": {"params": {"name": "新名称", "type": "normal"}},
            },
        )

        request_body = record["data"]["request"]["body"]
        self.assertEqual(request_body, {"name": "新名称", "type": "normal"})


if __name__ == "__main__":
    unittest.main()
