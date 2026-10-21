"""Add explicit fixture preparation to chains which previously began mid-process."""
import json
from copy import deepcopy

from inventory import HERE


def product_fixtures():
    products = {}
    for pattern in ("case-suite-results*.json", "native-82*.json", "shop-rich-native-results.json"):
        for path in sorted(HERE.parent.glob(pattern)):
            source = json.loads(path.read_text(encoding="utf-8"))
            for fixture in source.get("fixtures", []):
                if fixture.get("type") == "product" and fixture.get("body"):
                    products[fixture["id"]] = fixture["body"]
    return products


def step(key, api, auth, method, path, body, *, content_type="application/json"):
    return {"old_key": key, "api_id": api, "case_id": 0, "auth_id": auth,
        "request": {"method": method, "path": path, "body": body, "params": {}, "query": {},
                    "content_type": content_type, "api_base_path": "/api/v1", "auth_id": auth},
        "bindings": [], "extracts": [],
        "assertions": [{"type": "status", "expected": 200}, {"type": "json_equals", "path": "code", "expected": 0}]}


def prepare_shop(branch, products):
    steps = branch["steps"]
    replacements, prefix = {}, []
    for node in steps:
        body = node["request"].get("body") or {}
        original_id = body.get("product_id")
        bound = any(b["target"] == "body" and b["path"] == "/product_id" for b in node["bindings"])
        if not original_id or bound or original_id not in products:
            continue
        if original_id not in replacements:
            key = f"fixture_product_{len(replacements) + 1}"
            replacements[original_id] = key
            data = deepcopy(products[original_id])
            data["name"] = "商城链路测试商品-{{timestamp_ms}}-" + str(len(replacements))
            created = step(key, 18714, 20373, "POST", "/beli/products", data)
            created["extracts"] = [{"name": "product_id", "source": "body", "path": "/data/id", "required": True}]
            prefix.append(created)
        node["bindings"].append({"source": replacements[original_id], "name": "product_id", "target": "body", "path": "/product_id"})
    branch["steps"] = prefix + steps
    if prefix:
        branch["prerequisites"] = ["准备本场景专用商品并传递新商品ID", "重新准备账号余额及对应预期；串行执行"]


def prepare_attendance(branch):
    first = branch["steps"][0]
    assert "/meeting/records/" in first["request"]["path"]
    created = step("meeting_create", 17983, first["auth_id"], "POST", "/meeting/records",
        {"title": "早会扣款链路-{{timestamp_ms}}", "meeting_type": "morning", "meeting_date": "{{attendance_day}}"},
        content_type="application/x-www-form-urlencoded")
    created["extracts"] = [{"name": "meeting_id", "source": "body", "path": "/data/id", "required": True}]
    for node in branch["steps"]:
        request = node["request"]
        if "/meeting/records/" in request["path"]:
            request["path"] = "/meeting/records/{meeting_id}/attendees"
            node["bindings"].append({"source": "meeting_create", "name": "meeting_id", "target": "params", "path": "/meeting_id"})
        if request["path"] == "/beli/attendance":
            branch["inputs"]["attendance_day"] = request["query"]["day"]
            request["query"]["day"] = "{{attendance_day}}"
    branch["steps"].insert(0, created)
    branch["prerequisites"] = ["仅隔离业务环境；新会议录入入口（非附件上传）", "准备日期、全员名单、专用账户余额与对应断言"]
