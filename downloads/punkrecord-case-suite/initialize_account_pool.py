"""One-time credentials for retained users. Never creates users or job titles."""
import argparse
import json
import os
import secrets
import requests

from account_pool import HERE, TARGET, SECRET_PATH, load_pool, save_password, read_password, ACTORS


RESULT = HERE / "account-pool-initialization.json"


def call(session, method, path, body=None):
    response = session.request(method, TARGET + "/api/v1" + path, json=body, timeout=25)
    response.raise_for_status()
    data = response.json()
    assert data.get("code") == 0, data.get("message")
    return data["data"]


def sign_in(username, password):
    session = requests.Session()
    response = session.post(TARGET + "/api/v1/auth/login", json={"username": username, "password": password}, timeout=25)
    response.raise_for_status()
    session.headers["Authorization"] = "Bearer " + response.json()["access_token"]
    return session


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--initialize-passwords", action="store_true", required=True)
    parser.parse_args()
    pool = load_pool()
    assert pool.get("version") != 2, "User-provided fixed accounts must never be reset; reuse their existing credentials"
    if SECRET_PATH.exists():
        password = read_password(pool)
    else:
        password = secrets.token_urlsafe(24)
        save_password(pool, password)
    state = json.loads(RESULT.read_text(encoding="utf-8")) if RESULT.exists() else {"target": TARGET, "accounts": []}
    completed = {u["id"] for u in state["accounts"] if u.get("initialized")}
    admin = sign_in("admin", os.environ["PUNKRECORD_PASSWORD"])
    for actor in ACTORS:
        expected = pool["accounts"][actor]
        user = call(admin, "GET", f"/iam/users/{expected['id']}")
        for field in ("id", "username", "display_name", "manager_user_id", "job_title_id"):
            assert user.get(field) == expected.get(field), "Retained identity changed; refusing initialization"
        original = user["status"]
        try:
            if original == "inactive":
                call(admin, "PATCH", f"/iam/users/{user['id']}", {"status": "active"})
            if user["id"] not in completed:
                call(admin, "POST", f"/iam/users/{user['id']}/reset-password")
                account = sign_in(user["username"], "punkrecord123")
                call(account, "POST", "/auth/complete-profile", {"new_password": password})
            account = sign_in(user["username"], password)
            actual = call(account, "GET", "/auth/me")
            assert actual["id"] == user["id"]
            record = {"id": user["id"], "username": user["username"], "actor": actor,
                      "initialized": True, "restored_status": original}
            state["accounts"] = [r for r in state["accounts"] if r["id"] != user["id"]] + [record]
            RESULT.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        finally:
            call(admin, "PATCH", f"/iam/users/{user['id']}", {"status": original})
    print(json.dumps({"initialized_count": len(state["accounts"]), "credentials": "Windows CurrentUser DPAPI; no plaintext export",
                      "usernames": [a["username"] for a in state["accounts"]]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
