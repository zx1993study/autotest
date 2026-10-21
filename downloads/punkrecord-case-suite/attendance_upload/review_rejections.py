"""Require the intended business rejection, not just any HTTP 4xx response."""
from copy import deepcopy

from bootstrap import HERE, CampaignRepository, save
from plan import equal

from app.db.session import SessionLocal
from app.repositories.sqlalchemy_resource_repository import SqlAlchemyResourceRepository
from app.services.api_flow_scenario_service import ApiFlowScenarioService


# These messages match the named test points and the reviewed API rules.
RULES = {
    21068: {7: "只有审核员才能审核此任务", 8: "只有审核员才能审核此任务"},
    21069: {7: "只有审核员才能审核此任务", 8: "只有审核员才能审核此任务"},
    21101: {14: "任务贝利已发放，请先重开任务冲销奖励后再修改计划"},
    21103: {5: "任务必须先通过待办验收", 9: "请先由管理员补录员工基本工资", 12: "仅 L0 可执行此操作"},
    21104: {12: "该任务不在本次奖励范围"},
    21105: {12: "奖励当前不可审核", 16: "预计工时必须大于零才能审核贝利"},
    21106: {12: "奖励当前不可审核", 16: "预计工时必须大于零才能审核贝利"},
    21108: {6: "重复请求标识对应的调整内容不同"},
    21112: {9: "仅上级主管可审批此请假申请", 12: "仅上级主管可审批此请假申请", 14: "仅待审批的请假可通过"},
    21113: {10: "仅上级主管可审批此请假申请", 15: "仅上级主管可审批此请假申请", 17: "仅待审批的请假可拒绝"},
    21115: {2: "仅 L0 可执行此操作"},
    21117: {17: "仅 L0 可执行此操作"},
    21120: {17: "订单状态不允许此操作"},
    21122: {14: "当前余额不足以支付被冻结的兑换，请先处理余额"},
    21128: {6: "商品已下架或库存不足"},
    21129: {6: "商品已下架或库存不足"},
    21130: {6: "商品已下架或库存不足"},
    21131: {6: "可用贝利不足"},
    21132: {6: "商城兑换面向非 L0 员工"},
    21133: {6: "可用贝利不足"},
    21134: {8: "重复请求标识对应的兑换内容不同", 9: "重复请求标识对应的兑换内容不同", 10: "重复请求标识对应的兑换内容不同"},
    21135: {12: "仅 L0 可执行此操作", 14: "仅 L0 可执行此操作", 17: "仅待发货实物订单可发货，请填写发货信息", 20: "未找到兑换单"},
    21136: {21: "可用贝利不足"},
    21137: {20: "订单状态不允许此操作", 22: "仅待发货实物订单可发货，请填写发货信息"},
    21157: {7: "只有上报完成的任务才能审核"},
    21159: {6: "可用假期不足，当前剩余 0.0 天"},
}
SCHEMA_RULES = {
    21063: {12: ("greater_than_equal", ["body", "tasks", 0, "estimated_hours"]),
            13: ("decimal_type", ["body", "tasks", 0, "estimated_hours"]),
            14: ("decimal_max_places", ["body", "tasks", 0, "estimated_hours"]),
            15: ("finite_number", ["body", "tasks", 0, "estimated_hours"]),
            16: ("finite_number", ["body", "tasks", 0, "estimated_hours"])},
    21121: {2: ("value_error", ["body"])},
    21135: {18: ("literal_error", ["body", "action"])},
}


def append_unique(assertions, rules):
    for rule in rules:
        if rule not in assertions:
            assertions.append(rule)


def main():
    changes = []
    with SessionLocal() as db:
        repo = CampaignRepository(SqlAlchemyResourceRepository(db))
        service = ApiFlowScenarioService(repo)
        for scene_id in sorted(RULES.keys() | SCHEMA_RULES.keys()):
            row = repo.get("api_flow_scenarios", scene_id)
            data = deepcopy(row["data"])
            for number, message in RULES.get(scene_id, {}).items():
                node = data["nodes"][f"review_node_{number:02d}"]
                http = next(r["expected"] for r in node["assertions"] if r["type"] == "status")
                assert 400 <= http < 500
                append_unique(node["assertions"], [equal("/code", http), equal("/message", message)])
            for number, (kind, location) in SCHEMA_RULES.get(scene_id, {}).items():
                node = data["nodes"][f"review_node_{number:02d}"]
                append_unique(node["assertions"], [equal("/detail/0/type", kind), equal("/detail/0/loc", location)])
            service.update_for_flow(data["flow_id"], scene_id, {"data": data})
            changes.append(scene_id)
    save(HERE / "rejections-applied.json", changes)
    print({"scenes": len(changes), "rejection_nodes": sum(map(len, RULES.values())) + sum(map(len, SCHEMA_RULES.values()))})


if __name__ == "__main__":
    main()
