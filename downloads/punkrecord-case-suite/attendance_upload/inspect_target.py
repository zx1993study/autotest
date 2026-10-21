"""Read-only business preflight; credentials stay in memory."""
import json
import sys
from datetime import date, timedelta
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(ROOT / "backend"))

from account_pool import TARGET, load_pool, read_password
from flow_reorganization.inventory import save


def sessions():
    pool = load_pool()
    password = read_password(pool)
    result = {}
    for actor in ("manager", "supervisor", "employee", "other"):
        session = requests.Session()
        response = session.post(TARGET + "/api/v1/auth/login", json={
            "username": pool["accounts"][actor]["username"], "password": password,
        }, timeout=25)
        response.raise_for_status()
        session.headers["Authorization"] = "Bearer " + response.json()["access_token"]
        result[actor] = session
    return result


def get(session, path, **query):
    response = session.get(TARGET + "/api/v1" + path, params=query, timeout=25)
    if response.status_code >= 400:
        save(HERE / "preflight-error.json", {"method": "GET", "path": path, "query": query,
                                            "http_status": response.status_code, "response": response.text[:3000]})
    response.raise_for_status()
    body = response.json()
    assert body["code"] == 0, (path, body.get("message"))
    return body["data"]


def diagnose():
    clients = sessions()
    result = []
    for path, query in (("/meeting/records", {"limit": 1}), ("/meeting/records", {"limit": 1, "skip": 10000}),
                        ("/beli/attendance", {"day": "2026-10-21"}), ("/beli/accounts", {})):
        response = clients["manager"].get(TARGET + "/api/v1" + path, params=query, timeout=25)
        result.append({"path": path, "query": query, "status": response.status_code, "body": response.text[:3000]})
    response = clients["manager"].get(TARGET + "/openapi.json", timeout=25)
    try:
        schema = response.json() if response.ok else {}
    except ValueError:
        schema = {}
    result.append({"schema_status": response.status_code,
                   "upload_paths": [path for path in schema.get("paths", {}) if "upload-transcript" in path]})
    save(HERE / "diagnostic.json", result)
    print(json.dumps(result, ensure_ascii=True))


def inspect():
    clients = sessions()
    result = {"target": TARGET, "accounts": get(clients["employee"], "/beli/accounts"), "days": []}
    response = clients["manager"].get(TARGET + "/api/v1/meeting/records", params={
        "search": "2026-10-21", "meeting_type": "morning", "limit": 100,
    }, timeout=25)
    result["search_probe"] = {"status": response.status_code, "body": response.text[:1500]}
    meetings = get(clients["manager"], "/meeting/records", meeting_type="morning", limit=100)
    assert meetings["total"] <= 100, "Paginate all meetings before selecting a safe date"
    result["morning_total"] = meetings["total"]
    for offset in range(3):
        day = (date(2026, 10, 21) - timedelta(days=offset)).isoformat()
        matching = [row for row in meetings["items"] if row["meeting_date"] == day]
        attendance = get(clients["employee"], "/beli/attendance", day=day)
        result["days"].append({"day": day, "meeting_total": len(matching),
                                "meetings": [{k: row.get(k) for k in ("id", "title", "meeting_date", "attendees")}
                                             for row in matching], "attendance": attendance})
    save(HERE / "preflight.json", result)
    print(json.dumps({"days": [{"day": row["day"], "meeting_total": row["meeting_total"]}
                                for row in result["days"]]}, ensure_ascii=True))


if __name__ == "__main__":
    diagnose() if "--diagnose" in sys.argv else inspect()
