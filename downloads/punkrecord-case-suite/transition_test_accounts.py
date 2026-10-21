"""Migrate the explicit test-account allowlist without creating or resetting users."""
import argparse
import json
import os
from pathlib import Path

import requests

from account_pool import save_password

HERE = Path(__file__).resolve().parent
BASE = "http://14.103.229.153:15173"
EXPECTED = {
    "manager": ("test_user1", "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9", None),
    "supervisor": ("test_user2", "0830f805-3a2f-4ce2-a6d4-b0055a3b88f5", "manager"),
    "employee": ("test_user3", "640d1a5c-bff5-4df0-9e02-cb42f8b46413", "supervisor"),
    "other": ("test_user4", "b65fa560-e319-4363-84b0-5dbf9e2f2728", "supervisor"),
}
FIELDS = ("id", "username", "display_name", "manager_user_id", "manager_name", "level",
          "job_title_id", "job_title_name", "status", "profile_completed", "must_change_password")


def write(name, value):
    (HERE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("audit", "configure"))
    parser.add_argument("--business-permissions", action="store_true")
    args = parser.parse_args()
    session = requests.Session()
    response = session.post(BASE + "/api/v1/auth/login", json={"username": "admin",
        "password": os.environ["PUNKRECORD_PASSWORD"]}, timeout=25)
    response.raise_for_status()
    session.headers["Authorization"] = "Bearer " + response.json()["access_token"]

    def call(method, path, body=None):
        result = session.request(method, BASE + "/api/v1" + path, json=body, timeout=30)
        result.raise_for_status()
        data = result.json()
        assert data.get("code") == 0
        return data["data"]

    users = call("GET", "/iam/users?page_size=100")["items"]
    selected = {}
    for actor, (username, expected_id, _) in EXPECTED.items():
        found = [u for u in users if u["username"] == username]
        assert len(found) == 1 and found[0]["id"] == expected_id
        selected[actor] = found[0]
        probe = requests.post(BASE + "/api/v1/auth/login", json={"username": username,
            "password": os.environ["PUNKRECORD_TEST_PASSWORD"]}, timeout=25)
        probe.raise_for_status()
        assert probe.json().get("access_token"), "Existing account cannot log in; no reset is permitted"

    snapshot = {"target": BASE, "users": {actor: {key: user.get(key) for key in FIELDS}
        for actor, user in selected.items()}, "permissions": {}}
    for actor, user in selected.items():
        snapshot["permissions"][actor] = call("GET", f"/iam/job-titles/{user['job_title_id']}/permissions")
    before_path = HERE / "four-test-accounts-before.json"
    if not before_path.exists():
        write(before_path.name, snapshot)
    if args.mode == "audit":
        print(json.dumps(snapshot, ensure_ascii=True))
        return

    old_pool = json.loads((HERE / "test-account-pool.json").read_text(encoding="utf-8"))
    if old_pool["accounts"]["manager"]["username"].startswith("case_"):
        write("retired-test-account-pool.json", old_pool)
    else:
        old_pool = json.loads((HERE / "retired-test-account-pool.json").read_text(encoding="utf-8"))
    for actor, (_, _, parent) in EXPECTED.items():
        expected_parent = EXPECTED[parent][1] if parent else None
        if parent and selected[actor]["manager_user_id"] != expected_parent:
            call("PATCH", f"/iam/users/{selected[actor]['id']}", {"manager_user_id": expected_parent})
        selected[actor] = call("GET", f"/iam/users/{selected[actor]['id']}")
        assert selected[actor]["manager_user_id"] == expected_parent
    if args.business_permissions:
        role_id = "6e7b5c6d-5e51-465c-ae5e-c94416536349"
        permitted_ids = {entry[1] for entry in EXPECTED.values()} | {u["id"] for u in old_pool["accounts"].values()}
        assert all(u["id"] in permitted_ids for u in users if u["job_title_id"] == role_id)
        required = {"todo.read", "todo.write", "project.read", "project.write", "iam.read", "meeting.read", "meeting.write"}
        assert set(call("GET", f"/iam/job-titles/{role_id}/permissions")) == required
        call("PATCH", f"/iam/job-titles/{role_id}", {"name": "API Workflow Test", "description": "Four reusable test accounts; no administrative or compensation permissions"})
        for actor, user in selected.items():
            call("PATCH", f"/iam/users/{user['id']}", {"job_title_id": role_id})
            selected[actor] = call("GET", f"/iam/users/{user['id']}")
    pool = {"version": 2, "target": BASE, "auto_create": False,
        "password_env": "PUNKRECORD_TEST_PASSWORD", "accounts": {
            actor: {key: user[key] for key in ("id", "username", "display_name", "manager_user_id", "job_title_id")}
            for actor, user in selected.items()}}
    write("test-account-pool.json", pool)
    save_password(pool, os.environ["PUNKRECORD_TEST_PASSWORD"])
    manifest = {"target": BASE, "expected_database": "punkrecord_local", "expected_keep_count": 4,
        "keep": list(pool["accounts"].values()), "delete": list(old_pool["accounts"].values()),
        "source": "Explicit user request: retire only the three CASE_20261019_144610 fixture users"}
    assert len(manifest["delete"]) == 3
    assert all(u["username"].startswith("case_20261019_144610_") for u in manifest["delete"])
    write("retired-three-cleanup-manifest.json", manifest)
    after = {actor: {key: user.get(key) for key in FIELDS} for actor, user in selected.items()}
    write("four-test-accounts-after.json", {"target": BASE, "users": after})
    print(json.dumps({"status": "configured", "users": after}, ensure_ascii=True))


if __name__ == "__main__":
    main()
