# cases.md 远程场景执行报告

目标：http://14.103.229.153:15173/；平台项目：PunkRecord (17796)；源码参考：5b44cbe96766ff0f56f7789271b245b5ce003518。
本轮前缀：CASE_20261019_140554；时间：2026-10-19T14:05:54.840146+08:00 至 2026-10-19T14:11:48.008549+08:00。

44个原始测试点。本轮执行 82 个细分场景：75通过、7失败。
平台原生API执行记录 360 条；这不是44个测试点全部通过，也不是代码覆盖率。

## 场景结果

| 场景 | 原编号 | 结果 | 平台记录 | 限制/错误 |
|---|---|---|---|---|
| IAM01-salary 工资仅管理员可读写，普通员工和非管理员L0拒绝 | IAM-01 | success | 18257,18259,18260,18261,18263 |  |
| IAM02-cross-user 员工跨账户流水及余额调整拒绝 | IAM-02 | success | 18265,18267,18269 |  |
| IAM03-legacy 旧余额调整与假期重置写接口不可绕过 | IAM-03 | success | 18271,18273 | 用户管理页面入口另行有头验证 |
| TODO01-custom-omitted custom 工时=omitted | TODO-01 | success | 18275 |  |
| TODO01-custom-0 custom 工时=0 | TODO-01 | success | 18276 |  |
| TODO01-custom-1_25 custom 工时=1.25 | TODO-01 | success | 18277 |  |
| TODO01-custom--1 custom 工时=-1 | TODO-01 | success | 18278 |  |
| TODO01-custom-None custom 工时=None | TODO-01 | success | 18279 |  |
| TODO01-custom-0_001 custom 工时=0.001 | TODO-01 | success | 18280 |  |
| TODO01-custom-NaN custom 工时=NaN | TODO-01 | success | 18281 |  |
| TODO01-custom-Infinity custom 工时=Infinity | TODO-01 | success | 18282 |  |
| TODO01-custom-date custom 缺少截止日拒绝 | TODO-01 | success | 18283 |  |
| TODO01-project-omitted project 工时=omitted | TODO-01 | success | 18284 |  |
| TODO01-project-0 project 工时=0 | TODO-01 | success | 18285 |  |
| TODO01-project-1_25 project 工时=1.25 | TODO-01 | success | 18286 |  |
| TODO01-project--1 project 工时=-1 | TODO-01 | success | 18287 |  |
| TODO01-project-None project 工时=None | TODO-01 | success | 18288 |  |
| TODO01-project-0_001 project 工时=0.001 | TODO-01 | success | 18289 |  |
| TODO01-project-NaN project 工时=NaN | TODO-01 | success | 18290 |  |
| TODO01-project-Infinity project 工时=Infinity | TODO-01 | success | 18291 |  |
| TODO01-project-date project 缺少截止日拒绝 | TODO-01 | success | 18292 |  |
| TODO01-bug-omitted bug 工时=omitted | TODO-01 | success | 18293 |  |
| TODO01-bug-0 bug 工时=0 | TODO-01 | success | 18294 |  |
| TODO01-bug-1_25 bug 工时=1.25 | TODO-01 | success | 18295 |  |
| TODO01-bug--1 bug 工时=-1 | TODO-01 | success | 18296 |  |
| TODO01-bug-None bug 工时=None | TODO-01 | success | 18297 |  |
| TODO01-bug-0_001 bug 工时=0.001 | TODO-01 | success | 18298 |  |
| TODO01-bug-NaN bug 工时=NaN | TODO-01 | success | 18299 |  |
| TODO01-bug-Infinity bug 工时=Infinity | TODO-01 | success | 18300 |  |
| TODO01-bug-date bug 缺少截止日拒绝 | TODO-01 | success | 18301 |  |
| TODO01-03-batch 批量生成默认0工时、边界与重复身份 | TODO-01,TODO-03 | success | 18303,18305,18307,18308,18309,18310,18311,18312,18313,18314 | 审核附件保留另需带真实图片的完整回归；MCP入口尚未执行 |
| TODO03-sync 重复同步不重建任务或复制Bug | TODO-01,TODO-03 | success | 18316,18318,18320,18321,18322,18323 | 未构造带已审核奖励与图片附件的同步组合 |
| TODO02-identity 项目与待办双向编辑保持同一ID和工时 | TODO-02 | success | 18324,18326,18327,18329,18331 | 图片及状态全组合尚未完整覆盖 |
| TODO05-resubmit 退回重提以最终提交时间验收 | TODO-05 | success | 18332,18334,18336,18337,18339 | 未跨真实午夜等待审核 |
| TODO05-zone UTC截止时间归一到上海18点 | TODO-05 | success | 18340 |  |
| BUG01-search Bug大小写、字面百分号/下划线和分页 | BUG-01 | success | 18341,18342,18343,18344,18347,18348,18349,18350,18351,18352 |  |
| BELI02-p0-0 工资12000、8小时、p0、延期0天 | BELI-02 | success | 18353,18354,18357,18359,18360,18362,18363 |  |
| BELI02-p0-1 工资12000、8小时、p0、延期1天 | BELI-02 | success | 18364,18365,18367,18369,18370,18372,18373 |  |
| BELI02-p0-2 工资12000、8小时、p0、延期2天 | BELI-02 | success | 18374,18375,18377,18379,18380,18382,18383 |  |
| BELI02-p0-3 工资12000、8小时、p0、延期3天 | BELI-02 | success | 18384,18385,18387,18389,18390,18392,18393 |  |
| BELI02-p0-4 工资12000、8小时、p0、延期4天 | BELI-02 | success | 18394,18395,18397,18399,18400,18402,18403 |  |
| BELI02-p0-5 工资12000、8小时、p0、延期5天 | BELI-02 | success | 18404,18405,18407,18409,18410,18412,18413 |  |
| BELI02-p0-8 工资12000、8小时、p0、延期8天 | BELI-02 | success | 18414,18415,18417,18419,18420,18422,18423 |  |
| BELI02-p1-0 工资12000、8小时、p1、延期0天 | BELI-02 | success | 18424,18425,18427,18429,18430,18432,18433 |  |
| BELI02-p1-1 工资12000、8小时、p1、延期1天 | BELI-02 | success | 18434,18435,18437,18439,18440,18442,18443 |  |
| BELI02-p1-2 工资12000、8小时、p1、延期2天 | BELI-02 | success | 18444,18445,18447,18449,18450,18452,18453 |  |
| BELI02-p1-3 工资12000、8小时、p1、延期3天 | BELI-02 | success | 18454,18455,18457,18459,18460,18462,18463 |  |
| BELI02-p1-4 工资12000、8小时、p1、延期4天 | BELI-02 | success | 18464,18465,18467,18469,18470,18472,18473 |  |
| BELI02-p1-5 工资12000、8小时、p1、延期5天 | BELI-02 | success | 18474,18475,18477,18479,18480,18482,18483 |  |
| BELI02-p1-8 工资12000、8小时、p1、延期8天 | BELI-02 | success | 18484,18485,18487,18489,18490,18492,18493 |  |
| BELI02-p2-0 工资12000、8小时、p2、延期0天 | BELI-02,BELI-01 | success | 18494,18495,18497,18499,18500,18502,18503 |  |
| BELI02-p2-1 工资12000、8小时、p2、延期1天 | BELI-02 | success | 18504,18505,18507,18509,18510,18512,18513 |  |
| BELI02-p2-2 工资12000、8小时、p2、延期2天 | BELI-02 | success | 18514,18515,18517,18519,18520,18522,18523 |  |
| BELI02-p2-3 工资12000、8小时、p2、延期3天 | BELI-02 | success | 18524,18525,18527,18529,18530,18532,18533 |  |
| BELI02-p2-4 工资12000、8小时、p2、延期4天 | BELI-02 | success | 18534,18535,18537,18539,18540,18542,18543 |  |
| BELI02-p2-5 工资12000、8小时、p2、延期5天 | BELI-02 | success | 18544,18545,18547,18549,18550,18552,18553 |  |
| BELI02-p2-8 工资12000、8小时、p2、延期8天 | BELI-02 | success | 18554,18555,18557,18559,18560,18562,18563 |  |
| BELI02-p3-0 工资12000、8小时、p3、延期0天 | BELI-02 | success | 18564,18565,18567,18569,18570,18572,18573 |  |
| BELI02-p3-1 工资12000、8小时、p3、延期1天 | BELI-02 | success | 18574,18575,18577,18579,18580,18582,18583 |  |
| BELI02-p3-2 工资12000、8小时、p3、延期2天 | BELI-02 | success | 18584,18585,18587,18589,18590,18592,18593 |  |
| BELI02-p3-3 工资12000、8小时、p3、延期3天 | BELI-02 | success | 18594,18595,18597,18599,18600,18602,18603 |  |
| BELI02-p3-4 工资12000、8小时、p3、延期4天 | BELI-02 | success | 18604,18605,18607,18609,18610,18612,18613 |  |
| BELI02-p3-5 工资12000、8小时、p3、延期5天 | BELI-02 | success | 18614,18615,18617,18619,18620,18622,18623 |  |
| BELI02-p3-8 工资12000、8小时、p3、延期8天 | BELI-02 | success | 18624,18625,18627,18629,18630,18632,18633 |  |
| BELI05-10-idempotency 重复审核只发一次、已发奖归零拒绝、重开冲销后再结算 | BELI-05,BELI-10 | success | 18634,18635,18637,18639,18641,18642,18643,18645,18647,18648,18649,18650,18651,18652 | 串行真实请求通过不代表MySQL并发锁验证通过 |
| BELI03-edits 独立审核修改工时重要级同步原任务且不泄露快照 | BELI-03 | success | 18653,18655,18657,18659,18661 | 内部结算快照旧值需要隔离数据库测试，远程只验证公开响应不泄密 |
| BELI04-guards 未验收/工资缺失/非L0不发奖，驳回奖励不改变完成态 | BELI-04 | success | 18662,18664,18666,18668,18669,18670,18671,18673 |  |
| BELI06-adjust 新员工余额调整防重、同键异参和原因校验 | BELI-06 | success | 18674,18676,18677,18678,18679,18680,18681,18682 | 假期调整防重另在商城/请假场景验证 |
| BELI07-backfill 0工时完成不入队，补录和重复保存只生成待审核不发钱 | BELI-07 | failed | 18683,18684,18686,18688,18690 | Expecting ',' delimiter: line 1 column 8001 (char 8000) |
| BELI08-pending pending归零退出且不能伪造工时审核，恢复唯一待审核 | BELI-08 | failed | 18691,18693,18695,18697,18698 | Unterminated string starting at: line 1 column 7989 (char 7988) |
| BELI08-rejected rejected归零退出且不能伪造工时审核，恢复唯一待审核 | BELI-08 | failed | 18699,18701,18703,18705,18707,18708 | Unterminated string starting at: line 1 column 7985 (char 7984) |
| LEAVE01-03-approve 未来工作日上午半天请假批准只扣0.5天、不创建Todo | LEAVE-01,LEAVE-03 | failed | 18711 | Unterminated string starting at: line 1 column 8000 (char 7999) |
| LEAVE01-reject 独立请假驳回不扣假期、不创建Todo | LEAVE-01 | failed | 18712 | Unterminated string starting at: line 1 column 8000 (char 7999) |
| SHOP01-publish L0建商品上下架，员工不能维护或看到下架商品 | SHOP-01 | success | 18715,18716,18718,18720,18721 | 图片上传/粘贴与认证查看尚未执行 |
| SHOP02-insufficient 余额不足和库存不足拒绝兑换 | SHOP-02 | success | 18723,18724 | 未验证并发最后一件行锁 |
| SHOP03-05-repeat 重复兑换只冻结一次，申请人重复取消不重复解冻 | SHOP-03,SHOP-05 | failed | 18725,18726 | record 18726: [{'type': 'json_equals', 'actual': '100.00', 'passed': False, 'expected': 100}]; {'code': 0, 'message': 'success', 'data': {'id': 'e6b77a0e-432d-4d6f-b55a-4f7ece3da8b4', 'product_id': '25332917-a43a-4b50-a032-05704740b462', 'updated_at': '2026-10-19T14:09:31', 'quantity': 1, 'status': 'pending', 'delivery': 'test', 'comment': '', 'user_id': '7f3ba884-4bc8-4fa7-a4d4-cb67e539e388', 'created_at': '2026-10-19T14:09:31', 'request_ke |
| SHOP05-reject L0 reject 重复操作不重复退款 | SHOP-05 | success | 18727,18728,18730,18731,18732 |  |
| SHOP05-approved_cancel L0 approved_cancel 重复操作不重复退款 | SHOP-05 | success | 18733,18734,18736,18737,18738,18739 |  |
| SHOP06-shipping 实物批准发货后不可普通取消退款 | SHOP-06 | success | 18740,18742,18743,18744 |  |
| SHOP04-leave 假期兑换最小0.5天，批准时扣款解冻并增假期 | SHOP-04 | success | 18745,18746,18747,18748,18750,18751 |  |
| SHOP07-balance 冻结后新员工余额下降，不得绕过余额不足完成审批 | SHOP-07 | success | 18752,18753,18754,18756,18757,18758 | 使用本轮新员工独立余额调整模拟下降；未执行会影响全员的真实早会扣款 |
| DOC01-tools 远程43个MCP工具名称集合和最新工作流文档完全一致 | DOC-01 | failed | 18761 | Unterminated string starting at: line 1 column 7920 (char 7919) |

## 未执行与边界

未执行原编号：TODO-04, TODO-07, TODO-06, TODO-08, BUG-02, BUG-03, LEAVE-02, LEAVE-04, LEAVE-05, BELI-09, ATT-01, ATT-02, ATT-03, ATT-04, ATT-05, ATT-06, ATT-07。
ATT系列会触发全员考勤结算；历史缺失字段/策略边界需隔离历史夹具；真实MySQL并发和迁移不能指向共享业务库。
真实微信消息、小程序真机、收费AI/ASR、迁移、全量本地pytest和构建未执行，不能借用仓库旧报告计为本轮通过。
已有图片、浏览器历史、完整移动端/暗色组合等缺口以逐条覆盖清单为准。

## 清理

仅处理本轮登记的前缀与ID，不扫描修改历史业务对象。
新建项目删除、普通独立待办撤销、测试员工停用、商品下架；没有删除接口的请假/订单/账本保留审计。
清理失败数：2。详见 case-suite-results.json。

## 复跑

通过环境变量提供 AUTOTEST_PASSWORD 和 PUNKRECORD_PASSWORD，执行 case_suite_runner.py run。
不要单独重跑含已清理ID的API步骤；脚本会新建夹具并重新生成对应记录。凭证不写入脚本或导出的用例。
