"""Read the existing project through repositories; never call the business API."""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))

from app.repositories.sqlalchemy_resource_repository import SqlAlchemyResourceRepository

PROJECT_ID = 17796
HERE = Path(__file__).resolve().parent
SECRET = re.compile(r"password|authorization|cookie|access_token|refresh_token|secret", re.IGNORECASE)


def sanitized(value):
    if isinstance(value, dict):
        return {k: "***" if SECRET.search(k) and v else sanitized(v) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitized(v) for v in value]
    return value


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(sanitized(value), ensure_ascii=False, indent=2), encoding="utf-8")


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=True, sort_keys=True, default=str).encode()).hexdigest()


def collect(db):
    repo = SqlAlchemyResourceRepository(db)
    project = repo.get("projects", PROJECT_ID)
    assert project and project["name"] == "PunkRecord", "Wrong project"
    assert project["data"]["base_url"].rstrip("/") == "http://14.103.229.153:15173", "Wrong target"
    tables = {}
    for table in ("execution_flows", "api_flow_scenarios", "api_interfaces"):
        rows, total = repo.list(table, project_id=PROJECT_ID, page_size=10000)
        assert total == len(rows), (table, total)
        tables[table] = rows
    ids = {n.get("case_id") for f in tables["execution_flows"] for n in f["data"].get("nodes", [])}
    ids.update(n.get("case_id") for s in tables["api_flow_scenarios"] for n in s["data"].get("nodes", {}).values())
    tables["api_test_cases"] = repo.get_many("api_test_cases", sorted(ids - {None}))
    active, _ = repo.list("api_flow_runs", project_id=PROJECT_ID, page_size=10000)
    tables["history"] = [{"id": r["id"], "flow_id": r["data"].get("flow_id"),
                          "status": r["status"], "fingerprint": fingerprint(r)} for r in active]
    assert not any(r["status"] in {"queued", "running"} for r in active), "Do not reorganize while runs are active"
    tables["project"] = {k: project[k] for k in ("id", "name")}
    return tables


def compact(snapshot):
    cases = {c["id"]: c for c in snapshot["api_test_cases"]}
    output = []
    for flow in snapshot["execution_flows"]:
        scenes = [s for s in snapshot["api_flow_scenarios"] if s["data"]["flow_id"] == flow["id"]]
        output.append({"id": flow["id"], "name": flow["name"], "description": flow["description"],
            "scenes": [{"id": s["id"], "name": s["name"]} for s in scenes],
            "steps": [{"api": n["api_id"], "case": n.get("case_id"),
                "method": cases.get(n.get("case_id"), {}).get("data", {}).get("method"),
                "path": cases.get(n.get("case_id"), {}).get("data", {}).get("path"),
                "body_keys": list((cases.get(n.get("case_id"), {}).get("data", {}).get("body") or {}).keys()),
                "routes": n.get("routes"), "next": n.get("next"),
                "assertions": cases.get(n.get("case_id"), {}).get("assertions", [])}
                for n in flow["data"].get("nodes", [])]})
    return output


if __name__ == "__main__":
    from app.db.session import SessionLocal

    with SessionLocal() as db:
        snapshot = collect(db)
    path = HERE / "before.json"
    assert not path.exists(), "Do not overwrite the original snapshot"
    save(path, snapshot)
    save(HERE / "inventory.json", compact(snapshot))
    print(json.dumps({k: len(v) for k, v in snapshot.items()}, ensure_ascii=True))
