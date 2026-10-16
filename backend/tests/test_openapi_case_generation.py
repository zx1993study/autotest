from __future__ import annotations

import unittest
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.exceptions import BusinessRuleError
from app.db.base import Base
from app.repositories.sqlalchemy_resource_repository import SqlAlchemyResourceRepository
from app.schemas.openapi_case_generation import OpenApiCaseGenerationRequest
from app.schemas.cases import CaseListQuery, TestCaseCreate
from app.scheduler.jobs.api_case_executor import ApiCaseExecutor
from app.services.api_case_template_builder import ApiCaseTemplateBuilder
from app.services.api_testing_service import ApiTestingService
from app.services.case_draft_service import CaseDraftService
from app.services.test_case_service import TestCaseService
from app.services.openapi_case_generation_service import OpenApiCaseGenerationService
from app.services.openapi_schema_service import OpenApiSchemaService
from app.utils.openapi_parser import OpenApiParser


class FakeResourceRepository:
    def __init__(self) -> None:
        self.tables: dict[str, list[dict[str, Any]]] = {}
        self.next_id = 1

    def list(
        self,
        table: str,
        keyword: str | None = None,
        project_id: int | None = None,
        page: int = 1,
        page_size: int = 20,
        data_filters: dict[str, Any] | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        rows = list(reversed(self.tables.get(table, [])))
        if project_id is not None:
            rows = [row for row in rows if row.get("project_id") == project_id]
        for key, value in (data_filters or {}).items():
            if key == "status":
                rows = [row for row in rows if row.get("status") == value]
            else:
                rows = [row for row in rows if row.get("data", {}).get(key) == value]
        start = (page - 1) * page_size
        return rows[start : start + page_size], len(rows)

    def get(self, table: str, item_id: int) -> dict[str, Any] | None:
        return next((row for row in self.tables.get(table, []) if row["id"] == item_id), None)

    def create(self, table: str, data: dict[str, Any]) -> dict[str, Any]:
        row = {
            "id": self.next_id,
            "name": data.get("name") or "Untitled",
            "project_id": data.get("project_id"),
            "description": data.get("description"),
            "status": data.get("status") or "active",
            "data": data.get("data") if isinstance(data.get("data"), dict) else {},
            **{
                key: value
                for key, value in data.items()
                if key not in {"name", "project_id", "description", "status", "data"}
            },
        }
        self.next_id += 1
        self.tables.setdefault(table, []).append(row)
        return row

    def create_many(self, table: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [self.create(table, row) for row in rows]

    def update(self, table: str, item_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
        row = self.get(table, item_id)
        if not row:
            return None
        row.update({key: value for key, value in data.items() if value is not None})
        return row

    def update_many(
        self,
        table: str,
        rows: list[tuple[int, dict[str, Any]]],
    ) -> list[dict[str, Any]]:
        return [updated for item_id, data in rows if (updated := self.update(table, item_id, data))]

    def delete(self, table: str, item_id: int) -> bool:
        return False

    def batch_delete(self, table: str, ids: list[int]) -> int:
        return 0

    def delete_by_project(self, table: str, project_id: int) -> int:
        before = len(self.tables.get(table, []))
        self.tables[table] = [row for row in self.tables.get(table, []) if row.get("project_id") != project_id]
        return before - len(self.tables[table])


def schema_document(*, version: str = "1", maximum: int = 10) -> dict[str, Any]:
    return {
        "openapi": "3.1.0",
        "info": {"title": "Demo", "version": version},
        "servers": [{"url": "/api/v1"}],
        "security": [{"bearerAuth": []}],
        "paths": {
            "/users/{userId}": {
                "parameters": [{"$ref": "#/components/parameters/UserId"}],
                "get": {
                    "operationId": "getUser",
                    "parameters": [
                        {
                            "name": "enabled",
                            "in": "query",
                            "schema": {"type": "boolean", "example": False},
                        },
                        {
                            "name": "limit",
                            "in": "query",
                            "schema": {"type": "integer", "minimum": 1, "maximum": maximum},
                        },
                        {
                            "name": "role",
                            "in": "query",
                            "required": True,
                            "schema": {"type": "string", "enum": ["admin", "user"]},
                        },
                        {
                            "name": "email",
                            "in": "query",
                            "schema": {"type": "string", "format": "email"},
                        },
                    ],
                    "responses": {
                        "200": {
                            "description": "ok",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/User"}}},
                        },
                        "400": {"description": "invalid input"},
                        "401": {"description": "unauthorized"},
                    },
                },
            }
        },
        "components": {
            "securitySchemes": {"bearerAuth": {"type": "http", "scheme": "bearer"}},
            "parameters": {
                "UserId": {
                    "name": "userId",
                    "in": "path",
                    "required": True,
                    "schema": {"type": "integer", "minimum": 1},
                }
            },
            "schemas": {"User": {"type": "object", "properties": {"id": {"type": "integer"}}}},
        },
    }


class OpenApiParserTest(unittest.TestCase):
    def test_parser_resolves_refs_and_preserves_schema_constraints(self) -> None:
        endpoint = OpenApiParser().parse(schema_document())[0]
        fields = {field["name"]: field for field in endpoint["fields"]}

        self.assertIs(fields["enabled"]["example"], False)
        self.assertEqual(fields["userId"]["schema"]["minimum"], 1)
        self.assertEqual(fields["limit"]["schema"]["maximum"], 10)
        self.assertEqual(fields["role"]["enum"], ["admin", "user"])
        self.assertEqual(fields["email"]["schema"]["format"], "email")
        self.assertEqual(endpoint["expected_statuses"], ["200", "400", "401"])
        self.assertEqual(endpoint["security"], [{"bearerAuth": []}])

    def test_parser_normalizes_all_of_recursive_refs_and_null_media_examples(self) -> None:
        document = {
            "openapi": "3.1.0",
            "info": {"title": "Tree", "version": "1"},
            "paths": {
                "/nodes": {
                    "post": {
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "example": {"name": None},
                                    "schema": {"$ref": "#/components/schemas/Node"},
                                }
                            },
                        },
                        "responses": {"201": {"description": "created"}},
                    }
                }
            },
            "components": {
                "schemas": {
                    "Named": {
                        "type": "object",
                        "required": ["name"],
                        "properties": {"name": {"type": ["string", "null"], "minLength": 2}},
                    },
                    "Node": {
                        "allOf": [
                            {"$ref": "#/components/schemas/Named"},
                            {
                                "type": "object",
                                "properties": {"child": {"$ref": "#/components/schemas/Node"}},
                            },
                        ]
                    },
                }
            },
        }

        endpoint = OpenApiParser().parse(document)[0]
        fields = {field["name"]: field for field in endpoint["fields"]}

        self.assertIsNone(fields["name"]["example"])
        self.assertTrue(fields["name"]["example_provided"])
        self.assertTrue(fields["name"]["required"])
        self.assertTrue(fields["name"]["schema"]["nullable"])
        self.assertEqual(fields["name"]["schema"]["minLength"], 2)
        child_schema = fields["child"]["schema"]
        self.assertEqual(child_schema["properties"]["child"], {"$ref": "#/components/schemas/Node"})

        self.assertIsNone(ApiCaseTemplateBuilder()._normal_value(fields["name"]))


class ApiCaseTemplateBuilderTest(unittest.TestCase):
    def test_native_case_names_contain_only_scenario_and_field_information(self) -> None:
        endpoint = OpenApiParser().parse(schema_document())[0]
        interface = {"name": "用户查询 API", "data": endpoint}
        fields = [{"name": field["name"], "data": field} for field in endpoint["fields"]]
        cases = ApiCaseTemplateBuilder().build_from_openapi(interface, fields, {"normal", "required", "boundary", "enum", "format", "type", "auth"})
        names = {case["name"] for case in cases}
        self.assertIn("[正常]", names)
        self.assertIn("[缺失必填] role", names)
        self.assertIn('[枚举值] role = "admin"', names)
        self.assertTrue(any(name.startswith("[非法枚举] role = ") for name in names))
        self.assertIn("[格式错误] email (email)", names)
        self.assertIn("[类型错误] limit", names)
        self.assertIn("[未鉴权]", names)
        for case in cases:
            self.assertNotIn("用户查询 API", case["name"])
            self.assertNotIn("GET", case["name"])
            self.assertNotIn("/users/", case["name"])
            self.assertEqual(case["path"], "/users/{userId}")

    def test_legacy_and_knowledge_case_names_also_omit_the_api_prefix(self) -> None:
        interface = {"name": "用户查询 API", "data": {"method": "GET", "path": "/users"}}
        knowledge = [{"id": 1, "name": "Token 鉴权", "data": {"category": "security"}},
                     {"id": 2, "name": "业务规则", "data": {"category": "strategy"}}]
        cases = ApiCaseTemplateBuilder().build(interface, [], "all", knowledge)
        self.assertEqual({case["name"] for case in cases}, {"[正常]", "[未登录]", "[策略场景] 业务规则"})

    def test_same_field_name_in_different_locations_has_distinct_scenario_keys(self) -> None:
        interface = {"name": "Lookup", "data": {"method": "GET", "path": "/lookup", "security": []}}
        fields = [
            {"name": "id", "data": {"name": "id", "location": "query", "schema": {"type": "integer"}}},
            {"name": "id", "data": {"name": "id", "location": "header", "schema": {"type": "integer"}}},
        ]

        cases = ApiCaseTemplateBuilder().build_from_openapi(interface, fields, {"type"})

        self.assertEqual(
            {case["openapi_scenario"]["field"] for case in cases},
            {"query.id", "header.id"},
        )

    def test_empty_security_requirement_means_auth_is_optional(self) -> None:
        interface = {"name": "Public", "data": {"method": "GET", "path": "/public", "security": [{}]}}

        cases = ApiCaseTemplateBuilder().build_from_openapi(interface, [], {"auth"})

        self.assertEqual(cases, [])


class OpenApiCaseGenerationServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = FakeResourceRepository()
        self.repository.create("projects", {"name": "Demo", "project_id": 1, "data": {}})
        self.import_result = ApiTestingService(self.repository).import_openapi(1, schema_document())
        self.service = OpenApiCaseGenerationService(self.repository)

    def request(self, **updates: Any) -> OpenApiCaseGenerationRequest:
        values: dict[str, Any] = {
            "project_id": 1,
            "snapshot_id": self.import_result["schema_snapshot_id"],
            "source_ids": [self.import_result["interfaces"][0]["id"]],
            "strategies": ["normal", "required", "boundary", "enum", "format", "type", "auth"],
        }
        values.update(updates)
        return OpenApiCaseGenerationRequest(**values)

    def test_snapshot_is_content_addressed(self) -> None:
        service = OpenApiSchemaService(self.repository)
        first = service.save_snapshot(1, schema_document(), source_type="file", source="openapi.yaml")
        second = service.save_snapshot(1, schema_document(), source_type="file", source="openapi.yaml")

        self.assertEqual(first["id"], second["id"])
        self.assertEqual(first["data"]["operation_count"], 1)

    def test_import_creates_module_records_and_links_interfaces(self) -> None:
        modules = self.repository.tables["api_modules"]
        interface = self.repository.tables["api_interfaces"][0]

        self.assertEqual(len(modules), 1)
        self.assertEqual(modules[0]["name"], "未分组")
        self.assertEqual(interface["data"]["module_id"], modules[0]["id"])

    def test_legacy_list_import_creates_and_links_module_records(self) -> None:
        repository = FakeResourceRepository()
        repository.create("projects", {"name": "Demo", "project_id": 1, "data": {}})

        result = ApiTestingService(repository).import_openapi(
            1,
            [
                {"name": "List users", "module": "Users", "method": "GET", "path": "/users"},
                {"name": "Health", "method": "GET", "path": "/health"},
            ],
        )

        modules = {item["name"]: item for item in repository.tables["api_modules"]}
        interfaces = repository.tables["api_interfaces"]
        self.assertEqual(result["interface_count"], 2)
        self.assertEqual(set(modules), {"Users", "未分组"})
        self.assertEqual(interfaces[0]["data"]["module_id"], modules["Users"]["id"])
        self.assertEqual(interfaces[1]["data"]["module_id"], modules["未分组"]["id"])

    def test_latest_snapshot_follows_current_import_when_old_content_is_reimported(self) -> None:
        first_snapshot_id = self.import_result["schema_snapshot_id"]
        ApiTestingService(self.repository).import_openapi(1, schema_document(version="2"))
        reimported = ApiTestingService(self.repository).import_openapi(1, schema_document())

        latest = OpenApiSchemaService(self.repository).latest(1)

        self.assertEqual(reimported["schema_snapshot_id"], first_snapshot_id)
        self.assertEqual(latest["id"], first_snapshot_id)

    def test_preview_explains_constraint_scenarios(self) -> None:
        preview = self.service.preview(self.request())
        strategy_names = {item["strategy"] for item in preview["items"]}
        categories = {item["category"] for item in preview["items"]}

        self.assertTrue({"normal", "required", "boundary", "enum", "format", "type", "auth"}.issubset(strategy_names))
        self.assertIn("required_missing", categories)
        self.assertIn("enum_invalid", categories)
        self.assertIn("format_invalid", categories)
        self.assertEqual(preview["summary"]["new"], preview["total"])
        self.assertFalse(preview["truncated"])

    def test_generate_only_selected_cases_and_preserves_false_example(self) -> None:
        preview = self.service.preview(self.request())
        normal = next(item for item in preview["items"] if item["strategy"] == "normal")
        result = self.service.generate(
            self.request(selected_fingerprints=[normal["fingerprint"]])
        )

        self.assertEqual(result["created_count"], 1)
        draft = self.repository.tables["case_drafts"][0]
        self.assertIs(draft["case_json"]["query"]["enabled"], False)
        metadata = draft["case_json"]["openapi_generation"]
        self.assertEqual(metadata["schema_hash"], self.import_result["schema_hash"])
        self.assertEqual(len(metadata["fingerprint"]), 64)

    def test_repeat_generation_is_idempotent(self) -> None:
        first = self.service.generate(self.request(strategies=["normal"]))
        second = self.service.generate(self.request(strategies=["normal"]))

        self.assertEqual(first["created_count"], 1)
        self.assertEqual(second["draft_count"], 0)
        self.assertEqual(second["skipped_count"], 1)
        self.assertEqual(len(self.repository.tables["case_drafts"]), 1)

    def test_preview_saved_draft_and_accepted_case_keep_the_short_name(self) -> None:
        preview = self.service.preview(self.request(strategies=["required"]))
        self.assertEqual(preview["items"][0]["name"], "[缺失必填] role")
        generated = self.service.generate(self.request(strategies=["required"]))
        draft = self.repository.get("case_drafts", generated["draft_ids"][0])
        self.assertEqual(draft["name"], "[缺失必填] role")
        accepted = CaseDraftService("API", self.repository).accept(draft["id"])
        self.assertEqual(accepted["name"], "[缺失必填] role")

    def test_new_schema_updates_matching_unreviewed_draft(self) -> None:
        first = self.service.generate(self.request(strategies=["normal"]))
        first_draft_id = first["draft_ids"][0]
        updated_schema = schema_document(version="2", maximum=20)
        imported = ApiTestingService(self.repository).import_openapi(1, updated_schema)

        result = self.service.generate(
            OpenApiCaseGenerationRequest(
                project_id=1,
                snapshot_id=imported["schema_snapshot_id"],
                source_ids=[imported["interfaces"][0]["id"]],
                strategies=["normal"],
            )
        )

        self.assertEqual(result["created_count"], 0)
        self.assertEqual(result["updated_count"], 1)
        self.assertEqual(result["draft_ids"], [first_draft_id])
        self.assertEqual(len(self.repository.tables["case_drafts"]), 1)
        metadata = self.repository.tables["case_drafts"][0]["case_json"]["openapi_generation"]
        self.assertEqual(metadata["schema_hash"], imported["schema_hash"])

    def test_stale_preview_fingerprint_is_rejected(self) -> None:
        with self.assertRaisesRegex(BusinessRuleError, "重新预览"):
            self.service.generate(self.request(selected_fingerprints=["0" * 64]))


class SqlAlchemyOpenApiCaseGenerationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.session = sessionmaker(bind=self.engine)()
        self.repository = SqlAlchemyResourceRepository(self.session)
        self.repository.create("projects", {"name": "Demo"})

    def tearDown(self) -> None:
        self.session.close()
        self.engine.dispose()

    def test_persisted_generation_is_detected_as_unchanged(self) -> None:
        imported = ApiTestingService(self.repository).import_openapi(1, schema_document())
        request = OpenApiCaseGenerationRequest(
            project_id=1,
            snapshot_id=imported["schema_snapshot_id"],
            source_ids=[imported["interfaces"][0]["id"]],
            strategies=["normal"],
        )
        service = OpenApiCaseGenerationService(self.repository)

        created = service.generate(request)
        preview = service.preview(request)

        self.assertEqual(created["created_count"], 1)
        self.assertEqual(preview["summary"], {"new": 0, "update": 0, "unchanged": 1})

    def test_generated_drafts_are_visible_for_their_source_api_and_review_status(self) -> None:
        imported = ApiTestingService(self.repository).import_openapi(1, schema_document())
        source_id = imported["interfaces"][0]["id"]
        generated = OpenApiCaseGenerationService(self.repository).generate(
            OpenApiCaseGenerationRequest(
                project_id=1,
                snapshot_id=imported["schema_snapshot_id"],
                source_ids=[source_id],
                strategies=["normal"],
            )
        )
        query = CaseListQuery(project_id=1, source_id=source_id, status="draft")
        service = CaseDraftService("API", self.repository)
        rows, total = service.list(1, None, 1, 20, query.status, query.source_id)

        self.assertEqual(total, generated["created_count"])
        self.assertEqual([row["id"] for row in rows], generated["draft_ids"])
        self.assertEqual(service.list(1, None, 1, 20, source_id=source_id + 1000)[1], 0)

        service.accept(rows[0]["id"])
        self.assertEqual(service.list(1, None, 1, 20, "draft", source_id)[1], 0)
        accepted, accepted_total = service.list(1, None, 1, 20, "accepted", source_id)
        self.assertEqual(accepted_total, 1)
        self.assertEqual(accepted[0]["id"], generated["draft_ids"][0])

    def test_manually_created_api_case_can_be_listed_and_built_for_execution(self) -> None:
        self.repository.update("projects", 1, {"data": {"base_url": "https://example.test"}})
        interface = self.repository.create("api_interfaces", {
            "name": "Create customer", "project_id": 1,
            "data": {"method": "POST", "path": "/customers", "content_type": "application/json"},
        })
        service = TestCaseService("API", self.repository)
        payload = TestCaseCreate(
            project_id=1, source_id=interface["id"], name="Manual customer case",
            data={"method": "POST", "path": "/customers", "params": {"name": "Customer", "enabled": False}},
            assertions=[{"type": "status", "expected": 201}],
        )
        created = service.create(payload.model_dump())
        rows, total = service.list(None, 1, 1, 20, source_id=interface["id"], status="active")

        self.assertEqual(total, 1)
        self.assertEqual(rows[0]["id"], created["id"])
        self.assertEqual(rows[0]["assertions"], [{"type": "status", "expected": 201}])
        request = ApiCaseExecutor(self.repository)._build_api_request(rows[0], {})
        self.assertEqual(request["method"], "POST")
        self.assertEqual(request["body"], {"name": "Customer", "enabled": False})


class ApiCaseExecutorAssertionTest(unittest.TestCase):
    def test_generated_status_assertions_are_enforced(self) -> None:
        executor = ApiCaseExecutor.__new__(ApiCaseExecutor)
        results = executor._assert_response(
            [
                {"type": "status_in", "expected": ["2XX", "404"]},
                {"type": "content_type_in", "expected": ["application/json"]},
                {"type": "unsupported_type"},
            ],
            404,
            {"Content-Type": "application/json; charset=utf-8"},
            20,
            "{}",
        )

        self.assertTrue(results[0]["passed"])
        self.assertTrue(results[1]["passed"])
        self.assertFalse(results[2]["passed"])


if __name__ == "__main__":
    unittest.main()
