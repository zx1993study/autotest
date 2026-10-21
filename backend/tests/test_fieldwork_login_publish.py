import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from app.core.exceptions import BusinessRuleError
from app.services.generation_candidate_service import validate_candidate
from app.services.web_case_secret_service import WebCaseSecretService
from app.services.web_feature_testing_service import WebFeatureTestingService
from fieldwork_login_definition import (
    EXPECTED_CASES,
    PLACEHOLDERS,
    candidate,
    legacy_inputs,
)
from fieldwork_login_publish import FEATURE_ID, publish_login
from test_web_page_management_service import FakeResourceRepository

EVIDENCE = {"commit": "a" * 40, "sha256": "b" * 64, "navbar_sha256": "c" * 64}


@pytest.fixture
def repo(monkeypatch, tmp_path):
    monkeypatch.setenv("AUTOTEST_STORAGE_DIR", str(tmp_path))
    result = FakeResourceRepository()
    result.rows = {}
    result.create("web_pages", {"id": FEATURE_ID, "name": "Login", "project_id": 10,
        "data": {"url": "https://example.test/login", "feature_type": "login"}})
    for cid, outcome in EXPECTED_CASES.items():
        steps = [{"action": "fill", "locator_type": "playwright", "locator": PLACEHOLDERS[key],
                  "value": "" if key == "username" and outcome == "username" else value}
                 for key, value in (("username", "synthetic-user"), ("password", "prior-secret"))]
        result.create("web_test_cases", {"id": cid, "name": f"Legacy {cid}", "project_id": 10, "source_id": FEATURE_ID,
            "steps": steps, "data": {"steps": steps, "request": {"steps": steps}, "focus": "prior-secret", "priority": "P1"}})
    return result


def test_dry_run_does_not_mutate_cases_or_create_versions(repo):
    before = copy.deepcopy(repo.rows)
    plan = publish_login(repo, EVIDENCE)
    assert plan["version_count"] == 4
    assert repo.rows == before


def test_migration_binds_same_six_ids_and_encrypts_all_password_copies(repo):
    result = publish_login(repo, EVIDENCE, True)
    assert {row["id"] for row in repo.rows["web_test_cases"]} == set(EXPECTED_CASES)
    assert len(repo.rows["web_function_versions"]) == 4
    assert repo.get("web_pages", FEATURE_ID)["data"]["script_version"] == result["active_version"]
    for row in repo.rows["web_test_cases"]:
        assert "prior-secret" not in json.dumps(row)
        assert row["data"]["script_version"]
        assert row["priority"] == "P1"
        assert "steps" not in row["data"] and "focus" not in row["data"]
        assert row["steps"][0]["action"] == "fill"
        assert row["steps"][1]["sensitive"] is True
        assert any(step["action"] == "assert" for step in row["steps"])
        assert row["data"]["expected_steps"]
        secret = WebCaseSecretService(repo).reveal(row["data"]["secret_inputs"])["password"]
        assert secret == ("" if EXPECTED_CASES[row["id"]] in {"password", "both"} else "prior-secret")
        public = WebCaseSecretService.public_case(row)
        assert public["data"]["secret_keys"] == ["password"]
        assert "secret_inputs" not in public["data"]


def test_each_negative_case_asserts_the_correct_field_without_manual_captcha(repo):
    publish_login(repo, EVIDENCE, True)
    for cid, outcome in EXPECTED_CASES.items():
        row = repo.get("web_test_cases", cid)
        assertions = [s for s in row["steps"] if s["action"] == "assert"]
        if outcome == "success":
            manual = [s for s in row["steps"] if s["action"] == "manual"]
            assert len(manual) == 1 and manual[0]["optional"] is True
            assert "value" not in manual[0]
            assert {a["expected"] for a in assertions} == {"首页", "退出登录"}
        else:
            assert not any(s["action"] == "manual" for s in row["steps"])
            keys = ("username", "password") if outcome == "both" else (outcome,)
            assert {a["expected"] for a in assertions} == {PLACEHOLDERS[key] for key in keys}
            assert row["data"]["allow_invalid_inputs"] is True


def test_repeat_publish_preserves_versions_and_user_inputs(repo):
    first = publish_login(repo, EVIDENCE, True)
    row = repo.get("web_test_cases", 9)
    row["data"]["input_info"]["username"] = "user-edited-account"
    before = copy.deepcopy(repo.rows["web_test_cases"])
    second = publish_login(repo, EVIDENCE, True)
    assert second["active_version"] == first["active_version"]
    assert len(repo.rows["web_function_versions"]) == 4
    assert repo.rows["web_test_cases"] == before
    assert all(r["status"] == "existing" for r in second["results"])


def test_missing_credentials_and_foreign_ownership_fail_before_writes(repo):
    row = repo.get("web_test_cases", 2)
    row["steps"][1]["value"] = ""
    before = copy.deepcopy(repo.rows)
    with pytest.raises(ValueError, match="credential review"):
        publish_login(repo, EVIDENCE, True)
    assert repo.rows == before
    row["steps"][1]["value"] = "prior-secret"
    row["project_id"] = 99
    with pytest.raises(Exception, match="不属于"):
        publish_login(repo, EVIDENCE, True)
    assert not repo.rows.get("web_function_versions")


def test_existing_user_script_is_not_replaced(repo):
    WebFeatureTestingService(repo).save_version(FEATURE_ID, {"name": "User script", "steps": [
        {"action": "assert", "locator_type": "css", "locator": "body", "expected": "Custom"}]})
    before = copy.deepcopy(repo.rows)
    with pytest.raises(ValueError, match="User script"):
        publish_login(repo, EVIDENCE, True)
    assert repo.rows == before


def test_legacy_chinese_keys_are_read_without_retaining_the_old_values():
    row = {"steps": [{"元素名称": PLACEHOLDERS["username"], "元素值": "user"},
                     {"元素名称": PLACEHOLDERS["password"], "元素值": "secret"}]}
    assert legacy_inputs(row) == {"username": "user", "password": "secret"}


@pytest.mark.parametrize("action,optional", [("click", True), ("assert", True), ("manual", "true")])
def test_optional_cannot_silently_disable_assertions_or_non_manual_actions(repo, action, optional):
    value = candidate("success", EVIDENCE)
    value["steps"][2].update(action=action, optional=optional)
    with pytest.raises(BusinessRuleError, match="optional"):
        validate_candidate("WEB", value, repo.get("web_pages", FEATURE_ID))
