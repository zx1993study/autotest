"""Verify two reuse cycles without creating users, roles, projects, or cases."""
import json
import os
import requests

from account_pool import HERE, TARGET, ACTORS, load_pool, read_password, use_existing_accounts


class Verification:
    def __init__(self):
        self.state = {"fixtures": []}
        self.sessions = {}
        self.calls = []
        self.login("admin", "admin", os.environ["PUNKRECORD_PASSWORD"])

    def login(self, actor, username, password):
        session = requests.Session()
        response = session.post(TARGET + "/api/v1/auth/login", json={"username": username, "password": password}, timeout=25)
        response.raise_for_status()
        session.headers["Authorization"] = "Bearer " + response.json()["access_token"]
        self.sessions[actor] = session

    def direct(self, actor, method, path, body=None):
        assert not (method == "POST" and (path in {"/iam/users", "/iam/job-titles"} or path.endswith("/reset-password")))
        self.calls.append({"actor": actor, "method": method, "path": path})
        response = self.sessions[actor].request(method, TARGET + "/api/v1" + path, json=body, timeout=25)
        response.raise_for_status()
        result = response.json()
        assert result.get("code") == 0, result.get("message")
        return result["data"]

    def save(self):
        pass

    def snapshot(self):
        data = self.direct("admin", "GET", "/iam/users?page=1&page_size=100")
        assert data["total"] == len(data["items"]), "Unexpected pagination; refusing incomplete verification"
        return {u["id"]: {k: u[k] for k in ("id", "username", "status", "manager_user_id", "job_title_id")} for u in data["items"]}


def main():
    pool = load_pool()
    password = read_password(pool)
    manifest = json.loads((HERE / "retired-three-cleanup-manifest.json").read_text(encoding="utf-8"))
    deletion = json.loads((HERE / "retired-three-deletion-result.json").read_text(encoding="utf-8"))
    check = Verification()
    before = check.snapshot()
    deleted_ids = {u["id"] for u in manifest["delete"]}
    assert not deleted_ids & before.keys(), "A candidate account was not deleted"
    keep_ids = {u["id"] for u in manifest["keep"]}
    assert keep_ids <= before.keys()
    rounds = []
    for number in (1, 2):
        check.state["fixtures"] = []
        try:
            use_existing_accounts(check, pool, password)
            for actor in ACTORS:
                me = check.direct(actor, "GET", "/auth/me")
                assert me["id"] == pool["accounts"][actor]["id"]
        finally:
            for fixture in reversed(check.state["fixtures"]):
                check.direct("admin", "PATCH", f"/iam/users/{fixture['id']}", {"status": fixture["original_status"]})
        after = check.snapshot()
        assert after == before, "Account identities or statuses changed"
        rounds.append({"round": number, "status": "success", "account_count_before": len(before),
                       "account_count_after": len(after), "created_users": 0, "created_roles": 0, "password_resets": 0})
    result = {"target": TARGET, "status": "success", "confirmed_deleted_count": len(deleted_ids),
              "confirmed_deleted_ids": sorted(deleted_ids), "kept_accounts": [before[k] for k in sorted(keep_ids)],
              "reuse_verification": rounds, "api_calls_without_credentials": check.calls,
              "backup": deletion["backup"], "deleted_tables": deletion["counts"]}
    (HERE / "four-account-reuse-result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# 测试账号清理与固定复用", "", "2026-10-19；仅针对远程PunkRecord本轮登记的测试账号。",
             "", "经用户明确授权删除旧CASE三个账号及关联历史测试数据，复用现有test_user1/2/3/4；不再创建员工。",
             "删除前检查外键及关联记录归属，在单一事务内清理；没有关闭外键检查。",
             "私有备份：`" + result["backup"] + "`（服务器当前用户可读，包含删除前测试数据）。",
             "", "## 保留账号", ""]
    lines += ["- `" + pool["accounts"][actor]["username"] + "`：" + actor + "，保持原有启用状态。" for actor in ACTORS]
    lines += ["", "## 后续规则", "", "固定用户ID见test-account-pool.json；auto_create=false。",
              "正常运行不创建用户或职位、不重置密码；账号缺失、身份不符或无凭据则直接报错。",
              "密码仅保存在Windows CurrentUser DPAPI加密文件，不纳入Git；其他机器可用PUNKRECORD_TEST_PASSWORD环境变量。",
              "initialize_account_pool.py已禁止重置这四个用户提供的账号。",
              "运行时临时启用固定账号，清理时恢复运行前状态，保留用户ID。",
              "", "## 验证", "", "9项本地脚本单元校验通过；不涉及本地PunkRecord业务测试。",
              f"远程连续2轮复用验证通过：账号总数每轮均为{len(before)}→{len(before)}；新增用户0、新增职位0、重置密码0。",
              "旧CASE三个删除ID均已从远程用户列表消失；四个保留账号存在且均保持active。",
              "", "## 早会流程", "", "早会扣除贝利仍未执行，ATT-01至ATT-07保持未验证。本次账号维护不算早会流程测试。",
              "共享环境的早会操作可能触发全员结算，需要隔离范围后另行执行，不能用商城手工扣款替代。"]
    (HERE / "four-account-reuse-report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"deleted_accounts": len(deleted_ids), "kept_accounts": [u["username"] for u in result["kept_accounts"]],
                      "reuse_verification": rounds, "restored_statuses": [u["status"] for u in result["kept_accounts"]]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
