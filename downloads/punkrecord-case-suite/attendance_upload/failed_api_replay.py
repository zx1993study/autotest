"""Replay failed API definitions with owned runtime fixtures, not historical IDs."""
import json
from collections import Counter
from copy import deepcopy
from uuid import uuid4

import requests

from bootstrap import HERE, CampaignRepository, save
from account_pool import TARGET
from inspect_target import sessions, get
from review_common import EMPLOYEE, OTHER, MANAGER
from run import accounts
from app.db.session import SessionLocal
from app.repositories.sqlalchemy_resource_repository import SqlAlchemyResourceRepository
from app.scheduler.jobs.api_case_executor import ApiCaseExecutor
from app.services.project_auth_service import ProjectAuthService

OUT = HERE / "failed-rerun-api-execution-2.json"
PREFIX = "FAILED_REPLAY_20261021_" + uuid4().hex[:8]
COLLECTIONS = {
    "职位": "/iam/job-titles", "部门": "/iam/departments",
    "停用贝利规则": "/iam/beli-rules", "交易方": "/contract/counterparties",
    "任务": "/todo", "项目": "/project/projects", "下架商品": "/beli/products",
    "更新日志": "/changelog/entries", "非业务会议": "/meeting/records",
    "独立财务账户": "/finance/accounts", "未对账测试交易": "/finance/transactions",
    "草稿合同": "/contract/contracts", "待批请假（有效额度重测）": "/todo/leaves",
}


def group(case):
    return case["name"].split(" - ")[0].split(" ", 1)[1].rsplit(" ", 1)[0]


def replace_ids(value, replacements):
    if isinstance(value, dict):
        return {key: replace_ids(item, replacements) for key, item in value.items()}
    if isinstance(value, list):
        return [replace_ids(item, replacements) for item in value]
    if isinstance(value, str):
        for old, new in replacements.items():
            value = value.replace(old, new)
    return value


class Replay:
    def __init__(self, repository):
        self.repo = repository
        self.clients = sessions()
        self.admin = requests.Session()
        self.admin.headers.update(ProjectAuthService(repository).auth_headers(17863))
        self.executor = ApiCaseExecutor(repository)
        self.cases = json.loads((HERE / "failed-rerun-api-cases.json").read_text(encoding="utf-8"))
        self.text_cases = [c for c in self.cases if c["name"].startswith(("REQ ", "STR3 "))]
        self.state = {"project_id": 17796, "date": "2026-10-21", "prefix": PREFIX,
                      "runs": [], "fixtures": [], "cleanup": [], "blocked": []}
        self.replacements, self.fixtures = {}, {}
        self.before = accounts(self.clients["manager"])
        self.original_name = get(self.admin, "/iam/users/" + OTHER)["display_name"]
        save(OUT, self.state)

    def call(self, method, path, body=None, actor="admin", form=False):
        client = self.admin if actor == "admin" else self.clients[actor]
        response = client.request(method, TARGET + "/api/v1" + path,
                                  **({"data": body} if form else {"json": body}), timeout=30)
        payload = response.json()
        self.state.setdefault("support_calls", []).append({"method": method, "path": path,
            "body": body, "http": response.status_code, "response": payload})
        save(OUT, self.state)
        response.raise_for_status()
        assert payload.get("code") == 0, (path, payload.get("message"))
        return payload.get("data")

    def remember(self, path, data, body, actor):
        if isinstance(data, dict) and data.get("id"):
            entry = {"path": path, "id": data["id"], "body": body, "actor": actor}
            if not any(x["path"] == path and x["id"] == data["id"] for x in self.state["fixtures"]):
                self.state["fixtures"].append(entry)
                save(OUT, self.state)

    def create(self, path, body, actor="admin"):
        result = self.call("POST", path, body, actor)
        self.remember(path, result, body, actor)
        return result

    def positive_body(self, case):
        data = deepcopy(case["data"])
        meta = data.get("required_text_validation") or data.get("string_validation")
        for field in meta["fields"]:
            data["body"][field] = PREFIX + " " + field
        resolved, _ = self.executor.prepare_execution({**case, "data": data}, {})
        return replace_ids(resolved["data"]["body"], self.replacements)

    def setup(self):
        party = self.create("/contract/counterparties", {"name": PREFIX + " party", "type": "customer",
            "identifier": PREFIX, "address": PREFIX, "bank_name": PREFIX})
        other_party = self.create("/contract/counterparties", {"name": PREFIX + " supplier", "type": "supplier",
            "identifier": PREFIX + "B", "address": PREFIX, "bank_name": PREFIX})
        for case in self.text_cases:
            for key in ("party_a_id", "party_b_id", "counterparty_id", "entity_id"):
                old = case["data"].get("body", {}).get(key)
                if old:
                    self.replacements[old] = other_party["id"] if key == "party_b_id" else party["id"]
        order = ["职位", "部门", "停用贝利规则", "交易方", "任务", "项目", "下架商品",
                 "更新日志", "独立财务账户", "未对账测试交易", "草稿合同"]
        for name in order:
            source = next((c for c in self.text_cases if group(c) == name
                           and c["data"]["path"] == COLLECTIONS[name]), None)
            if name == "交易方":
                fixture = party
            else:
                assert source, (name, "Missing positive fixture source")
                actor = "manager" if source["data"]["auth_id"] == 20373 else "admin"
                fixture = self.create(COLLECTIONS[name], self.positive_body(source), actor)
            self.fixtures[name] = fixture
            if name == "独立财务账户":
                for case in self.text_cases:
                    old = case["data"].get("body", {}).get("account_id")
                    if old:
                        self.replacements[old] = fixture["id"]
        project = self.fixtures["项目"]["id"]
        self.call("POST", f"/project/projects/{project}/members", {"user_id": EMPLOYEE}, "manager")
        self.stage = get(self.clients["manager"], f"/project/projects/{project}/stages")[0]["id"]
        self.plan_task = self.create("/todo", {"title": PREFIX + " plan", "assignee_user_id": EMPLOYEE,
            "source_type": "custom", "action_type": "do", "estimated_hours": 0,
            "due_at": "2026-10-23T18:00:00+08:00",
            "link": {"project_id": project, "dev_type": "dev_backend"}}, "manager")

    def runtime_case(self, original):
        case = deepcopy(original)
        data = replace_ids(case["data"], self.replacements)
        name, method, path = group(case), data["method"], data["path"]
        if name == "项目阶段":
            data["path"] = f"/project/projects/{self.fixtures['项目']['id']}/stages/{self.stage}"
        elif name == "项目任务计划":
            data["path"] = f"/project/projects/{self.fixtures['项目']['id']}/todos/{self.plan_task['id']}/plan"
        elif method in {"PATCH", "PUT"} and name != "员工":
            data["path"] = COLLECTIONS[name] + "/" + self.fixtures[name]["id"]
        data["replay_context"] = {"original_path": path, "scope": PREFIX, "assertions_unchanged": True}
        case["data"] = data
        return case

    def execute(self, case):
        captured = {}
        record = self.executor.execute(case, {"project_id": 17796, "mode": "server_headless",
                                               "config": {"timeout": 30}}, response_capture=captured)
        data = record["data"]
        entry = {"case_id": case["id"], "name": case["name"], "record_id": record["id"],
                 "status": record["status"], "data": data}
        self.state["runs"].append(entry)
        save(OUT, self.state)
        request = data.get("request", {})
        try:
            body = json.loads(captured.get("body") or "{}")
        except ValueError:
            body = {}
        if request.get("method") == "POST" and request.get("path") in COLLECTIONS.values():
            actor = "employee" if case["data"]["auth_id"] == 20375 else "manager" if case["data"]["auth_id"] == 20373 else "admin"
            self.remember(request["path"], body.get("data"), request.get("body"), actor)
        print(json.dumps({"case_id": case["id"], "record_id": record["id"], "http": data.get("response_status"),
                          "status": record["status"], "error": data.get("error")}, ensure_ascii=False), flush=True)

    def cleanup(self):
        self.call("PATCH", "/iam/users/" + OTHER, {"display_name": self.original_name})
        self.state["employee_name_restored"] = get(self.admin, "/iam/users/" + OTHER)["display_name"] == self.original_name
        for item in reversed(self.state["fixtures"]):
            path, item_id = item["path"], item["id"]
            target = path + "/" + item_id
            try:
                action = self.cleanup_one(item, target)
                self.state["cleanup"].append({"path": target, "status": "success", "action": action})
            except Exception as error:
                self.state["cleanup"].append({"path": target, "status": "failed", "error": str(error)})
            save(OUT, self.state)
        self.state["balances_restored"] = accounts(self.clients["manager"]) == self.before
        self.state["counts"] = dict(Counter(row["status"] for row in self.state["runs"]))
        save(OUT, self.state)

    def cleanup_one(self, item, target):
        path = item["path"]
        if path in {"/iam/job-titles", "/iam/departments", "/iam/beli-rules", "/project/projects",
                    "/changelog/entries", "/meeting/records"}:
            self.call("DELETE", target, actor=item["actor"])
            return "deleted_owned_id"
        if path == "/todo":
            self.call("POST", target + "/dismiss", {"dismiss_reason": PREFIX + " cleanup"}, "employee")
            return "dismissed_owned_task"
        if path == "/todo/leaves":
            self.call("POST", target + "/reject", {"comment": PREFIX + " cleanup"}, "manager")
            return "rejected_owned_leave"
        if path == "/finance/transactions":
            self.call("POST", target + "/void")
            self.call("DELETE", target)
            return "voided_and_deleted_owned_transaction"
        if path == "/finance/accounts":
            self.call("PATCH", target, {"status": "inactive"})
            return "disabled_owned_account"
        if path == "/beli/products":
            self.call("PUT", target, {**item["body"], "active": False}, "manager")
            return "unpublished_owned_product"
        return "audit_retained_no_delete_api"


def main():
    assert not OUT.exists(), "Evidence already exists; do not overwrite or repeat writes"
    with SessionLocal() as db:
        run = Replay(CampaignRepository(SqlAlchemyResourceRepository(db)))
        try:
            run.setup()
            for case in sorted(run.text_cases, key=lambda c: c["id"]):
                run.execute(run.runtime_case(case))
            for case in run.cases:
                if case not in run.text_cases:
                    run.state["blocked"].append({"case_id": case["id"], "reason": "Legacy deleted account/one-time fixture; replay owning chain separately"})
        finally:
            run.cleanup()
        print(json.dumps({k: run.state[k] for k in ("counts", "balances_restored", "employee_name_restored", "blocked")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
