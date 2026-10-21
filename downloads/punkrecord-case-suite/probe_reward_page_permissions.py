"""Read-only headed checks using the already-active fixed test identities."""
from datetime import datetime
import json
import os
import time

from account_pool import load_pool, read_password
import case_suite_runner as core
from case_suite_runner import BASE, CN, HERE, PROJECT_ID, Platform, write_json
from headed_case_runner import HeadedSuite, check, click, login, step


class Probe(HeadedSuite):
    def __init__(self):
        # This deployed endpoint supports headed jobs; native API flows use local8000.
        core.MANAGEMENT = "https://dev-cn-01.yios.cn/autotest/api/v1"
        self.platform = Platform()
        for attempt in range(30):
            try:
                run = json.loads((HERE / "native-82-four-accounts-results.json").read_text(encoding="utf-8"))
                break
            except json.JSONDecodeError:
                time.sleep(.2)
        else:
            raise RuntimeError("Native run state is being rewritten; retry the read-only probe later")
        self.prefix = run["run_prefix"]
        self.account_pool = load_pool()
        self.password = read_password(self.account_pool)
        self.state = {"target": BASE, "project_id": PROJECT_ID, "run_prefix": self.prefix,
            "scenarios": [], "web_cases": [], "fixtures": [row for row in run["fixtures"] if row["type"] == "user"], "cleanup": []}

    def save(self):
        write_json(HERE / "reward-page-four-accounts-results.json", self.state)


def main():
    suite = Probe()
    for actor in ("supervisor", "employee", "other"):
        name = suite.account_pool["accounts"][actor]["display_name"]
        suite.run_case("BELI-PERM-" + actor.upper() + "-PAGE", name + "非L0仅看本人奖励，无审核和工作日历入口", ["IAM-02", "BELI-04"], "/beli",
            login() + [click("贝利"), check('h1:text-is("贝利")', "贝利"), click("任务奖励"), step("wait", "", 1500),
                check('.beli-tabs:not(:has(button:text-is("工作日历")))', "任务奖励"),
                check('.beli-table-wrap:not(:has(button:text-is("审核")))', "员工 / 任务"),
                check(f'.beli-table-wrap:not(:has(tbody tr:not(:has(td:first-child:has-text("{name}")))))', "员工 / 任务")], actor=actor)
    suite.run_case("BELI-PERM-L0-PAGE", "固定L0账号能看到待审核奖励入口但不提交", ["BELI-04"], "/beli",
        login() + [click("贝利"), check('h1:text-is("贝利")', "贝利"), click("任务奖励"), step("wait", "", 1500),
            check('.beli-tabs button:text-is("工作日历")', "工作日历"),
            check('.beli-table-wrap tr:has(button:text-is("审核")) >> nth=0', "审核")], actor="manager")
    suite.state["finished_at"] = datetime.now(CN).isoformat()
    suite.save()


if __name__ == "__main__":
    main()
