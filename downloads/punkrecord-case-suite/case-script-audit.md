# cases.md 脚本盘点与补充清单

来源：origin/main `5b44cbe96766ff0f56f7789271b245b5ce003518`；仅静态读取，不运行本地业务测试。

此前使用旧 dev 分支 a2ace19，未读取最新 .agent/test/cases.md。这是此前生成来源不完整的原因。
现有61条远程冒烟用例不能代替本清单44个回归测试点。一个测试点含多个分支，触达不等于完整覆盖。

## 已有测试脚本

| 文件 | test函数数（非参数化用例数） |
|---|---:|
| backend/tests/test_asr_service.py | 6 |
| backend/tests/test_beli_migration.py | 2 |
| backend/tests/test_beli_mysql.py | 3 |
| backend/tests/test_beli_workflow.py | 36 |
| backend/tests/test_finance_transactions.py | 3 |
| backend/tests/test_health.py | 1 |
| backend/tests/test_mcp_todo_tools.py | 8 |
| backend/tests/test_meeting_transcript_import.py | 8 |
| backend/tests/test_project_workflow.py | 5 |
| backend/tests/test_todo_ordering.py | 2 |
| backend/tests/test_wechat_inbound.py | 19 |
| backend/tests/test_wechat_notify_queue.py | 10 |

另有 scripts/test-planning-ui.cjs：浏览器请求转发隔离SQLite，不是当前远程验收证据。

## 逐条映射

| 原编号 | 已有脚本 | 需补充/远程限制 |
|---|---|---|
| TODO-01 | test_beli_workflow.py; test_mcp_todo_tools.py | 跨创建来源的真实 HTTP 参数边界 |
| TODO-02 | test_project_workflow.py | 同一任务双向编辑、真实图片与状态持久化 |
| TODO-03 | test_beli_workflow.py | 重复生成/同步后身份、审核和附件不丢失 |
| TODO-04 | test_beli_workflow.py | 历史缺失字段需隔离历史夹具，不能修改存量业务记录 |
| TODO-05 | test_beli_workflow.py | 退回重提、最终提交时间及上海自然日结算 |
| TODO-07 | test_beli_workflow.py | 缺少提交时间的历史夹具与撤回重提 |
| TODO-06 | test_todo_ordering.py | 分页大小10、展开/加载更多及跨页排序 |
| TODO-08 | scripts/test-planning-ui.cjs | 远程桌面/手机、明暗色、看板/列表/团队完整组合 |
| BUG-01 | test_beli_workflow.py; test_mcp_todo_tools.py | 真实字面量百分号/下划线、大小写和分页断言 |
| BUG-02 | scripts/test-planning-ui.cjs | 远程刷新、翻页、浏览器历史和URL一致 |
| BUG-03 | test_project_workflow.py; scripts/test-planning-ui.cjs | 独立页完整生命周期、图片、390视口 |
| LEAVE-01 | test_beli_workflow.py | 新员工独立请假批准/驳回与Todo数量不变 |
| LEAVE-02 | test_beli_workflow.py | 只允许隔离历史请假待办，远程存量不造假 |
| LEAVE-03 | test_beli_workflow.py | 真实半天和休息日；不改全局调休日历 |
| LEAVE-04 | test_wechat_inbound.py | 真实微信通道、编号和批量消息需专用绑定 |
| LEAVE-05 | test_mcp_todo_tools.py | MCP实际RPC调用而非mock转发 |
| IAM-01 | test_beli_workflow.py | 管理员、非管理员L0、普通员工三身份与敏感字段检查 |
| IAM-02 | test_beli_workflow.py | 普通员工跨账户/流水/调整拒绝 |
| IAM-03 | test_beli_workflow.py | 旧写接口拒绝和用户页面入口移除 |
| BELI-01 | test_beli_workflow.py | 真实完成后未发奖、独立审核后240 |
| BELI-02 | test_beli_workflow.py | 4重要级×7延期日的28个真实结算组合 |
| BELI-03 | test_beli_workflow.py | 审核修改计划同步、敏感字段不公开；内部快照只静态覆盖 |
| BELI-04 | test_beli_workflow.py | 工资缺失/未验收/非L0及驳回后任务仍完成 |
| BELI-05 | test_beli_workflow.py; test_beli_mysql.py | 重复审批、重开冲销、再次结算和流水唯一性 |
| BELI-06 | test_beli_workflow.py | 金额/假期防重、同键异参、原因必填 |
| BELI-07 | test_beli_workflow.py | 0工时完成后补录、重复保存不直接发奖 |
| BELI-08 | test_beli_workflow.py | pending/rejected归零退出，伪造审核拒绝，恢复唯一 |
| BELI-09 | test_beli_workflow.py | 需隔离策略和历史时间夹具，禁止改远程策略 |
| BELI-10 | test_beli_workflow.py; test_beli_mysql.py | 已发奖保护可远程测；真实锁并发需隔离MySQL |
| ATT-01 | test_beli_workflow.py | 启用日前/无记录/非工作日/L0四分支 |
| ATT-02 | test_beli_workflow.py | 不能在共享环境造早会触发全员扣款 |
| ATT-03 | test_beli_workflow.py | 同名、未匹配、未发言名单，不影响现有员工 |
| ATT-04 | test_beli_workflow.py | 上午/下午/事后补批引发全局考勤重算 |
| ATT-05 | test_beli_workflow.py | 补参会人/删早会/改日历会影响现有余额 |
| ATT-06 | test_beli_workflow.py | 后台跨日中断恢复缺少独立时钟和服务沙箱 |
| ATT-07 | test_beli_workflow.py | 历史员工快照需专属隔离数据集 |
| SHOP-01 | test_beli_workflow.py; scripts/test-planning-ui.cjs | 商品上下架、认证图片与员工可见性 |
| SHOP-02 | test_beli_mysql.py; test_beli_workflow.py | 金额/库存不足可远程；行锁并发只在隔离MySQL |
| SHOP-03 | test_beli_workflow.py | 重复申请只冻结一次，余额与库存精确断言 |
| SHOP-04 | test_beli_workflow.py | 批准扣款解冻并增假期，0.5天边界 |
| SHOP-05 | test_beli_workflow.py | 拒绝、本人取消、L0取消及重复退款保护 |
| SHOP-06 | test_beli_workflow.py | 实物发货后禁止普通退款 |
| SHOP-07 | test_beli_workflow.py | 用新员工手工扣款验证余额保护；不伪造真实早会扣款 |
| DOC-01 | test_mcp_todo_tools.py | 远程mcp-info工具名称和总数与最新文档逐项一致 |

## 安全边界

目标仅为 http://14.103.229.153:15173/。只创建、修改本轮前缀数据。
不创建早会、不修改全局日历/策略、不运行迁移、不重启服务、不发真实微信、不调用收费AI。
历史数据、全员考勤和真实行锁并发保留为未验证；不能以静态代码或旧隔离测试报告计为本轮通过。
测试员工结束后停用、商品下架；无删除接口的订单/请假/账本保留审计记录。新测试项目和非早会会议删除。

会议参会人应在说话人识别中编辑，并由实际分段同步。旧MEET-002错误定位独立输入框，应归为脚本问题。
