"""Configuration-only regression checks. No remote business requests."""
import json
from copy import deepcopy

import pytest
from catalog import classify
from compiler import flatten, merge_order, signature
from inventory import HERE, PROJECT_ID, fingerprint
from plan import build
from prerequisites import product_fixtures

# isort: split
from app.models.resource_record import ResourceRecord
from app.repositories.api_flow_snapshot_repository import ApiFlowSnapshotRepository
from app.repositories.sqlalchemy_resource_repository import SqlAlchemyResourceRepository
from app.schemas.api_flow_scenario import ScenarioDefinition
from app.schemas.execution_flow import FlowDefinition, FlowExtract
from app.services.api_flow_validation import validate_references
from app.services.api_flow_values import apply_request_override
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session


@pytest.fixture(scope="module")
def before():
    return json.loads((HERE / "before.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def plan(before):
    return build(before)


def test_every_old_flow_has_one_explicit_destination(before, plan):
    assert len(plan["decisions"]) == 138
    assert {d["flow_id"] for d in plan["decisions"]} == {f["id"] for f in before["execution_flows"]}
    scene_ids = [i for d in plan["decisions"] for i in d["scene_ids"]]
    assert len(scene_ids) == len(set(scene_ids)) == 141
    assert sum(d["destination"] == "api" for d in plan["decisions"]) == 68


def test_business_grouping_and_no_fake_execution_status(plan):
    counts = {g["key"]: len(g["branches"]) for g in plan["groups"]}
    assert counts["reward"] == 34 and counts["shop"] == 21 and counts["attendance"] == 2
    assert len(counts) == 9
    for group in plan["groups"]:
        assert 2 <= len(group["definition"]["nodes"]) <= 100
        for branch in group["branches"]:
            assert not ({"latest_status", "latest_run_id"} & branch["compiled"].keys())


def test_all_parameter_variants_stay_under_api(before, plan):
    cases = {c["id"] for c in before["api_test_cases"]}
    for decision in plan["decisions"]:
        if any(s in decision["name"] for s in ("SHOPPLUS-INPUT-", "SHOPPLUS-QTY-", "SHOPPLUS-DELIVERY-MAX")):
            assert decision["destination"] == "api"
        assert set(decision["api_case_ids"]) <= cases
    for group in plan["groups"]:
        assert all(not any(s in b["name"] for s in ("INPUT-", "QTY-", "DELIVERY-MAX")) for b in group["branches"])


def test_plan_does_not_mutate_backup(before):
    previous = fingerprint(before)
    assert build(before)["source_fingerprint"] == previous
    assert fingerprint(before) == previous


@pytest.mark.parametrize("group_key", ["shop", "reward", "attendance", "task", "project", "leave", "product", "bug", "adjust"])
def test_order_requests_assertions_auth_and_binding_targets(plan, before, group_key):
    group = next(g for g in plan["groups"] if g["key"] == group_key)
    flow = FlowDefinition.model_validate(group["definition"]).model_dump()
    case_map = {key: {"id": i + 50000, **payload} for i, (key, payload) in enumerate(plan["base_cases"].items())}
    repository = ApiFlowSnapshotRepository({"projects": [{"id": PROJECT_ID}],
        "api_interfaces": before["api_interfaces"], "api_test_cases": list(case_map.values())})
    for branch in group["branches"]:
        data = deepcopy(branch["compiled"])
        for override in data["nodes"].values():
            if "case_key" in override:
                override["case_id"] = case_map[override.pop("case_key")]["id"]
        scene = ScenarioDefinition.model_validate(data).model_dump()
        validate_references(repository, PROJECT_ID, flow, scene, running=True)
        active = [n for n in flow["nodes"] if scene["nodes"][n["key"]]["mode"] != "skip"]
        assert len(active) == len(branch["steps"])
        assert scene["expected_end"] == active[-1]["key"]
        available = {"global": set(branch["inputs"])}
        for node, original in zip(active, branch["steps"]):
            override = scene["nodes"][node["key"]]
            base = repository.get("api_test_cases", override["case_id"])
            assert base["source_id"] == node["api_id"]
            assert base["data"]["auth_id"] == original["auth_id"]
            request = deepcopy(base["data"])
            apply_request_override(request, node)
            apply_request_override(request, override)
            assert request == original["request"]
            assert override["assertions"] == original["assertions"]
            assert override["extracts"] == [FlowExtract.model_validate(e).model_dump() for e in original["extracts"]]
            assert signature(original) == (node["name"].split(" ", 1)[0], node["name"].split(" ", 1)[1])
            for binding in override["bindings"]:
                assert binding["source"] in available
                assert binding["name"] in available[binding["source"]]
            available[node["key"]] = {x["name"] for x in override["extracts"]}


def test_shop_prepares_new_products_and_never_reuses_known_fixture_ids(plan):
    products = product_fixtures()
    group = next(g for g in plan["groups"] if g["key"] == "shop")
    prepared = 0
    for branch in group["branches"]:
        prior = set()
        for step in branch["steps"]:
            body = step["request"].get("body") or {}
            if step["old_key"].startswith("fixture_product_"):
                prepared += 1
                assert "{{timestamp_ms}}" in body["name"]
            if body.get("product_id") in products:
                bind = next(b for b in step["bindings"] if b["target"] == "body" and b["path"] == "/product_id")
                assert bind["source"] in prior
            prior.add(step["old_key"])
    assert prepared >= 15


def test_attendance_creates_new_meeting_before_settlement(plan):
    group = next(g for g in plan["groups"] if g["key"] == "attendance")
    for branch in group["branches"]:
        first = branch["steps"][0]
        assert first["request"]["path"] == "/meeting/records"
        assert first["request"]["body"]["meeting_type"] == "morning"
        assert first["request"]["content_type"] == "application/x-www-form-urlencoded"
        for step in branch["steps"][1:]:
            if step["request"]["method"] == "PATCH":
                assert step["request"]["path"] == "/meeting/records/{meeting_id}/attendees"
                assert any(b["source"] == "meeting_create" and b["name"] == "meeting_id" for b in step["bindings"])


def test_unknown_flows_are_never_silently_deleted():
    with pytest.raises(ValueError, match="Unclassified"):
        classify({"id": 999, "name": "A new unknown business"})


def test_repeated_nodes_keep_order():
    combined = merge_order(list("ABACA"), list("ACBA"))
    for expected in ("ABACA", "ACBA"):
        iterator = iter(combined)
        assert all(any(value == next_value for next_value in iterator) for value in expected)


def test_all_original_scenes_flatten_without_losing_assertions(before):
    flows = {f["id"]: f for f in before["execution_flows"]}
    cases = {c["id"]: c for c in before["api_test_cases"]}
    for scene in before["api_flow_scenarios"]:
        assert flatten(flows[scene["data"]["flow_id"]], scene, cases)


@pytest.mark.parametrize("commit", [False, True])
def test_repository_commits_cannot_escape_owning_transaction(commit):
    engine = create_engine("sqlite://")

    @event.listens_for(engine, "connect")
    def sqlite_transaction_mode(connection, _):
        connection.isolation_level = None

    @event.listens_for(engine, "begin")
    def explicit_begin(connection):
        connection.exec_driver_sql("BEGIN")

    ResourceRecord.__table__.create(engine)
    with engine.connect() as connection:
        transaction = connection.begin()
        with Session(bind=connection, join_transaction_mode="create_savepoint") as db:
            repo = SqlAlchemyResourceRepository(db)
            created = repo.create("execution_flows", {"name": "Configuration only", "project_id": PROJECT_ID})
            repo.update("execution_flows", created["id"], {"status": "disabled"})
        transaction.commit() if commit else transaction.rollback()
    with Session(engine) as db:
        row = SqlAlchemyResourceRepository(db).get("execution_flows", created["id"])
        assert bool(row) is commit
    engine.dispose()
