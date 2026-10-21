# cases.md 远程场景执行报告

目标：http://14.103.229.153:15173/；平台项目：PunkRecord (17796)；源码参考：5b44cbe96766ff0f56f7789271b245b5ce003518。
本轮前缀：CASE_20261019_141335；时间：2026-10-19T14:13:35.064749+08:00 至 2026-10-19T14:37:37.970117+08:00。

44个原始测试点。本轮执行 8 个细分场景：7通过、1失败。
平台原生API执行记录 55 条；这不是44个测试点全部通过，也不是代码覆盖率。

## 场景结果

| 场景 | 原编号 | 结果 | 平台记录 | 限制/错误 |
|---|---|---|---|---|
| BELI07-backfill 0工时完成不入队，补录和重复保存只生成待审核不发钱 | BELI-07 | success | 18853,18855,18857,18859,18861,18863,18865,18866,18867,18868 | 本轮验证指派任务；自建任务组合需额外执行 |
| BELI08-pending pending归零退出且不能伪造工时审核，恢复唯一待审核 | BELI-08 | success | 18869,18871,18873,18875,18876,18878,18879,18880,18881 |  |
| BELI08-rejected rejected归零退出且不能伪造工时审核，恢复唯一待审核 | BELI-08 | success | 18882,18884,18886,18888,18890,18891,18892,18893,18894,18895 |  |
| LEAVE01-03-approve 未来工作日上午半天请假批准只扣0.5天、不创建Todo | LEAVE-01,LEAVE-03 | success | 18897,18898,18900,18902,18903,18904 | 未修改调休日历，未测周末调休；未来日期避免影响现有考勤 |
| LEAVE01-reject 独立请假驳回不扣假期、不创建Todo | LEAVE-01 | success | 18905,18906,18907,18909,18910,18911 |  |
| SHOP01-publish L0建商品上下架，员工不能维护或看到下架商品 | SHOP-01 | success | 18913,18914,18916,18918,18919 | 图片上传/粘贴与认证查看尚未执行 |
| SHOP03-05-repeat 重复兑换只冻结一次，申请人重复取消不重复解冻 | SHOP-03,SHOP-05 | failed | 18920,18922,18923,18925,18926,18927,18929,18930 | record 18930: [{'type': 'status', 'actual': 403, 'passed': False, 'expected': 200}, {'type': 'json_equals', 'actual': 403, 'passed': False, 'expected': 0}, {'type': 'json_equals', 'actual': {'code': 403, 'errors': None, 'message': '仅 L0 可执行此操作'}, 'passed': False, 'expected': 'cancelled'}]; {'code': 403, 'message': '仅 L0 可执行此操作', 'errors': None} |
| DOC01-tools 远程43个MCP工具名称集合和最新工作流文档完全一致 | DOC-01 | success | 18932 |  |

## 未执行与边界

未执行原编号：TODO-01, TODO-02, TODO-03, TODO-04, TODO-05, TODO-07, TODO-06, TODO-08, BUG-01, BUG-02, BUG-03, LEAVE-02, LEAVE-04, LEAVE-05, IAM-01, IAM-02, IAM-03, BELI-01, BELI-02, BELI-03, BELI-04, BELI-05, BELI-06, BELI-09, BELI-10, ATT-01, ATT-02, ATT-03, ATT-04, ATT-05, ATT-06, ATT-07, SHOP-02, SHOP-04, SHOP-06, SHOP-07。
ATT系列会触发全员考勤结算；历史缺失字段/策略边界需隔离历史夹具；真实MySQL并发和迁移不能指向共享业务库。
真实微信消息、小程序真机、收费AI/ASR、迁移、全量本地pytest和构建未执行，不能借用仓库旧报告计为本轮通过。
已有图片、浏览器历史、完整移动端/暗色组合等缺口以逐条覆盖清单为准。

## 清理

仅处理本轮登记的前缀与ID，不扫描修改历史业务对象。
新建项目删除、普通独立待办撤销、测试员工停用、商品下架；没有删除接口的请假/订单/账本保留审计。
清理失败数：1。详见 case-suite-results.json。

## 复跑

通过环境变量提供 AUTOTEST_PASSWORD 和 PUNKRECORD_PASSWORD，执行 case_suite_runner.py run。
不要单独重跑含已清理ID的API步骤；脚本会新建夹具并重新生成对应记录。凭证不写入脚本或导出的用例。
