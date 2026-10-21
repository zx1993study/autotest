import copy
import importlib.util
from pathlib import Path

import pytest
from app.services.web_feature_testing_service import WebFeatureTestingService
from app.services.web_page_management_service import WebPageManagementService
from test_web_page_management_service import FakeResourceRepository

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("fieldwork_publish", ROOT / "scripts/fieldwork_web_publish.py")
publish = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(publish)


@pytest.fixture
def context():
    repo = FakeResourceRepository()
    repo.rows = {}
    group = WebPageManagementService(repo).create_group({"name": "Warehouse", "project_id": 1,
                                                        "url": "https://example.test/warehouse"})
    service = WebFeatureTestingService(repo)
    feature = service.save_feature(group["id"], {"name": "Query", "feature_type": "query"})
    case = repo.create("web_test_cases", {"name": "Existing", "project_id": 1, "source_id": feature["id"],
        "data": {"steps": [{"action": "fill", "locator": "Old", "value": "WH001"}], "priority": "P1"}})
    candidate = {"name": "Query", "url": "https://example.test/warehouse", "steps": [
        {"action": "fill", "locator_type": "css", "locator": "input", "value": "{{warehouseCode}}"},
        {"action": "assert", "locator_type": "css", "locator": ".table", "expected": "{{warehouseCode}}"}]}
    plan = {"feature_id": feature["id"], "candidate": candidate, "commit": "a" * 40}
    linked = {"case_id": case["id"], "candidate": candidate, "input_info": {"warehouseCode": "WH001"},
              "search_fields": [{"key": "warehouseCode", "label": "Code"}]}
    snapshot = {"project_id": 1, "features": [copy.deepcopy(feature)], "cases": [publish.public_case(case)]}
    return repo, plan, linked, snapshot


def test_dry_run_never_writes_versions_or_cases(context):
    repo, plan, linked, snapshot = context
    old = copy.deepcopy(repo.rows)
    result = publish.publish_one(repo, plan, linked, snapshot, False)
    assert result["status"] == "planned"
    assert repo.rows == old


def test_publish_pins_same_case_and_retains_legacy_steps_and_priority(context):
    repo, plan, linked, snapshot = context
    original = copy.deepcopy(repo.get("web_test_cases", linked["case_id"]))
    result = publish.publish_one(repo, plan, linked, snapshot, True)
    assert result["status"] == "published_draft"
    saved = repo.get("web_test_cases", linked["case_id"])
    assert len(repo.rows["web_test_cases"]) == 1
    assert saved["id"] == original["id"] and saved["name"] == original["name"]
    assert saved["priority"] == "P1"
    assert saved["data"]["input_info"] == {"warehouseCode": "WH001"}
    assert saved["data"]["source_legacy_steps"] == original["data"]["steps"]
    assert saved["data"]["script_version"] == result["version_id"]
    assert repo.get("web_function_versions", result["version_id"])["status"] == "draft"


def test_repeat_publish_is_idempotent(context):
    repo, plan, linked, snapshot = context
    first = publish.publish_one(repo, plan, linked, snapshot, True)
    second = publish.publish_one(repo, plan, linked, snapshot, True)
    assert second["status"] == "existing"
    assert second["version_id"] == first["version_id"]
    assert len(repo.rows["web_function_versions"]) == 1


def test_user_version_is_never_overwritten(context):
    repo, plan, linked, snapshot = context
    candidate = copy.deepcopy(plan["candidate"])
    candidate["steps"][-1]["expected"] = "User assertion"
    old = WebFeatureTestingService(repo).save_version(plan["feature_id"], candidate, parameters=[])
    result = publish.publish_one(repo, plan, linked, snapshot, True)
    assert result["status"] == "existing_version_preserved"
    assert repo.get("web_pages", plan["feature_id"])["data"]["script_version"] == old["id"]


def test_edited_case_is_not_silently_migrated(context):
    repo, plan, linked, snapshot = context
    repo.update("web_test_cases", linked["case_id"], {"name": "Edited by user"})
    result = publish.publish_one(repo, plan, linked, snapshot, True)
    assert result["status"] == "case_conflict"
    assert repo.rows.get("web_function_versions", []) == []


def test_edited_target_url_is_not_overwritten(context):
    repo, plan, linked, snapshot = context
    row = repo.get("web_pages", plan["feature_id"])
    row["data"]["url"] = "https://example.test/other"
    result = publish.publish_one(repo, plan, linked, snapshot, True)
    assert result["status"] == "metadata_conflict"
    assert repo.rows.get("web_function_versions", []) == []
