# 贝利补测与可见金额

目标：http://14.103.229.153:15173；项目：CASE_20261019_151947 Project。仅复用固定3账号，没有新建账号。

## 查看位置

管理员登录远程页面，进入“贝利 → 贝利与假期”，员工选择 CASE_20261019_144610 employee；任务奖励栏目可看每项任务奖励。
账号恢复原停用状态，但管理员员工列表包含停用账号，金额与流水保留。本轮测试项目及奖励不清理、不自动冲销。

本轮去重场景：51；最新通过：51；最新失败：0；下方保留重测前失败尝试。

## 账户核对

期初 0.0；任务奖励收入 5142.46；全部收入 5142.47；支出 -0.01；净增 5142.46；期末 5142.46；冻结 0.0。
读取全量 41 条流水，新流水 40 条；唯一事件键、分页无重复、流水合计和余额一致。

## 逐项金额

| 场景 | 应得 | 实得 | 发放前 | 发放后 | 执行记录 |
|---|---:|---:|---:|---:|---:|
| 贝利边界 P0 延期0天 8小时 | 288.00 | 288.00 | 0.00 | 288.00 | 19158 |
| 贝利边界 P0 延期1天 8小时 | 273.60 | 273.60 | 288.00 | 561.60 | 19170 |
| 贝利边界 P0 延期2天 8小时 | 259.20 | 259.20 | 561.60 | 820.80 | 19182 |
| 贝利边界 P0 延期3天 8小时 | 230.40 | 230.40 | 820.80 | 1051.20 | 19194 |
| 贝利边界 P0 延期4天 8小时 | 172.80 | 172.80 | 1051.20 | 1224.00 | 19206 |
| 贝利边界 P0 延期5天 8小时 | 144.00 | 144.00 | 1224.00 | 1368.00 | 19218 |
| 贝利边界 P0 延期8天 8小时 | 144.00 | 144.00 | 1368.00 | 1512.00 | 19230 |
| 贝利边界 P1 延期0天 8小时 | 240.00 | 240.00 | 1512.00 | 1752.00 | 19242 |
| 贝利边界 P1 延期1天 8小时 | 228.00 | 228.00 | 1752.00 | 1980.00 | 19254 |
| 贝利边界 P1 延期2天 8小时 | 216.00 | 216.00 | 1980.00 | 2196.00 | 19266 |
| 贝利边界 P1 延期3天 8小时 | 192.00 | 192.00 | 2196.00 | 2388.00 | 19278 |
| 贝利边界 P1 延期4天 8小时 | 144.00 | 144.00 | 2388.00 | 2532.00 | 19290 |
| 贝利边界 P1 延期5天 8小时 | 120.00 | 120.00 | 2532.00 | 2652.00 | 19302 |
| 贝利边界 P1 延期8天 8小时 | 120.00 | 120.00 | 2652.00 | 2772.00 | 19314 |
| 贝利边界 P2 延期0天 8小时 | 240.00 | 240.00 | 2772.00 | 3012.00 | 19326 |
| 贝利边界 P2 延期1天 8小时 | 228.00 | 228.00 | 3012.00 | 3240.00 | 19338 |
| 贝利边界 P2 延期2天 8小时 | 216.00 | 216.00 | 3240.00 | 3456.00 | 19350 |
| 贝利边界 P2 延期3天 8小时 | 192.00 | 192.00 | 3456.00 | 3648.00 | 19362 |
| 贝利边界 P2 延期4天 8小时 | 144.00 | 144.00 | 3648.00 | 3792.00 | 19374 |
| 贝利边界 P2 延期5天 8小时 | 120.00 | 120.00 | 3792.00 | 3912.00 | 19386 |
| 贝利边界 P2 延期8天 8小时 | 120.00 | 120.00 | 3912.00 | 4032.00 | 19398 |
| 贝利边界 P3 延期0天 8小时 | 192.00 | 192.00 | 4032.00 | 4224.00 | 19410 |
| 贝利边界 P3 延期1天 8小时 | 182.40 | 182.40 | 4224.00 | 4406.40 | 19422 |
| 贝利边界 P3 延期2天 8小时 | 172.80 | 172.80 | 4406.40 | 4579.20 | 19434 |
| 贝利边界 P3 延期3天 8小时 | 153.60 | 153.60 | 4579.20 | 4732.80 | 19446 |
| 贝利边界 P3 延期4天 8小时 | 115.20 | 115.20 | 4732.80 | 4848.00 | 19458 |
| 贝利边界 P3 延期5天 8小时 | 96.00 | 96.00 | 4848.00 | 4944.00 | 19470 |
| 贝利边界 P3 延期8天 8小时 | 96.00 | 96.00 | 4944.00 | 5040.00 | 19482 |
| 最小工时0.01 | 0.30 | 0.30 | 5040.00 | 5040.30 | 19495 |
| 两位工时1.23 | 36.90 | 36.90 | 5040.30 | 5077.20 | 19508 |
| 半分四舍五入 | 0.01 | 0.01 | 5077.20 | 5077.21 | 19521 |
| 小于半分归零 | 0.00 | 0.00 | 5077.21 | 5077.21 | 19534 |
| 带分工资 | 5.25 | 5.25 | 5077.21 | 5082.46 | 19547 |

## 新增场景

| 编号 | 场景 | 结果 |
|---|---|---|
| SUP-AMOUNT-p0-0 | 保留金额证据 P0 延期0天 | success  |
| SUP-AMOUNT-p0-1 | 保留金额证据 P0 延期1天 | success  |
| SUP-AMOUNT-p0-2 | 保留金额证据 P0 延期2天 | success  |
| SUP-AMOUNT-p0-3 | 保留金额证据 P0 延期3天 | success  |
| SUP-AMOUNT-p0-4 | 保留金额证据 P0 延期4天 | success  |
| SUP-AMOUNT-p0-5 | 保留金额证据 P0 延期5天 | success  |
| SUP-AMOUNT-p0-8 | 保留金额证据 P0 延期8天 | success  |
| SUP-AMOUNT-p1-0 | 保留金额证据 P1 延期0天 | success  |
| SUP-AMOUNT-p1-1 | 保留金额证据 P1 延期1天 | success  |
| SUP-AMOUNT-p1-2 | 保留金额证据 P1 延期2天 | success  |
| SUP-AMOUNT-p1-3 | 保留金额证据 P1 延期3天 | success  |
| SUP-AMOUNT-p1-4 | 保留金额证据 P1 延期4天 | success  |
| SUP-AMOUNT-p1-5 | 保留金额证据 P1 延期5天 | success  |
| SUP-AMOUNT-p1-8 | 保留金额证据 P1 延期8天 | success  |
| SUP-AMOUNT-p2-0 | 保留金额证据 P2 延期0天 | success  |
| SUP-AMOUNT-p2-1 | 保留金额证据 P2 延期1天 | success  |
| SUP-AMOUNT-p2-2 | 保留金额证据 P2 延期2天 | success  |
| SUP-AMOUNT-p2-3 | 保留金额证据 P2 延期3天 | success  |
| SUP-AMOUNT-p2-4 | 保留金额证据 P2 延期4天 | success  |
| SUP-AMOUNT-p2-5 | 保留金额证据 P2 延期5天 | success  |
| SUP-AMOUNT-p2-8 | 保留金额证据 P2 延期8天 | success  |
| SUP-AMOUNT-p3-0 | 保留金额证据 P3 延期0天 | success  |
| SUP-AMOUNT-p3-1 | 保留金额证据 P3 延期1天 | success  |
| SUP-AMOUNT-p3-2 | 保留金额证据 P3 延期2天 | success  |
| SUP-AMOUNT-p3-3 | 保留金额证据 P3 延期3天 | success  |
| SUP-AMOUNT-p3-4 | 保留金额证据 P3 延期4天 | success  |
| SUP-AMOUNT-p3-5 | 保留金额证据 P3 延期5天 | success  |
| SUP-AMOUNT-p3-8 | 保留金额证据 P3 延期8天 | success  |
| SUP-PRECISION-.01-12000 | 最小工时0.01 | success  |
| SUP-PRECISION-1.23-12000 | 两位工时1.23 | success  |
| SUP-PRECISION-.01-200 | 半分四舍五入 | success  |
| SUP-PRECISION-.01-199 | 小于半分归零 | success  |
| SUP-PRECISION-.17-12345.67 | 带分工资 | success  |
| SUP-SALARY-INVALID | 工资零值、负数、空值、精度、非有限和位数上界拒绝且不改原值 | success  |
| SUP-ADJUST-PRECISION | 分币调整、防重和非法精度，最终余额不变 | success  |
| SUP-LEAVE-ADJUST | 假期0.5边界、防重、异参拒绝和0.1拒绝 | success  |
| SUP-SELF-BACKFILL | 员工自建任务零工时完成后补录，只入队不发钱 | success  |
| SUP-CONCURRENT-REVIEW | 4个并发请求审核同一任务，只发放30一次 | success  |
| SUP-CONCURRENT-ZERO-0 | 归零与发奖真实HTTP竞争第1轮 | success  |
| SUP-CONCURRENT-ZERO-1 | 归零与发奖真实HTTP竞争第2轮 | success  |
| SUP-CONCURRENT-ZERO-2 | 归零与发奖真实HTTP竞争第3轮 | success  |
| SUP-CONCURRENT-STOCK | 最后一件商品并发兑换，只冻结一次且取消恢复库存 | success  |
| SUP-MCP-LEAVE | 真实MCP请假待审批、批准、驳回，不创建待办 | failed [] |
| SUP-LEDGER-RECONCILE | 全量分页流水、唯一事件键和期初期末余额核对 | success  |
| SUP-WEB-EARNINGS | 有头查看固定员工余额、奖励金额及流水分页 | running  |
| SUP-MCP-LEAVE | 真实MCP请假待审批、批准、驳回，不创建待办（解析修正重测） | success  |
| SUP-LEDGER-RECONCILE | MCP补测后全量流水与期末余额再核对 | success  |
| SUP-WEB-EARNINGS | 有头查看固定员工余额、奖励金额及流水分页 | success  |
| SUP-HISTORY-DATE | 本轮历史缺日期夹具提交拒绝，补齐后可验收 | success  |
| SUP-HISTORY-HOURS | 历史空工时不覆盖、不阻止验收、不参与奖励 | success  |
| SUP-HISTORY-SUBMIT | 历史待验收缺提交时间拒绝，撤回重提后通过 | failed Traceback (most recent call last):
  File "<string>", line 1, in <module>
  File "<test-history-fixture>", line 61, in <module>
  File "<test-history-fixture>", line 39, in main
AssertionError
 |
| SUP-HISTORY-PRE-RULE | 生效前已完成任务补录工时不追溯入队 | failed Traceback (most recent call last):
  File "<string>", line 1, in <module>
  File "<test-history-fixture>", line 61, in <module>
  File "<test-history-fixture>", line 42, in main
AssertionError
 |
| SUP-HISTORY-NO-TIME | 历史已完成缺可靠提交时间，补录不伪造时间或发奖 | failed Traceback (most recent call last):
  File "<string>", line 1, in <module>
  File "<test-history-fixture>", line 61, in <module>
  File "<test-history-fixture>", line 39, in main
AssertionError
 |
| SUP-HISTORY-LEAVE | 历史请假待办保留可读，列表隔离且六类旧写操作拒绝 | success  |
| SUP-LEDGER-RECONCILE | 历史兼容补测后全量流水与余额复核 | success  |
| SUP-HISTORY-SUBMIT | 历史待验收缺提交时间拒绝，撤回重提后通过 | success  |
| SUP-HISTORY-PRE-RULE | 生效前已完成任务补录工时不追溯入队 | success  |
| SUP-HISTORY-NO-TIME | 历史已完成缺可靠提交时间，补录不伪造时间或发奖 | success  |
| SUP-LEDGER-RECONCILE | 历史兼容补测后全量流水与余额复核 | success  |

## 历史兼容补测

仅本轮新建任务按精确ID构造历史形状；不改已有业务任务和全局策略。通过：SUP-HISTORY-DATE、SUP-HISTORY-HOURS、SUP-HISTORY-SUBMIT、SUP-HISTORY-PRE-RULE、SUP-HISTORY-NO-TIME、SUP-HISTORY-LEAVE。

## 仍待验证

BELI-09策略未初始化、缺done_at的额外组合及迁移仍未执行；已完成的历史缺字段分支见上方实际结果。
ATT-01～ATT-07、SHOP-07真实早会：考勤按全体员工重算；未创建早会或修改日历，防止影响其他账号余额。SHOP-07此前只验证手工扣减后的余额保护。
LEAVE-04：微信真实通道需专用绑定，未发真实微信。移动390/暗色完整组合、图片全生命周期、迁移、收费AI/ASR仍未完整覆盖。
团队任务审核人下拉缺当前主管的原失败保留，未修复业务代码。本轮并发是当前远程服务真实HTTP并发，不等于后台pytest/MySQL隔离测试全套通过。

## 保留和清理

仅测试项目、任务、奖励、账本与请假审计保留；商品下架，临时MCP密钥删除，固定账号恢复运行前状态。具体ID见JSON。
