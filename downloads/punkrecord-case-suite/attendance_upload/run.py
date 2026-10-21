"""Run saved scenes with the real platform batch worker and guarded cleanup."""
import json
import time
from decimal import Decimal

from bootstrap import HERE, save

from account_pool import TARGET
from app.db.session import SessionLocal
from app.repositories.sqlalchemy_resource_repository import SqlAlchemyResourceRepository
from app.services.api_flow_run_service import ApiFlowRunService
from inspect_target import get, sessions
from plan import FLOW_ID

DAY = "2026-10-21"


def accounts(client):
    data = get(client, "/beli/accounts")
    return {row["user_id"]: {key: str(Decimal(str(row[key]))) for key in ("balance", "frozen")}
            for row in data["items"]}


def guarded_cleanup(client, result):
    records = []
    for created in result["nodes"]:
        request = created.get("request") or {}
        if request.get("method") != "POST" or request.get("path") != "/meeting/records":
            continue
        records.append(cleanup_meeting(client, result, created))
    return {"meetings": records}


def cleanup_meeting(client, result, created):
    meeting_id = (created.get("outputs") or {}).get("meeting_id")
    if not meeting_id:
        return {"needed": False, "reason": "No successfully created meeting ID in run evidence"}
    deleted = any((node.get("request") or {}).get("method") == "DELETE"
                  and (node.get("request") or {}).get("path") == "/meeting/records/" + meeting_id
                  and node.get("response_status") == 200 for node in result["nodes"])
    if deleted:
        return {"needed": False, "meeting_id": meeting_id, "deleted_by_flow": True}
    meeting = get(client, "/meeting/records/" + meeting_id)
    title = created.get("request", {}).get("body", {}).get("title")
    assert title and meeting["title"] == title and title.startswith("早会文稿链路-"), "Unowned meeting; do not delete"
    response = client.delete(TARGET + "/api/v1/meeting/records/" + meeting_id, timeout=25)
    record = {"needed": True, "meeting_id": meeting_id, "http_status": response.status_code,
              "response": response.json()}
    response.raise_for_status()
    assert record["response"]["code"] == 0, "Cleanup rejected"
    return record


def execute_one(scene_id, flow_id=FLOW_ID, inputs=None):
    with SessionLocal() as db:
        repo = SqlAlchemyResourceRepository(db)
        batch = ApiFlowRunService(repo).create_batch(flow_id, {
            "scenario_ids": [scene_id], "inputs": inputs or {}, "mode": "serial", "concurrency": 1})
        batch_id = batch["id"]
    deadline = time.monotonic() + 300
    while time.monotonic() < deadline:
        with SessionLocal() as db:
            row = SqlAlchemyResourceRepository(db).get("api_flow_runs", batch_id)
        if row["status"] not in {"queued", "running"}:
            return row
        time.sleep(2)
    from app.scheduler.jobs.api_flow_jobs import cancel_batch
    cancel_batch(batch_id)
    raise TimeoutError(f"Batch {batch_id} exceeded 300 seconds; inspect before another run")


def main():
    applied = json.loads((HERE / "applied.json").read_text(encoding="utf-8"))
    clients = sessions()
    manager = clients["manager"]
    baseline = accounts(manager)
    assert get(manager, "/meeting/records", meeting_type="morning", search=DAY, limit=1)["total"] == 0
    report = {"day": DAY, "baseline": baseline, "runs": []}
    save(HERE / "execution.json", report)
    for scene in applied["scenarios"]:
        row = execute_one(scene["id"])
        result = row["data"]["results"][0]
        item = {"scene": scene, "batch_id": row["id"], "status": row["status"], "result": result}
        report["runs"].append(item)
        save(HERE / "execution.json", report)
        try:
            item["cleanup"] = guarded_cleanup(manager, result)
            after = accounts(manager)
            item["balances_restored"] = after == baseline
            item["account_drift"] = {key: value for key, value in after.items() if baseline.get(key) != value}
            save(HERE / "execution.json", report)
            assert item["balances_restored"], "Account drift after cleanup; stop, do not compensate manually"
        finally:
            save(HERE / "execution.json", report)
        failed = [{"key": n["key"], "error": n.get("error"),
                   "assertions": [a for a in n.get("assertions", []) if not a.get("passed")]}
                  for n in result["nodes"] if n["status"] == "failed"]
        print(json.dumps({"scene_id": scene["id"], "kind": scene["kind"], "batch_id": row["id"],
                          "status": row["status"], "failed": failed}, ensure_ascii=True), flush=True)
    report["after"] = accounts(manager)
    report["remaining_meetings"] = get(manager, "/meeting/records", meeting_type="morning", search=DAY, limit=1)["total"]
    save(HERE / "execution.json", report)


if __name__ == "__main__":
    main()
