import json
from copy import deepcopy
from types import SimpleNamespace

import pytest

from bootstrap import HERE
from app.schemas.api_flow_scenario import ScenarioDefinition
from app.schemas.execution_flow import FlowDefinition
from app.services.api_flow_validation import validate_references
from flow_reorganization.compiler import signature
from review_plan import build
from review_assertions import convert_account
from review_rejections import append_unique
from plan import equal
from app.scheduler.jobs.api_case_executor import ApiCaseExecutor
from tests.test_api_flows import MemoryRepository


def test_review_keeps_original_scenes_and_adds_four_business_branches():
    snapshot = json.loads((HERE / "current-inventory.json").read_text(encoding="utf-8"))
    before = deepcopy(snapshot)
    groups = build(snapshot)
    assert snapshot == before
    original = {s["id"] for s in snapshot["api_flow_scenarios"] if s["data"]["flow_id"] != 21138}
    assert {b["id"] for g in groups for b in g["branches"] if b["id"]} == original
    assert len(original) == 68
    assert sum(b["id"] is None for g in groups for b in g["branches"]) == 4


def test_every_reviewed_scene_validates_before_publish():
    snapshot = json.loads((HERE / "current-inventory.json").read_text(encoding="utf-8"))
    groups, repo, cases = build(snapshot), MemoryRepository(), {}
    repo.tables["api_interfaces"] = {row["id"]: row for row in snapshot["api_interfaces"]}
    repo.tables["api_test_cases"] = {}
    for group in groups:
        for step in group["definition"]["nodes"]:
            if step["api_id"] < 0:
                original = step["api_id"]
                step["api_id"] = 50000 - original
                repo.tables["api_interfaces"][step["api_id"]] = {"id": step["api_id"], "project_id": 17796, "data": {}}
        for branch in group["branches"]:
            for step in branch["steps"]:
                key = repr((signature(step), step["auth_id"]))
                case_id = cases.setdefault(key, len(cases) + 60000)
                api_id = step["api_id"] if step["api_id"] > 0 else 50000 - step["api_id"]
                repo.tables["api_test_cases"][case_id] = {"id": case_id, "project_id": 17796, "source_id": api_id,
                                                        "status": "active", "data": {"auth_id": step["auth_id"]}}
            for item in branch["compiled"]["nodes"].values():
                if "case_key" in item:
                    item["case_id"] = cases[item.pop("case_key")]
        flow = FlowDefinition.model_validate(group["definition"]).model_dump()
        for branch in group["branches"]:
            scene = ScenarioDefinition.model_validate(branch["compiled"]).model_dump()
            validate_references(repo, 17796, flow, scene, running=True)


def test_only_new_project_ids_are_used_for_project_business_writes():
    snapshot = json.loads((HERE / "current-inventory.json").read_text(encoding="utf-8"))
    for group in build(snapshot):
        if group["group"] not in {"project", "task", "reward", "bug"}:
            continue
        for branch in group["branches"]:
            assert any(step["old_key"] == "fixture_project" for step in branch["steps"])
            assert branch["steps"][-1]["old_key"] == "cleanup_project"
            assert "4b1cca48-28f1-4e90-bb20-cce59ab7d3a7" not in json.dumps(branch)


def test_existing_relative_assertion_is_not_converted_twice():
    rule = {"type": "json_number_delta", "path": "/data/items/0/balance",
            "baseline": "{{bound_balance}}", "expected": 0}
    step = {"auth_id": 20375, "bindings": [], "assertions": [deepcopy(rule)]}
    convert_account(step, {"id": 21158}, "reward", {})
    assert step["assertions"] == [rule]


def test_empty_feature_list_checks_zero_created_and_deleted_on_each_sync():
    snapshot = json.loads((HERE / "current-inventory.json").read_text(encoding="utf-8"))
    project = next(group for group in build(snapshot) if group["group"] == "project")
    branch = next(branch for branch in project["branches"] if branch["id"] is None)
    syncs = [step for step in branch["steps"] if step["request"]["path"].endswith("/sync-dev-tasks")]
    assert len(syncs) >= 2
    for step in syncs:
        for field in ("created", "deleted", "feature_total"):
            assert equal("/data/" + field, 0) in step["assertions"]


def test_rejection_checks_are_idempotent_and_reject_wrong_reason():
    rules = [equal("/code", 400), equal("/message", "可用贝利不足")]
    assertions = [{"type": "status", "expected": 400}]
    append_unique(assertions, rules)
    append_unique(assertions, rules)
    assert len(assertions) == 3
    executor = ApiCaseExecutor(MemoryRepository())
    right = executor._assert_response(assertions, 400, {}, 1, json.dumps({"code": 400, "message": "可用贝利不足"}))
    wrong = executor._assert_response(assertions, 400, {}, 1, json.dumps({"code": 400, "message": "其他校验失败"}))
    assert all(result["passed"] for result in right)
    assert not all(result["passed"] for result in wrong)


def test_multi_meeting_cleanup_uses_only_ids_created_in_the_run(monkeypatch):
    import run

    def created(item_id):
        return {"request": {"method": "POST", "path": "/meeting/records",
                            "body": {"title": "早会文稿链路-" + item_id}},
                "outputs": {"meeting_id": item_id}}

    deleted = []
    client = SimpleNamespace(delete=lambda url, **kwargs: (
        deleted.append(url) or SimpleNamespace(status_code=200, json=lambda: {"code": 0}, raise_for_status=lambda: None)))
    monkeypatch.setattr(run, "get", lambda *_: {"title": "早会文稿链路-second"})
    result = {"nodes": [created("first"), created("second"),
                        {"request": {"method": "GET", "path": "/meeting/records/historical"},
                         "outputs": {"meeting_id": "historical"}},
                        {"request": {"method": "DELETE", "path": "/meeting/records/first"}, "response_status": 200}]}
    report = run.guarded_cleanup(client, result)
    assert len(report["meetings"]) == 2
    assert report["meetings"][0]["deleted_by_flow"] is True
    assert len(deleted) == 1 and deleted[0].endswith("/second")


def test_meeting_cleanup_refuses_unowned_title(monkeypatch):
    import run

    monkeypatch.setattr(run, "get", lambda *_: {"title": "历史会议"})
    created = {"request": {"method": "POST", "path": "/meeting/records", "body": {"title": "早会文稿链路-owned"}},
               "outputs": {"meeting_id": "owned"}}
    with pytest.raises(AssertionError, match="Unowned meeting"):
        run.guarded_cleanup(object(), {"nodes": [created]})
