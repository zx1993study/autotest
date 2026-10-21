"""Explicit decisions for this one project's workflow cleanup."""
import re

GROUPS = {
    "shop": ("商城下单与审核", "准备商品与余额→购买商品→审核通过/拒绝/取消→核对订单、库存与冻结"),
    "reward": ("获取贝利", "创建任务→提交完成→主管验收→L0奖励审核→核对到账；含奖励计算、拒绝、重开冲销分支"),
    "task": ("任务提交与验收", "创建任务→提交完成→上级验收/退回→重新提交与验收"),
    "project": ("项目任务生成与同步", "准备项目计划→生成/同步任务→修改计划→重复同步→核对任务身份"),
    "leave": ("请假申请与审核", "准备假期额度→提交请假→主管查看→批准/拒绝→核对假期余额"),
    "adjust": ("贝利调整与防重", "读取账户→调整余额→重复请求/异参重放→核对余额与流水"),
    "attendance": ("扣除贝利（早会考勤）", "录入早会信息→更新参会人→考勤结算→核对扣款及重复结算"),
    "product": ("商城商品上架与下架", "创建商品→发布→员工可见性→下架→员工不可见"),
    "bug": ("Bug创建与检索", "创建不同标题Bug→关键词/分页检索→核对返回记录"),
}


def classify(flow):
    name = flow["name"]
    if flow["id"] == 19763 or "FOUR-ADJUST-BOUNDARIES" in name:
        return "api", "单接口金额参数校验，保留对应 API 正式用例"
    if "SHOPPLUS-QTY-" in name or "SHOPPLUS-INPUT-" in name or "SHOPPLUS-DELIVERY-MAX" in name:
        return "api", "单接口字段输入校验（含空文本、纯空格、长文本），不建立功能场景"
    if re.search(r"TODO01-(custom|project|bug)-", name):
        return "api", "单接口工时/必填参数校验，保留对应 API 正式用例"
    if "IAM" in name or "DOC01" in name or "TODO05-zone" in name:
        return "api", "接口授权/文档/单值校验，不是业务链路"
    if "FOUR-" in name and not any(s in name for s in ("TASK-ACCEPT-", "LEAVE-CHAIN-")):
        return "api", "独立接口授权/历史对象操作，保留 API 用例，不伪装完整流程"
    if "SHOP02-insufficient" in name:
        return "api", "两个独立下单拒绝参数测试，无完整业务链路"
    if "ATT-" in name:
        return "attendance", "合并早会缺席扣款和防重复扣款"
    if "SHOP01-publish" in name:
        return "product", "保留商品发布生命周期"
    if "SHOP" in name:
        return "shop", "合并商城下单、审核和资金/库存状态分支"
    if "BELI06" in name:
        return "adjust", "保留余额调整与幂等链路"
    if "BELI" in name:
        return "reward", "合并任务奖励端到端场景"
    if "LEAVE" in name:
        return "leave", "合并请假批准与拒绝链路"
    if any(s in name for s in ("TODO01-03", "TODO02", "TODO03")):
        return "project", "合并项目任务生成/同步链路"
    if "TODO05-resubmit" in name or "TASK-ACCEPT" in name:
        return "task", "合并任务提交、退回、验收链路"
    if "BUG01" in name:
        return "bug", "创建后检索的真实链路，不包含空文本/长文本校验"
    raise ValueError("Unclassified flow: " + name)


def scenario_name(flow, scene):
    # Old scene names were all '完整回归'; their descriptions carry the actual branch.
    desc = scene.get("description") or ""
    label = desc.split("；所有步骤")[0] if desc else scene["name"]
    code = flow["name"].split()[-1]
    return (code + " " + label)[:200]
