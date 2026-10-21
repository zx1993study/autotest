"""Rebuild the 82 archived API flows and execute real native scenario batches.

Historical responses are planning fixtures only. Verdicts use new native runs and
replay the original Python scenario assertions against their captured responses.
"""
from copy import deepcopy
from datetime import datetime
from decimal import Decimal
import argparse
import hashlib
import json
import os
import re
import time
from urllib.parse import parse_qsl, urlsplit

import case_suite_runner as core
from case_suite_runner import BASE, CN, HERE, PROJECT_ID, Platform, Suite, write_json

OUTPUT = HERE / os.environ.get("NATIVE82_OUTPUT", "native-82-results.json")
UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


def walk(value, path=""):
    if isinstance(value, dict):
        for key, item in value.items():
            yield from walk(item, path + "/" + str(key).replace("~", "~0").replace("/", "~1"))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from walk(item, path + "/" + str(index))
    else:
        yield path, value


def dotted(value, path):
    for part in path.removeprefix("$.").split("."):
        value = value[int(part)] if isinstance(value, list) else value[part]
    return value


class Replay(Suite):
    def __init__(self, *, selected=()):
        core.MANAGEMENT = "http://127.0.0.1:8000/api/v1"
        self.platform = Platform()
        self.output = OUTPUT
        assert not OUTPUT.exists(), "Keep prior history; use --resume to continue this run"
        self.prefix = "CASE_" + datetime.now(CN).strftime("%Y%m%d_%H%M%S")
        self.state = {"target": BASE, "management": core.MANAGEMENT, "project_id": PROJECT_ID,
            "run_prefix": self.prefix, "started_at": datetime.now(CN).isoformat(),
            "scenarios": [], "api_cases": [], "web_cases": [], "fixtures": [], "cleanup": [],
            "selected_scenarios": list(selected)}
        self.sessions, self.auth, self.user_ids, self.interfaces = {}, {}, {}, {}
        self.password, self.current = None, None
        self.mode = "idle"
        self.load_sources()

    def load_sources(self):
        audit = json.loads((HERE / "native-flow-audit-local.json").read_text(encoding="utf-8"))
        self.flows = {row["name"].removeprefix("CASEMD "): row for row in audit["flows"]}
        assert len(self.flows) == 82
        summary = json.loads((HERE / "case-coverage-final.json").read_text(encoding="utf-8"))
        self.old_scenes = {row["code"]: row for row in summary["scenarios"]}
        self.old_records = json.loads((HERE / "native-replay-old-records.json").read_text(encoding="utf-8"))
        self.old_cases = {row["id"]: row for row in json.loads((HERE / "case-native-api-cases.json").read_text(encoding="utf-8"))}
        self.translations = self.state.setdefault("id_translations", {})
        self.old_prefixes = set()
        for path in HERE.glob("case-suite-results*.json"):
            old = json.loads(path.read_text(encoding="utf-8"))
            if old.get("run_prefix"):
                self.old_prefixes.add(old["run_prefix"])
            for fixture in old.get("fixtures", []):
                if fixture["type"] == "user":
                    actor = fixture.get("username", "").rsplit("_", 1)[-1]
                    if actor in self.user_ids:
                        self.translations[fixture["id"]] = self.user_ids[actor]
                if fixture["type"] == "project" and hasattr(self, "pid"):
                    self.translations[fixture["id"]] = self.pid

    def save(self):
        write_json(self.output, self.state)

    def replace(self, value):
        if isinstance(value, dict):
            return {key: self.replace(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self.replace(item) for item in value]
        if isinstance(value, str):
            value = UUID.sub(lambda match: self.translations.get(match[0], match[0]), value)
            for prefix in self.old_prefixes:
                value = value.replace(prefix, self.prefix)
        return value

    def prepare_responses(self, code):
        scene = self.old_scenes[code]
        self.old_evidence = deepcopy(scene["evidence"])
        for item in self.old_evidence:
            if item["method"] == "POST" and item["path"] in {"/todo", "/beli/products", "/beli/orders", "/todo/leaves"}:
                try:
                    created_id = json.loads(self.old_records[str(item["record_id"])]["data"]["response_body"])["data"]["id"]
                    self.translations.pop(created_id, None)
                except (KeyError, TypeError, ValueError):
                    pass
        self.responses = []
        for item in self.old_evidence:
            record = self.old_records[str(item["record_id"])]
            if code == "DOC01-tools":
                text = (core.REFERENCE / ".agent/workflows/backend-api.md").read_text(encoding="utf-8")
                line = next(line for line in text.splitlines() if line.startswith("- **工具（43）**"))
                body = {"code": 0, "data": {"tools": [{"name": name} for name in re.findall(r"`([^`]+)`", line)]}}
            else:
                body = json.loads(record["data"]["response_body"])
            self.responses.append(self.replace(body))
        old_account = next((body["data"]["items"][0] for item, body in zip(self.old_evidence, self.responses)
                            if item["path"] == "/beli/accounts" and body.get("data", {}).get("items")), None)
        if old_account:
            now = self.direct("employee", "GET", "/beli/accounts")["items"][0]
            if code == "SHOP03-05-repeat" and Decimal(str(now["available"])) >= 100:
                for index, item in enumerate(self.old_evidence):
                    case_body = self.old_cases[item["case_id"]].get("data", {}).get("body", {})
                    if item["method"] == "POST" and "fund temporary redemption test" in case_body.get("reason", ""):
                        funding = Decimal(str(case_body["amount"]))
                        for key in ("balance", "available"):
                            old_account[key] = str(Decimal(str(old_account[key])) + funding)
                        del self.old_evidence[index]
                        del self.responses[index]
                        break
            balance_offset = Decimal(str(now["balance"])) - Decimal(str(old_account["balance"]))
            frozen_offset = Decimal(str(now["frozen"])) - Decimal(str(old_account["frozen"]))
            if code == "SHOP07-balance":
                frozen_offset += 100
            leave_offset = {key: Decimal(str(now["leave"][key])) - Decimal(str(old_account["leave"][key])) for key in now["leave"]}
            for item, body in zip(self.old_evidence, self.responses):
                if item["path"] != "/beli/accounts":
                    continue
                for account in body["data"]["items"]:
                    for key, offset in (("balance", balance_offset), ("frozen", frozen_offset), ("available", balance_offset - frozen_offset)):
                        account[key] = str(Decimal(str(account[key])) + offset)
                    for key, offset in leave_offset.items():
                        account["leave"][key] = str(Decimal(str(account["leave"][key])) + offset)
        if code.startswith("LEAVE01"):
            total = self.direct("employee", "GET", "/todo/my?page_size=100")["total"]
            for item, body in zip(self.old_evidence, self.responses):
                if item["path"].startswith("/todo/my?"):
                    body["data"]["total"] = total

    def call(self, actor, method, path, body=None, *, expected=200, equals=None, contains=None, missing=(), content_type="application/json"):
        index = self.cursor
        self.cursor += 1
        assert index < len(self.responses), f"Unexpected extra call {method} {path}"
        response = deepcopy(self.responses[index])
        if self.mode == "plan":
            evidence = self.old_evidence[index]
            assert evidence["method"] == method, (evidence, method, path)
            self.plan.append({"actor": actor, "method": method, "path": path, "body": deepcopy(body or {}),
                "expected": expected, "equals": deepcopy(equals or {}), "contains": contains, "missing": list(missing),
                "content_type": content_type, "response": response,
                "source_id": self.old_cases[evidence["case_id"]]["source_id"]})
        elif self.mode == "verify":
            row = self.actual_nodes[index]
            assert row["status"] == "success", f"Native step {index + 1}: {row.get('error') or row.get('assertions')}"
            assert row["response_status"] == expected, (row["response_status"], expected)
            request = row["request"]
            expected_path = "/api/v1" + urlsplit(path).path
            assert urlsplit(request["url"]).path == expected_path, (request["url"], expected_path)
            assert request["method"] == method
            def stable(value):
                if isinstance(value, dict):
                    return {key: stable(item) for key, item in value.items() if key not in {"request_key", "feature_key"}}
                if isinstance(value, list):
                    return [stable(item) for item in value]
                return value
            assert stable(request.get("body") or {}) == stable(body or {}), f"Step {index + 1} request body differs from scenario"
            assert request.get("query", {}) == dict(parse_qsl(urlsplit(path).query, keep_blank_values=True))
            for pointer, value in (equals or {}).items():
                assert dotted(response, pointer) == value, f"Step {index + 1} {pointer}: {dotted(response, pointer)!r} != {value!r}"
            if contains:
                assert contains in json.dumps(response, ensure_ascii=False)
            for pointer in missing:
                try:
                    dotted(response, pointer.strip("/").replace("/", "."))
                except (KeyError, IndexError, TypeError):
                    pass
                else:
                    raise AssertionError(f"Sensitive field present: {pointer}")
            self.current["semantic_steps_checked"] = self.cursor
        else:
            raise AssertionError(self.mode)
        return response.get("data")

    def account(self, **kwargs):
        account = super().account(**kwargs)
        for key in ("balance", "frozen", "available"):
            account[key] = str(Decimal(str(account[key])).quantize(Decimal(".01")))
        return account

    def compile(self):
        nodes, producers = [], {}
        live_ids = set(self.user_ids.values()) | {self.pid} | set(self.translations.values())
        for index, item in enumerate(self.plan):
            key = f"step_{index + 1}"
            bindings = []
            parsed = urlsplit(item["path"])
            path = parsed.path
            params = {}
            for value in UUID.findall(path):
                if value in producers:
                    source, name = producers[value]
                    variable = "ref_" + name
                    path = path.replace(value, "{" + variable + "}")
                    params[variable] = value
                    bindings.append({"source": source, "name": name, "target": "params", "path": "/" + variable})
            fields = self.state.setdefault("path_fields", {})
            for variable in params:
                field_key = str(item["source_id"]) + ":" + variable
                if field_key not in fields:
                    field = self.platform.call("POST", "/api-testing/fields", {"project_id": PROJECT_ID,
                        "name": variable, "status": "active", "description": "原生82流程动态响应ID的路径参数",
                        "data": {"interface_id": item["source_id"], "name": variable, "location": "path", "type": "string", "required": True}})
                    fields[field_key] = field["id"]
            query = dict(parse_qsl(parsed.query, keep_blank_values=True))
            for pointer, value in walk({"body": item["body"], "query": query}):
                if isinstance(value, str) and value in producers:
                    source, name = producers[value]
                    target, tail = pointer[1:].split("/", 1)
                    bindings.append({"source": source, "name": name, "target": target, "path": "/" + tail})
            assertions = [{"type": "status", "expected": item["expected"]}]
            if item["expected"] == 200:
                assertions.append({"type": "json_equals", "path": "code", "expected": 0})
            for pointer, value in item["equals"].items():
                dynamic = isinstance(value, str) and (value in producers or pointer.endswith("submitted_at"))
                assertions.append({"type": "json_pointer_exists", "path": "/" + pointer.replace(".", "/"), "expected": True}
                                  if dynamic else {"type": "json_equals", "path": pointer, "expected": value})
            if item["contains"]:
                assertions.append({"type": "body_contains", "expected": item["contains"]})
            assertions.extend({"type": "json_pointer_exists", "path": pointer, "expected": False} for pointer in item["missing"])
            payload = {"project_id": PROJECT_ID, "case_type": "API",
                "source_id": item["source_id"], "name": f"{getattr(self, 'case_label', 'NATIVE82')} {self.current['code']}.{index + 1:02} {self.current['title']}",
                "status": "active", "description": f"远程15173；复用固定账号；夹具{self.prefix}；动态ID及最终提交时间另由原场景函数逐项核验",
                "assertions": assertions, "data": {"method": item["method"], "path": path, "body": item["body"],
                    "params": params, "query": query, "auth_id": self.auth[item["actor"]], "api_base_path": "/api/v1", "content_type": item["content_type"]}}
            cache_key = hashlib.sha256(json.dumps({key: payload[key] for key in ("source_id", "assertions", "data")}, sort_keys=True).encode()).hexdigest()
            cache = self.state.setdefault("shared_read_cases", {}) if getattr(self, "reuse_read_cases", False) and item["method"] == "GET" else {}
            if cache_key in cache:
                case = {"id": cache[cache_key]}
            else:
                if getattr(self, "reuse_read_cases", False) and item["method"] == "GET":
                    payload["name"] = self.case_label + " 共享状态核对 " + item["method"] + " " + path
                case = self.platform.call("POST", "/api-testing/cases", payload)
                cache[cache_key] = case["id"]
            extracts = [{"name": "response", "source": "body", "path": "", "required": True, "sensitive": False}]
            node = {"key": key, "name": item["method"] + " " + path, "api_id": item["source_id"], "case_id": case["id"],
                "auth_id": self.auth[item["actor"]], "bindings": bindings, "extracts": extracts, "next": "auto"}
            for pointer, value in walk(item["response"]):
                if not isinstance(value, str) or not UUID.fullmatch(value) or value in producers or value in live_ids:
                    continue
                if not pointer.endswith("/id"):
                    continue
                name = "id_" + str(len(producers) + 1)
                extraction = {"name": name, "source": "body", "path": pointer, "required": True, "sensitive": False}
                parts = pointer.split("/")
                if len(parts) >= 4 and parts[-2].isdigit():
                    parent = item["response"]
                    for part in parts[1:-1]:
                        parent = parent[int(part)] if isinstance(parent, list) else parent[part]
                    if isinstance(parent, dict) and parent.get("title"):
                        extraction.update(path="/id", selection={"path": "/".join(parts[:-2]), "equals": {"/title": parent["title"]}})
                extracts.append(extraction)
                producers[value] = (key, name)
            nodes.append(node)
            self.current.setdefault("case_ids", []).append(case["id"])
            self.save()
        self.producers = producers
        return nodes

    def scenario(self, code, title, points, fn, *, limitation=None):
        if code not in self.flows or (self.state.get("selected_scenarios") and code not in self.state["selected_scenarios"]):
            return
        previous = next((scene for scene in self.state["scenarios"] if scene["code"] == code), None)
        if previous and previous["status"] == "success":
            return
        self.current = {"code": code, "title": title, "case_points": points, "status": "running", "evidence": [], "started_at": datetime.now(CN).isoformat()}
        self.state["scenarios"].append(self.current)
        flow_id = self.flows[code]["id"]
        self.current["flow_id"] = flow_id
        self.save()
        fixtures_before = deepcopy(self.state["fixtures"])
        properties_before = {key: deepcopy(getattr(self, key)) for key in ("product_id", "product_body") if hasattr(self, key)}
        try:
            self.prepare_responses(code)
            self.mode, self.cursor, self.plan = "plan", 0, []
            fn()
            assert self.cursor == len(self.responses), (code, self.cursor, len(self.responses))
            self.state["fixtures"] = fixtures_before
            for key in ("product_id", "product_body"):
                if key in properties_before:
                    setattr(self, key, properties_before[key])
                elif hasattr(self, key):
                    delattr(self, key)
            nodes = self.compile()
            old_flow = self.platform.call("GET", f"/execution/flows/{flow_id}")
            flow = self.platform.call("PUT", f"/execution/flows/{flow_id}", {"status": "active", "description":
                f".agent/test/cases.md {','.join(points)}；{title}；远程15173原生流程回归；{self.prefix}。运行后保留奖励审计并禁用模板，复跑需重新准备夹具。",
                "data": {"version": old_flow["data"]["version"], "inputs": {}, "nodes": nodes}})
            old_scenes = self.platform.call("GET", f"/execution/flows/{flow_id}/scenarios")
            old_scene = next((row for row in old_scenes if row["name"] == "远程15173完整回归"), None)
            if old_scene and old_scene["data"]["template_version"] != flow["data"]["version"]:
                self.platform.call("POST", f"/execution/flows/{flow_id}/scenarios/{old_scene['id']}/sync")
            payload = {"name": "远程15173完整回归", "status": "active", "description": title + "；所有步骤真实执行，无跳过；数值和集合补充核验见原生82流程报告",
                "data": {"flow_id": flow_id, "template_version": flow["data"]["version"], "nodes": {}, "failure_policy": "stop", "expected_end": "auto"}}
            scene = self.platform.call("PUT", f"/execution/flows/{flow_id}/scenarios/{old_scene['id']}", payload) if old_scene else self.platform.call("POST", f"/execution/flows/{flow_id}/scenarios", payload)
            batch = self.platform.call("POST", f"/execution/flows/{flow_id}/runs", {"scenario_ids": [scene["id"]], "mode": "serial", "concurrency": 1, "inputs": {}})
            self.current.update(scenario_id=scene["id"], run_id=batch["id"])
            self.save()
            while batch["status"] in {"queued", "running"}:
                time.sleep(1)
                batch = self.platform.call("GET", f"/execution/flows/{flow_id}/runs/{batch['id']}")
            self.current["native_status"] = batch["status"]
            self.current["native_result"] = batch
            self.save()
            result = batch["data"]["results"][0]
            self.actual_nodes = result["nodes"]
            by_key = {row["key"]: row for row in self.actual_nodes}
            for old_id, (key, name) in self.producers.items():
                actual = by_key.get(key, {}).get("outputs", {}).get(name)
                if actual:
                    self.translations[old_id] = actual
            self.responses = [row.get("outputs", {}).get("response", {}) for row in self.actual_nodes]
            self.capture_fixtures()
            self.mode, self.cursor = "verify", 0
            fn()
            assert batch["status"] == "success", "Native flow failed"
            assert self.cursor == len(self.actual_nodes), "Not all native steps were semantically checked"
            self.current["semantic_assertions_passed"] = True
            self.current["status"] = "success"
        except Exception as error:
            self.current.update(status="failed", error=str(error)[:2000])
            if not self.current.get("run_id"):
                self.state["fixtures"] = fixtures_before
        finally:
            self.mode = "idle"
            try:
                self.platform.call("PUT", f"/execution/flows/{flow_id}", {"status": "disabled"})
            except Exception as error:
                self.current["disable_error"] = str(error)
            self.current["finished_at"] = datetime.now(CN).isoformat()
            self.save()
            print(self.current["status"].upper(), code, "run=" + str(self.current.get("run_id")), self.current.get("error", ""), flush=True)

    def capture_fixtures(self):
        known = {row["id"] for row in self.state["fixtures"]}
        for item, response in zip(self.plan, self.responses):
            data = response.get("data") or {}
            if item["method"] != "POST" or item["expected"] != 200 or not isinstance(data, dict) or not data.get("id") or data["id"] in known:
                continue
            if item["path"] == "/beli/products":
                self.state["fixtures"].append({"type": "product", "id": data["id"], "name": data["name"], "body": item["body"]})
            elif item["path"] == "/todo" and item["body"].get("source_type") != "project_task":
                self.state["fixtures"].append({"type": "custom_todo", "id": data["id"], "name": data["title"]})
            known.add(data["id"])

    def cleanup(self):
        products = {row["id"]: row for row in self.state["fixtures"] if row["type"] == "product"}
        for order in self.direct("employee", "GET", "/beli/orders"):
            if order["product_id"] in products and order["status"] == "pending":
                self.direct("employee", "POST", f"/beli/orders/{order['id']}/action", {"action": "cancel"})
        seen = set()
        for fixture in reversed(self.state["fixtures"]):
            if fixture["id"] in seen:
                continue
            seen.add(fixture["id"])
            try:
                if fixture["type"] == "product":
                    assert fixture["name"].startswith(self.prefix + " ")
                    self.direct("manager", "PUT", f"/beli/products/{fixture['id']}", {**fixture["body"], "active": False})
                    action = "unpublished; order audit retained"
                elif fixture["type"] == "user":
                    assert fixture.get("reused")
                    self.direct("admin", "PATCH", f"/iam/users/{fixture['id']}", {"status": fixture["original_status"]})
                    action = "fixed account status restored"
                else:
                    action = "retained for test evidence and balance reconciliation"
                self.state["cleanup"].append({"type": fixture["type"], "id": fixture["id"], "status": "success", "action": action})
            except Exception as error:
                self.state["cleanup"].append({"type": fixture["type"], "id": fixture["id"], "status": "failed", "error": str(error)})
        self.save()

    def run_all(self):
        self.permission_scenarios()
        self.task_scenarios()
        self.bug_scenarios()
        self.reward_scenarios()
        self.leave_scenarios()
        self.shop_scenarios()
        self.documentation()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--select", action="append", default=[])
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.resume:
        suite = Replay.__new__(Replay)
        core.MANAGEMENT = "http://127.0.0.1:8000/api/v1"
        suite.platform, suite.output = Platform(), OUTPUT
        suite.state = json.loads(OUTPUT.read_text(encoding="utf-8"))
        suite.prefix = suite.state["run_prefix"]
        suite.sessions, suite.auth, suite.user_ids, suite.interfaces = {}, {}, {}, {}
        suite.current, suite.mode = None, "idle"
        suite.pid = next(row["id"] for row in suite.state["fixtures"] if row["type"] == "project")
        suite.login("admin", "admin", os.environ["PUNKRECORD_PASSWORD"])
        from account_pool import load_pool, read_password, use_existing_accounts
        pool = load_pool()
        original_statuses = {row["id"]: row["original_status"] for row in reversed(suite.state["fixtures"]) if row["type"] == "user"}
        use_existing_accounts(suite, pool, read_password(pool))
        for row in suite.state["fixtures"]:
            if row["type"] == "user":
                row["original_status"] = original_statuses[row["id"]]
        product = next((row for row in suite.state["fixtures"] if row["type"] == "product" and row["body"]["kind"] == "physical"), None)
        if product:
            suite.product_id, suite.product_body = product["id"], product["body"]
            suite.direct("manager", "PUT", f"/beli/products/{suite.product_id}", suite.product_body)
        suite.load_sources()
    else:
        suite = Replay(selected=args.select)
        suite.setup()
        suite.load_sources()
        suite.state["baseline_account"] = suite.direct("employee", "GET", "/beli/accounts")["items"][0]
        suite.save()
    try:
        suite.run_all()
    finally:
        try:
            suite.state["final_account"] = suite.direct("employee", "GET", "/beli/accounts")["items"][0]
        finally:
            suite.cleanup()
        suite.state["finished_at"] = datetime.now(CN).isoformat()
        suite.save()
        latest = {row["code"]: row for row in suite.state["scenarios"]}
        print("SUMMARY", json.dumps({"total": len(latest), "success": sum(row["status"] == "success" for row in latest.values()),
            "failed": [row["code"] for row in latest.values() if row["status"] != "success"]}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
