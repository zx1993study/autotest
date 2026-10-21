from copy import deepcopy

import pytest
from non_morning import TYPES, scenario
from plan import EMPLOYEE, STEPS, equal

MANAGER_CASES = {"accounts": 101, "ledger": 102, "attendance": 103}


def source():
    nodes = {key: {"mode": "skip" if key.endswith("_again") else "always", "request": {"body": {}, "query": {}},
                   "bindings": [], "extracts": [], "assertions": []} for key, _, _ in STEPS}
    nodes["date_guard"]["request"]["query"] = {"day": "{{attendance_day}}"}
    nodes["detail"]["assertions"] = [equal("/data/meeting_type", "morning")]
    nodes["upload"]["request"]["files"] = [{"file_id": 123}]
    return {"inputs": {}, "nodes": nodes, "latest_run_id": 1, "latest_status": "success"}


@pytest.mark.parametrize("kind", TYPES)
def test_each_non_morning_type_checks_creation_before_import(kind):
    weekly, absent = source(), source()
    original = deepcopy(weekly)
    result = scenario(weekly, absent, kind, "2026-10-21", MANAGER_CASES)
    nodes = result["data"]["nodes"]
    assert weekly == original
    assert result["data"]["inputs"]["meeting_type"] == kind
    assert "latest_status" not in result["data"]
    assert nodes["upload"]["mode"] == "skip"
    assert nodes["upload_again"]["mode"] == "always"
    assert nodes["upload_again"]["request"]["files"] == [{"file_id": 123}]
    assert equal("/data/attendees", None) in nodes["detail"]["assertions"]
    assert equal("/data/meeting_type", "{{meeting_type}}") in nodes["detail_again"]["assertions"]
    for key in ("baseline", "balance", "balance_again", "balance_restored"):
        assert nodes[key]["case_id"] == MANAGER_CASES["accounts"]
        assert "auth_id" not in nodes[key]["request"]
    for key in ("ledger_before", "ledger", "ledger_again"):
        assert nodes[key]["case_id"] == MANAGER_CASES["ledger"]
        assert nodes[key]["request"]["query"]["user_id"] == EMPLOYEE
    for key in ("date_guard", "attendance", "attendance_again"):
        assert nodes[key]["case_id"] == MANAGER_CASES["attendance"]
    for key in ("balance", "balance_again", "balance_restored"):
        assert equal("/data/items", "{{bound_accounts}}") in nodes[key]["assertions"]
    for key in ("ledger", "ledger_again"):
        assert equal("/data", "{{bound_entries}}") in nodes[key]["assertions"]


def test_morning_meeting_is_not_mislabelled_as_a_non_charge_scenario():
    with pytest.raises(AssertionError, match="non-morning"):
        scenario(source(), source(), "morning", "2026-10-21", MANAGER_CASES)
