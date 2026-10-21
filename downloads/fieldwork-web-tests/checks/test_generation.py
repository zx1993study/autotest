import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("fieldwork_source_build", ROOT / "tools/build.py")
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


def test_existing_case_ids_are_preserved_without_secrets():
    snapshot = build.read("platform-snapshot.json")
    catalog = build.read("catalog.json")
    assert {case["id"] for case in snapshot["cases"]} == {case["case_id"] for case in catalog["cases"]}
    assert len({case["case_id"] for case in catalog["cases"]}) == len(catalog["cases"])
    for case in snapshot["cases"]:
        assert all(step["value"] is None for step in case["steps"] if step.get("sensitive"))
    assert "Bearer " not in json.dumps(catalog)


def test_name_action_mismatch_cannot_become_list_smoke():
    catalog = build.read("catalog.json")
    feature = next(item for item in catalog["features"] if item["feature_id"] == 11880)
    assert feature["status"] == "blocked"
    assert feature["candidate"] is None


def test_original_warehouse_query_value_and_real_toolbar_are_used():
    case = next(item for item in build.read("catalog.json")["cases"] if item["case_id"] == 31)
    assert case["input_info"] == {"warehouseCode": "WH001"}
    assert any("unified-list__field" in step["locator"] for step in case["candidate"]["steps"])
    assert any(step.get("expected") == "{{warehouseCode}}" for step in case["candidate"]["steps"])
    assert not any("请输入仓库编码" in step["locator"] for step in case["candidate"]["steps"])


def test_no_mutation_is_silently_replaced_by_readonly_script():
    for feature in build.read("catalog.json")["features"]:
        if feature["feature_type"] not in {"page", "query"}:
            assert feature["status"] == "blocked"
        if feature["status"] == "source_ready":
            assert feature["source_sha256"] and feature["commit"]
            assert all(step["require_unique"] for step in feature["candidate"]["steps"])


def test_unsafe_legacy_delete_stays_blocked():
    case = next(item for item in build.read("catalog.json")["cases"] if item["case_id"] == 32)
    assert case["status"] == "blocked"
    assert "owned record" in case["reason"]
