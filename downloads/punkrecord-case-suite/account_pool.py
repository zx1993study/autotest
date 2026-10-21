"""Reuse a fixed allowlist; missing accounts or credentials never trigger creation."""
import base64
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
from uuid import UUID


HERE = Path(__file__).resolve().parent
POOL_PATH = HERE / "test-account-pool.json"
SECRET_PATH = HERE / "test-account-secrets.dpapi.json"
TARGET = "http://14.103.229.153:15173"
ACTORS = ("manager", "supervisor", "employee", "other")


def load_pool(path=POOL_PATH):
    pool = json.loads(path.read_text(encoding="utf-8"))
    assert pool["target"] == TARGET and pool["auto_create"] is False
    assert set(pool["accounts"]) == set(ACTORS)
    accounts = pool["accounts"]
    assert pool["version"] == 2
    assert len({a["id"] for a in accounts.values()}) == 4
    usernames = {"manager": "test_user1", "supervisor": "test_user2", "employee": "test_user3", "other": "test_user4"}
    for actor, account in accounts.items():
        assert str(UUID(account["id"])) == account["id"]
        assert account["username"] == usernames[actor]
        parent = {"manager": None, "supervisor": "manager", "employee": "supervisor", "other": "supervisor"}[actor]
        expected_manager = accounts[parent]["id"] if parent else None
        assert account["manager_user_id"] == expected_manager
    return pool


def _dpapi(data, decrypt=False):
    if os.name != "nt":
        raise RuntimeError("Use PUNKRECORD_TEST_PASSWORD on non-Windows hosts; no automatic account creation")

    class Blob(ctypes.Structure):
        _fields_ = [("size", wintypes.DWORD), ("data", ctypes.POINTER(ctypes.c_ubyte))]

    crypt = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    buffer = ctypes.create_string_buffer(data)
    source = Blob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    output = Blob()
    if decrypt:
        function = crypt.CryptUnprotectData
        function.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
                             ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
        ok = function(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(output))
    else:
        function = crypt.CryptProtectData
        function.argtypes = [ctypes.POINTER(Blob), wintypes.LPCWSTR, ctypes.c_void_p, ctypes.c_void_p,
                             ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
        ok = function(ctypes.byref(source), "PunkRecord fixed test accounts", None, None, None, 1, ctypes.byref(output))
    if not ok:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return ctypes.string_at(output.data, output.size)
    finally:
        kernel.LocalFree(output.data)


def save_password(pool, password, path=SECRET_PATH):
    protected = _dpapi(password.encode("utf-8"))
    data = {"version": 1, "target": TARGET, "account_ids": sorted(a["id"] for a in pool["accounts"].values()),
            "encrypted_password": base64.b64encode(protected).decode("ascii")}
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def read_password(pool, path=SECRET_PATH):
    supplied = os.environ.get(pool["password_env"], "")
    if supplied:
        return supplied
    if not path.exists():
        raise RuntimeError("Missing fixed test account credentials; set PUNKRECORD_TEST_PASSWORD. Account creation is disabled.")
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["target"] == TARGET
    assert data["account_ids"] == sorted(a["id"] for a in pool["accounts"].values())
    return _dpapi(base64.b64decode(data["encrypted_password"]), decrypt=True).decode("utf-8")


def use_existing_accounts(suite, pool, password):
    suite.account_pool = pool
    suite.password = password
    validated = {}
    # Validate every identity before activating any account.
    for actor in ACTORS:
        expected = pool["accounts"][actor]
        user = suite.direct("admin", "GET", f"/iam/users/{expected['id']}")
        for field in ("id", "username", "display_name", "manager_user_id", "job_title_id"):
            assert user.get(field) == expected.get(field), f"Fixed account mismatch: {actor}.{field}; refusing to create or replace"
        assert not user.get("is_admin", False), "Expected non-admin fixed test role"
        assert user.get("profile_completed") and not user.get("must_change_password"), "Fixed credentials require one-time initialization"
        assert user["status"] in {"active", "inactive"}
        validated[actor] = user
    for actor in ACTORS:
        expected, user = pool["accounts"][actor], validated[actor]
        suite.state["fixtures"].append({"type": "user", "id": user["id"], "name": user["display_name"],
            "username": user["username"], "reused": True, "original_status": user["status"]})
        suite.save()
        if user["status"] == "inactive":
            suite.direct("admin", "PATCH", f"/iam/users/{user['id']}", {"status": "active"})
        suite.login(actor, expected["username"], password)
