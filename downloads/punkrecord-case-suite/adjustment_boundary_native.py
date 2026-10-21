"""Save and execute balance edge cases in native local-platform case/flow history."""
from datetime import datetime
import json
import os
import time
from uuid import uuid4

from account_pool import load_pool, read_password, use_existing_accounts
import case_suite_runner as core
from case_suite_runner import BASE, CN, HERE, PROJECT_ID, Platform, Suite, write_json


OUTPUT = HERE / "adjustment-boundary-native-results.json"
CASES = [("zero", 0, 400), ("huge-positive", 99999999999999999999999999, 422),
         ("huge-negative", -9999999999999999999999, 422), ("four-decimals", .0005, 422)]


class Check(Suite):
    def __init__(self):
        core.MANAGEMENT = "http://127.0.0.1:8000/api/v1"
        self.platform = Platform()
        self.prefix = "CASE_" + datetime.now(CN).strftime("%Y%m%d_%H%M%S")
        self.state = {"target": BASE, "management": core.MANAGEMENT, "project_id": PROJECT_ID,
            "run_prefix": self.prefix, "scenarios": [], "api_cases": [], "web_cases": [], "fixtures": [], "cleanup": []}
        self.sessions, self.auth, self.user_ids, self.interfaces = {}, {}, {}, {}
        self.password, self.current = None, None

    def save(self):
        write_json(OUTPUT, self.state)

    def ledger_ids(self):
        ids = []
        for page in range(1, 100):
            rows = self.direct("employee", "GET", f"/beli/ledger?user_id={self.user_ids['employee']}&page={page}")
            ids.extend(row["id"] for row in rows)
            if len(rows) < 30:
                return sorted(ids)
        raise AssertionError("Unexpected ledger volume")

    def balance(self):
        return self.direct("employee", "GET", "/beli/accounts")["items"][0]

    def run(self):
        self.login("admin", "admin", os.environ["PUNKRECORD_PASSWORD"])
        pool = load_pool()
        use_existing_accounts(self, pool, read_password(pool))
        path = f"/beli/accounts/{self.user_ids['employee']}/adjust"
        interfaces = []
        for page in range(1, 50):
            batch = self.platform.call("GET", f"/api-testing/interfaces?project_id={PROJECT_ID}&pageSize=200&page={page}")
            interfaces.extend(batch["items"])
            if len(interfaces) >= batch["total"]:
                break
        matches = [row for row in interfaces if row.get("data", {}).get("method", "").upper() == "POST"
            and row.get("data", {}).get("path") in (path, "/beli/accounts/{user_id}/adjust")]
        assert matches, "No matching balance-adjustment interface; refusing to save cases under an unrelated API"
        interface = min(matches, key=lambda row: (row["data"]["path"] != "/beli/accounts/{user_id}/adjust", row["id"]))
        self.interfaces["POST " + path] = interface["id"]
        self.state["interface"] = {"id": interface["id"], "name": interface["name"], "path": interface["data"]["path"]}
        before = self.balance()
        ledger = self.ledger_ids()
        self.state["baseline"] = {"account": before, "ledger_ids": ledger}
        case_ids = []
        for code, amount, expected in CASES:
            def check(code=code, amount=amount, expected=expected):
                try:
                    self.call("manager", "POST", path, {"amount": amount, "reason": self.prefix + " 用户补充金额边界", "request_key": str(uuid4())}, expected=expected)
                finally:
                    after, after_ledger = self.balance(), self.ledger_ids()
                    unchanged = all(after[key] == before[key] for key in ("balance", "frozen", "available", "leave")) and after_ledger == ledger
                    self.current["no_side_effects"] = {"balance_before": before["balance"], "balance_after": after["balance"],
                        "ledger_count_before": len(ledger), "ledger_count_after": len(after_ledger), "passed": unchanged}
                    assert unchanged, "Rejected adjustment changed account or ledger"
                case_ids.append(self.current["evidence"][-1]["case_id"])
            self.scenario("ADJUST-BOUNDARY-" + code, f"调整余额 amount={amount}：明确拒绝且余额流水不变", ["BELI-06"], check)
        if len(case_ids) != 4:
            return
        flows = self.platform.call("GET", f"/execution/flows?project_id={PROJECT_ID}&pageSize=200")["items"]
        name = "调整余额金额边界（用户补充）"
        flow = next((row for row in flows if row["name"] == name), None)
        body = {"project_id": PROJECT_ID, "name": name, "status": "active", "description": "0、超大正数、超大负数、0.0005；只应拒绝且不改余额流水",
            "data": {"version": 1, "inputs": {}, "nodes": [{"key": "adjust", "name": "调整余额非法金额", "api_id": interface["id"], "case_id": case_ids[0], "auth_id": self.auth["manager"], "next": "end"}]}}
        flow = self.platform.call("PUT", f"/execution/flows/{flow['id']}", body) if flow else self.platform.call("POST", "/execution/flows", body)
        old = self.platform.call("GET", f"/execution/flows/{flow['id']}/scenarios")
        scene_ids = []
        for (code, amount, expected), case_id in zip(CASES, case_ids):
            name = f"金额{amount}拒绝（HTTP {expected}）"
            scene = next((row for row in old if row["name"] == name), None)
            payload = {"project_id": PROJECT_ID, "name": name, "status": "active", "description": "用户反馈的调整余额边界；账户和流水不变已在原生接口执行后核对",
                "data": {"flow_id": flow["id"], "template_version": flow["data"]["version"], "failure_policy": "stop", "nodes": {"adjust": {"case_id": case_id, "mode": "always"}}}}
            scene = self.platform.call("PUT", f"/execution/flows/{flow['id']}/scenarios/{scene['id']}", payload) if scene else self.platform.call("POST", f"/execution/flows/{flow['id']}/scenarios", payload)
            scene_ids.append(scene["id"])
        batch = self.platform.call("POST", f"/execution/flows/{flow['id']}/runs", {"scenario_ids": scene_ids, "mode": "serial", "concurrency": 1, "inputs": {}})
        self.state["native_flow"] = {"flow_id": flow["id"], "scenario_ids": scene_ids, "run_id": batch["id"]}
        self.save()
        deadline = time.monotonic() + 240
        while batch["status"] in {"queued", "running"} and time.monotonic() < deadline:
            time.sleep(2)
            batch = self.platform.call("GET", f"/execution/flows/{flow['id']}/runs/{batch['id']}")
        self.state["native_flow"]["result"] = batch
        assert batch["status"] in {"success", "failed", "cancelled", "interrupted"}, "Native flow did not complete"
        assert self.ledger_ids() == ledger and self.balance()["balance"] == before["balance"], "Flow changed balance/ledger"
        self.save()
        print("NATIVE_FLOW", flow["id"], batch["id"], batch["status"], flush=True)


def main():
    suite = Check()
    try:
        suite.run()
    finally:
        suite.cleanup()
        suite.state["finished_at"] = datetime.now(CN).isoformat()
        suite.save()
        print("OUTPUT", str(OUTPUT), flush=True)


if __name__ == "__main__":
    main()
