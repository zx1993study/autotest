"""Persist unexecuted branches as explicit Given/When/Then cases, not passes."""
import json

from case_suite_runner import HERE, PROJECT_ID, SOURCE, Platform, write_json


CASES = [
    ("TODO-04", "历史任务缺截止日", "仅测试账号名下、历史截止日为空的任务", "提交完成前补齐截止日期，再提交并验收", "补录前拒绝提交，补录后成功；旧任务其他字段不被覆盖", "需要专属历史空值夹具；不修改现有历史任务"),
    ("TODO-04", "历史空工时与正数不被迁移覆盖", "历史任务工时分别为NULL、0和正数", "读取、编辑非计划字段并验收", "NULL按0显示，不因普通编辑发奖；原NULL和正数不被迁移改写", "需要历史空值夹具及迁移沙箱"),
    ("TODO-07", "历史待验收缺提交时间", "固定员工待验收任务submitted_at为空", "直接验收；再撤回并由员工重新提交验收", "第一次明确拒绝；重新提交后成功，提交时间为本次真实时间", "需要数据库历史夹具，不伪造远程当前任务时间"),
    ("LEAVE-02", "历史请假待办隔离", "历史Todo的link.leave_id指向独立请假单", "查看普通待办、奖励队列并依次尝试开始/提交/批准/退回/取消旧Todo", "不进入普通队列；旧写操作拒绝，历史记录保留；请假审批仍走独立接口", "需要历史请假Todo夹具"),
    ("LEAVE-04", "微信请假与任务编号区分", "专用测试微信绑定固定主管，任务与请假均待审批", "分别引用请假编号和任务编号执行审批", "正确识别单据类型，不把请假调用普通任务审批", "缺专用微信绑定；不发送真实业务消息"),
    ("LEAVE-04", "微信混合批量审批", "专用测试微信会话有多条任务/请假待审批", "同条消息批准和驳回混合编号，包含无效与已处理编号", "逐条结果可追溯，重复不重复扣假；无效编号不误操作其他单据", "缺专用微信绑定及通道授权"),
    ("BELI-09", "规则生效前完成后补录", "固定员工任务完成时间早于hours_rule_starts_at", "补录正数工时、重复保存和普通编辑", "不生成追溯奖励、不改完成时间、不直接发钱", "需要历史完成时间夹具"),
    ("BELI-09", "缺少可靠时间不自动入队", "固定员工历史已完成任务缺submitted_at或done_at", "补录正数工时，再尝试奖励审核", "不自动入队，不伪造时间；明确拒绝不可靠结算", "需要历史空时间夹具"),
    ("BELI-09", "策略未初始化及合法旧审核保留", "独立策略未初始化数据集，另有合法已审核奖励", "普通编辑历史任务并重新读取旧奖励", "不追溯旧任务、不丢失已有合法审核和流水", "不能删除当前环境全局策略；需专属数据集"),
    ("ATT-01", "启用日前与无会议", "有可控启用日期和仅3账号的应到名单", "分别结算启用日前、启用后无会议日期", "均不扣款，余额和流水数不变", "当前考勤结算会遍历全体员工"),
    ("ATT-01", "非工作日与L0豁免", "休息日早会以及工作日L0缺席", "结算并重复结算", "非工作日和L0均不扣款", "全局日历/考勤会涉及其他账号"),
    ("ATT-02", "缺席扣500允许负数", "固定员工余额分别500、499.99、0，工作日早会未参会", "结算三种余额边界", "分别为0、-0.01、-500，流水每人仅一笔-500", "全员考勤重算，未获准影响其他账号"),
    ("ATT-02", "同日多会议取并集防重", "同日两份早会，固定两员工分别在不同会议", "创建第二份、重复结算和重复保存", "名单取并集，两人均不扣；真正缺席仅扣一次", "创建早会会重算已有员工"),
    ("ATT-03", "精确姓名和未匹配提示", "参会名分别为精确姓名、同音/近似姓名、未知姓名", "保存说话人映射并结算，管理员查看未匹配列表", "不模糊匹配；未知和近似均明确提示；未匹配员工按缺席", "早会全员重算，需专用名单"),
    ("ATT-03", "重名及未发言人员", "两员工同名，另有应到但无语音分段的员工", "分别以重名和明确补录方式保存参会人", "重名不任意匹配；未发言不等于自动到场；明确参会后差额冲正", "需要重名夹具且早会涉及全员"),
    ("ATT-04", "上午请假和仅下午请假", "同工作日员工一上午已批假、员工二仅下午已批假", "结算未参会早会", "上午请假豁免，下午请假仍扣500；仅扣对应假期", "早会重算和当日请假可能涉及已有员工"),
    ("ATT-04", "事后批准请假自动冲正", "固定员工已被当日早会扣500，上午假待审批", "批准该假并重复请求", "冲正500仅一次，余额恢复，独立请假流水不重复", "需真实早会扣款前置，当前尚未执行"),
    ("ATT-05", "补录和删除早会差额更正", "固定员工已缺席扣款且有本轮早会", "补录参会人、移除参会人、删除会议", "只按差额冲正/扣款，保留全部历史流水，重复保存不重复扣款", "需要可控早会且会重算其他账号"),
    ("ATT-05", "日历调整与作废不重扣", "缺席扣款已生成，L0可作废", "空原因作废、合法作废、工作日休息日互改、重复重算", "原因必填；合法冲正一次；之后重算不恢复已作废扣款", "不修改全局日历和他人考勤"),
    ("ATT-06", "中断补结算和未来会议到期", "可控时钟及定时任务，固定员工未来早会", "模拟中断跨过结算日，恢复任务并重复运行", "补结算一次；未来日期到期前不扣，到期后按应到结算", "当前15173不重启服务、不改系统时间"),
    ("ATT-07", "历史更名停用升L0保留快照", "已结算早会，保存姓名快照与当时应到身份", "分别更名、停用、升L0后重算历史日期", "不重扣已出席者、不返还旧缺席款；历史姓名/身份快照不变", "需要早会历史数据集；不能更改已有员工身份"),
    ("SHOP-07", "冻结后真实早会扣款", "固定员工余额100、兑换冻结100且工作日缺席", "真实早会扣500后批准兑换，再取消兑换", "余额为-400；审批拒绝；取消只解冻不凭空退款；库存恢复", "此前仅手工扣减模拟，真实早会前置仍受全员重算限制"),
    ("BUG-02", "URL刷新和前进后退", "本轮项目31个Bug，含多状态和唯一搜索词", "搜索、筛选、翻页、浏览器前进后退并刷新", "URL与结果一致，分页不丢筛选，不跨项目泄漏", "待补浏览器历史操作和31项分页自动化"),
    ("BUG-03", "Bug附件完整生命周期", "本轮项目Bug与有效PNG附件", "创建、编辑、补图、预览、验收、重开，390与1440视口检查", "始终同一Todo，图可访问，状态一致，无页面横向溢出", "待补真实上传/预览及双视口脚本"),
    ("TODO-08", "全视图明暗色和移动端", "固定账号的正数、0、空工时及已完成任务", "我的/团队、看板/列表、明/暗色、390/1440组合，工时归零恢复", "贝利标识和颜色正确，移动不溢出，优先级/状态语义不变", "团队审核人下拉缺项原失败未修复；其余组合待补"),
    ("SHOP-01", "认证商品图片上传粘贴", "仅本轮测试商品与有效/伪造/超限图片", "上传和粘贴；管理员及员工查看；下架后再请求图片", "有效图渲染；伪造和超限拒绝；员工不能看下架图片", "待补图片二进制及浏览器渲染检查"),
    ("GENERAL", "HTTP无randomUUID弹窗", "当前HTTP页面且crypto.randomUUID不可用", "调整与兑换弹窗提交固定账号测试数据", "回退生成合法UUID，弹窗正常，重复提交保持防重", "待补页面能力覆盖与UUID回退断言"),
    ("GENERAL", "迁移无追溯且可重复", "专属迁移前备份含NULL/正数工时、历史余额与旧任务", "升级并重复执行迁移", "期初只结转一次，不重置规则时间，不伪造日期/工时、不补历史奖励", "禁止在当前共享数据集执行破坏性迁移"),
    ("GENERAL", "真实ASR和文稿模板", "本轮非早会会议、测试音频及明确文稿模板", "上传音频、转写、编辑说话人和按模板生成文稿", "转写和映射持久化、模板结构字段可核对", "收费AI/ASR未获具体额度授权；模板期望需确认"),
]


def main():
    rows = [{"id": f"GAP-{number:02}", "case_point": point, "title": title, "given": given,
        "when": when, "then": then, "status": "not_run", "blocker": blocker,
        "source_commit": SOURCE, "target": "http://14.103.229.153:15173"}
        for number, (point, title, given, when, then, blocker) in enumerate(CASES, 1)]
    result_path = HERE / "beli-supplement-results.json"
    if result_path.exists():
        result = json.loads(result_path.read_text(encoding="utf-8"))
        latest = {row["code"]: row for row in result["scenarios"]}
        mapping = {1: ("SUP-HISTORY-DATE", "verified"), 2: ("SUP-HISTORY-HOURS", "partial"),
            3: ("SUP-HISTORY-SUBMIT", "verified"), 4: ("SUP-HISTORY-LEAVE", "verified"),
            7: ("SUP-HISTORY-PRE-RULE", "verified"), 8: ("SUP-HISTORY-NO-TIME", "partial")}
        for number, (code, status) in mapping.items():
            if latest.get(code, {}).get("status") == "success":
                row = rows[number - 1]
                row.update(status=status, evidence=code,
                    blocker="本轮新建任务夹具已验证" if status == "verified" else "缺字段主分支已验证；迁移或额外缺done_at组合仍未执行")
    write_json(HERE / "supplement-unfinished-cases.json", rows)
    lines = ["# 回归分支补充用例", "", "明确区分已验证、部分验证和未执行；不创建账号、不变更当前15173服务。", ""]
    for row in rows:
        lines += [f"## {row['id']} {row['case_point']} {row['title']}", "", f"前置：{row['given']}",
            f"步骤：{row['when']}", f"预期：{row['then']}", f"状态：{row['status']}；{row['blocker']}", ""]
    text = "\n".join(lines)
    (HERE / "supplement-unfinished-cases.md").write_text(text, encoding="utf-8")
    api = Platform()
    old = json.loads((HERE / "supplement-gap-platform.json").read_text(encoding="utf-8")) if (HERE / "supplement-gap-platform.json").exists() else None
    body = {"project_id": PROJECT_ID, "name": "cases.md回归分支补充用例29项", "status": "active",
        "data": {"domain": "WEB", "kind": "test_case_catalog", "knowledge_key": "punkrecord.cases_md.remaining_branches",
            "content": text, "verification_status": "unverified", "cases": rows}}
    saved = api.call("PUT", f"/project-knowledge/{old['knowledge_id']}", body) if old else api.call("POST", "/project-knowledge", body)
    write_json(HERE / "supplement-gap-platform.json", {"knowledge_id": saved["id"], "count": len(rows)})
    print("GAP_CATALOG", len(rows), "KNOWLEDGE", saved["id"], flush=True)


if __name__ == "__main__":
    main()
