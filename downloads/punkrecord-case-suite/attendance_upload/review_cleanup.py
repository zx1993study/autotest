"""Only clean entities created in the supplied run evidence, through APIs."""
import json
from decimal import Decimal
from uuid import uuid4

from account_pool import TARGET
from inspect_target import get
from review_common import EMPLOYEE, OTHER


def body(row):
    try:
        return json.loads(row.get("response_body") or "{}")
    except ValueError:
        return {}


def write(client, log, method, path, data=None):
    response = client.request(method, TARGET + "/api/v1" + path, json=data, timeout=25)
    try:
        payload = response.json()
    except ValueError:
        payload = {"text": response.text[:2000]}
    log.append({"method": method, "path": path, "request": data, "http_status": response.status_code, "response": payload})
    response.raise_for_status()
    assert payload.get("code") == 0, (path, payload.get("message"))
    return payload.get("data")


def account_state(client):
    return {row["user_id"]: row for row in get(client, "/beli/accounts")["items"]}


def created_entities(result):
    found = {}
    for row in result["nodes"]:
        request = row.get("request") or {}
        data = body(row).get("data")
        if request.get("method") == "POST" and request.get("path") in {
                "/project/projects", "/beli/products", "/beli/orders", "/todo/leaves"}:
            if row.get("response_status") == 200 and isinstance(data, dict) and data.get("id"):
                found[(request["path"], data["id"])] = {"data": data, "request": request}
    return found


def cleanup(manager, result, before):
    log, entities = [], created_entities(result)
    for (kind, item_id), item in entities.items():
        data = item["data"]
        if kind == "/beli/orders":
            states = [body(row).get("data") for row in result["nodes"]]
            final = next((state for state in reversed(states) if isinstance(state, dict) and state.get("id") == item_id), data)
            if final.get("status") in {"pending", "approved"}:
                write(manager, log, "POST", "/beli/orders/" + item_id + "/action", {"action": "cancel", "comment": "仅清理本次回归订单"})
        elif kind == "/todo/leaves":
            states = [body(row).get("data") for row in result["nodes"]]
            final = next((state for state in reversed(states) if isinstance(state, dict) and state.get("id") == item_id), data)
            if final.get("status") == "pending":
                write(manager, log, "POST", "/todo/leaves/" + item_id + "/reject", {"comment": "清理本轮未完成审批的测试申请"})
    projects(manager, result, entities, log)
    products(manager, entities, log)
    restore_accounts(manager, before, log)
    return log


def projects(manager, result, entities, log):
    for (kind, item_id), item in entities.items():
        if kind != "/project/projects":
            continue
        deleted = any(row.get("request", {}).get("method") == "DELETE" and
                      row.get("request", {}).get("path") == "/project/projects/" + item_id and
                      row.get("response_status") == 200 for row in result["nodes"])
        if deleted:
            continue
        current = get(manager, "/project/projects/" + item_id)
        assert current["name"] == item["request"]["body"]["name"] and current["name"].startswith("回归隔离项目-")
        tasks = get(manager, "/project/projects/" + item_id + "/todos")
        if isinstance(tasks, dict):
            tasks = tasks["items"]
        for task in tasks:
            if task["status"] == "done":
                write(manager, log, "POST", "/todo/" + task["id"] + "/status", {"status": "open"})
        write(manager, log, "DELETE", "/project/projects/" + item_id)


def products(manager, entities, log):
    owned = {item_id: item for (kind, item_id), item in entities.items() if kind == "/beli/products"}
    if not owned:
        return
    for row in get(manager, "/beli/products"):
        if row["id"] not in owned:
            continue
        assert row["name"] == owned[row["id"]]["request"]["body"]["name"]
        if row["active"]:
            payload = {key: row.get(key) for key in ("name", "description", "kind", "price", "stock", "leave_type", "leave_days")}
            payload["active"] = False
            write(manager, log, "PUT", "/beli/products/" + row["id"], payload)


def restore_accounts(manager, before, log):
    after = account_state(manager)
    for user_id in (EMPLOYEE, OTHER):
        assert Decimal(str(after[user_id]["frozen"])) == Decimal(str(before[user_id]["frozen"])), "Frozen money did not restore; stop"
        fields = [(None, before[user_id]["balance"], after[user_id]["balance"])]
        fields += [(key, value, after[user_id]["leave"][key]) for key, value in before[user_id]["leave"].items()]
        for leave_type, old, new in fields:
            difference = Decimal(str(old)) - Decimal(str(new))
            if not difference:
                continue
            assert abs(difference) <= 10000, "Unexpected account drift; do not compensate"
            payload = {"amount": str(difference), "reason": "清理本轮回归余额或假期变动；不改变已记录的测试结论", "request_key": str(uuid4())}
            if leave_type:
                payload["leave_type"] = leave_type
            write(manager, log, "POST", "/beli/accounts/" + user_id + "/adjust", payload)
    restored = account_state(manager)
    for user_id in (EMPLOYEE, OTHER):
        for key in ("balance", "frozen", "leave"):
            assert restored[user_id][key] == before[user_id][key], (user_id, key, "Not restored")
