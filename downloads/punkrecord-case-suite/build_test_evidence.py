"""Reconcile saved amount assertions; this does not execute new remote tests."""
from decimal import Decimal
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent


def main():
    summary = json.loads((HERE / "case-coverage-final.json").read_text(encoding="utf-8"))
    native = {c["id"]: c for c in json.loads((HERE / "case-native-api-cases.json").read_text(encoding="utf-8"))}

    def assertion(evidence, path):
        definition = native[evidence["case_id"]]["assertions"]
        index = next(i for i, a in enumerate(definition) if a.get("path") == path)
        result = evidence["assertions"][index]
        assert result["passed"] and Decimal(str(result["actual"])) == Decimal(str(result["expected"]))
        return Decimal(str(result["actual"]))

    rows = []
    for scene in summary["scenarios"]:
        if not scene["code"].startswith("BELI02-"):
            continue
        assert scene["status"] == "success"
        _, priority, days = scene["code"].split("-")
        evidence = scene["evidence"]
        review = next(e for e in evidence if e["path"].startswith("/beli/rewards/") and e["method"] == "POST")
        accounts = [e for e in evidence if e["path"] == "/beli/accounts"]
        assert len(accounts) == 3
        amount = assertion(review, "data.amount")
        before = assertion(accounts[1], "data.items.0.balance")
        after = assertion(accounts[2], "data.items.0.balance")
        assert after - before == amount
        rows.append({"scenario": scene["code"], "priority": priority, "days_late": int(days),
                     "expected_reward": str(amount.quantize(Decimal(".01"))),
                     "actual_reward": str(amount.quantize(Decimal(".01"))),
                     "before_balance": str(before), "after_balance": str(after),
                     "reward_record": review["record_id"], "before_record": accounts[1]["record_id"],
                     "after_record": accounts[2]["record_id"], "status": "success"})
    assert len(rows) == 28
    (HERE / "beli-value-evidence.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# 异常、边界与贝利数值核对", "", "依据2026-10-19远程执行的已保存证据重新核对，不表示本次又执行了一轮业务测试。",
             "", "## 已执行异常场景", "",
             "- IAM01/IAM02：普通员工、非管理员L0读取工资拒绝；员工跨账户流水和调整余额拒绝。",
             "- BELI04：未验收、工资缺失、非L0审核不发奖；拒绝奖励不改变任务完成态。",
             "- BELI06/BELI08：原因为空、同键异参、工时归零后伪造审核拒绝。",
             "- SHOP02/SHOP06/SHOP07：余额或库存不足拒绝，已发货禁止普通退款，冻结后余额下降不能审批通过。",
             "", "## 已执行边界场景", "",
             "- 普通待办/项目任务/Bug三种来源：工时省略、0、1.25、-1、null、0.001、字符串NaN/Infinity；前三种有效，其余应422。",
             "- 三种来源缺截止日拒绝；批量生成同样验证非法工时与重复生成；UTC截止时间转上海时间。",
             "- 延期0/1/2/3/4/5/8天；4个重要级；假期兑换0.5天通过、0.1天拒绝。",
             "- 任务工时归零/恢复、重复审批/取消/重开等串行幂等；完成列表首批10条并加载到12条。",
             "", "## 贝利数值证据", "", "工资12000、工时8小时。下表28个组合均核对奖励金额及账户余额增量。",
             "金额预期值保存在原生用例assertions；实际值来自执行记录assertions.actual，不是重新调用业务接口得到的值。",
             "", "| 重要级 | 延期天 | 预期奖励 | 实际奖励 | 账户余额前→后 | 奖励记录 | 余额记录 |",
             "|---|---:|---:|---:|---|---:|---|"]
    for row in rows:
        lines.append(f"| {row['priority']} | {row['days_late']} | {row['expected_reward']} | {row['actual_reward']} | {row['before_balance']}→{row['after_balance']} | {row['reward_record']} | {row['before_record']},{row['after_record']} |")
    lines += ["", "其他已测数值：重复审核1小时任务仅增加30；重开冲销回原余额；审核改2小时P0奖励72；手工加10重复只加一次，再减10恢复；兑换冻结/解冻100及假期0.5天。",
              "", "## 尚未完成", "", "- ATT-01～ATT-07早会扣款、缺席/请假冲销与全员结算未执行。",
              "- MySQL并发审批、归零与发奖竞态、最后一件库存竞争未执行；串行防重不能代替并发。",
              "- 历史缺失字段、规则生效前任务、全局策略未初始化、网络失败/事务回滚未执行。",
              "- 多种工资/工时导致分位舍入的完整组合、极大值上下限未穷举；不能认定全部数值边界已覆盖。",
              "- 尚未逐笔核对完整账本与期初期末勾稽，只验证了相关操作金额、账户余额和冻结额；不宣称全量账本对账通过。",
              "", "## 测试数据状态", "", "按用户确认，重复的33个停用测试账号及专属依赖记录已备份后删除；平台历史执行记录保留。",
              "保留最近3个固定账号，后续只复用，不再自动新建。详见test-account-maintenance-report.md。"]
    (HERE / "test-types-and-beli-values.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    sample = next(r for r in rows if r["scenario"] == "BELI02-p2-0")
    print(json.dumps({"reconciled_combinations": len(rows), "sample": sample}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
