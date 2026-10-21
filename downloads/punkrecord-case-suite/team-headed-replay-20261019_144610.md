# 团队审核人有头慢速复现

目标：http://14.103.229.153:15173；前缀：CASE_20261019_144610

密码使用平台加密参数，不截图或录屏；不修改已有业务数据。

## 步骤

1. 输入本轮新主管用户名
2. 输入加密密码
3. 提交登录
4. 确认工作台已加载
5. 停留工作台2.5秒
6. 进入待办事项
7. 停留3秒
8. 切换团队任务
9. 确认团队任务标题
10. 等待团队任务加载4秒
11. 打开审核人下拉
12. 展开后停留10秒供查看
13. 选择当前测试主管（原失败步骤）

## 结果

执行任务19135，执行记录19136；确认模式为local_headed、headless=false，执行耗时41429毫秒。
平台记录step_count=12：前12步完成，第13步选择当前主管失败。
失败信息：`Option is missing or ambiguous; refusing to select another value`。
该结果只确认下拉无法选择本轮主管；姓名字段不一致仍属于已核对的代码线索，不把线索等同于修复验证。

场景：TODO08-team-replay；结果：failed
[{'id': 19136, 'status': 'failed', 'error': 'Option is missing or ambiguous; refusing to select another value'}]
任务：19135；模式：local_headed；headless=False；执行记录：[{'id': 19136, 'status': 'failed', 'error': 'Option is missing or ambiguous; refusing to select another value'}]

## 清理

[
  {
    "type": "project",
    "id": "965ae948-133b-4fe2-93ae-c4c47b237635",
    "status": "success",
    "action": "reopened own test tasks to reverse awards, then deleted"
  },
  {
    "type": "user",
    "id": "a6be1d21-7582-46d5-97c9-e6ecacb4b3ad",
    "status": "success",
    "action": "disabled; audit retained"
  },
  {
    "type": "user",
    "id": "23aec9cd-977d-448a-a716-22546cec2e9c",
    "status": "success",
    "action": "disabled; audit retained"
  },
  {
    "type": "user",
    "id": "8cf5d346-2a85-4ffc-ae03-a07e07e26e7c",
    "status": "success",
    "action": "disabled; audit retained"
  },
  {
    "type": "job_title",
    "id": "6e7b5c6d-5e51-465c-ae5e-c94416536349",
    "status": "success",
    "action": "audit retained (no delete endpoint)"
  }
]
