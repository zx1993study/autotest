# 团队视图测试发现

## 未通过场景

- 来源：`.agent/test/cases.md` TODO-08。
- 平台有头任务19039，执行记录19040，case代码TODO08-team。
- 新建非管理员L0主管登录，进入待办事项、团队任务；审核人下拉无法选择当前主管姓名。
- 任务明确为local_headed，headless=false。使用的用户名经记录核实为本轮新建主管，不是生产员工或错误权限账号。
- 同一夹具在接口 `/todo/team?status=open&reviewed_by_user_id=<本轮主管ID>` 返回3条本轮任务，其中正工时任务1.25、零工时任务0，创建人均为本轮主管。

## 根因线索

已只读核对远程实际部署源码（Vite source map），不是仅凭旧本地代码推断：

- `frontend/src/contexts/AuthContext.jsx:33` 保存 `name: profile.display_name`。
- 同文件65行登录后保存 `{ id: user_id, name: display_name, ... }`。
- `frontend/src/pages/todo/TodoPage.jsx:232` 构造审核人选项时要求 `user?.id && user?.display_name`。
- 自定义新任务 `reviewed_by_user_id` 为空，接口以创建人作为隐含审核人；选项集合只额外收集显式reviewed_by_user_id与reviewer_name，也不会补入此主管。

因此当前主管姓名选项缺失，与认证上下文姓名字段不一致吻合。初次卡片未出现和下拉缺项都保留为失败证据；不要把API能返回任务等同于团队页面通过。

## 建议修复与回归

统一认证用户姓名字段，或在审核人选项中使用 `user.display_name || user.name`；并考虑将隐含审核人（创建人）加入选项。
补“新主管创建但未显式指定审核人”的真实登录场景，复测默认筛选、全部审核人、卡片和列表。

本轮只补测试与报告，未修改、部署业务代码。测试夹具已清理。

## 有头慢速复现

2026-10-19 14:46再次使用本轮新建非管理员L0主管复现，任务19135、执行记录19136。
已确认local_headed、headless=false；前12步完成，包括展开审核人下拉并停留10秒。
第13步选择当前主管失败，错误为`Option is missing or ambiguous; refusing to select another value`；总耗时41429毫秒。
具体步骤与清理记录见`team-headed-replay-20261019_144610.md`和同名JSON。测试项目删除，测试员工停用。
