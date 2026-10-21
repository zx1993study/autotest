import hashlib
import unittest

from app.schemas.api_flow_scenario import ScenarioDefinition
from app.schemas.execution_flow import FlowDefinition
from app.services.api_flow_validation import validate_references
from bootstrap import HERE
from fixtures import MIME, change_member, speakers
from plan import ROUTES, STEPS, definition, scenario
from tests.test_api_flows import MemoryRepository


class AttendancePlanTest(unittest.TestCase):
    def setUp(self):
        self.provided = (HERE / "input" / "provided.docx").read_bytes()
        self.contents = {"provided": self.provided,
                         "present": change_member(self.provided, "test_user2", True),
                         "absent": change_member(self.provided, "test_user2", False), "invalid": b"invalid Word"}
        self.files = {key: {"field": "file", "filename": key + ".docx", "content_type": MIME,
                           "size": len(content), "sha256": hashlib.sha256(content).hexdigest()}
                      for key, content in self.contents.items()}
        self.names = {key: speakers(content) for key, content in self.contents.items() if key != "invalid"}
        self.repo = MemoryRepository()
        self.resources, apis = {}, {}
        for index, (key, (method, path, auth)) in enumerate(ROUTES.items(), 1):
            api = apis.setdefault((method, path), len(apis) + 1)
            case = index + 100
            self.resources[key] = {"api_id": api, "case_id": case}
            self.repo.tables.setdefault("api_interfaces", {})[api] = {"id": api, "project_id": 17796,
                                                                     "data": {"method": method, "path": path}}
            self.repo.tables.setdefault("api_test_cases", {})[case] = {"id": case, "source_id": api,
                "project_id": 17796, "status": "active", "data": {"auth_id": auth, "requires_flow": True}}

    def test_all_seven_branches_validate_and_keep_shared_template(self):
        flow = FlowDefinition.model_validate(definition(self.resources)).model_dump()
        for kind in ("absent", "repeat", "present", "correction", "weekly", "duplicate", "invalid"):
            with self.subTest(kind=kind):
                scene = scenario(kind, self.files, self.names, "2026-10-21", self.resources)
                data = ScenarioDefinition.model_validate(scene["data"]).model_dump()
                validate_references(self.repo, 17796, flow, data, running=True)
                self.assertEqual(list(data["nodes"]), [row[0] for row in STEPS])
                self.assertEqual(data["expected_end"], "balance_restored")
                self.assertEqual(data["failure_policy"], "stop")

    def test_documents_and_cleanup_are_bound_to_new_meeting(self):
        scene = scenario("repeat", self.files, self.names, resources=self.resources)["data"]["nodes"]
        for key in ("upload", "upload_again", "detail", "cleanup"):
            self.assertIn("{{bound_meeting_id}}", scene[key]["request"]["path"])
            self.assertEqual(scene[key]["bindings"][0]["source"], "create")
        self.assertIn("files", scene["upload"]["request"])
        self.assertFalse(any(node["request"]["path"].endswith("/attendees") for node in scene.values()))

    def test_duplicate_branch_preserves_ambiguity_without_mapping(self):
        nodes = scenario("duplicate", self.files, self.names, resources=self.resources)["data"]["nodes"]
        self.assertEqual(nodes["baseline"]["case_id"], self.resources["duplicate_accounts"]["case_id"])
        self.assertNotEqual(nodes["ambiguous_name"].get("mode"), "skip")
        self.assertTrue(any(rule.get("expected") == -500 for rule in nodes["balance"]["assertions"]))
        self.assertFalse(any(node["request"]["method"] == "PUT" for node in nodes.values()))

    def test_invalid_upload_rejects_internal_errors_and_keeps_financial_assertions(self):
        nodes = scenario("invalid", self.files, self.names, resources=self.resources)["data"]["nodes"]
        self.assertEqual(nodes["upload"]["assertions"], [{"type": "api_rejection", "expected": "validation"}])
        self.assertEqual(nodes["upload"]["request"]["files"][0], self.files["invalid"])
        self.assertTrue(any(rule["type"] == "json_number_delta" for rule in nodes["balance"]["assertions"]))

    def test_fixture_variants_do_not_change_provided_document(self):
        self.assertEqual((HERE / "input" / "provided.docx").read_bytes(), self.provided)
        self.assertIn("test_user2", self.names["present"])
        self.assertNotIn("test_user2", self.names["absent"])
        self.assertIn("test_user3", self.names["provided"])
