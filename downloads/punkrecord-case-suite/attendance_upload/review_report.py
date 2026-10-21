"""Read platform state and collate scenario-level outcomes without hiding retries."""
import json
from collections import Counter

from bootstrap import HERE, CampaignRepository, save

from app.db.session import SessionLocal
from app.repositories.sqlalchemy_resource_repository import SqlAlchemyResourceRepository
from app.services.api_flow_validation import validate_references


def main():
    attempts = []
    for filename in ("execution.json", "review-execution.json", "edges-execution.json", "multi-execution.json", "non-morning-execution.json"):
        source = json.loads((HERE / filename).read_text(encoding="utf-8"))
        for run in source["runs"]:
            scene_id = run["scene"].get("scene_id", run["scene"].get("id"))
            attempts.append({**run, "scene_id": scene_id, "evidence_file": filename})
    latest = {}
    for run in sorted(attempts, key=lambda row: row["batch_id"]):
        latest[run["scene_id"]] = run
    with SessionLocal() as db:
        repo = CampaignRepository(SqlAlchemyResourceRepository(db))
        scenes, _ = repo.list("api_flow_scenarios", project_id=17796, page_size=10000)
        runs, _ = repo.list("api_flow_runs", project_id=17796, page_size=10000)
        flows = []
        for flow_id in (21062, 21066, 21070, 21072, 21107, 21109, 21114, 21116, 21138):
            flow = repo.get("execution_flows", flow_id)
            members = [scene for scene in scenes if scene["data"].get("flow_id") == flow_id]
            details = []
            for scene in members:
                assert scene["data"]["template_version"] == flow["data"]["version"]
                validate_references(repo, 17796, flow["data"], scene["data"], running=True)
                run = latest.get(scene["id"])
                failed_nodes = []
                if run:
                    batch = repo.get("api_flow_runs", run["batch_id"])
                    assert batch["status"] == run["status"], "Saved evidence must match actual platform state"
                    failed_nodes = [{"key": n["key"], "assertions": [a for a in n.get("assertions", []) if not a.get("passed")]}
                                    for n in run["result"].get("nodes", []) if n["status"] == "failed"]
                details.append({"id": scene["id"], "name": scene["name"], "status": run["status"] if run else "not_run",
                                "batch_id": run["batch_id"] if run else None, "failed_nodes": failed_nodes,
                                "evidence_file": run["evidence_file"] if run else None})
            flows.append({"id": flow_id, "name": flow["name"], "counts": dict(Counter(row["status"] for row in details)),
                          "scenarios": sorted(details, key=lambda row: row["id"])})
    details = [row for flow in flows for row in flow["scenarios"]]
    report = {"project_id": 17796, "date": "2026-10-21", "flows": flows,
              "latest_counts": dict(Counter(row["status"] for row in details)), "scenario_count": len(details),
              "validated_scene_count": len(details),
              "attempt_count": len(attempts), "attempt_counts": dict(Counter(row["status"] for row in attempts)),
              "running_project_batches": [row["id"] for row in runs if row["status"] in {"running", "queued"}],
              "cleanup_failures": [row["batch_id"] for row in attempts if row.get("cleanup_success") is False
                                   or row.get("balances_restored") is False],
              "configuration_failures_before_requests": [row["batch_id"] for row in attempts
                                                          if not row["result"].get("nodes")]}
    assert not report["running_project_batches"], "Wait for all project batches before final reporting"
    assert not report["cleanup_failures"], "Investigate cleanup errors before final reporting"
    save(HERE / "review-summary.json", report)
    print(json.dumps({key: value for key, value in report.items() if key != "flows"}, ensure_ascii=True))


if __name__ == "__main__":
    main()
