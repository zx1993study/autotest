# PunkRecord 页面用例复测

- 测试地址：http://14.103.229.153:15173
- 执行入口：本机 autotest，专用本地 Agent，有头执行。
- 已执行 37 条：通过 35 条，失败 2 条。
- 不修改或启动本地 PunkRecord；本轮测试数据保留。

## 已处理原因

- 旧 CASE 账号已删除、历史密码无法解密，改为复用现有账号并重新加密保存用例密码。
- 旧页面定位、旧版本关联及固定任务、完成数量、余额依赖失效，已按当前页面和专用数据修正。
- 员工名称重复时改用唯一 ID；输入型 combobox 保留自由输入，不隐式选首项。
- 只读状态轮询支持短暂连接重置重试；业务写入、租约拒绝不重试。
- 必须完整执行并通过业务后置断言才记为成功；断言不允许 AI 换元素修复。

- 每条用例保留通过或失败现场截图，敏感输入遮蔽；长文本同时验证输入上限和展示框溢出。

## 最新结果

| 用例 | 功能 | 结果 | 任务 / 记录 | 截图 |
| --- | --- | --- | --- | --- |
| 55 | [AUTH-001 未登录访问待办重定向登录页](http://127.0.0.1:5173/web/features/17799) | success | 21448 / 21449 | [截图 1](D:/project/autotest/downloads/punkrecord-web-recheck-20261021/screenshots/case-55-record-21449-1.png) / [截图 2](D:/project/autotest/downloads/punkrecord-web-recheck-20261021/screenshots/case-55-record-21449-2.png) |
| 56 | [AUTH-002 正确账号登录工作台](http://127.0.0.1:5173/web/features/17803) | success | 21450 / 21451 | [截图 1](D:/project/autotest/downloads/punkrecord-web-recheck-20261021/screenshots/case-56-record-21451-1.png) |
| 57 | [AUTH-003 错误密码拒绝登录](http://127.0.0.1:5173/web/features/17805) | success | 21452 / 21453 | [截图 1](D:/project/autotest/downloads/punkrecord-web-recheck-20261021/screenshots/case-57-record-21453-1.png) |
| 58 | [AUTH-004 管理员可见企业大脑菜单](http://127.0.0.1:5173/web/features/17809) | success | 21454 / 21455 | [截图 1](D:/project/autotest/downloads/punkrecord-web-recheck-20261021/screenshots/case-58-record-21455-1.png) |
| 59 | [AUTH-005 管理员可见会议记录菜单](http://127.0.0.1:5173/web/features/17813) | success | 21456 / 21457 | [截图 1](D:/project/autotest/downloads/punkrecord-web-recheck-20261021/screenshots/case-59-record-21457-1.png) |
| 60 | [AUTH-006 退出登录返回远程根路径登录页](http://127.0.0.1:5173/web/features/17817) | success | 21458 / 21459 | [截图 1](D:/project/autotest/downloads/punkrecord-web-recheck-20261021/screenshots/case-60-record-21459-1.png) |
| 61 | [TODO-001 空标题不能创建任务](http://127.0.0.1:5173/web/features/17819) | success | 21460 / 21461 | [截图 1](D:/project/autotest/downloads/punkrecord-web-recheck-20261021/screenshots/case-61-record-21461-1.png) |
| 62 | [TODO-002 自分配任务创建并开始](http://127.0.0.1:5173/web/features/17821) | success | 21462 / 21463 | [截图 1](D:/project/autotest/downloads/punkrecord-web-recheck-20261021/screenshots/case-62-record-21463-1.png) |
| 63 | [PROJ-001 创建 B2B 项目生成 8 个阶段](http://127.0.0.1:5173/web/features/17825) | success | 21464 / 21465 | [截图 1](D:/project/autotest/downloads/punkrecord-web-recheck-20261021/screenshots/case-63-record-21465-1.png) |
| 64 | [PROJ-002 创建 B2C 项目生成 9 个阶段](http://127.0.0.1:5173/web/features/17827) | success | 21466 / 21467 | [截图 1](D:/project/autotest/downloads/punkrecord-web-recheck-20261021/screenshots/case-64-record-21467-1.png) |
| 65 | [MCP-001 生成一次性 MCP 密钥](http://127.0.0.1:5173/web/features/17831) | success | 21468 / 21469 | [截图 1](D:/project/autotest/downloads/punkrecord-web-recheck-20261021/screenshots/case-65-record-21469-1.png) |
| 66 | [MCP-002 打开 MCP 工具文档并返回](http://127.0.0.1:5173/web/features/17833) | success | 21470 / 21471 | [截图 1](D:/project/autotest/downloads/punkrecord-web-recheck-20261021/screenshots/case-66-record-21471-1.png) |
| 67 | [IAM-001 员工列表正常加载](http://127.0.0.1:5173/web/features/17837) | success | 21472 / 21473 | [截图 1](D:/project/autotest/downloads/punkrecord-web-recheck-20261021/screenshots/case-67-record-21473-1.png) |
| 68 | [CONTRACT-001 合同列表和交易方切换](http://127.0.0.1:5173/web/features/17841) | success | 21474 / 21475 | [截图 1](D:/project/autotest/downloads/punkrecord-web-recheck-20261021/screenshots/case-68-record-21475-1.png) |
| 69 | [FINANCE-001 账户和交易明细切换](http://127.0.0.1:5173/web/features/17845) | success | 21476 / 21477 | [截图 1](D:/project/autotest/downloads/punkrecord-web-recheck-20261021/screenshots/case-69-record-21477-1.png) |
| 70 | [TODO-003 长文本输入限制及保存展示（中文）](http://127.0.0.1:5173/web/features/17847) | success | 21444 / 21445 | [截图 1](D:/project/autotest/downloads/punkrecord-web-recheck-20261021/screenshots/case-70-record-21445-1.png) / [截图 2](D:/project/autotest/downloads/punkrecord-web-recheck-20261021/screenshots/case-70-record-21445-2.png) / [截图 3](D:/project/autotest/downloads/punkrecord-web-recheck-20261021/screenshots/case-70-record-21445-3.png) / [截图 4](D:/project/autotest/downloads/punkrecord-web-recheck-20261021/screenshots/case-70-record-21445-4.png) |
| 71 | [KB-001 企业大脑页面可访问](http://127.0.0.1:5173/web/features/17849) | success | 21478 / 21479 | [截图 1](D:/project/autotest/downloads/punkrecord-web-recheck-20261021/screenshots/case-71-record-21479-1.png) |
| 72 | [MEET-001 会议列表可访问](http://127.0.0.1:5173/web/features/17851) | success | 21480 / 21481 | [截图 1](D:/project/autotest/downloads/punkrecord-web-recheck-20261021/screenshots/case-72-record-21481-1.png) |
| 73 | [MEET-002 无音频创建会议并保存参会人员](http://127.0.0.1:5173/web/features/17853) | success | 21482 / 21483 | [截图 1](D:/project/autotest/downloads/punkrecord-web-recheck-20261021/screenshots/case-73-record-21483-1.png) |
| 84 | [CASE TODO08-my-edit 我的任务看板/列表与工时归零恢复标识](http://127.0.0.1:5173/web/features/18990) | success | 21484 / 21485 | [截图 1](D:/project/autotest/downloads/punkrecord-web-recheck-20261021/screenshots/case-84-record-21485-1.png) |
| 85 | [CASE TODO08-my-edit 我的任务看板/列表与工时归零恢复标识](http://127.0.0.1:5173/web/features/18999) | success | 21486 / 21487 | [截图 1](D:/project/autotest/downloads/punkrecord-web-recheck-20261021/screenshots/case-85-record-21487-1.png) |
| 86 | [CASE TODO08-team 团队任务看板和列表的贝利/普通样式分类](http://127.0.0.1:5173/web/features/19003) | success | 21488 / 21489 | [截图 1](D:/project/autotest/downloads/punkrecord-web-recheck-20261021/screenshots/case-86-record-21489-1.png) |
| 87 | [CASE TODO06-pagination 完成任务默认10条，加载更多到12条](http://127.0.0.1:5173/web/features/19007) | success | 21490 / 21491 | [截图 1](D:/project/autotest/downloads/punkrecord-web-recheck-20261021/screenshots/case-87-record-21491-1.png) |
| 88 | [CASE BUG02-filter-refresh 独立Bug页面标题搜索、状态筛选和刷新保持](http://127.0.0.1:5173/web/features/19011) | success | 21492 / 21493 | [截图 1](D:/project/autotest/downloads/punkrecord-web-recheck-20261021/screenshots/case-88-record-21493-1.png) |
| 89 | [CASE MEET02-speaker-corrected 说话人识别编辑姓名并自动同步参会人员](http://127.0.0.1:5173/web/features/19015) | success | 21494 / 21495 | [截图 1](D:/project/autotest/downloads/punkrecord-web-recheck-20261021/screenshots/case-89-record-21495-1.png) |
| 90 | [CASE TODO08-team 团队任务看板和列表的贝利/普通样式分类](http://127.0.0.1:5173/web/features/19024) | success | 21496 / 21497 | [截图 1](D:/project/autotest/downloads/punkrecord-web-recheck-20261021/screenshots/case-90-record-21497-1.png) |
| 91 | [CASE TODO06-pagination 完成任务默认10条，加载更多到12条](http://127.0.0.1:5173/web/features/19028) | success | 21498 / 21499 | [截图 1](D:/project/autotest/downloads/punkrecord-web-recheck-20261021/screenshots/case-91-record-21499-1.png) |
| 92 | [CASE TODO08-team 团队任务看板和列表的贝利/普通样式分类](http://127.0.0.1:5173/web/features/19037) | success | 21500 / 21501 | [截图 1](D:/project/autotest/downloads/punkrecord-web-recheck-20261021/screenshots/case-92-record-21501-1.png) |
| 93 | [CASE TODO08-team-replay 团队审核人下拉缺项有头慢速复现](http://127.0.0.1:5173/web/features/19133) | failed | 21502 / 21503 | [截图 1](D:/project/autotest/downloads/punkrecord-web-recheck-20261021/screenshots/case-93-record-21503-1.png) |
| 94 | [CASE SUP-WEB-EARNINGS 有头查看固定员工余额、奖励金额及流水分页](http://127.0.0.1:5173/web/features/19665) | success | 21504 / 21505 | [截图 1](D:/project/autotest/downloads/punkrecord-web-recheck-20261021/screenshots/case-94-record-21505-1.png) |
| 95 | [CASE BELI-PERM-EMPLOYEE-PAGE 非L0仅看本人奖励，无审核和工作日历入口](http://127.0.0.1:5173/web/features/20057) | success | 21506 / 21507 | [截图 1](D:/project/autotest/downloads/punkrecord-web-recheck-20261021/screenshots/case-95-record-21507-1.png) |
| 96 | [CASE BELI-PERM-L0-PAGE 固定L0账号能看到待审核奖励入口但不提交](http://127.0.0.1:5173/web/features/20061) | success | 21508 / 21509 | [截图 1](D:/project/autotest/downloads/punkrecord-web-recheck-20261021/screenshots/case-96-record-21509-1.png) |
| 97 | [CASE BELI-PERM-SUPERVISOR-PAGE test_user2非L0仅看本人奖励，无审核和工作日历入口](http://127.0.0.1:5173/web/features/20162) | success | 21510 / 21511 | [截图 1](D:/project/autotest/downloads/punkrecord-web-recheck-20261021/screenshots/case-97-record-21511-1.png) |
| 98 | [CASE BELI-PERM-EMPLOYEE-PAGE test_user3非L0仅看本人奖励，无审核和工作日历入口](http://127.0.0.1:5173/web/features/20170) | success | 21512 / 21513 | [截图 1](D:/project/autotest/downloads/punkrecord-web-recheck-20261021/screenshots/case-98-record-21513-1.png) |
| 99 | [CASE BELI-PERM-OTHER-PAGE test_requset_leave非L0仅看本人奖励，无审核和工作日历入口](http://127.0.0.1:5173/web/features/20178) | success | 21514 / 21515 | [截图 1](D:/project/autotest/downloads/punkrecord-web-recheck-20261021/screenshots/case-99-record-21515-1.png) |
| 100 | [CASE BELI-PERM-L0-PAGE 固定L0账号能看到待审核奖励入口但不提交](http://127.0.0.1:5173/web/features/20186) | success | 21516 / 21517 | [截图 1](D:/project/autotest/downloads/punkrecord-web-recheck-20261021/screenshots/case-100-record-21517-1.png) |
| 101 | [TODO-003 长文本输入限制及保存展示（连续英文）](http://127.0.0.1:5173/web/features/17847) | failed | 21446 / 21447 | [截图 1](D:/project/autotest/downloads/punkrecord-web-recheck-20261021/screenshots/case-101-record-21447-1.png) / [截图 2](D:/project/autotest/downloads/punkrecord-web-recheck-20261021/screenshots/case-101-record-21447-2.png) / [截图 3](D:/project/autotest/downloads/punkrecord-web-recheck-20261021/screenshots/case-101-record-21447-3.png) |

## 未通过明细

### 用例 93：CASE TODO08-team-replay 团队审核人下拉缺项有头慢速复现

[平台功能详情](http://127.0.0.1:5173/web/features/19133)

```text
Option ['test_user2'] is missing; refusing to select another value
```

![失败现场](D:/project/autotest/downloads/punkrecord-web-recheck-20261021/screenshots/case-93-record-21503-1.png)

### 用例 101：TODO-003 长文本输入限制及保存展示（连续英文）

[平台功能详情](http://127.0.0.1:5173/web/features/17847)

```text
Assertion within_container: expected 'contained'; actual: {'clientWidth': 676, 'scrollWidth': 112598, 'clientHeight': 67, 'scrollHeight': 67, 'overflowX': 'visible', 'overflowY': 'visible', 'contained': False}
```

```json
[
  {
    "name": ".detail-section:has(h4:text-is(\"描述\")) .detail-description",
    "step": 19,
    "actual": {
      "contained": false,
      "overflowX": "visible",
      "overflowY": "visible",
      "clientWidth": 676,
      "scrollWidth": 112598,
      "clientHeight": 67,
      "scrollHeight": 67
    },
    "passed": false,
    "locator": ".detail-section:has(h4:text-is(\"描述\")) .detail-description",
    "expected": "contained"
  }
]
```

![失败现场](D:/project/autotest/downloads/punkrecord-web-recheck-20261021/screenshots/case-101-record-21447-1.png)

![失败现场](D:/project/autotest/downloads/punkrecord-web-recheck-20261021/screenshots/case-101-record-21447-2.png)

![失败现场](D:/project/autotest/downloads/punkrecord-web-recheck-20261021/screenshots/case-101-record-21447-3.png)

## 长文本通过示例

- 中文描述输入 10001 字后实际保留 10000 字；备注输入 2001 字后实际保留 2000 字。
- 保存并重新展示的内容与预期一致，描述和备注均未超出展示框。

![中文长文本通过现场](D:/project/autotest/downloads/punkrecord-web-recheck-20261021/screenshots/case-70-record-21445-1.png)

![中文长文本通过现场](D:/project/autotest/downloads/punkrecord-web-recheck-20261021/screenshots/case-70-record-21445-2.png)

![中文长文本通过现场](D:/project/autotest/downloads/punkrecord-web-recheck-20261021/screenshots/case-70-record-21445-3.png)

![中文长文本通过现场](D:/project/autotest/downloads/punkrecord-web-recheck-20261021/screenshots/case-70-record-21445-4.png)

## 登录态复用检查

- 当前 PunkRecord 的五条项目鉴权均为 API Bearer，不是 Web 浏览器会话。
- 本轮业务脚本内含登录步骤，每条用例独立上下文，因此重复登录；本轮尚未改为登录态复用。
- PunkRecord 页面依赖 localStorage 中的 token、user。运行时支持恢复 storage_state，但现有登录态保存流程要求非空 Cookie，不能直接保存仅 localStorage 的会话。
- 普通业务用例应按账号复用 Cookie + localStorage，失效后再刷新；未登录、登录、错误密码和退出登录用例仍需独立验证。
