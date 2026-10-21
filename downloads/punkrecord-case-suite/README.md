# PunkRecord cases.md 远程测试

## 当前功能流程目录（2026-10-21）

功能流程已按业务链路归并为 9 个流程、70 个场景。空文本、长文本等输入变体只保留在 API 下，不再一测试点一流程。
当前平台 ID、归并去向、验证结果及安全限制见 `flow_reorganization/RESULT.md` 和 `flow_reorganization/plan.md`。
下文 82 个流程及旧导出脚本是历史执行资料，不是当前目录。不要运行旧脚本恢复这些已软删除的模板。
新模板、场景和共享节点保持停用，须重新准备隔离夹具、核对余额/日期/认证后再启用；本轮只整理配置，不表示业务重跑通过。

来源为 origin/main `5b44cbe` 的 `.agent/test/cases.md`，不是旧 dev 分支的通用冒烟清单。
目标固定为 `http://14.103.229.153:15173/`，代码仅用作生成脚本参考，不测试本地PunkRecord。

## 入口

- `case-final-report.md`：最终汇总与未覆盖项。
- `case-script-audit.md`：现有测试脚本静态盘点、44个原编号的补充计划。
- `case-catalog.json`：原始场景、预期、文件行号与执行追溯。
- `case-coverage-final.json`：精确用例、执行记录及清理证据。
- `case_suite_runner.py`：平台原生API用例导入、场景编排、远程执行和清理。
- `headed_case_runner.py`：平台本地Agent有头执行5个页面场景。
- `finalize_case_review.py`：按同一场景的最新复测结果汇总，保留历史失败。
- `team-view-findings.md`：团队审核人下拉缺失当前主管的复现与代码线索。
- `test-types-and-beli-values.md`：异常/边界已测范围及28组奖励金额、账户差额核对。
- `case-scenario-flows.json`：82个禁用流程模板的平台ID；当前远程平台尚无流程场景子接口。

## 运行

凭证通过环境变量 `AUTOTEST_PASSWORD`、`PUNKRECORD_PASSWORD` 传入，不在脚本和用例文件保存。
在已安装requests和tzdata的PunkRecord Python环境执行：

```powershell
python case_suite_runner.py catalog
python case_suite_runner.py run
python headed_case_runner.py
```

`PUNKRECORD_REFERENCE` 指向包含 `.agent/test/cases.md` 和最新测试源码的只读参考目录。
本目录附带 `source-reference` 时会自动使用该静态快照；也可通过环境变量显式指定。

API步骤包含本轮夹具ID，清理后不要在平台单独重放写请求；完整复跑需要脚本新建测试夹具。
用户/商品/订单/请假等没有删除接口时，停用或下架并保留审计，不直接修改数据库。
恢复中断清理可使用 `case_suite_runner.py cleanup`，只处理结果文件中登记的本轮ID。

## 固定测试账号（2026-10-19起）

不再每轮创建用户或职位。固定复用`test-account-pool.json`中的最近3个账号，`auto_create=false`。
账号不存在、身份不符或凭据缺失时直接报错，不自动补建、不自动重置密码。
本机凭据保存在`test-account-secrets.dpapi.json`，由Windows CurrentUser DPAPI加密并由.gitignore排除；其他机器通过`PUNKRECORD_TEST_PASSWORD`传入。
运行时临时启用账号，结束恢复原状态；3个账号不作为临时夹具删除。密码初始化只需进行一次。
已按用户明确确认删除其余33个重复停用账号及仅属于它们的依赖测试记录，删除前在服务器保留私有备份。
维护结果及两轮复用验证见`test-account-maintenance-report.md`。
这些账号已删除，因此旧报告中的账号“停用”是当时状态；旧执行结果不重写，不能再用旧ID重放。

## 不在共享远程造数的项目

历史任务伪造、全员早会扣款、全局日历和策略修改、迁移及MySQL隔离建库并发测试不直接执行。
真实微信通道、收费AI/ASR和小程序真机也未执行。对应原编号保留为未验证，不以源码或旧报告冒充通过。

## 贝利可见金额补测

`beli-supplement-report.md`记录51个补测场景、每项金额和账户对账。
`beli-supplement-results.json`保存原生API执行记录、MCP RPC、HTTP并发及有头任务证据。
固定员工`case_20261019_144610_employee`奖励收入5142.46，期末5142.46，冻结0。
管理员进入远程“贝利 → 贝利与假期”，选择`CASE_20261019_144610 employee`查看流水；“任务奖励”查看各任务金额。
本轮项目、任务和奖励特意保留，不执行通用清理，不要重开任务冲销或单独重放奖励写请求。
`supplement_beli.py`输出存在时拒绝重复整轮执行；`resume_beli_supplement.py`仅重试未通过的MCP/页面步骤，不重跑金额发放。
`supplement_history.py`仅按ID对白名单新测试任务构造历史缺字段形状，并通过15173接口验证；重跑复用相同任务。
`supplement-unfinished-cases.md/json`补齐29个细分用例步骤、预期、实际进展和受限原因，未执行分支不能当作通过。
