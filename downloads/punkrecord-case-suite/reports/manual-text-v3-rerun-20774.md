# PunkRecord 手动文本三类复测报告（V3）

执行平台：[本机 autotest](http://127.0.0.1:5173/)
被测系统：[远程 PunkRecord](http://14.103.229.153:15173/)
项目：17796；报告知识：20774。
开始：2026-10-20T12:18:03.232272+08:00；结束：2026-10-20T12:22:44.057463+08:00。

## 结论

- 最终有效用例78条：29通过、49失败、0未核实。失败用例数不等于独立Bug数。
- 纯空格26条：3通过、23失败。23条返回HTTP200/code0，空格文本被保存。
- 首尾空格26条：全部失败。HTTP200成功，但至少一个手动文本字段未清除首尾空格。
- 中间空格26条：全部通过，保存后回查验证内部空格保留。
- 贝利规则名称、项目任务计划标题已做trim及空格拦截；但同请求中的规则说明note、任务描述description未做首尾trim。
- 自动编号、只读/隐藏/关联字段及UUID、日期、金额、枚举等特殊类型均不参与三类变更。
- 本次只测这组三类文本规则，不代表整个项目所有业务分支均已回归。
- 原测试项目/任务已不存在，本轮补3个正常前置对象及1个项目成员关系。未新建用户。
- 任务计划首轮3次403因测试员工未加入新项目，已排除为前置无效；补齐成员后仅复测这3条。81次测试请求中78条为最终有效结果，3条原始记录保留。
- 业务测试数据保留；未修改或启动本地PunkRecord；员工资料和测试账号贝利余额核对未变。
- 本机、远程平台均可查询81条本轮普通执行记录（78最终有效+3前置无效）。

## 输入与断言规则

|场景|同一请求中所有手动普通文本输入|预期断言|
|---|---|---|
|纯空格|三个ASCII空格，JSON为"   "，不是空字符串|HTTP属于[400,422]，不得保存|
|首尾空格|"  有效文本  "|HTTP200；每字段等于输入.strip()；保存后回查一致|
|中间空格|"有效文本 A B"|HTTP200；每字段等于原输入；保存后回查一致|

## 功能异常汇总

|功能|本轮字段|纯空格返回|首尾空格未清理字段|中间空格|
|---|---|---|---|---|
|职位 新增|name, description|HTTP200，错误保存|description, name|通过|
|职位 编辑|name, description|HTTP200，错误保存|description, name|通过|
|部门 新增|name, description|HTTP200，错误保存|description, name|通过|
|部门 编辑|name, description|HTTP200，错误保存|description, name|通过|
|停用贝利规则 新增|name, note|HTTP400，正确拦截|note|通过|
|停用贝利规则 编辑|name, note|HTTP400，正确拦截|note|通过|
|交易方 新增|name, address, bank_name|HTTP200，错误保存|address, bank_name, name|通过|
|交易方 编辑|name, address, bank_name|HTTP200，错误保存|address, bank_name, name|通过|
|任务 新增|title, description, notes|HTTP200，错误保存|description, notes, title|通过|
|任务 编辑|title, description, notes|HTTP200，错误保存|description, notes, title|通过|
|项目 新增|name, description|HTTP200，错误保存|description, name|通过|
|项目 编辑|name, description|HTTP200，错误保存|description, name|通过|
|下架商品 新增|name, description|HTTP200，错误保存|description, name|通过|
|下架商品 编辑|name, description|HTTP200，错误保存|description, name|通过|
|更新日志 新增|version, title, content|HTTP200，错误保存|content, title, version|通过|
|更新日志 编辑|version, title, content|HTTP200，错误保存|content, title, version|通过|
|非业务会议 新增|title|HTTP200，错误保存|title|通过|
|独立财务账户 新增|account_name, bank_name, bank_branch|HTTP200，错误保存|account_name, bank_branch, bank_name|通过|
|独立财务账户 编辑|account_name, bank_name, bank_branch|HTTP200，错误保存|account_name, bank_branch, bank_name|通过|
|未对账测试交易 新增|purpose|HTTP200，错误保存|purpose|通过|
|未对账测试交易 编辑|purpose|HTTP200，错误保存|purpose|通过|
|草稿合同 新增|name|HTTP200，错误保存|name|通过|
|草稿合同 编辑|name|HTTP200，错误保存|name|通过|
|待批请假（有效额度重测） 新增|reason|HTTP200，错误保存|reason|通过|
|项目阶段 编辑|deliverables|HTTP200，错误保存|deliverables|通过|
|项目任务计划 编辑|title, description|HTTP400，正确拦截|description|通过|

## 逐用例实际输入、返回和断言

以下均为本轮实际值，不是脚本模板。完整请求参数含保持正常的编号、ID、日期和金额；鉴权头已脱敏。返回不省略字段。

### 职位 新增 / 纯空格（用例4244，执行记录20775）
结果：failed；Bug类别：whitespace_only_saved
请求：POST http://14.103.229.153:15173/api/v1/iam/job-titles
手动字段：name, description

实际输入参数：
```json
{
  "body": {
    "name": "   ",
    "description": "   "
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "92ac2640-fb78-4c48-a14d-9329984a2056",
    "name": "   ",
    "created_at": "2026-10-20T12:18:05",
    "description": "   "
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status_in",
    "expected": [
      400,
      422
    ],
    "actual": 200,
    "passed": false
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "unexpectedly_saved",
  "missing": [],
  "expected": {
    "name": "   ",
    "description": "   "
  },
  "observed": {
    "name": "   ",
    "description": "   "
  },
  "mismatches": {},
  "read_route": "/iam/job-titles",
  "expected_action": "reject_whitespace_without_saving"
}
```

### 职位 新增 / 首尾空格（用例4245，执行记录20776）
结果：failed；Bug类别：leading_trailing_spaces_not_fully_removed
请求：POST http://14.103.229.153:15173/api/v1/iam/job-titles
手动字段：name, description

实际输入参数：
```json
{
  "body": {
    "name": "  STR3_1792469885497_600443  ",
    "description": "  STR3_1792469885497_600443  "
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "ace950f3-ba44-4579-8ac8-fa74cd8714f3",
    "name": "  STR3_1792469885497_600443  ",
    "created_at": "2026-10-20T12:18:06",
    "description": "  STR3_1792469885497_600443  "
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status",
    "expected": 200,
    "actual": 200,
    "passed": true
  },
  {
    "path": "data.name",
    "type": "json_equals",
    "expected": "STR3_1792469885497_600443",
    "actual": "  STR3_1792469885497_600443  ",
    "passed": false
  },
  {
    "path": "data.description",
    "type": "json_equals",
    "expected": "STR3_1792469885497_600443",
    "actual": "  STR3_1792469885497_600443  ",
    "passed": false
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "failed",
  "missing": [],
  "expected": {
    "name": "STR3_1792469885497_600443",
    "description": "STR3_1792469885497_600443"
  },
  "observed": {
    "name": "  STR3_1792469885497_600443  ",
    "description": "  STR3_1792469885497_600443  "
  },
  "mismatches": {
    "name": {
      "actual": "  STR3_1792469885497_600443  ",
      "expected": "STR3_1792469885497_600443"
    },
    "description": {
      "actual": "  STR3_1792469885497_600443  ",
      "expected": "STR3_1792469885497_600443"
    }
  },
  "read_route": "/iam/job-titles"
}
```
回查字段断言：
```json
[
  {
    "type": "stored_field_equals",
    "path": "name",
    "expected": "STR3_1792469885497_600443",
    "actual": "  STR3_1792469885497_600443  ",
    "passed": false
  },
  {
    "type": "stored_field_equals",
    "path": "description",
    "expected": "STR3_1792469885497_600443",
    "actual": "  STR3_1792469885497_600443  ",
    "passed": false
  }
]
```

### 职位 新增 / 中间空格（用例4246，执行记录20777）
结果：passed；Bug类别：None
请求：POST http://14.103.229.153:15173/api/v1/iam/job-titles
手动字段：name, description

实际输入参数：
```json
{
  "body": {
    "name": "STR3_1792469887247_666047 A B",
    "description": "STR3_1792469887247_666047 A B"
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "c253f5ca-86ef-4ab4-9804-935e4855fb78",
    "name": "STR3_1792469887247_666047 A B",
    "created_at": "2026-10-20T12:18:08",
    "description": "STR3_1792469887247_666047 A B"
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status",
    "expected": 200,
    "actual": 200,
    "passed": true
  },
  {
    "path": "data.name",
    "type": "json_equals",
    "expected": "STR3_1792469887247_666047 A B",
    "actual": "STR3_1792469887247_666047 A B",
    "passed": true
  },
  {
    "path": "data.description",
    "type": "json_equals",
    "expected": "STR3_1792469887247_666047 A B",
    "actual": "STR3_1792469887247_666047 A B",
    "passed": true
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "passed",
  "missing": [],
  "expected": {
    "name": "STR3_1792469887247_666047 A B",
    "description": "STR3_1792469887247_666047 A B"
  },
  "observed": {
    "name": "STR3_1792469887247_666047 A B",
    "description": "STR3_1792469887247_666047 A B"
  },
  "mismatches": {},
  "read_route": "/iam/job-titles"
}
```
回查字段断言：
```json
[
  {
    "type": "stored_field_equals",
    "path": "name",
    "expected": "STR3_1792469887247_666047 A B",
    "actual": "STR3_1792469887247_666047 A B",
    "passed": true
  },
  {
    "type": "stored_field_equals",
    "path": "description",
    "expected": "STR3_1792469887247_666047 A B",
    "actual": "STR3_1792469887247_666047 A B",
    "passed": true
  }
]
```

### 职位 编辑 / 纯空格（用例4247，执行记录20778）
结果：failed；Bug类别：whitespace_only_saved
请求：PATCH http://14.103.229.153:15173/api/v1/iam/job-titles/997aeddf-7f3a-4013-80c4-1897f48f2742
手动字段：name, description

实际输入参数：
```json
{
  "body": {
    "name": "   ",
    "description": "   "
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "997aeddf-7f3a-4013-80c4-1897f48f2742",
    "name": "   ",
    "created_at": "2026-10-20T10:27:42",
    "description": "   "
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status_in",
    "expected": [
      400,
      422
    ],
    "actual": 200,
    "passed": false
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "unexpectedly_saved",
  "missing": [],
  "expected": {
    "name": "   ",
    "description": "   "
  },
  "observed": {
    "name": "   ",
    "description": "   "
  },
  "mismatches": {},
  "read_route": "/iam/job-titles",
  "expected_action": "reject_whitespace_without_saving"
}
```

### 职位 编辑 / 首尾空格（用例4248，执行记录20779）
结果：failed；Bug类别：leading_trailing_spaces_not_fully_removed
请求：PATCH http://14.103.229.153:15173/api/v1/iam/job-titles/997aeddf-7f3a-4013-80c4-1897f48f2742
手动字段：name, description

实际输入参数：
```json
{
  "body": {
    "name": "  STR3_1792469890276_552783  ",
    "description": "  STR3_1792469890276_552783  "
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "997aeddf-7f3a-4013-80c4-1897f48f2742",
    "name": "  STR3_1792469890276_552783  ",
    "created_at": "2026-10-20T10:27:42",
    "description": "  STR3_1792469890276_552783  "
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status",
    "expected": 200,
    "actual": 200,
    "passed": true
  },
  {
    "path": "data.name",
    "type": "json_equals",
    "expected": "STR3_1792469890276_552783",
    "actual": "  STR3_1792469890276_552783  ",
    "passed": false
  },
  {
    "path": "data.description",
    "type": "json_equals",
    "expected": "STR3_1792469890276_552783",
    "actual": "  STR3_1792469890276_552783  ",
    "passed": false
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "failed",
  "missing": [],
  "expected": {
    "name": "STR3_1792469890276_552783",
    "description": "STR3_1792469890276_552783"
  },
  "observed": {
    "name": "  STR3_1792469890276_552783  ",
    "description": "  STR3_1792469890276_552783  "
  },
  "mismatches": {
    "name": {
      "actual": "  STR3_1792469890276_552783  ",
      "expected": "STR3_1792469890276_552783"
    },
    "description": {
      "actual": "  STR3_1792469890276_552783  ",
      "expected": "STR3_1792469890276_552783"
    }
  },
  "read_route": "/iam/job-titles"
}
```
回查字段断言：
```json
[
  {
    "type": "stored_field_equals",
    "path": "name",
    "expected": "STR3_1792469890276_552783",
    "actual": "  STR3_1792469890276_552783  ",
    "passed": false
  },
  {
    "type": "stored_field_equals",
    "path": "description",
    "expected": "STR3_1792469890276_552783",
    "actual": "  STR3_1792469890276_552783  ",
    "passed": false
  }
]
```

### 职位 编辑 / 中间空格（用例4249，执行记录20780）
结果：passed；Bug类别：None
请求：PATCH http://14.103.229.153:15173/api/v1/iam/job-titles/997aeddf-7f3a-4013-80c4-1897f48f2742
手动字段：name, description

实际输入参数：
```json
{
  "body": {
    "name": "STR3_1792469891785_246260 A B",
    "description": "STR3_1792469891785_246260 A B"
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "997aeddf-7f3a-4013-80c4-1897f48f2742",
    "name": "STR3_1792469891785_246260 A B",
    "created_at": "2026-10-20T10:27:42",
    "description": "STR3_1792469891785_246260 A B"
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status",
    "expected": 200,
    "actual": 200,
    "passed": true
  },
  {
    "path": "data.name",
    "type": "json_equals",
    "expected": "STR3_1792469891785_246260 A B",
    "actual": "STR3_1792469891785_246260 A B",
    "passed": true
  },
  {
    "path": "data.description",
    "type": "json_equals",
    "expected": "STR3_1792469891785_246260 A B",
    "actual": "STR3_1792469891785_246260 A B",
    "passed": true
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "passed",
  "missing": [],
  "expected": {
    "name": "STR3_1792469891785_246260 A B",
    "description": "STR3_1792469891785_246260 A B"
  },
  "observed": {
    "name": "STR3_1792469891785_246260 A B",
    "description": "STR3_1792469891785_246260 A B"
  },
  "mismatches": {},
  "read_route": "/iam/job-titles"
}
```
回查字段断言：
```json
[
  {
    "type": "stored_field_equals",
    "path": "name",
    "expected": "STR3_1792469891785_246260 A B",
    "actual": "STR3_1792469891785_246260 A B",
    "passed": true
  },
  {
    "type": "stored_field_equals",
    "path": "description",
    "expected": "STR3_1792469891785_246260 A B",
    "actual": "STR3_1792469891785_246260 A B",
    "passed": true
  }
]
```

### 部门 新增 / 纯空格（用例4250，执行记录20781）
结果：failed；Bug类别：whitespace_only_saved
请求：POST http://14.103.229.153:15173/api/v1/iam/departments
手动字段：name, description

实际输入参数：
```json
{
  "body": {
    "name": "   ",
    "description": "   "
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "e713804c-4780-4e72-8a1c-aa6be5e2ccca",
    "name": "   ",
    "children": [],
    "created_at": "2026-10-20T12:18:15",
    "description": "   ",
    "member_count": 0,
    "parent_org_unit_id": null
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status_in",
    "expected": [
      400,
      422
    ],
    "actual": 200,
    "passed": false
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "unexpectedly_saved",
  "missing": [],
  "expected": {
    "name": "   ",
    "description": "   "
  },
  "observed": {
    "name": "   ",
    "description": "   "
  },
  "mismatches": {},
  "read_route": "/iam/departments",
  "expected_action": "reject_whitespace_without_saving"
}
```

### 部门 新增 / 首尾空格（用例4251，执行记录20782）
结果：failed；Bug类别：leading_trailing_spaces_not_fully_removed
请求：POST http://14.103.229.153:15173/api/v1/iam/departments
手动字段：name, description

实际输入参数：
```json
{
  "body": {
    "name": "  STR3_1792469895506_451007  ",
    "description": "  STR3_1792469895506_451007  "
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "a95505c4-85a8-4f40-941e-75945ac15251",
    "name": "  STR3_1792469895506_451007  ",
    "children": [],
    "created_at": "2026-10-20T12:18:16",
    "description": "  STR3_1792469895506_451007  ",
    "member_count": 0,
    "parent_org_unit_id": null
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status",
    "expected": 200,
    "actual": 200,
    "passed": true
  },
  {
    "path": "data.name",
    "type": "json_equals",
    "expected": "STR3_1792469895506_451007",
    "actual": "  STR3_1792469895506_451007  ",
    "passed": false
  },
  {
    "path": "data.description",
    "type": "json_equals",
    "expected": "STR3_1792469895506_451007",
    "actual": "  STR3_1792469895506_451007  ",
    "passed": false
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "failed",
  "missing": [],
  "expected": {
    "name": "STR3_1792469895506_451007",
    "description": "STR3_1792469895506_451007"
  },
  "observed": {
    "name": "  STR3_1792469895506_451007  ",
    "description": "  STR3_1792469895506_451007  "
  },
  "mismatches": {
    "name": {
      "actual": "  STR3_1792469895506_451007  ",
      "expected": "STR3_1792469895506_451007"
    },
    "description": {
      "actual": "  STR3_1792469895506_451007  ",
      "expected": "STR3_1792469895506_451007"
    }
  },
  "read_route": "/iam/departments"
}
```
回查字段断言：
```json
[
  {
    "type": "stored_field_equals",
    "path": "name",
    "expected": "STR3_1792469895506_451007",
    "actual": "  STR3_1792469895506_451007  ",
    "passed": false
  },
  {
    "type": "stored_field_equals",
    "path": "description",
    "expected": "STR3_1792469895506_451007",
    "actual": "  STR3_1792469895506_451007  ",
    "passed": false
  }
]
```

### 部门 新增 / 中间空格（用例4252，执行记录20783）
结果：passed；Bug类别：None
请求：POST http://14.103.229.153:15173/api/v1/iam/departments
手动字段：name, description

实际输入参数：
```json
{
  "body": {
    "name": "STR3_1792469897560_956199 A B",
    "description": "STR3_1792469897560_956199 A B"
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "64dc4029-685c-45cf-8135-f2b4e39cab7d",
    "name": "STR3_1792469897560_956199 A B",
    "children": [],
    "created_at": "2026-10-20T12:18:18",
    "description": "STR3_1792469897560_956199 A B",
    "member_count": 0,
    "parent_org_unit_id": null
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status",
    "expected": 200,
    "actual": 200,
    "passed": true
  },
  {
    "path": "data.name",
    "type": "json_equals",
    "expected": "STR3_1792469897560_956199 A B",
    "actual": "STR3_1792469897560_956199 A B",
    "passed": true
  },
  {
    "path": "data.description",
    "type": "json_equals",
    "expected": "STR3_1792469897560_956199 A B",
    "actual": "STR3_1792469897560_956199 A B",
    "passed": true
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "passed",
  "missing": [],
  "expected": {
    "name": "STR3_1792469897560_956199 A B",
    "description": "STR3_1792469897560_956199 A B"
  },
  "observed": {
    "name": "STR3_1792469897560_956199 A B",
    "description": "STR3_1792469897560_956199 A B"
  },
  "mismatches": {},
  "read_route": "/iam/departments"
}
```
回查字段断言：
```json
[
  {
    "type": "stored_field_equals",
    "path": "name",
    "expected": "STR3_1792469897560_956199 A B",
    "actual": "STR3_1792469897560_956199 A B",
    "passed": true
  },
  {
    "type": "stored_field_equals",
    "path": "description",
    "expected": "STR3_1792469897560_956199 A B",
    "actual": "STR3_1792469897560_956199 A B",
    "passed": true
  }
]
```

### 部门 编辑 / 纯空格（用例4253，执行记录20784）
结果：failed；Bug类别：whitespace_only_saved
请求：PATCH http://14.103.229.153:15173/api/v1/iam/departments/e705f892-c5c9-42ca-a8fb-22198e1bcda9
手动字段：name, description

实际输入参数：
```json
{
  "body": {
    "name": "   ",
    "description": "   "
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "e705f892-c5c9-42ca-a8fb-22198e1bcda9",
    "name": "   ",
    "children": [],
    "created_at": "2026-10-20T10:28:13",
    "description": "   ",
    "member_count": 0,
    "parent_org_unit_id": null
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status_in",
    "expected": [
      400,
      422
    ],
    "actual": 200,
    "passed": false
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "unexpectedly_saved",
  "missing": [],
  "expected": {
    "name": "   ",
    "description": "   "
  },
  "observed": {
    "name": "   ",
    "description": "   "
  },
  "mismatches": {},
  "read_route": "/iam/departments",
  "expected_action": "reject_whitespace_without_saving"
}
```

### 部门 编辑 / 首尾空格（用例4254，执行记录20785）
结果：failed；Bug类别：leading_trailing_spaces_not_fully_removed
请求：PATCH http://14.103.229.153:15173/api/v1/iam/departments/e705f892-c5c9-42ca-a8fb-22198e1bcda9
手动字段：name, description

实际输入参数：
```json
{
  "body": {
    "name": "  STR3_1792469901893_546822  ",
    "description": "  STR3_1792469901893_546822  "
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "e705f892-c5c9-42ca-a8fb-22198e1bcda9",
    "name": "  STR3_1792469901893_546822  ",
    "children": [],
    "created_at": "2026-10-20T10:28:13",
    "description": "  STR3_1792469901893_546822  ",
    "member_count": 0,
    "parent_org_unit_id": null
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status",
    "expected": 200,
    "actual": 200,
    "passed": true
  },
  {
    "path": "data.name",
    "type": "json_equals",
    "expected": "STR3_1792469901893_546822",
    "actual": "  STR3_1792469901893_546822  ",
    "passed": false
  },
  {
    "path": "data.description",
    "type": "json_equals",
    "expected": "STR3_1792469901893_546822",
    "actual": "  STR3_1792469901893_546822  ",
    "passed": false
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "failed",
  "missing": [],
  "expected": {
    "name": "STR3_1792469901893_546822",
    "description": "STR3_1792469901893_546822"
  },
  "observed": {
    "name": "  STR3_1792469901893_546822  ",
    "description": "  STR3_1792469901893_546822  "
  },
  "mismatches": {
    "name": {
      "actual": "  STR3_1792469901893_546822  ",
      "expected": "STR3_1792469901893_546822"
    },
    "description": {
      "actual": "  STR3_1792469901893_546822  ",
      "expected": "STR3_1792469901893_546822"
    }
  },
  "read_route": "/iam/departments"
}
```
回查字段断言：
```json
[
  {
    "type": "stored_field_equals",
    "path": "name",
    "expected": "STR3_1792469901893_546822",
    "actual": "  STR3_1792469901893_546822  ",
    "passed": false
  },
  {
    "type": "stored_field_equals",
    "path": "description",
    "expected": "STR3_1792469901893_546822",
    "actual": "  STR3_1792469901893_546822  ",
    "passed": false
  }
]
```

### 部门 编辑 / 中间空格（用例4255，执行记录20786）
结果：passed；Bug类别：None
请求：PATCH http://14.103.229.153:15173/api/v1/iam/departments/e705f892-c5c9-42ca-a8fb-22198e1bcda9
手动字段：name, description

实际输入参数：
```json
{
  "body": {
    "name": "STR3_1792469903477_645939 A B",
    "description": "STR3_1792469903477_645939 A B"
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "e705f892-c5c9-42ca-a8fb-22198e1bcda9",
    "name": "STR3_1792469903477_645939 A B",
    "children": [],
    "created_at": "2026-10-20T10:28:13",
    "description": "STR3_1792469903477_645939 A B",
    "member_count": 0,
    "parent_org_unit_id": null
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status",
    "expected": 200,
    "actual": 200,
    "passed": true
  },
  {
    "path": "data.name",
    "type": "json_equals",
    "expected": "STR3_1792469903477_645939 A B",
    "actual": "STR3_1792469903477_645939 A B",
    "passed": true
  },
  {
    "path": "data.description",
    "type": "json_equals",
    "expected": "STR3_1792469903477_645939 A B",
    "actual": "STR3_1792469903477_645939 A B",
    "passed": true
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "passed",
  "missing": [],
  "expected": {
    "name": "STR3_1792469903477_645939 A B",
    "description": "STR3_1792469903477_645939 A B"
  },
  "observed": {
    "name": "STR3_1792469903477_645939 A B",
    "description": "STR3_1792469903477_645939 A B"
  },
  "mismatches": {},
  "read_route": "/iam/departments"
}
```
回查字段断言：
```json
[
  {
    "type": "stored_field_equals",
    "path": "name",
    "expected": "STR3_1792469903477_645939 A B",
    "actual": "STR3_1792469903477_645939 A B",
    "passed": true
  },
  {
    "type": "stored_field_equals",
    "path": "description",
    "expected": "STR3_1792469903477_645939 A B",
    "actual": "STR3_1792469903477_645939 A B",
    "passed": true
  }
]
```

### 停用贝利规则 新增 / 纯空格（用例4256，执行记录20787）
结果：passed；Bug类别：None
请求：POST http://14.103.229.153:15173/api/v1/iam/beli-rules
手动字段：name, note

实际输入参数：
```json
{
  "body": {
    "name": "   ",
    "note": "   ",
    "enabled": false,
    "late_days": 0,
    "rule_type": "task_timeliness",
    "early_days": 0,
    "reward_beili": 0,
    "penalty_beili": 0
  },
  "query": {}
}
```
实际返回：HTTP 400
```json
{
  "code": 400,
  "errors": null,
  "message": "规则名称不能为空"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status_in",
    "expected": [
      400,
      422
    ],
    "actual": 400,
    "passed": true
  }
]
```

### 停用贝利规则 新增 / 首尾空格（用例4257，执行记录20788）
结果：failed；Bug类别：leading_trailing_spaces_not_fully_removed
请求：POST http://14.103.229.153:15173/api/v1/iam/beli-rules
手动字段：name, note

实际输入参数：
```json
{
  "body": {
    "name": "  STR3_1792469907297_123537  ",
    "note": "  STR3_1792469907297_123537  ",
    "enabled": false,
    "late_days": 0,
    "rule_type": "task_timeliness",
    "early_days": 0,
    "reward_beili": 0,
    "penalty_beili": 0
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "a1861ea5-0178-410e-9d03-2d14905c0cd6",
    "name": "STR3_1792469907297_123537",
    "note": "  STR3_1792469907297_123537  ",
    "enabled": false,
    "late_days": 0,
    "rule_type": "task_timeliness",
    "created_at": "2026-10-20T12:18:28",
    "early_days": 0,
    "updated_at": "2026-10-20T12:18:28",
    "reward_beili": 0.0,
    "penalty_beili": 0.0
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status",
    "expected": 200,
    "actual": 200,
    "passed": true
  },
  {
    "path": "data.name",
    "type": "json_equals",
    "expected": "STR3_1792469907297_123537",
    "actual": "STR3_1792469907297_123537",
    "passed": true
  },
  {
    "path": "data.note",
    "type": "json_equals",
    "expected": "STR3_1792469907297_123537",
    "actual": "  STR3_1792469907297_123537  ",
    "passed": false
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "failed",
  "missing": [],
  "expected": {
    "name": "STR3_1792469907297_123537",
    "note": "STR3_1792469907297_123537"
  },
  "observed": {
    "name": "STR3_1792469907297_123537",
    "note": "  STR3_1792469907297_123537  "
  },
  "mismatches": {
    "note": {
      "actual": "  STR3_1792469907297_123537  ",
      "expected": "STR3_1792469907297_123537"
    }
  },
  "read_route": "/iam/beli-rules"
}
```
回查字段断言：
```json
[
  {
    "type": "stored_field_equals",
    "path": "name",
    "expected": "STR3_1792469907297_123537",
    "actual": "STR3_1792469907297_123537",
    "passed": true
  },
  {
    "type": "stored_field_equals",
    "path": "note",
    "expected": "STR3_1792469907297_123537",
    "actual": "  STR3_1792469907297_123537  ",
    "passed": false
  }
]
```

### 停用贝利规则 新增 / 中间空格（用例4258，执行记录20789）
结果：passed；Bug类别：None
请求：POST http://14.103.229.153:15173/api/v1/iam/beli-rules
手动字段：name, note

实际输入参数：
```json
{
  "body": {
    "name": "STR3_1792469908876_068433 A B",
    "note": "STR3_1792469908876_068433 A B",
    "enabled": false,
    "late_days": 0,
    "rule_type": "task_timeliness",
    "early_days": 0,
    "reward_beili": 0,
    "penalty_beili": 0
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "adaf7747-1eb3-49f7-92cd-8d22b09e9e35",
    "name": "STR3_1792469908876_068433 A B",
    "note": "STR3_1792469908876_068433 A B",
    "enabled": false,
    "late_days": 0,
    "rule_type": "task_timeliness",
    "created_at": "2026-10-20T12:18:30",
    "early_days": 0,
    "updated_at": "2026-10-20T12:18:30",
    "reward_beili": 0.0,
    "penalty_beili": 0.0
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status",
    "expected": 200,
    "actual": 200,
    "passed": true
  },
  {
    "path": "data.name",
    "type": "json_equals",
    "expected": "STR3_1792469908876_068433 A B",
    "actual": "STR3_1792469908876_068433 A B",
    "passed": true
  },
  {
    "path": "data.note",
    "type": "json_equals",
    "expected": "STR3_1792469908876_068433 A B",
    "actual": "STR3_1792469908876_068433 A B",
    "passed": true
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "passed",
  "missing": [],
  "expected": {
    "name": "STR3_1792469908876_068433 A B",
    "note": "STR3_1792469908876_068433 A B"
  },
  "observed": {
    "name": "STR3_1792469908876_068433 A B",
    "note": "STR3_1792469908876_068433 A B"
  },
  "mismatches": {},
  "read_route": "/iam/beli-rules"
}
```
回查字段断言：
```json
[
  {
    "type": "stored_field_equals",
    "path": "name",
    "expected": "STR3_1792469908876_068433 A B",
    "actual": "STR3_1792469908876_068433 A B",
    "passed": true
  },
  {
    "type": "stored_field_equals",
    "path": "note",
    "expected": "STR3_1792469908876_068433 A B",
    "actual": "STR3_1792469908876_068433 A B",
    "passed": true
  }
]
```

### 停用贝利规则 编辑 / 纯空格（用例4259，执行记录20790）
结果：passed；Bug类别：None
请求：PATCH http://14.103.229.153:15173/api/v1/iam/beli-rules/2bd21ff8-f885-4303-bc95-c3955700bba7
手动字段：name, note

实际输入参数：
```json
{
  "body": {
    "name": "   ",
    "note": "   ",
    "enabled": false,
    "late_days": 0,
    "rule_type": "task_timeliness",
    "early_days": 0,
    "reward_beili": 0,
    "penalty_beili": 0
  },
  "query": {}
}
```
实际返回：HTTP 400
```json
{
  "code": 400,
  "errors": null,
  "message": "规则名称不能为空"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status_in",
    "expected": [
      400,
      422
    ],
    "actual": 400,
    "passed": true
  }
]
```

### 停用贝利规则 编辑 / 首尾空格（用例4260，执行记录20791）
结果：failed；Bug类别：leading_trailing_spaces_not_fully_removed
请求：PATCH http://14.103.229.153:15173/api/v1/iam/beli-rules/2bd21ff8-f885-4303-bc95-c3955700bba7
手动字段：name, note

实际输入参数：
```json
{
  "body": {
    "name": "  STR3_1792469912075_700775  ",
    "note": "  STR3_1792469912075_700775  ",
    "enabled": false,
    "late_days": 0,
    "rule_type": "task_timeliness",
    "early_days": 0,
    "reward_beili": 0,
    "penalty_beili": 0
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "2bd21ff8-f885-4303-bc95-c3955700bba7",
    "name": "STR3_1792469912075_700775",
    "note": "  STR3_1792469912075_700775  ",
    "enabled": false,
    "late_days": 0,
    "rule_type": "task_timeliness",
    "created_at": "2026-10-20T10:28:55",
    "early_days": 0,
    "updated_at": "2026-10-20T10:28:55",
    "reward_beili": 0.0,
    "penalty_beili": 0.0
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status",
    "expected": 200,
    "actual": 200,
    "passed": true
  },
  {
    "path": "data.name",
    "type": "json_equals",
    "expected": "STR3_1792469912075_700775",
    "actual": "STR3_1792469912075_700775",
    "passed": true
  },
  {
    "path": "data.note",
    "type": "json_equals",
    "expected": "STR3_1792469912075_700775",
    "actual": "  STR3_1792469912075_700775  ",
    "passed": false
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "failed",
  "missing": [],
  "expected": {
    "name": "STR3_1792469912075_700775",
    "note": "STR3_1792469912075_700775"
  },
  "observed": {
    "name": "STR3_1792469912075_700775",
    "note": "  STR3_1792469912075_700775  "
  },
  "mismatches": {
    "note": {
      "actual": "  STR3_1792469912075_700775  ",
      "expected": "STR3_1792469912075_700775"
    }
  },
  "read_route": "/iam/beli-rules"
}
```
回查字段断言：
```json
[
  {
    "type": "stored_field_equals",
    "path": "name",
    "expected": "STR3_1792469912075_700775",
    "actual": "STR3_1792469912075_700775",
    "passed": true
  },
  {
    "type": "stored_field_equals",
    "path": "note",
    "expected": "STR3_1792469912075_700775",
    "actual": "  STR3_1792469912075_700775  ",
    "passed": false
  }
]
```

### 停用贝利规则 编辑 / 中间空格（用例4261，执行记录20792）
结果：passed；Bug类别：None
请求：PATCH http://14.103.229.153:15173/api/v1/iam/beli-rules/2bd21ff8-f885-4303-bc95-c3955700bba7
手动字段：name, note

实际输入参数：
```json
{
  "body": {
    "name": "STR3_1792469913809_053396 A B",
    "note": "STR3_1792469913809_053396 A B",
    "enabled": false,
    "late_days": 0,
    "rule_type": "task_timeliness",
    "early_days": 0,
    "reward_beili": 0,
    "penalty_beili": 0
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "2bd21ff8-f885-4303-bc95-c3955700bba7",
    "name": "STR3_1792469913809_053396 A B",
    "note": "STR3_1792469913809_053396 A B",
    "enabled": false,
    "late_days": 0,
    "rule_type": "task_timeliness",
    "created_at": "2026-10-20T10:28:55",
    "early_days": 0,
    "updated_at": "2026-10-20T10:28:55",
    "reward_beili": 0.0,
    "penalty_beili": 0.0
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status",
    "expected": 200,
    "actual": 200,
    "passed": true
  },
  {
    "path": "data.name",
    "type": "json_equals",
    "expected": "STR3_1792469913809_053396 A B",
    "actual": "STR3_1792469913809_053396 A B",
    "passed": true
  },
  {
    "path": "data.note",
    "type": "json_equals",
    "expected": "STR3_1792469913809_053396 A B",
    "actual": "STR3_1792469913809_053396 A B",
    "passed": true
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "passed",
  "missing": [],
  "expected": {
    "name": "STR3_1792469913809_053396 A B",
    "note": "STR3_1792469913809_053396 A B"
  },
  "observed": {
    "name": "STR3_1792469913809_053396 A B",
    "note": "STR3_1792469913809_053396 A B"
  },
  "mismatches": {},
  "read_route": "/iam/beli-rules"
}
```
回查字段断言：
```json
[
  {
    "type": "stored_field_equals",
    "path": "name",
    "expected": "STR3_1792469913809_053396 A B",
    "actual": "STR3_1792469913809_053396 A B",
    "passed": true
  },
  {
    "type": "stored_field_equals",
    "path": "note",
    "expected": "STR3_1792469913809_053396 A B",
    "actual": "STR3_1792469913809_053396 A B",
    "passed": true
  }
]
```

### 交易方 新增 / 纯空格（用例4265，执行记录20793）
结果：failed；Bug类别：whitespace_only_saved
请求：POST http://14.103.229.153:15173/api/v1/contract/counterparties
手动字段：name, address, bank_name

实际输入参数：
```json
{
  "body": {
    "name": "   ",
    "type": "customer",
    "phone": "13800138000",
    "address": "   ",
    "bank_name": "   ",
    "identifier": "STR_20261020_102732_59",
    "bank_account": "6222000012345678"
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "7802f030-4631-413c-aa1c-c1ed3d5f491c",
    "name": "   ",
    "type": "customer",
    "phone": "13800138000",
    "address": "   ",
    "bank_name": "   ",
    "created_at": "2026-10-20T12:18:37",
    "identifier": "STR_20261020_102732_59",
    "bank_account": "6222000012345678"
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status_in",
    "expected": [
      400,
      422
    ],
    "actual": 200,
    "passed": false
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "unexpectedly_saved",
  "missing": [],
  "expected": {
    "name": "   ",
    "address": "   ",
    "bank_name": "   "
  },
  "observed": {
    "name": "   ",
    "address": "   ",
    "bank_name": "   "
  },
  "mismatches": {},
  "read_route": "/contract/counterparties?page_size=200",
  "expected_action": "reject_whitespace_without_saving"
}
```

### 交易方 新增 / 首尾空格（用例4266，执行记录20794）
结果：failed；Bug类别：leading_trailing_spaces_not_fully_removed
请求：POST http://14.103.229.153:15173/api/v1/contract/counterparties
手动字段：name, address, bank_name

实际输入参数：
```json
{
  "body": {
    "name": "  STR3_1792469918204_684551  ",
    "type": "customer",
    "phone": "13800138000",
    "address": "  STR3_1792469918204_684551  ",
    "bank_name": "  STR3_1792469918204_684551  ",
    "identifier": "STR_20261020_102732_59",
    "bank_account": "6222000012345678"
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "4f9588b7-8c8a-4f5a-bed6-9aed63b7c78f",
    "name": "  STR3_1792469918204_684551  ",
    "type": "customer",
    "phone": "13800138000",
    "address": "  STR3_1792469918204_684551  ",
    "bank_name": "  STR3_1792469918204_684551  ",
    "created_at": "2026-10-20T12:18:39",
    "identifier": "STR_20261020_102732_59",
    "bank_account": "6222000012345678"
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status",
    "expected": 200,
    "actual": 200,
    "passed": true
  },
  {
    "path": "data.name",
    "type": "json_equals",
    "expected": "STR3_1792469918204_684551",
    "actual": "  STR3_1792469918204_684551  ",
    "passed": false
  },
  {
    "path": "data.address",
    "type": "json_equals",
    "expected": "STR3_1792469918204_684551",
    "actual": "  STR3_1792469918204_684551  ",
    "passed": false
  },
  {
    "path": "data.bank_name",
    "type": "json_equals",
    "expected": "STR3_1792469918204_684551",
    "actual": "  STR3_1792469918204_684551  ",
    "passed": false
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "failed",
  "missing": [],
  "expected": {
    "name": "STR3_1792469918204_684551",
    "address": "STR3_1792469918204_684551",
    "bank_name": "STR3_1792469918204_684551"
  },
  "observed": {
    "name": "  STR3_1792469918204_684551  ",
    "address": "  STR3_1792469918204_684551  ",
    "bank_name": "  STR3_1792469918204_684551  "
  },
  "mismatches": {
    "name": {
      "actual": "  STR3_1792469918204_684551  ",
      "expected": "STR3_1792469918204_684551"
    },
    "address": {
      "actual": "  STR3_1792469918204_684551  ",
      "expected": "STR3_1792469918204_684551"
    },
    "bank_name": {
      "actual": "  STR3_1792469918204_684551  ",
      "expected": "STR3_1792469918204_684551"
    }
  },
  "read_route": "/contract/counterparties?page_size=200"
}
```
回查字段断言：
```json
[
  {
    "type": "stored_field_equals",
    "path": "name",
    "expected": "STR3_1792469918204_684551",
    "actual": "  STR3_1792469918204_684551  ",
    "passed": false
  },
  {
    "type": "stored_field_equals",
    "path": "address",
    "expected": "STR3_1792469918204_684551",
    "actual": "  STR3_1792469918204_684551  ",
    "passed": false
  },
  {
    "type": "stored_field_equals",
    "path": "bank_name",
    "expected": "STR3_1792469918204_684551",
    "actual": "  STR3_1792469918204_684551  ",
    "passed": false
  }
]
```

### 交易方 新增 / 中间空格（用例4267，执行记录20795）
结果：passed；Bug类别：None
请求：POST http://14.103.229.153:15173/api/v1/contract/counterparties
手动字段：name, address, bank_name

实际输入参数：
```json
{
  "body": {
    "name": "STR3_1792469920282_759944 A B",
    "type": "customer",
    "phone": "13800138000",
    "address": "STR3_1792469920282_759944 A B",
    "bank_name": "STR3_1792469920282_759944 A B",
    "identifier": "STR_20261020_102732_59",
    "bank_account": "6222000012345678"
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "c12910f7-5e8f-49d9-8c5d-2aa380d97946",
    "name": "STR3_1792469920282_759944 A B",
    "type": "customer",
    "phone": "13800138000",
    "address": "STR3_1792469920282_759944 A B",
    "bank_name": "STR3_1792469920282_759944 A B",
    "created_at": "2026-10-20T12:18:41",
    "identifier": "STR_20261020_102732_59",
    "bank_account": "6222000012345678"
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status",
    "expected": 200,
    "actual": 200,
    "passed": true
  },
  {
    "path": "data.name",
    "type": "json_equals",
    "expected": "STR3_1792469920282_759944 A B",
    "actual": "STR3_1792469920282_759944 A B",
    "passed": true
  },
  {
    "path": "data.address",
    "type": "json_equals",
    "expected": "STR3_1792469920282_759944 A B",
    "actual": "STR3_1792469920282_759944 A B",
    "passed": true
  },
  {
    "path": "data.bank_name",
    "type": "json_equals",
    "expected": "STR3_1792469920282_759944 A B",
    "actual": "STR3_1792469920282_759944 A B",
    "passed": true
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "passed",
  "missing": [],
  "expected": {
    "name": "STR3_1792469920282_759944 A B",
    "address": "STR3_1792469920282_759944 A B",
    "bank_name": "STR3_1792469920282_759944 A B"
  },
  "observed": {
    "name": "STR3_1792469920282_759944 A B",
    "address": "STR3_1792469920282_759944 A B",
    "bank_name": "STR3_1792469920282_759944 A B"
  },
  "mismatches": {},
  "read_route": "/contract/counterparties?page_size=200"
}
```
回查字段断言：
```json
[
  {
    "type": "stored_field_equals",
    "path": "name",
    "expected": "STR3_1792469920282_759944 A B",
    "actual": "STR3_1792469920282_759944 A B",
    "passed": true
  },
  {
    "type": "stored_field_equals",
    "path": "address",
    "expected": "STR3_1792469920282_759944 A B",
    "actual": "STR3_1792469920282_759944 A B",
    "passed": true
  },
  {
    "type": "stored_field_equals",
    "path": "bank_name",
    "expected": "STR3_1792469920282_759944 A B",
    "actual": "STR3_1792469920282_759944 A B",
    "passed": true
  }
]
```

### 交易方 编辑 / 纯空格（用例4268，执行记录20796）
结果：failed；Bug类别：whitespace_only_saved
请求：PATCH http://14.103.229.153:15173/api/v1/contract/counterparties/4952f6f1-9766-452e-a9a4-715e17fa87a0
手动字段：name, address, bank_name

实际输入参数：
```json
{
  "body": {
    "name": "   ",
    "type": "customer",
    "phone": "13800138000",
    "address": "   ",
    "bank_name": "   ",
    "identifier": "STR_20261020_102732_81",
    "bank_account": "6222000012345678"
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
    "name": "   ",
    "type": "customer",
    "phone": "13800138000",
    "address": "   ",
    "bank_name": "   ",
    "created_at": "2026-10-20T10:30:37",
    "identifier": "STR_20261020_102732_81",
    "bank_account": "6222000012345678"
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status_in",
    "expected": [
      400,
      422
    ],
    "actual": 200,
    "passed": false
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "unexpectedly_saved",
  "missing": [],
  "expected": {
    "name": "   ",
    "address": "   ",
    "bank_name": "   "
  },
  "observed": {
    "name": "   ",
    "address": "   ",
    "bank_name": "   "
  },
  "mismatches": {},
  "read_route": "/contract/counterparties?page_size=200",
  "expected_action": "reject_whitespace_without_saving"
}
```

### 交易方 编辑 / 首尾空格（用例4269，执行记录20797）
结果：failed；Bug类别：leading_trailing_spaces_not_fully_removed
请求：PATCH http://14.103.229.153:15173/api/v1/contract/counterparties/4952f6f1-9766-452e-a9a4-715e17fa87a0
手动字段：name, address, bank_name

实际输入参数：
```json
{
  "body": {
    "name": "  STR3_1792469924269_327150  ",
    "type": "customer",
    "phone": "13800138000",
    "address": "  STR3_1792469924269_327150  ",
    "bank_name": "  STR3_1792469924269_327150  ",
    "identifier": "STR_20261020_102732_81",
    "bank_account": "6222000012345678"
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
    "name": "  STR3_1792469924269_327150  ",
    "type": "customer",
    "phone": "13800138000",
    "address": "  STR3_1792469924269_327150  ",
    "bank_name": "  STR3_1792469924269_327150  ",
    "created_at": "2026-10-20T10:30:37",
    "identifier": "STR_20261020_102732_81",
    "bank_account": "6222000012345678"
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status",
    "expected": 200,
    "actual": 200,
    "passed": true
  },
  {
    "path": "data.name",
    "type": "json_equals",
    "expected": "STR3_1792469924269_327150",
    "actual": "  STR3_1792469924269_327150  ",
    "passed": false
  },
  {
    "path": "data.address",
    "type": "json_equals",
    "expected": "STR3_1792469924269_327150",
    "actual": "  STR3_1792469924269_327150  ",
    "passed": false
  },
  {
    "path": "data.bank_name",
    "type": "json_equals",
    "expected": "STR3_1792469924269_327150",
    "actual": "  STR3_1792469924269_327150  ",
    "passed": false
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "failed",
  "missing": [],
  "expected": {
    "name": "STR3_1792469924269_327150",
    "address": "STR3_1792469924269_327150",
    "bank_name": "STR3_1792469924269_327150"
  },
  "observed": {
    "name": "  STR3_1792469924269_327150  ",
    "address": "  STR3_1792469924269_327150  ",
    "bank_name": "  STR3_1792469924269_327150  "
  },
  "mismatches": {
    "name": {
      "actual": "  STR3_1792469924269_327150  ",
      "expected": "STR3_1792469924269_327150"
    },
    "address": {
      "actual": "  STR3_1792469924269_327150  ",
      "expected": "STR3_1792469924269_327150"
    },
    "bank_name": {
      "actual": "  STR3_1792469924269_327150  ",
      "expected": "STR3_1792469924269_327150"
    }
  },
  "read_route": "/contract/counterparties?page_size=200"
}
```
回查字段断言：
```json
[
  {
    "type": "stored_field_equals",
    "path": "name",
    "expected": "STR3_1792469924269_327150",
    "actual": "  STR3_1792469924269_327150  ",
    "passed": false
  },
  {
    "type": "stored_field_equals",
    "path": "address",
    "expected": "STR3_1792469924269_327150",
    "actual": "  STR3_1792469924269_327150  ",
    "passed": false
  },
  {
    "type": "stored_field_equals",
    "path": "bank_name",
    "expected": "STR3_1792469924269_327150",
    "actual": "  STR3_1792469924269_327150  ",
    "passed": false
  }
]
```

### 交易方 编辑 / 中间空格（用例4270，执行记录20798）
结果：passed；Bug类别：None
请求：PATCH http://14.103.229.153:15173/api/v1/contract/counterparties/4952f6f1-9766-452e-a9a4-715e17fa87a0
手动字段：name, address, bank_name

实际输入参数：
```json
{
  "body": {
    "name": "STR3_1792469926162_173061 A B",
    "type": "customer",
    "phone": "13800138000",
    "address": "STR3_1792469926162_173061 A B",
    "bank_name": "STR3_1792469926162_173061 A B",
    "identifier": "STR_20261020_102732_81",
    "bank_account": "6222000012345678"
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
    "name": "STR3_1792469926162_173061 A B",
    "type": "customer",
    "phone": "13800138000",
    "address": "STR3_1792469926162_173061 A B",
    "bank_name": "STR3_1792469926162_173061 A B",
    "created_at": "2026-10-20T10:30:37",
    "identifier": "STR_20261020_102732_81",
    "bank_account": "6222000012345678"
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status",
    "expected": 200,
    "actual": 200,
    "passed": true
  },
  {
    "path": "data.name",
    "type": "json_equals",
    "expected": "STR3_1792469926162_173061 A B",
    "actual": "STR3_1792469926162_173061 A B",
    "passed": true
  },
  {
    "path": "data.address",
    "type": "json_equals",
    "expected": "STR3_1792469926162_173061 A B",
    "actual": "STR3_1792469926162_173061 A B",
    "passed": true
  },
  {
    "path": "data.bank_name",
    "type": "json_equals",
    "expected": "STR3_1792469926162_173061 A B",
    "actual": "STR3_1792469926162_173061 A B",
    "passed": true
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "passed",
  "missing": [],
  "expected": {
    "name": "STR3_1792469926162_173061 A B",
    "address": "STR3_1792469926162_173061 A B",
    "bank_name": "STR3_1792469926162_173061 A B"
  },
  "observed": {
    "name": "STR3_1792469926162_173061 A B",
    "address": "STR3_1792469926162_173061 A B",
    "bank_name": "STR3_1792469926162_173061 A B"
  },
  "mismatches": {},
  "read_route": "/contract/counterparties?page_size=200"
}
```
回查字段断言：
```json
[
  {
    "type": "stored_field_equals",
    "path": "name",
    "expected": "STR3_1792469926162_173061 A B",
    "actual": "STR3_1792469926162_173061 A B",
    "passed": true
  },
  {
    "type": "stored_field_equals",
    "path": "address",
    "expected": "STR3_1792469926162_173061 A B",
    "actual": "STR3_1792469926162_173061 A B",
    "passed": true
  },
  {
    "type": "stored_field_equals",
    "path": "bank_name",
    "expected": "STR3_1792469926162_173061 A B",
    "actual": "STR3_1792469926162_173061 A B",
    "passed": true
  }
]
```

### 任务 新增 / 纯空格（用例4271，执行记录20799）
结果：failed；Bug类别：whitespace_only_saved
请求：POST http://14.103.229.153:15173/api/v1/todo
手动字段：title, description, notes

实际输入参数：
```json
{
  "body": {
    "tags": [
      "STR_20261020_102732"
    ],
    "notes": "   ",
    "title": "   ",
    "due_at": "2026-10-23T18:00:00+08:00",
    "priority": "p2",
    "start_at": "2026-10-21T09:00:00+08:00",
    "source_id": "",
    "action_type": "do",
    "description": "   ",
    "source_type": "custom",
    "estimated_hours": 0,
    "assignee_user_id": "640d1a5c-bff5-4df0-9e02-cb42f8b46413"
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "fb9e26f3-3109-4b07-9df9-213b2d7a8d6b",
    "link": {},
    "tags": [
      "STR_20261020_102732"
    ],
    "notes": "   ",
    "title": "   ",
    "due_at": "2026-10-23T18:00:00",
    "status": "open",
    "done_at": null,
    "priority": "p2",
    "start_at": "2026-10-21T09:00:00",
    "source_id": "05b1ed99-5f53-464e-b9a5-e625646b94b3",
    "created_at": "2026-10-20T12:18:50",
    "updated_at": "2026-10-20T12:18:50",
    "action_type": "do",
    "description": "   ",
    "source_type": "custom",
    "creator_name": "test_user1",
    "submitted_at": null,
    "assignee_name": "test_user3",
    "our_entity_id": "14efc508-797d-4a29-b359-3d5b51424a84",
    "reviewer_name": null,
    "blocked_reason": null,
    "dismiss_reason": null,
    "review_comment": null,
    "creator_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "done_by_user_id": null,
    "estimated_hours": "0.00",
    "assignee_user_id": "640d1a5c-bff5-4df0-9e02-cb42f8b46413",
    "reviewed_by_user_id": null
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status_in",
    "expected": [
      400,
      422
    ],
    "actual": 200,
    "passed": false
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "unexpectedly_saved",
  "missing": [],
  "expected": {
    "notes": "   ",
    "title": "   ",
    "description": "   "
  },
  "observed": {
    "notes": "   ",
    "title": "   ",
    "description": "   "
  },
  "mismatches": {},
  "read_route": "/todo/fb9e26f3-3109-4b07-9df9-213b2d7a8d6b",
  "expected_action": "reject_whitespace_without_saving"
}
```

### 任务 新增 / 首尾空格（用例4272，执行记录20800）
结果：failed；Bug类别：leading_trailing_spaces_not_fully_removed
请求：POST http://14.103.229.153:15173/api/v1/todo
手动字段：title, description, notes

实际输入参数：
```json
{
  "body": {
    "tags": [
      "STR_20261020_102732"
    ],
    "notes": "  STR3_1792469931249_213936  ",
    "title": "  STR3_1792469931249_213936  ",
    "due_at": "2026-10-23T18:00:00+08:00",
    "priority": "p2",
    "start_at": "2026-10-21T09:00:00+08:00",
    "source_id": "",
    "action_type": "do",
    "description": "  STR3_1792469931249_213936  ",
    "source_type": "custom",
    "estimated_hours": 0,
    "assignee_user_id": "640d1a5c-bff5-4df0-9e02-cb42f8b46413"
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "2c63f37a-7a3a-43fc-9203-7384445868c2",
    "link": {},
    "tags": [
      "STR_20261020_102732"
    ],
    "notes": "  STR3_1792469931249_213936  ",
    "title": "  STR3_1792469931249_213936  ",
    "due_at": "2026-10-23T18:00:00",
    "status": "open",
    "done_at": null,
    "priority": "p2",
    "start_at": "2026-10-21T09:00:00",
    "source_id": "a77a181b-72d3-4517-b63f-f50c5e668a16",
    "created_at": "2026-10-20T12:18:52",
    "updated_at": "2026-10-20T12:18:52",
    "action_type": "do",
    "description": "  STR3_1792469931249_213936  ",
    "source_type": "custom",
    "creator_name": "test_user1",
    "submitted_at": null,
    "assignee_name": "test_user3",
    "our_entity_id": "14efc508-797d-4a29-b359-3d5b51424a84",
    "reviewer_name": null,
    "blocked_reason": null,
    "dismiss_reason": null,
    "review_comment": null,
    "creator_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "done_by_user_id": null,
    "estimated_hours": "0.00",
    "assignee_user_id": "640d1a5c-bff5-4df0-9e02-cb42f8b46413",
    "reviewed_by_user_id": null
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status",
    "expected": 200,
    "actual": 200,
    "passed": true
  },
  {
    "path": "data.title",
    "type": "json_equals",
    "expected": "STR3_1792469931249_213936",
    "actual": "  STR3_1792469931249_213936  ",
    "passed": false
  },
  {
    "path": "data.description",
    "type": "json_equals",
    "expected": "STR3_1792469931249_213936",
    "actual": "  STR3_1792469931249_213936  ",
    "passed": false
  },
  {
    "path": "data.notes",
    "type": "json_equals",
    "expected": "STR3_1792469931249_213936",
    "actual": "  STR3_1792469931249_213936  ",
    "passed": false
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "failed",
  "missing": [],
  "expected": {
    "notes": "STR3_1792469931249_213936",
    "title": "STR3_1792469931249_213936",
    "description": "STR3_1792469931249_213936"
  },
  "observed": {
    "notes": "  STR3_1792469931249_213936  ",
    "title": "  STR3_1792469931249_213936  ",
    "description": "  STR3_1792469931249_213936  "
  },
  "mismatches": {
    "notes": {
      "actual": "  STR3_1792469931249_213936  ",
      "expected": "STR3_1792469931249_213936"
    },
    "title": {
      "actual": "  STR3_1792469931249_213936  ",
      "expected": "STR3_1792469931249_213936"
    },
    "description": {
      "actual": "  STR3_1792469931249_213936  ",
      "expected": "STR3_1792469931249_213936"
    }
  },
  "read_route": "/todo/2c63f37a-7a3a-43fc-9203-7384445868c2"
}
```
回查字段断言：
```json
[
  {
    "type": "stored_field_equals",
    "path": "notes",
    "expected": "STR3_1792469931249_213936",
    "actual": "  STR3_1792469931249_213936  ",
    "passed": false
  },
  {
    "type": "stored_field_equals",
    "path": "title",
    "expected": "STR3_1792469931249_213936",
    "actual": "  STR3_1792469931249_213936  ",
    "passed": false
  },
  {
    "type": "stored_field_equals",
    "path": "description",
    "expected": "STR3_1792469931249_213936",
    "actual": "  STR3_1792469931249_213936  ",
    "passed": false
  }
]
```

### 任务 新增 / 中间空格（用例4273，执行记录20801）
结果：passed；Bug类别：None
请求：POST http://14.103.229.153:15173/api/v1/todo
手动字段：title, description, notes

实际输入参数：
```json
{
  "body": {
    "tags": [
      "STR_20261020_102732"
    ],
    "notes": "STR3_1792469933051_775367 A B",
    "title": "STR3_1792469933051_775367 A B",
    "due_at": "2026-10-23T18:00:00+08:00",
    "priority": "p2",
    "start_at": "2026-10-21T09:00:00+08:00",
    "source_id": "",
    "action_type": "do",
    "description": "STR3_1792469933051_775367 A B",
    "source_type": "custom",
    "estimated_hours": 0,
    "assignee_user_id": "640d1a5c-bff5-4df0-9e02-cb42f8b46413"
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "f2a63529-8249-4964-8f6c-61639081bf9a",
    "link": {},
    "tags": [
      "STR_20261020_102732"
    ],
    "notes": "STR3_1792469933051_775367 A B",
    "title": "STR3_1792469933051_775367 A B",
    "due_at": "2026-10-23T18:00:00",
    "status": "open",
    "done_at": null,
    "priority": "p2",
    "start_at": "2026-10-21T09:00:00",
    "source_id": "eeba24fd-5597-469e-a3ea-ec2a1fa0dbfe",
    "created_at": "2026-10-20T12:18:54",
    "updated_at": "2026-10-20T12:18:54",
    "action_type": "do",
    "description": "STR3_1792469933051_775367 A B",
    "source_type": "custom",
    "creator_name": "test_user1",
    "submitted_at": null,
    "assignee_name": "test_user3",
    "our_entity_id": "14efc508-797d-4a29-b359-3d5b51424a84",
    "reviewer_name": null,
    "blocked_reason": null,
    "dismiss_reason": null,
    "review_comment": null,
    "creator_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "done_by_user_id": null,
    "estimated_hours": "0.00",
    "assignee_user_id": "640d1a5c-bff5-4df0-9e02-cb42f8b46413",
    "reviewed_by_user_id": null
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status",
    "expected": 200,
    "actual": 200,
    "passed": true
  },
  {
    "path": "data.title",
    "type": "json_equals",
    "expected": "STR3_1792469933051_775367 A B",
    "actual": "STR3_1792469933051_775367 A B",
    "passed": true
  },
  {
    "path": "data.description",
    "type": "json_equals",
    "expected": "STR3_1792469933051_775367 A B",
    "actual": "STR3_1792469933051_775367 A B",
    "passed": true
  },
  {
    "path": "data.notes",
    "type": "json_equals",
    "expected": "STR3_1792469933051_775367 A B",
    "actual": "STR3_1792469933051_775367 A B",
    "passed": true
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "passed",
  "missing": [],
  "expected": {
    "notes": "STR3_1792469933051_775367 A B",
    "title": "STR3_1792469933051_775367 A B",
    "description": "STR3_1792469933051_775367 A B"
  },
  "observed": {
    "notes": "STR3_1792469933051_775367 A B",
    "title": "STR3_1792469933051_775367 A B",
    "description": "STR3_1792469933051_775367 A B"
  },
  "mismatches": {},
  "read_route": "/todo/f2a63529-8249-4964-8f6c-61639081bf9a"
}
```
回查字段断言：
```json
[
  {
    "type": "stored_field_equals",
    "path": "notes",
    "expected": "STR3_1792469933051_775367 A B",
    "actual": "STR3_1792469933051_775367 A B",
    "passed": true
  },
  {
    "type": "stored_field_equals",
    "path": "title",
    "expected": "STR3_1792469933051_775367 A B",
    "actual": "STR3_1792469933051_775367 A B",
    "passed": true
  },
  {
    "type": "stored_field_equals",
    "path": "description",
    "expected": "STR3_1792469933051_775367 A B",
    "actual": "STR3_1792469933051_775367 A B",
    "passed": true
  }
]
```

### 任务 编辑 / 纯空格（用例4274，执行记录20802）
结果：failed；Bug类别：whitespace_only_saved
请求：PATCH http://14.103.229.153:15173/api/v1/todo/0c07a499-a09a-4ee0-935e-5c1172b85532
手动字段：title, description, notes

实际输入参数：
```json
{
  "body": {
    "tags": [
      "STR_20261020_102732"
    ],
    "notes": "   ",
    "title": "   ",
    "due_at": "2026-10-23T18:00:00+08:00",
    "priority": "p2",
    "start_at": "2026-10-21T09:00:00+08:00",
    "description": "   ",
    "estimated_hours": 0,
    "assignee_user_id": "640d1a5c-bff5-4df0-9e02-cb42f8b46413"
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "0c07a499-a09a-4ee0-935e-5c1172b85532",
    "link": {},
    "tags": [
      "STR_20261020_102732"
    ],
    "notes": "   ",
    "title": "   ",
    "due_at": "2026-10-23T18:00:00",
    "status": "open",
    "done_at": null,
    "priority": "p2",
    "start_at": "2026-10-21T09:00:00",
    "source_id": "3d58971f-23b5-4113-8879-b2f68c36434c",
    "created_at": "2026-10-20T12:17:21",
    "updated_at": "2026-10-20T12:18:56",
    "action_type": "do",
    "description": "   ",
    "source_type": "custom",
    "creator_name": "test_user1",
    "submitted_at": null,
    "assignee_name": "test_user3",
    "our_entity_id": "14efc508-797d-4a29-b359-3d5b51424a84",
    "reviewer_name": null,
    "blocked_reason": null,
    "dismiss_reason": null,
    "review_comment": null,
    "creator_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "done_by_user_id": null,
    "estimated_hours": "0.00",
    "assignee_user_id": "640d1a5c-bff5-4df0-9e02-cb42f8b46413",
    "reviewed_by_user_id": null
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status_in",
    "expected": [
      400,
      422
    ],
    "actual": 200,
    "passed": false
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "unexpectedly_saved",
  "missing": [],
  "expected": {
    "notes": "   ",
    "title": "   ",
    "description": "   "
  },
  "observed": {
    "notes": "   ",
    "title": "   ",
    "description": "   "
  },
  "mismatches": {},
  "read_route": "/todo/0c07a499-a09a-4ee0-935e-5c1172b85532",
  "expected_action": "reject_whitespace_without_saving"
}
```

### 任务 编辑 / 首尾空格（用例4275，执行记录20803）
结果：failed；Bug类别：leading_trailing_spaces_not_fully_removed
请求：PATCH http://14.103.229.153:15173/api/v1/todo/0c07a499-a09a-4ee0-935e-5c1172b85532
手动字段：title, description, notes

实际输入参数：
```json
{
  "body": {
    "tags": [
      "STR_20261020_102732"
    ],
    "notes": "  STR3_1792469937241_886098  ",
    "title": "  STR3_1792469937241_886098  ",
    "due_at": "2026-10-23T18:00:00+08:00",
    "priority": "p2",
    "start_at": "2026-10-21T09:00:00+08:00",
    "description": "  STR3_1792469937241_886098  ",
    "estimated_hours": 0,
    "assignee_user_id": "640d1a5c-bff5-4df0-9e02-cb42f8b46413"
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "0c07a499-a09a-4ee0-935e-5c1172b85532",
    "link": {},
    "tags": [
      "STR_20261020_102732"
    ],
    "notes": "  STR3_1792469937241_886098  ",
    "title": "  STR3_1792469937241_886098  ",
    "due_at": "2026-10-23T18:00:00",
    "status": "open",
    "done_at": null,
    "priority": "p2",
    "start_at": "2026-10-21T09:00:00",
    "source_id": "3d58971f-23b5-4113-8879-b2f68c36434c",
    "created_at": "2026-10-20T12:17:21",
    "updated_at": "2026-10-20T12:18:58",
    "action_type": "do",
    "description": "  STR3_1792469937241_886098  ",
    "source_type": "custom",
    "creator_name": "test_user1",
    "submitted_at": null,
    "assignee_name": "test_user3",
    "our_entity_id": "14efc508-797d-4a29-b359-3d5b51424a84",
    "reviewer_name": null,
    "blocked_reason": null,
    "dismiss_reason": null,
    "review_comment": null,
    "creator_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "done_by_user_id": null,
    "estimated_hours": "0.00",
    "assignee_user_id": "640d1a5c-bff5-4df0-9e02-cb42f8b46413",
    "reviewed_by_user_id": null
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status",
    "expected": 200,
    "actual": 200,
    "passed": true
  },
  {
    "path": "data.title",
    "type": "json_equals",
    "expected": "STR3_1792469937241_886098",
    "actual": "  STR3_1792469937241_886098  ",
    "passed": false
  },
  {
    "path": "data.description",
    "type": "json_equals",
    "expected": "STR3_1792469937241_886098",
    "actual": "  STR3_1792469937241_886098  ",
    "passed": false
  },
  {
    "path": "data.notes",
    "type": "json_equals",
    "expected": "STR3_1792469937241_886098",
    "actual": "  STR3_1792469937241_886098  ",
    "passed": false
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "failed",
  "missing": [],
  "expected": {
    "notes": "STR3_1792469937241_886098",
    "title": "STR3_1792469937241_886098",
    "description": "STR3_1792469937241_886098"
  },
  "observed": {
    "notes": "  STR3_1792469937241_886098  ",
    "title": "  STR3_1792469937241_886098  ",
    "description": "  STR3_1792469937241_886098  "
  },
  "mismatches": {
    "notes": {
      "actual": "  STR3_1792469937241_886098  ",
      "expected": "STR3_1792469937241_886098"
    },
    "title": {
      "actual": "  STR3_1792469937241_886098  ",
      "expected": "STR3_1792469937241_886098"
    },
    "description": {
      "actual": "  STR3_1792469937241_886098  ",
      "expected": "STR3_1792469937241_886098"
    }
  },
  "read_route": "/todo/0c07a499-a09a-4ee0-935e-5c1172b85532"
}
```
回查字段断言：
```json
[
  {
    "type": "stored_field_equals",
    "path": "notes",
    "expected": "STR3_1792469937241_886098",
    "actual": "  STR3_1792469937241_886098  ",
    "passed": false
  },
  {
    "type": "stored_field_equals",
    "path": "title",
    "expected": "STR3_1792469937241_886098",
    "actual": "  STR3_1792469937241_886098  ",
    "passed": false
  },
  {
    "type": "stored_field_equals",
    "path": "description",
    "expected": "STR3_1792469937241_886098",
    "actual": "  STR3_1792469937241_886098  ",
    "passed": false
  }
]
```

### 任务 编辑 / 中间空格（用例4276，执行记录20804）
结果：passed；Bug类别：None
请求：PATCH http://14.103.229.153:15173/api/v1/todo/0c07a499-a09a-4ee0-935e-5c1172b85532
手动字段：title, description, notes

实际输入参数：
```json
{
  "body": {
    "tags": [
      "STR_20261020_102732"
    ],
    "notes": "STR3_1792469939159_335324 A B",
    "title": "STR3_1792469939159_335324 A B",
    "due_at": "2026-10-23T18:00:00+08:00",
    "priority": "p2",
    "start_at": "2026-10-21T09:00:00+08:00",
    "description": "STR3_1792469939159_335324 A B",
    "estimated_hours": 0,
    "assignee_user_id": "640d1a5c-bff5-4df0-9e02-cb42f8b46413"
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "0c07a499-a09a-4ee0-935e-5c1172b85532",
    "link": {},
    "tags": [
      "STR_20261020_102732"
    ],
    "notes": "STR3_1792469939159_335324 A B",
    "title": "STR3_1792469939159_335324 A B",
    "due_at": "2026-10-23T18:00:00",
    "status": "open",
    "done_at": null,
    "priority": "p2",
    "start_at": "2026-10-21T09:00:00",
    "source_id": "3d58971f-23b5-4113-8879-b2f68c36434c",
    "created_at": "2026-10-20T12:17:21",
    "updated_at": "2026-10-20T12:19:00",
    "action_type": "do",
    "description": "STR3_1792469939159_335324 A B",
    "source_type": "custom",
    "creator_name": "test_user1",
    "submitted_at": null,
    "assignee_name": "test_user3",
    "our_entity_id": "14efc508-797d-4a29-b359-3d5b51424a84",
    "reviewer_name": null,
    "blocked_reason": null,
    "dismiss_reason": null,
    "review_comment": null,
    "creator_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "done_by_user_id": null,
    "estimated_hours": "0.00",
    "assignee_user_id": "640d1a5c-bff5-4df0-9e02-cb42f8b46413",
    "reviewed_by_user_id": null
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status",
    "expected": 200,
    "actual": 200,
    "passed": true
  },
  {
    "path": "data.title",
    "type": "json_equals",
    "expected": "STR3_1792469939159_335324 A B",
    "actual": "STR3_1792469939159_335324 A B",
    "passed": true
  },
  {
    "path": "data.description",
    "type": "json_equals",
    "expected": "STR3_1792469939159_335324 A B",
    "actual": "STR3_1792469939159_335324 A B",
    "passed": true
  },
  {
    "path": "data.notes",
    "type": "json_equals",
    "expected": "STR3_1792469939159_335324 A B",
    "actual": "STR3_1792469939159_335324 A B",
    "passed": true
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "passed",
  "missing": [],
  "expected": {
    "notes": "STR3_1792469939159_335324 A B",
    "title": "STR3_1792469939159_335324 A B",
    "description": "STR3_1792469939159_335324 A B"
  },
  "observed": {
    "notes": "STR3_1792469939159_335324 A B",
    "title": "STR3_1792469939159_335324 A B",
    "description": "STR3_1792469939159_335324 A B"
  },
  "mismatches": {},
  "read_route": "/todo/0c07a499-a09a-4ee0-935e-5c1172b85532"
}
```
回查字段断言：
```json
[
  {
    "type": "stored_field_equals",
    "path": "notes",
    "expected": "STR3_1792469939159_335324 A B",
    "actual": "STR3_1792469939159_335324 A B",
    "passed": true
  },
  {
    "type": "stored_field_equals",
    "path": "title",
    "expected": "STR3_1792469939159_335324 A B",
    "actual": "STR3_1792469939159_335324 A B",
    "passed": true
  },
  {
    "type": "stored_field_equals",
    "path": "description",
    "expected": "STR3_1792469939159_335324 A B",
    "actual": "STR3_1792469939159_335324 A B",
    "passed": true
  }
]
```

### 项目 新增 / 纯空格（用例4277，执行记录20805）
结果：failed；Bug类别：whitespace_only_saved
请求：POST http://14.103.229.153:15173/api/v1/project/projects
手动字段：name, description

实际输入参数：
```json
{
  "body": {
    "name": "   ",
    "due_at": "2026-10-30",
    "start_at": "2026-10-20",
    "pm_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "project_no": "PR-20261020121902-006557",
    "description": "   ",
    "project_type": "b2b"
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "2b7e739b-238b-4145-8065-ea767bb355fc",
    "name": "   ",
    "due_at": "2026-10-30",
    "status": "draft",
    "pm_name": "test_user1",
    "progress": 0.0,
    "start_at": "2026-10-20",
    "created_at": "2026-10-20T12:19:04",
    "pm_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "project_no": "PR-20261020121902-006557",
    "updated_at": "2026-10-20T12:19:04",
    "contract_id": null,
    "customer_id": null,
    "description": "   ",
    "project_type": "b2b",
    "our_entity_id": null,
    "owner_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "current_stage_code": "requirement_alignment"
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status_in",
    "expected": [
      400,
      422
    ],
    "actual": 200,
    "passed": false
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "unexpectedly_saved",
  "missing": [],
  "expected": {
    "name": "   ",
    "description": "   "
  },
  "observed": {
    "name": "   ",
    "description": "   "
  },
  "mismatches": {},
  "read_route": "/project/projects/2b7e739b-238b-4145-8065-ea767bb355fc",
  "expected_action": "reject_whitespace_without_saving"
}
```

### 项目 新增 / 首尾空格（用例4278，执行记录20806）
结果：failed；Bug类别：leading_trailing_spaces_not_fully_removed
请求：POST http://14.103.229.153:15173/api/v1/project/projects
手动字段：name, description

实际输入参数：
```json
{
  "body": {
    "name": "  STR3_1792469945169_347413  ",
    "due_at": "2026-10-30",
    "start_at": "2026-10-20",
    "pm_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "project_no": "PR-20261020121905-347413",
    "description": "  STR3_1792469945169_347413  ",
    "project_type": "b2b"
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "f1592361-e24c-47d9-9e5f-4ff5a6a0ee09",
    "name": "  STR3_1792469945169_347413  ",
    "due_at": "2026-10-30",
    "status": "draft",
    "pm_name": "test_user1",
    "progress": 0.0,
    "start_at": "2026-10-20",
    "created_at": "2026-10-20T12:19:06",
    "pm_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "project_no": "PR-20261020121905-347413",
    "updated_at": "2026-10-20T12:19:06",
    "contract_id": null,
    "customer_id": null,
    "description": "  STR3_1792469945169_347413  ",
    "project_type": "b2b",
    "our_entity_id": null,
    "owner_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "current_stage_code": "requirement_alignment"
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status",
    "expected": 200,
    "actual": 200,
    "passed": true
  },
  {
    "path": "data.name",
    "type": "json_equals",
    "expected": "STR3_1792469945169_347413",
    "actual": "  STR3_1792469945169_347413  ",
    "passed": false
  },
  {
    "path": "data.description",
    "type": "json_equals",
    "expected": "STR3_1792469945169_347413",
    "actual": "  STR3_1792469945169_347413  ",
    "passed": false
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "failed",
  "missing": [],
  "expected": {
    "name": "STR3_1792469945169_347413",
    "description": "STR3_1792469945169_347413"
  },
  "observed": {
    "name": "  STR3_1792469945169_347413  ",
    "description": "  STR3_1792469945169_347413  "
  },
  "mismatches": {
    "name": {
      "actual": "  STR3_1792469945169_347413  ",
      "expected": "STR3_1792469945169_347413"
    },
    "description": {
      "actual": "  STR3_1792469945169_347413  ",
      "expected": "STR3_1792469945169_347413"
    }
  },
  "read_route": "/project/projects/f1592361-e24c-47d9-9e5f-4ff5a6a0ee09"
}
```
回查字段断言：
```json
[
  {
    "type": "stored_field_equals",
    "path": "name",
    "expected": "STR3_1792469945169_347413",
    "actual": "  STR3_1792469945169_347413  ",
    "passed": false
  },
  {
    "type": "stored_field_equals",
    "path": "description",
    "expected": "STR3_1792469945169_347413",
    "actual": "  STR3_1792469945169_347413  ",
    "passed": false
  }
]
```

### 项目 新增 / 中间空格（用例4279，执行记录20807）
结果：passed；Bug类别：None
请求：POST http://14.103.229.153:15173/api/v1/project/projects
手动字段：name, description

实际输入参数：
```json
{
  "body": {
    "name": "STR3_1792469947121_365056 A B",
    "due_at": "2026-10-30",
    "start_at": "2026-10-20",
    "pm_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "project_no": "PR-20261020121907-365056",
    "description": "STR3_1792469947121_365056 A B",
    "project_type": "b2b"
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "c4a4aa5b-4751-492c-a245-0e2dce964011",
    "name": "STR3_1792469947121_365056 A B",
    "due_at": "2026-10-30",
    "status": "draft",
    "pm_name": "test_user1",
    "progress": 0.0,
    "start_at": "2026-10-20",
    "created_at": "2026-10-20T12:19:08",
    "pm_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "project_no": "PR-20261020121907-365056",
    "updated_at": "2026-10-20T12:19:08",
    "contract_id": null,
    "customer_id": null,
    "description": "STR3_1792469947121_365056 A B",
    "project_type": "b2b",
    "our_entity_id": null,
    "owner_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "current_stage_code": "requirement_alignment"
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status",
    "expected": 200,
    "actual": 200,
    "passed": true
  },
  {
    "path": "data.name",
    "type": "json_equals",
    "expected": "STR3_1792469947121_365056 A B",
    "actual": "STR3_1792469947121_365056 A B",
    "passed": true
  },
  {
    "path": "data.description",
    "type": "json_equals",
    "expected": "STR3_1792469947121_365056 A B",
    "actual": "STR3_1792469947121_365056 A B",
    "passed": true
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "passed",
  "missing": [],
  "expected": {
    "name": "STR3_1792469947121_365056 A B",
    "description": "STR3_1792469947121_365056 A B"
  },
  "observed": {
    "name": "STR3_1792469947121_365056 A B",
    "description": "STR3_1792469947121_365056 A B"
  },
  "mismatches": {},
  "read_route": "/project/projects/c4a4aa5b-4751-492c-a245-0e2dce964011"
}
```
回查字段断言：
```json
[
  {
    "type": "stored_field_equals",
    "path": "name",
    "expected": "STR3_1792469947121_365056 A B",
    "actual": "STR3_1792469947121_365056 A B",
    "passed": true
  },
  {
    "type": "stored_field_equals",
    "path": "description",
    "expected": "STR3_1792469947121_365056 A B",
    "actual": "STR3_1792469947121_365056 A B",
    "passed": true
  }
]
```

### 项目 编辑 / 纯空格（用例4280，执行记录20808）
结果：failed；Bug类别：whitespace_only_saved
请求：PATCH http://14.103.229.153:15173/api/v1/project/projects/2efb27cb-7d26-42bc-89af-3949c79139d3
手动字段：name, description

实际输入参数：
```json
{
  "body": {
    "name": "   ",
    "due_at": "2026-10-30",
    "status": "draft",
    "start_at": "2026-10-20",
    "pm_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "description": "   "
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "2efb27cb-7d26-42bc-89af-3949c79139d3",
    "name": "   ",
    "due_at": "2026-10-30",
    "status": "draft",
    "pm_name": "test_user1",
    "progress": 0.0,
    "start_at": "2026-10-20",
    "created_at": "2026-10-20T12:17:21",
    "pm_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "project_no": "RUN3_PRE_20261020121719",
    "updated_at": "2026-10-20T12:19:10",
    "contract_id": null,
    "customer_id": null,
    "description": "   ",
    "project_type": "b2b",
    "our_entity_id": null,
    "owner_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "current_stage_code": "requirement_alignment"
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status_in",
    "expected": [
      400,
      422
    ],
    "actual": 200,
    "passed": false
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "unexpectedly_saved",
  "missing": [],
  "expected": {
    "name": "   ",
    "description": "   "
  },
  "observed": {
    "name": "   ",
    "description": "   "
  },
  "mismatches": {},
  "read_route": "/project/projects/2efb27cb-7d26-42bc-89af-3949c79139d3",
  "expected_action": "reject_whitespace_without_saving"
}
```

### 项目 编辑 / 首尾空格（用例4281，执行记录20809）
结果：failed；Bug类别：leading_trailing_spaces_not_fully_removed
请求：PATCH http://14.103.229.153:15173/api/v1/project/projects/2efb27cb-7d26-42bc-89af-3949c79139d3
手动字段：name, description

实际输入参数：
```json
{
  "body": {
    "name": "  STR3_1792469951225_967394  ",
    "due_at": "2026-10-30",
    "status": "draft",
    "start_at": "2026-10-20",
    "pm_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "description": "  STR3_1792469951225_967394  "
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "2efb27cb-7d26-42bc-89af-3949c79139d3",
    "name": "  STR3_1792469951225_967394  ",
    "due_at": "2026-10-30",
    "status": "draft",
    "pm_name": "test_user1",
    "progress": 0.0,
    "start_at": "2026-10-20",
    "created_at": "2026-10-20T12:17:21",
    "pm_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "project_no": "RUN3_PRE_20261020121719",
    "updated_at": "2026-10-20T12:19:12",
    "contract_id": null,
    "customer_id": null,
    "description": "  STR3_1792469951225_967394  ",
    "project_type": "b2b",
    "our_entity_id": null,
    "owner_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "current_stage_code": "requirement_alignment"
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status",
    "expected": 200,
    "actual": 200,
    "passed": true
  },
  {
    "path": "data.name",
    "type": "json_equals",
    "expected": "STR3_1792469951225_967394",
    "actual": "  STR3_1792469951225_967394  ",
    "passed": false
  },
  {
    "path": "data.description",
    "type": "json_equals",
    "expected": "STR3_1792469951225_967394",
    "actual": "  STR3_1792469951225_967394  ",
    "passed": false
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "failed",
  "missing": [],
  "expected": {
    "name": "STR3_1792469951225_967394",
    "description": "STR3_1792469951225_967394"
  },
  "observed": {
    "name": "  STR3_1792469951225_967394  ",
    "description": "  STR3_1792469951225_967394  "
  },
  "mismatches": {
    "name": {
      "actual": "  STR3_1792469951225_967394  ",
      "expected": "STR3_1792469951225_967394"
    },
    "description": {
      "actual": "  STR3_1792469951225_967394  ",
      "expected": "STR3_1792469951225_967394"
    }
  },
  "read_route": "/project/projects/2efb27cb-7d26-42bc-89af-3949c79139d3"
}
```
回查字段断言：
```json
[
  {
    "type": "stored_field_equals",
    "path": "name",
    "expected": "STR3_1792469951225_967394",
    "actual": "  STR3_1792469951225_967394  ",
    "passed": false
  },
  {
    "type": "stored_field_equals",
    "path": "description",
    "expected": "STR3_1792469951225_967394",
    "actual": "  STR3_1792469951225_967394  ",
    "passed": false
  }
]
```

### 项目 编辑 / 中间空格（用例4282，执行记录20810）
结果：passed；Bug类别：None
请求：PATCH http://14.103.229.153:15173/api/v1/project/projects/2efb27cb-7d26-42bc-89af-3949c79139d3
手动字段：name, description

实际输入参数：
```json
{
  "body": {
    "name": "STR3_1792469953301_536327 A B",
    "due_at": "2026-10-30",
    "status": "draft",
    "start_at": "2026-10-20",
    "pm_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "description": "STR3_1792469953301_536327 A B"
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "2efb27cb-7d26-42bc-89af-3949c79139d3",
    "name": "STR3_1792469953301_536327 A B",
    "due_at": "2026-10-30",
    "status": "draft",
    "pm_name": "test_user1",
    "progress": 0.0,
    "start_at": "2026-10-20",
    "created_at": "2026-10-20T12:17:21",
    "pm_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "project_no": "RUN3_PRE_20261020121719",
    "updated_at": "2026-10-20T12:19:14",
    "contract_id": null,
    "customer_id": null,
    "description": "STR3_1792469953301_536327 A B",
    "project_type": "b2b",
    "our_entity_id": null,
    "owner_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "current_stage_code": "requirement_alignment"
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status",
    "expected": 200,
    "actual": 200,
    "passed": true
  },
  {
    "path": "data.name",
    "type": "json_equals",
    "expected": "STR3_1792469953301_536327 A B",
    "actual": "STR3_1792469953301_536327 A B",
    "passed": true
  },
  {
    "path": "data.description",
    "type": "json_equals",
    "expected": "STR3_1792469953301_536327 A B",
    "actual": "STR3_1792469953301_536327 A B",
    "passed": true
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "passed",
  "missing": [],
  "expected": {
    "name": "STR3_1792469953301_536327 A B",
    "description": "STR3_1792469953301_536327 A B"
  },
  "observed": {
    "name": "STR3_1792469953301_536327 A B",
    "description": "STR3_1792469953301_536327 A B"
  },
  "mismatches": {},
  "read_route": "/project/projects/2efb27cb-7d26-42bc-89af-3949c79139d3"
}
```
回查字段断言：
```json
[
  {
    "type": "stored_field_equals",
    "path": "name",
    "expected": "STR3_1792469953301_536327 A B",
    "actual": "STR3_1792469953301_536327 A B",
    "passed": true
  },
  {
    "type": "stored_field_equals",
    "path": "description",
    "expected": "STR3_1792469953301_536327 A B",
    "actual": "STR3_1792469953301_536327 A B",
    "passed": true
  }
]
```

### 下架商品 新增 / 纯空格（用例4283，执行记录20811）
结果：failed；Bug类别：whitespace_only_saved
请求：POST http://14.103.229.153:15173/api/v1/beli/products
手动字段：name, description

实际输入参数：
```json
{
  "body": {
    "kind": "physical",
    "name": "   ",
    "price": "1.23",
    "stock": 0,
    "active": false,
    "leave_type": "annual",
    "description": "   "
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "731b5dd4-f291-4e09-ad7c-9703d6e72b29",
    "kind": "physical",
    "name": "   ",
    "price": "1.23",
    "stock": 0,
    "active": false,
    "created_at": "2026-10-20T12:19:18",
    "image_name": null,
    "leave_days": null,
    "leave_type": "annual",
    "updated_at": "2026-10-20T12:19:18",
    "description": "   "
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status_in",
    "expected": [
      400,
      422
    ],
    "actual": 200,
    "passed": false
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "unexpectedly_saved",
  "missing": [],
  "expected": {
    "name": "   ",
    "description": "   "
  },
  "observed": {
    "name": "   ",
    "description": "   "
  },
  "mismatches": {},
  "read_route": "/beli/products",
  "expected_action": "reject_whitespace_without_saving"
}
```

### 下架商品 新增 / 首尾空格（用例4284，执行记录20812）
结果：failed；Bug类别：leading_trailing_spaces_not_fully_removed
请求：POST http://14.103.229.153:15173/api/v1/beli/products
手动字段：name, description

实际输入参数：
```json
{
  "body": {
    "kind": "physical",
    "name": "  STR3_1792469960758_231860  ",
    "price": "1.23",
    "stock": 0,
    "active": false,
    "leave_type": "annual",
    "description": "  STR3_1792469960758_231860  "
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "b6540301-d44a-4824-ad9c-c90db78fcdde",
    "kind": "physical",
    "name": "  STR3_1792469960758_231860  ",
    "price": "1.23",
    "stock": 0,
    "active": false,
    "created_at": "2026-10-20T12:19:22",
    "image_name": null,
    "leave_days": null,
    "leave_type": "annual",
    "updated_at": "2026-10-20T12:19:22",
    "description": "  STR3_1792469960758_231860  "
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status",
    "expected": 200,
    "actual": 200,
    "passed": true
  },
  {
    "path": "data.name",
    "type": "json_equals",
    "expected": "STR3_1792469960758_231860",
    "actual": "  STR3_1792469960758_231860  ",
    "passed": false
  },
  {
    "path": "data.description",
    "type": "json_equals",
    "expected": "STR3_1792469960758_231860",
    "actual": "  STR3_1792469960758_231860  ",
    "passed": false
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "failed",
  "missing": [],
  "expected": {
    "name": "STR3_1792469960758_231860",
    "description": "STR3_1792469960758_231860"
  },
  "observed": {
    "name": "  STR3_1792469960758_231860  ",
    "description": "  STR3_1792469960758_231860  "
  },
  "mismatches": {
    "name": {
      "actual": "  STR3_1792469960758_231860  ",
      "expected": "STR3_1792469960758_231860"
    },
    "description": {
      "actual": "  STR3_1792469960758_231860  ",
      "expected": "STR3_1792469960758_231860"
    }
  },
  "read_route": "/beli/products"
}
```
回查字段断言：
```json
[
  {
    "type": "stored_field_equals",
    "path": "name",
    "expected": "STR3_1792469960758_231860",
    "actual": "  STR3_1792469960758_231860  ",
    "passed": false
  },
  {
    "type": "stored_field_equals",
    "path": "description",
    "expected": "STR3_1792469960758_231860",
    "actual": "  STR3_1792469960758_231860  ",
    "passed": false
  }
]
```

### 下架商品 新增 / 中间空格（用例4285，执行记录20813）
结果：passed；Bug类别：None
请求：POST http://14.103.229.153:15173/api/v1/beli/products
手动字段：name, description

实际输入参数：
```json
{
  "body": {
    "kind": "physical",
    "name": "STR3_1792469963121_645759 A B",
    "price": "1.23",
    "stock": 0,
    "active": false,
    "leave_type": "annual",
    "description": "STR3_1792469963121_645759 A B"
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "dff6027e-2010-4fae-85d2-236e9d42a4e4",
    "kind": "physical",
    "name": "STR3_1792469963121_645759 A B",
    "price": "1.23",
    "stock": 0,
    "active": false,
    "created_at": "2026-10-20T12:19:24",
    "image_name": null,
    "leave_days": null,
    "leave_type": "annual",
    "updated_at": "2026-10-20T12:19:24",
    "description": "STR3_1792469963121_645759 A B"
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status",
    "expected": 200,
    "actual": 200,
    "passed": true
  },
  {
    "path": "data.name",
    "type": "json_equals",
    "expected": "STR3_1792469963121_645759 A B",
    "actual": "STR3_1792469963121_645759 A B",
    "passed": true
  },
  {
    "path": "data.description",
    "type": "json_equals",
    "expected": "STR3_1792469963121_645759 A B",
    "actual": "STR3_1792469963121_645759 A B",
    "passed": true
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "passed",
  "missing": [],
  "expected": {
    "name": "STR3_1792469963121_645759 A B",
    "description": "STR3_1792469963121_645759 A B"
  },
  "observed": {
    "name": "STR3_1792469963121_645759 A B",
    "description": "STR3_1792469963121_645759 A B"
  },
  "mismatches": {},
  "read_route": "/beli/products"
}
```
回查字段断言：
```json
[
  {
    "type": "stored_field_equals",
    "path": "name",
    "expected": "STR3_1792469963121_645759 A B",
    "actual": "STR3_1792469963121_645759 A B",
    "passed": true
  },
  {
    "type": "stored_field_equals",
    "path": "description",
    "expected": "STR3_1792469963121_645759 A B",
    "actual": "STR3_1792469963121_645759 A B",
    "passed": true
  }
]
```

### 下架商品 编辑 / 纯空格（用例4286，执行记录20814）
结果：failed；Bug类别：whitespace_only_saved
请求：PUT http://14.103.229.153:15173/api/v1/beli/products/286574a9-3d90-4dff-85ea-5297def47750
手动字段：name, description

实际输入参数：
```json
{
  "body": {
    "kind": "physical",
    "name": "   ",
    "price": "1.23",
    "stock": 0,
    "active": false,
    "leave_type": "annual",
    "description": "   "
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "286574a9-3d90-4dff-85ea-5297def47750",
    "kind": "physical",
    "name": "   ",
    "price": "1.23",
    "stock": 0,
    "active": false,
    "created_at": "2026-10-20T10:34:35",
    "image_name": null,
    "leave_days": null,
    "leave_type": "annual",
    "updated_at": "2026-10-20T10:34:35",
    "description": "   "
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status_in",
    "expected": [
      400,
      422
    ],
    "actual": 200,
    "passed": false
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "unexpectedly_saved",
  "missing": [],
  "expected": {
    "name": "   ",
    "description": "   "
  },
  "observed": {
    "name": "   ",
    "description": "   "
  },
  "mismatches": {},
  "read_route": "/beli/products",
  "expected_action": "reject_whitespace_without_saving"
}
```

### 下架商品 编辑 / 首尾空格（用例4287，执行记录20815）
结果：failed；Bug类别：leading_trailing_spaces_not_fully_removed
请求：PUT http://14.103.229.153:15173/api/v1/beli/products/286574a9-3d90-4dff-85ea-5297def47750
手动字段：name, description

实际输入参数：
```json
{
  "body": {
    "kind": "physical",
    "name": "  STR3_1792469967191_753675  ",
    "price": "1.23",
    "stock": 0,
    "active": false,
    "leave_type": "annual",
    "description": "  STR3_1792469967191_753675  "
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "286574a9-3d90-4dff-85ea-5297def47750",
    "kind": "physical",
    "name": "  STR3_1792469967191_753675  ",
    "price": "1.23",
    "stock": 0,
    "active": false,
    "created_at": "2026-10-20T10:34:35",
    "image_name": null,
    "leave_days": null,
    "leave_type": "annual",
    "updated_at": "2026-10-20T10:34:35",
    "description": "  STR3_1792469967191_753675  "
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status",
    "expected": 200,
    "actual": 200,
    "passed": true
  },
  {
    "path": "data.name",
    "type": "json_equals",
    "expected": "STR3_1792469967191_753675",
    "actual": "  STR3_1792469967191_753675  ",
    "passed": false
  },
  {
    "path": "data.description",
    "type": "json_equals",
    "expected": "STR3_1792469967191_753675",
    "actual": "  STR3_1792469967191_753675  ",
    "passed": false
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "failed",
  "missing": [],
  "expected": {
    "name": "STR3_1792469967191_753675",
    "description": "STR3_1792469967191_753675"
  },
  "observed": {
    "name": "  STR3_1792469967191_753675  ",
    "description": "  STR3_1792469967191_753675  "
  },
  "mismatches": {
    "name": {
      "actual": "  STR3_1792469967191_753675  ",
      "expected": "STR3_1792469967191_753675"
    },
    "description": {
      "actual": "  STR3_1792469967191_753675  ",
      "expected": "STR3_1792469967191_753675"
    }
  },
  "read_route": "/beli/products"
}
```
回查字段断言：
```json
[
  {
    "type": "stored_field_equals",
    "path": "name",
    "expected": "STR3_1792469967191_753675",
    "actual": "  STR3_1792469967191_753675  ",
    "passed": false
  },
  {
    "type": "stored_field_equals",
    "path": "description",
    "expected": "STR3_1792469967191_753675",
    "actual": "  STR3_1792469967191_753675  ",
    "passed": false
  }
]
```

### 下架商品 编辑 / 中间空格（用例4288，执行记录20816）
结果：passed；Bug类别：None
请求：PUT http://14.103.229.153:15173/api/v1/beli/products/286574a9-3d90-4dff-85ea-5297def47750
手动字段：name, description

实际输入参数：
```json
{
  "body": {
    "kind": "physical",
    "name": "STR3_1792469969259_306021 A B",
    "price": "1.23",
    "stock": 0,
    "active": false,
    "leave_type": "annual",
    "description": "STR3_1792469969259_306021 A B"
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "286574a9-3d90-4dff-85ea-5297def47750",
    "kind": "physical",
    "name": "STR3_1792469969259_306021 A B",
    "price": "1.23",
    "stock": 0,
    "active": false,
    "created_at": "2026-10-20T10:34:35",
    "image_name": null,
    "leave_days": null,
    "leave_type": "annual",
    "updated_at": "2026-10-20T10:34:35",
    "description": "STR3_1792469969259_306021 A B"
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status",
    "expected": 200,
    "actual": 200,
    "passed": true
  },
  {
    "path": "data.name",
    "type": "json_equals",
    "expected": "STR3_1792469969259_306021 A B",
    "actual": "STR3_1792469969259_306021 A B",
    "passed": true
  },
  {
    "path": "data.description",
    "type": "json_equals",
    "expected": "STR3_1792469969259_306021 A B",
    "actual": "STR3_1792469969259_306021 A B",
    "passed": true
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "passed",
  "missing": [],
  "expected": {
    "name": "STR3_1792469969259_306021 A B",
    "description": "STR3_1792469969259_306021 A B"
  },
  "observed": {
    "name": "STR3_1792469969259_306021 A B",
    "description": "STR3_1792469969259_306021 A B"
  },
  "mismatches": {},
  "read_route": "/beli/products"
}
```
回查字段断言：
```json
[
  {
    "type": "stored_field_equals",
    "path": "name",
    "expected": "STR3_1792469969259_306021 A B",
    "actual": "STR3_1792469969259_306021 A B",
    "passed": true
  },
  {
    "type": "stored_field_equals",
    "path": "description",
    "expected": "STR3_1792469969259_306021 A B",
    "actual": "STR3_1792469969259_306021 A B",
    "passed": true
  }
]
```

### 更新日志 新增 / 纯空格（用例4289，执行记录20817）
结果：failed；Bug类别：whitespace_only_saved
请求：POST http://14.103.229.153:15173/api/v1/changelog/entries
手动字段：version, title, content

实际输入参数：
```json
{
  "body": {
    "title": "   ",
    "content": "   ",
    "version": "   "
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "79a30f83-9c63-47de-a7be-6087efd0e14a",
    "title": "   ",
    "version": "   "
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status_in",
    "expected": [
      400,
      422
    ],
    "actual": 200,
    "passed": false
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "unexpectedly_saved",
  "missing": [],
  "expected": {
    "title": "   ",
    "content": "   ",
    "version": "   "
  },
  "observed": {
    "title": "   ",
    "content": "   ",
    "version": "   "
  },
  "mismatches": {},
  "read_route": "/changelog/entries?page_size=100",
  "expected_action": "reject_whitespace_without_saving"
}
```

### 更新日志 新增 / 首尾空格（用例4290，执行记录20818）
结果：failed；Bug类别：leading_trailing_spaces_not_fully_removed
请求：POST http://14.103.229.153:15173/api/v1/changelog/entries
手动字段：version, title, content

实际输入参数：
```json
{
  "body": {
    "title": "  STR3_1792469974262_594374  ",
    "content": "  STR3_1792469974262_594374  ",
    "version": "  STR3_1792469974262_594374  "
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "183480ea-6d40-464d-ba58-fcda910de5be",
    "title": "  STR3_1792469974262_594374  ",
    "version": "  STR3_1792469974262_594374  "
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status",
    "expected": 200,
    "actual": 200,
    "passed": true
  },
  {
    "path": "data.version",
    "type": "json_equals",
    "expected": "STR3_1792469974262_594374",
    "actual": "  STR3_1792469974262_594374  ",
    "passed": false
  },
  {
    "path": "data.title",
    "type": "json_equals",
    "expected": "STR3_1792469974262_594374",
    "actual": "  STR3_1792469974262_594374  ",
    "passed": false
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "failed",
  "missing": [],
  "expected": {
    "title": "STR3_1792469974262_594374",
    "content": "STR3_1792469974262_594374",
    "version": "STR3_1792469974262_594374"
  },
  "observed": {
    "title": "  STR3_1792469974262_594374  ",
    "content": "  STR3_1792469974262_594374  ",
    "version": "  STR3_1792469974262_594374  "
  },
  "mismatches": {
    "title": {
      "actual": "  STR3_1792469974262_594374  ",
      "expected": "STR3_1792469974262_594374"
    },
    "content": {
      "actual": "  STR3_1792469974262_594374  ",
      "expected": "STR3_1792469974262_594374"
    },
    "version": {
      "actual": "  STR3_1792469974262_594374  ",
      "expected": "STR3_1792469974262_594374"
    }
  },
  "read_route": "/changelog/entries?page_size=100"
}
```
回查字段断言：
```json
[
  {
    "type": "stored_field_equals",
    "path": "title",
    "expected": "STR3_1792469974262_594374",
    "actual": "  STR3_1792469974262_594374  ",
    "passed": false
  },
  {
    "type": "stored_field_equals",
    "path": "content",
    "expected": "STR3_1792469974262_594374",
    "actual": "  STR3_1792469974262_594374  ",
    "passed": false
  },
  {
    "type": "stored_field_equals",
    "path": "version",
    "expected": "STR3_1792469974262_594374",
    "actual": "  STR3_1792469974262_594374  ",
    "passed": false
  }
]
```

### 更新日志 新增 / 中间空格（用例4291，执行记录20819）
结果：passed；Bug类别：None
请求：POST http://14.103.229.153:15173/api/v1/changelog/entries
手动字段：version, title, content

实际输入参数：
```json
{
  "body": {
    "title": "STR3_1792469976733_268868 A B",
    "content": "STR3_1792469976733_268868 A B",
    "version": "STR3_1792469976733_268868 A B"
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "58ca9806-1b7c-423e-a4cb-63ef4e4e74c1",
    "title": "STR3_1792469976733_268868 A B",
    "version": "STR3_1792469976733_268868 A B"
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status",
    "expected": 200,
    "actual": 200,
    "passed": true
  },
  {
    "path": "data.version",
    "type": "json_equals",
    "expected": "STR3_1792469976733_268868 A B",
    "actual": "STR3_1792469976733_268868 A B",
    "passed": true
  },
  {
    "path": "data.title",
    "type": "json_equals",
    "expected": "STR3_1792469976733_268868 A B",
    "actual": "STR3_1792469976733_268868 A B",
    "passed": true
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "passed",
  "missing": [],
  "expected": {
    "title": "STR3_1792469976733_268868 A B",
    "content": "STR3_1792469976733_268868 A B",
    "version": "STR3_1792469976733_268868 A B"
  },
  "observed": {
    "title": "STR3_1792469976733_268868 A B",
    "content": "STR3_1792469976733_268868 A B",
    "version": "STR3_1792469976733_268868 A B"
  },
  "mismatches": {},
  "read_route": "/changelog/entries?page_size=100"
}
```
回查字段断言：
```json
[
  {
    "type": "stored_field_equals",
    "path": "title",
    "expected": "STR3_1792469976733_268868 A B",
    "actual": "STR3_1792469976733_268868 A B",
    "passed": true
  },
  {
    "type": "stored_field_equals",
    "path": "content",
    "expected": "STR3_1792469976733_268868 A B",
    "actual": "STR3_1792469976733_268868 A B",
    "passed": true
  },
  {
    "type": "stored_field_equals",
    "path": "version",
    "expected": "STR3_1792469976733_268868 A B",
    "actual": "STR3_1792469976733_268868 A B",
    "passed": true
  }
]
```

### 更新日志 编辑 / 纯空格（用例4292，执行记录20820）
结果：failed；Bug类别：whitespace_only_saved
请求：PATCH http://14.103.229.153:15173/api/v1/changelog/entries/1b38374d-fc46-43a6-9a3a-885e174d45a3
手动字段：version, title, content

实际输入参数：
```json
{
  "body": {
    "title": "   ",
    "content": "   ",
    "version": "   "
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "1b38374d-fc46-43a6-9a3a-885e174d45a3",
    "title": "   ",
    "version": "   "
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status_in",
    "expected": [
      400,
      422
    ],
    "actual": 200,
    "passed": false
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "unexpectedly_saved",
  "missing": [],
  "expected": {
    "title": "   ",
    "content": "   ",
    "version": "   "
  },
  "observed": {
    "title": "   ",
    "content": "   ",
    "version": "   "
  },
  "mismatches": {},
  "read_route": "/changelog/entries?page_size=100",
  "expected_action": "reject_whitespace_without_saving"
}
```

### 更新日志 编辑 / 首尾空格（用例4293，执行记录20821）
结果：failed；Bug类别：leading_trailing_spaces_not_fully_removed
请求：PATCH http://14.103.229.153:15173/api/v1/changelog/entries/1b38374d-fc46-43a6-9a3a-885e174d45a3
手动字段：version, title, content

实际输入参数：
```json
{
  "body": {
    "title": "  STR3_1792469980137_879913  ",
    "content": "  STR3_1792469980137_879913  ",
    "version": "  STR3_1792469980137_879913  "
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "1b38374d-fc46-43a6-9a3a-885e174d45a3",
    "title": "  STR3_1792469980137_879913  ",
    "version": "  STR3_1792469980137_879913  "
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status",
    "expected": 200,
    "actual": 200,
    "passed": true
  },
  {
    "path": "data.version",
    "type": "json_equals",
    "expected": "STR3_1792469980137_879913",
    "actual": "  STR3_1792469980137_879913  ",
    "passed": false
  },
  {
    "path": "data.title",
    "type": "json_equals",
    "expected": "STR3_1792469980137_879913",
    "actual": "  STR3_1792469980137_879913  ",
    "passed": false
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "failed",
  "missing": [],
  "expected": {
    "title": "STR3_1792469980137_879913",
    "content": "STR3_1792469980137_879913",
    "version": "STR3_1792469980137_879913"
  },
  "observed": {
    "title": "  STR3_1792469980137_879913  ",
    "content": "  STR3_1792469980137_879913  ",
    "version": "  STR3_1792469980137_879913  "
  },
  "mismatches": {
    "title": {
      "actual": "  STR3_1792469980137_879913  ",
      "expected": "STR3_1792469980137_879913"
    },
    "content": {
      "actual": "  STR3_1792469980137_879913  ",
      "expected": "STR3_1792469980137_879913"
    },
    "version": {
      "actual": "  STR3_1792469980137_879913  ",
      "expected": "STR3_1792469980137_879913"
    }
  },
  "read_route": "/changelog/entries?page_size=100"
}
```
回查字段断言：
```json
[
  {
    "type": "stored_field_equals",
    "path": "title",
    "expected": "STR3_1792469980137_879913",
    "actual": "  STR3_1792469980137_879913  ",
    "passed": false
  },
  {
    "type": "stored_field_equals",
    "path": "content",
    "expected": "STR3_1792469980137_879913",
    "actual": "  STR3_1792469980137_879913  ",
    "passed": false
  },
  {
    "type": "stored_field_equals",
    "path": "version",
    "expected": "STR3_1792469980137_879913",
    "actual": "  STR3_1792469980137_879913  ",
    "passed": false
  }
]
```

### 更新日志 编辑 / 中间空格（用例4294，执行记录20822）
结果：passed；Bug类别：None
请求：PATCH http://14.103.229.153:15173/api/v1/changelog/entries/1b38374d-fc46-43a6-9a3a-885e174d45a3
手动字段：version, title, content

实际输入参数：
```json
{
  "body": {
    "title": "STR3_1792469981732_585779 A B",
    "content": "STR3_1792469981732_585779 A B",
    "version": "STR3_1792469981732_585779 A B"
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "1b38374d-fc46-43a6-9a3a-885e174d45a3",
    "title": "STR3_1792469981732_585779 A B",
    "version": "STR3_1792469981732_585779 A B"
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status",
    "expected": 200,
    "actual": 200,
    "passed": true
  },
  {
    "path": "data.version",
    "type": "json_equals",
    "expected": "STR3_1792469981732_585779 A B",
    "actual": "STR3_1792469981732_585779 A B",
    "passed": true
  },
  {
    "path": "data.title",
    "type": "json_equals",
    "expected": "STR3_1792469981732_585779 A B",
    "actual": "STR3_1792469981732_585779 A B",
    "passed": true
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "passed",
  "missing": [],
  "expected": {
    "title": "STR3_1792469981732_585779 A B",
    "content": "STR3_1792469981732_585779 A B",
    "version": "STR3_1792469981732_585779 A B"
  },
  "observed": {
    "title": "STR3_1792469981732_585779 A B",
    "content": "STR3_1792469981732_585779 A B",
    "version": "STR3_1792469981732_585779 A B"
  },
  "mismatches": {},
  "read_route": "/changelog/entries?page_size=100"
}
```
回查字段断言：
```json
[
  {
    "type": "stored_field_equals",
    "path": "title",
    "expected": "STR3_1792469981732_585779 A B",
    "actual": "STR3_1792469981732_585779 A B",
    "passed": true
  },
  {
    "type": "stored_field_equals",
    "path": "content",
    "expected": "STR3_1792469981732_585779 A B",
    "actual": "STR3_1792469981732_585779 A B",
    "passed": true
  },
  {
    "type": "stored_field_equals",
    "path": "version",
    "expected": "STR3_1792469981732_585779 A B",
    "actual": "STR3_1792469981732_585779 A B",
    "passed": true
  }
]
```

### 非业务会议 新增 / 纯空格（用例4295，执行记录20823）
结果：failed；Bug类别：whitespace_only_saved
请求：POST http://14.103.229.153:15173/api/v1/meeting/records
手动字段：title

实际输入参数：
```json
{
  "body": {
    "title": "   ",
    "meeting_date": "2026-10-15",
    "meeting_type": "project"
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "f35bfb34-be54-4eee-b7ac-5a1b86634cff",
    "title": "   ",
    "status": "transcribed",
    "created_at": "2026-10-20T12:19:45",
    "meeting_date": "2026-10-15",
    "meeting_type": "project"
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status_in",
    "expected": [
      400,
      422
    ],
    "actual": 200,
    "passed": false
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "unexpectedly_saved",
  "missing": [],
  "expected": {
    "title": "   "
  },
  "observed": {
    "title": "   "
  },
  "mismatches": {},
  "read_route": "/meeting/records/f35bfb34-be54-4eee-b7ac-5a1b86634cff",
  "expected_action": "reject_whitespace_without_saving"
}
```

### 非业务会议 新增 / 首尾空格（用例4296，执行记录20824）
结果：failed；Bug类别：leading_trailing_spaces_not_fully_removed
请求：POST http://14.103.229.153:15173/api/v1/meeting/records
手动字段：title

实际输入参数：
```json
{
  "body": {
    "title": "  STR3_1792469986088_649231  ",
    "meeting_date": "2026-10-15",
    "meeting_type": "project"
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "bde8f654-41c6-4c2d-9da2-2833671cc1b7",
    "title": "  STR3_1792469986088_649231  ",
    "status": "transcribed",
    "created_at": "2026-10-20T12:19:47",
    "meeting_date": "2026-10-15",
    "meeting_type": "project"
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status",
    "expected": 200,
    "actual": 200,
    "passed": true
  },
  {
    "path": "data.title",
    "type": "json_equals",
    "expected": "STR3_1792469986088_649231",
    "actual": "  STR3_1792469986088_649231  ",
    "passed": false
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "failed",
  "missing": [],
  "expected": {
    "title": "STR3_1792469986088_649231"
  },
  "observed": {
    "title": "  STR3_1792469986088_649231  "
  },
  "mismatches": {
    "title": {
      "actual": "  STR3_1792469986088_649231  ",
      "expected": "STR3_1792469986088_649231"
    }
  },
  "read_route": "/meeting/records/bde8f654-41c6-4c2d-9da2-2833671cc1b7"
}
```
回查字段断言：
```json
[
  {
    "type": "stored_field_equals",
    "path": "title",
    "expected": "STR3_1792469986088_649231",
    "actual": "  STR3_1792469986088_649231  ",
    "passed": false
  }
]
```

### 非业务会议 新增 / 中间空格（用例4297，执行记录20825）
结果：passed；Bug类别：None
请求：POST http://14.103.229.153:15173/api/v1/meeting/records
手动字段：title

实际输入参数：
```json
{
  "body": {
    "title": "STR3_1792469987661_190770 A B",
    "meeting_date": "2026-10-15",
    "meeting_type": "project"
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "6332a71f-d9c3-4a88-8a43-65b67e5558ca",
    "title": "STR3_1792469987661_190770 A B",
    "status": "transcribed",
    "created_at": "2026-10-20T12:19:48",
    "meeting_date": "2026-10-15",
    "meeting_type": "project"
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status",
    "expected": 200,
    "actual": 200,
    "passed": true
  },
  {
    "path": "data.title",
    "type": "json_equals",
    "expected": "STR3_1792469987661_190770 A B",
    "actual": "STR3_1792469987661_190770 A B",
    "passed": true
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "passed",
  "missing": [],
  "expected": {
    "title": "STR3_1792469987661_190770 A B"
  },
  "observed": {
    "title": "STR3_1792469987661_190770 A B"
  },
  "mismatches": {},
  "read_route": "/meeting/records/6332a71f-d9c3-4a88-8a43-65b67e5558ca"
}
```
回查字段断言：
```json
[
  {
    "type": "stored_field_equals",
    "path": "title",
    "expected": "STR3_1792469987661_190770 A B",
    "actual": "STR3_1792469987661_190770 A B",
    "passed": true
  }
]
```

### 独立财务账户 新增 / 纯空格（用例4301，执行记录20826）
结果：failed；Bug类别：whitespace_only_saved
请求：POST http://14.103.229.153:15173/api/v1/finance/accounts
手动字段：account_name, bank_name, bank_branch

实际输入参数：
```json
{
  "body": {
    "currency": "CNY",
    "bank_name": "   ",
    "entity_id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
    "account_no": "6222000012345678",
    "is_default": false,
    "bank_branch": "   ",
    "account_name": "   ",
    "initial_balance": 0,
    "account_category": "public"
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "72104f7f-202f-4b2d-ae52-686949108588",
    "status": "active",
    "balance": 0,
    "currency": "CNY",
    "bank_name": "   ",
    "entity_id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
    "created_at": "2026-10-20T12:19:50",
    "is_default": false,
    "bank_branch": "   ",
    "account_name": "   ",
    "initial_balance": "0.00",
    "account_category": "public",
    "account_no_masked": "************5678",
    "shareholder_user_id": null
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status_in",
    "expected": [
      400,
      422
    ],
    "actual": 200,
    "passed": false
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "unexpectedly_saved",
  "missing": [],
  "expected": {
    "bank_name": "   ",
    "bank_branch": "   ",
    "account_name": "   "
  },
  "observed": {
    "bank_name": "   ",
    "bank_branch": "   ",
    "account_name": "   "
  },
  "mismatches": {},
  "read_route": "/finance/accounts?page_size=200",
  "expected_action": "reject_whitespace_without_saving"
}
```

### 独立财务账户 新增 / 首尾空格（用例4302，执行记录20827）
结果：failed；Bug类别：leading_trailing_spaces_not_fully_removed
请求：POST http://14.103.229.153:15173/api/v1/finance/accounts
手动字段：account_name, bank_name, bank_branch

实际输入参数：
```json
{
  "body": {
    "currency": "CNY",
    "bank_name": "  STR3_1792469991412_205069  ",
    "entity_id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
    "account_no": "6222000012345678",
    "is_default": false,
    "bank_branch": "  STR3_1792469991412_205069  ",
    "account_name": "  STR3_1792469991412_205069  ",
    "initial_balance": 0,
    "account_category": "public"
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "18662416-79b1-4d1b-b5b8-999330f9f1d8",
    "status": "active",
    "balance": 0,
    "currency": "CNY",
    "bank_name": "  STR3_1792469991412_205069  ",
    "entity_id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
    "created_at": "2026-10-20T12:19:52",
    "is_default": false,
    "bank_branch": "  STR3_1792469991412_205069  ",
    "account_name": "  STR3_1792469991412_205069  ",
    "initial_balance": "0.00",
    "account_category": "public",
    "account_no_masked": "************5678",
    "shareholder_user_id": null
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status",
    "expected": 200,
    "actual": 200,
    "passed": true
  },
  {
    "path": "data.account_name",
    "type": "json_equals",
    "expected": "STR3_1792469991412_205069",
    "actual": "  STR3_1792469991412_205069  ",
    "passed": false
  },
  {
    "path": "data.bank_name",
    "type": "json_equals",
    "expected": "STR3_1792469991412_205069",
    "actual": "  STR3_1792469991412_205069  ",
    "passed": false
  },
  {
    "path": "data.bank_branch",
    "type": "json_equals",
    "expected": "STR3_1792469991412_205069",
    "actual": "  STR3_1792469991412_205069  ",
    "passed": false
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "failed",
  "missing": [],
  "expected": {
    "bank_name": "STR3_1792469991412_205069",
    "bank_branch": "STR3_1792469991412_205069",
    "account_name": "STR3_1792469991412_205069"
  },
  "observed": {
    "bank_name": "  STR3_1792469991412_205069  ",
    "bank_branch": "  STR3_1792469991412_205069  ",
    "account_name": "  STR3_1792469991412_205069  "
  },
  "mismatches": {
    "bank_name": {
      "actual": "  STR3_1792469991412_205069  ",
      "expected": "STR3_1792469991412_205069"
    },
    "bank_branch": {
      "actual": "  STR3_1792469991412_205069  ",
      "expected": "STR3_1792469991412_205069"
    },
    "account_name": {
      "actual": "  STR3_1792469991412_205069  ",
      "expected": "STR3_1792469991412_205069"
    }
  },
  "read_route": "/finance/accounts?page_size=200"
}
```
回查字段断言：
```json
[
  {
    "type": "stored_field_equals",
    "path": "bank_name",
    "expected": "STR3_1792469991412_205069",
    "actual": "  STR3_1792469991412_205069  ",
    "passed": false
  },
  {
    "type": "stored_field_equals",
    "path": "bank_branch",
    "expected": "STR3_1792469991412_205069",
    "actual": "  STR3_1792469991412_205069  ",
    "passed": false
  },
  {
    "type": "stored_field_equals",
    "path": "account_name",
    "expected": "STR3_1792469991412_205069",
    "actual": "  STR3_1792469991412_205069  ",
    "passed": false
  }
]
```

### 独立财务账户 新增 / 中间空格（用例4303，执行记录20828）
结果：passed；Bug类别：None
请求：POST http://14.103.229.153:15173/api/v1/finance/accounts
手动字段：account_name, bank_name, bank_branch

实际输入参数：
```json
{
  "body": {
    "currency": "CNY",
    "bank_name": "STR3_1792469993124_726739 A B",
    "entity_id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
    "account_no": "6222000012345678",
    "is_default": false,
    "bank_branch": "STR3_1792469993124_726739 A B",
    "account_name": "STR3_1792469993124_726739 A B",
    "initial_balance": 0,
    "account_category": "public"
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "5e79eb8a-0602-4246-91be-e9f9cacc7f61",
    "status": "active",
    "balance": 0,
    "currency": "CNY",
    "bank_name": "STR3_1792469993124_726739 A B",
    "entity_id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
    "created_at": "2026-10-20T12:19:54",
    "is_default": false,
    "bank_branch": "STR3_1792469993124_726739 A B",
    "account_name": "STR3_1792469993124_726739 A B",
    "initial_balance": "0.00",
    "account_category": "public",
    "account_no_masked": "************5678",
    "shareholder_user_id": null
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status",
    "expected": 200,
    "actual": 200,
    "passed": true
  },
  {
    "path": "data.account_name",
    "type": "json_equals",
    "expected": "STR3_1792469993124_726739 A B",
    "actual": "STR3_1792469993124_726739 A B",
    "passed": true
  },
  {
    "path": "data.bank_name",
    "type": "json_equals",
    "expected": "STR3_1792469993124_726739 A B",
    "actual": "STR3_1792469993124_726739 A B",
    "passed": true
  },
  {
    "path": "data.bank_branch",
    "type": "json_equals",
    "expected": "STR3_1792469993124_726739 A B",
    "actual": "STR3_1792469993124_726739 A B",
    "passed": true
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "passed",
  "missing": [],
  "expected": {
    "bank_name": "STR3_1792469993124_726739 A B",
    "bank_branch": "STR3_1792469993124_726739 A B",
    "account_name": "STR3_1792469993124_726739 A B"
  },
  "observed": {
    "bank_name": "STR3_1792469993124_726739 A B",
    "bank_branch": "STR3_1792469993124_726739 A B",
    "account_name": "STR3_1792469993124_726739 A B"
  },
  "mismatches": {},
  "read_route": "/finance/accounts?page_size=200"
}
```
回查字段断言：
```json
[
  {
    "type": "stored_field_equals",
    "path": "bank_name",
    "expected": "STR3_1792469993124_726739 A B",
    "actual": "STR3_1792469993124_726739 A B",
    "passed": true
  },
  {
    "type": "stored_field_equals",
    "path": "bank_branch",
    "expected": "STR3_1792469993124_726739 A B",
    "actual": "STR3_1792469993124_726739 A B",
    "passed": true
  },
  {
    "type": "stored_field_equals",
    "path": "account_name",
    "expected": "STR3_1792469993124_726739 A B",
    "actual": "STR3_1792469993124_726739 A B",
    "passed": true
  }
]
```

### 独立财务账户 编辑 / 纯空格（用例4304，执行记录20829）
结果：failed；Bug类别：whitespace_only_saved
请求：PATCH http://14.103.229.153:15173/api/v1/finance/accounts/b9ae50dc-9fef-474c-93e2-738b84b21f77
手动字段：account_name, bank_name, bank_branch

实际输入参数：
```json
{
  "body": {
    "status": "active",
    "currency": "CNY",
    "bank_name": "   ",
    "entity_id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
    "account_no": "6222000012345678",
    "is_default": false,
    "bank_branch": "   ",
    "account_name": "   ",
    "initial_balance": 0,
    "account_category": "public"
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "b9ae50dc-9fef-474c-93e2-738b84b21f77",
    "status": "active",
    "balance": 0,
    "currency": "CNY",
    "bank_name": "   ",
    "entity_id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
    "created_at": "2026-10-20T10:39:05",
    "is_default": false,
    "bank_branch": "   ",
    "account_name": "   ",
    "initial_balance": "0.00",
    "account_category": "public",
    "account_no_masked": "************5678",
    "shareholder_user_id": null
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status_in",
    "expected": [
      400,
      422
    ],
    "actual": 200,
    "passed": false
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "unexpectedly_saved",
  "missing": [],
  "expected": {
    "bank_name": "   ",
    "bank_branch": "   ",
    "account_name": "   "
  },
  "observed": {
    "bank_name": "   ",
    "bank_branch": "   ",
    "account_name": "   "
  },
  "mismatches": {},
  "read_route": "/finance/accounts?page_size=200",
  "expected_action": "reject_whitespace_without_saving"
}
```

### 独立财务账户 编辑 / 首尾空格（用例4305，执行记录20830）
结果：failed；Bug类别：leading_trailing_spaces_not_fully_removed
请求：PATCH http://14.103.229.153:15173/api/v1/finance/accounts/b9ae50dc-9fef-474c-93e2-738b84b21f77
手动字段：account_name, bank_name, bank_branch

实际输入参数：
```json
{
  "body": {
    "status": "active",
    "currency": "CNY",
    "bank_name": "  STR3_1792469997430_800351  ",
    "entity_id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
    "account_no": "6222000012345678",
    "is_default": false,
    "bank_branch": "  STR3_1792469997430_800351  ",
    "account_name": "  STR3_1792469997430_800351  ",
    "initial_balance": 0,
    "account_category": "public"
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "b9ae50dc-9fef-474c-93e2-738b84b21f77",
    "status": "active",
    "balance": 0,
    "currency": "CNY",
    "bank_name": "  STR3_1792469997430_800351  ",
    "entity_id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
    "created_at": "2026-10-20T10:39:05",
    "is_default": false,
    "bank_branch": "  STR3_1792469997430_800351  ",
    "account_name": "  STR3_1792469997430_800351  ",
    "initial_balance": "0.00",
    "account_category": "public",
    "account_no_masked": "************5678",
    "shareholder_user_id": null
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status",
    "expected": 200,
    "actual": 200,
    "passed": true
  },
  {
    "path": "data.account_name",
    "type": "json_equals",
    "expected": "STR3_1792469997430_800351",
    "actual": "  STR3_1792469997430_800351  ",
    "passed": false
  },
  {
    "path": "data.bank_name",
    "type": "json_equals",
    "expected": "STR3_1792469997430_800351",
    "actual": "  STR3_1792469997430_800351  ",
    "passed": false
  },
  {
    "path": "data.bank_branch",
    "type": "json_equals",
    "expected": "STR3_1792469997430_800351",
    "actual": "  STR3_1792469997430_800351  ",
    "passed": false
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "failed",
  "missing": [],
  "expected": {
    "bank_name": "STR3_1792469997430_800351",
    "bank_branch": "STR3_1792469997430_800351",
    "account_name": "STR3_1792469997430_800351"
  },
  "observed": {
    "bank_name": "  STR3_1792469997430_800351  ",
    "bank_branch": "  STR3_1792469997430_800351  ",
    "account_name": "  STR3_1792469997430_800351  "
  },
  "mismatches": {
    "bank_name": {
      "actual": "  STR3_1792469997430_800351  ",
      "expected": "STR3_1792469997430_800351"
    },
    "bank_branch": {
      "actual": "  STR3_1792469997430_800351  ",
      "expected": "STR3_1792469997430_800351"
    },
    "account_name": {
      "actual": "  STR3_1792469997430_800351  ",
      "expected": "STR3_1792469997430_800351"
    }
  },
  "read_route": "/finance/accounts?page_size=200"
}
```
回查字段断言：
```json
[
  {
    "type": "stored_field_equals",
    "path": "bank_name",
    "expected": "STR3_1792469997430_800351",
    "actual": "  STR3_1792469997430_800351  ",
    "passed": false
  },
  {
    "type": "stored_field_equals",
    "path": "bank_branch",
    "expected": "STR3_1792469997430_800351",
    "actual": "  STR3_1792469997430_800351  ",
    "passed": false
  },
  {
    "type": "stored_field_equals",
    "path": "account_name",
    "expected": "STR3_1792469997430_800351",
    "actual": "  STR3_1792469997430_800351  ",
    "passed": false
  }
]
```

### 独立财务账户 编辑 / 中间空格（用例4306，执行记录20831）
结果：passed；Bug类别：None
请求：PATCH http://14.103.229.153:15173/api/v1/finance/accounts/b9ae50dc-9fef-474c-93e2-738b84b21f77
手动字段：account_name, bank_name, bank_branch

实际输入参数：
```json
{
  "body": {
    "status": "active",
    "currency": "CNY",
    "bank_name": "STR3_1792469999377_700911 A B",
    "entity_id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
    "account_no": "6222000012345678",
    "is_default": false,
    "bank_branch": "STR3_1792469999377_700911 A B",
    "account_name": "STR3_1792469999377_700911 A B",
    "initial_balance": 0,
    "account_category": "public"
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "b9ae50dc-9fef-474c-93e2-738b84b21f77",
    "status": "active",
    "balance": 0,
    "currency": "CNY",
    "bank_name": "STR3_1792469999377_700911 A B",
    "entity_id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
    "created_at": "2026-10-20T10:39:05",
    "is_default": false,
    "bank_branch": "STR3_1792469999377_700911 A B",
    "account_name": "STR3_1792469999377_700911 A B",
    "initial_balance": "0.00",
    "account_category": "public",
    "account_no_masked": "************5678",
    "shareholder_user_id": null
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status",
    "expected": 200,
    "actual": 200,
    "passed": true
  },
  {
    "path": "data.account_name",
    "type": "json_equals",
    "expected": "STR3_1792469999377_700911 A B",
    "actual": "STR3_1792469999377_700911 A B",
    "passed": true
  },
  {
    "path": "data.bank_name",
    "type": "json_equals",
    "expected": "STR3_1792469999377_700911 A B",
    "actual": "STR3_1792469999377_700911 A B",
    "passed": true
  },
  {
    "path": "data.bank_branch",
    "type": "json_equals",
    "expected": "STR3_1792469999377_700911 A B",
    "actual": "STR3_1792469999377_700911 A B",
    "passed": true
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "passed",
  "missing": [],
  "expected": {
    "bank_name": "STR3_1792469999377_700911 A B",
    "bank_branch": "STR3_1792469999377_700911 A B",
    "account_name": "STR3_1792469999377_700911 A B"
  },
  "observed": {
    "bank_name": "STR3_1792469999377_700911 A B",
    "bank_branch": "STR3_1792469999377_700911 A B",
    "account_name": "STR3_1792469999377_700911 A B"
  },
  "mismatches": {},
  "read_route": "/finance/accounts?page_size=200"
}
```
回查字段断言：
```json
[
  {
    "type": "stored_field_equals",
    "path": "bank_name",
    "expected": "STR3_1792469999377_700911 A B",
    "actual": "STR3_1792469999377_700911 A B",
    "passed": true
  },
  {
    "type": "stored_field_equals",
    "path": "bank_branch",
    "expected": "STR3_1792469999377_700911 A B",
    "actual": "STR3_1792469999377_700911 A B",
    "passed": true
  },
  {
    "type": "stored_field_equals",
    "path": "account_name",
    "expected": "STR3_1792469999377_700911 A B",
    "actual": "STR3_1792469999377_700911 A B",
    "passed": true
  }
]
```

### 未对账测试交易 新增 / 纯空格（用例4310，执行记录20832）
结果：failed；Bug类别：whitespace_only_saved
请求：POST http://14.103.229.153:15173/api/v1/finance/transactions
手动字段：purpose

实际输入参数：
```json
{
  "body": {
    "amount": "1.00",
    "purpose": "   ",
    "currency": "CNY",
    "txn_date": "2026-10-20",
    "txn_type": "receipt",
    "account_id": "b9ae50dc-9fef-474c-93e2-738b84b21f77",
    "our_entity_id": "b8a068ff-298d-40de-aede-4e9893dd6024",
    "txn_direction": "in",
    "counterparty_id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
    "reconcile_status": "unreconciled"
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "b2b2e395-59ab-416d-a287-15e741b56d08",
    "amount": "1.00",
    "voided": false,
    "purpose": "   ",
    "currency": "CNY",
    "txn_date": "2026-10-20",
    "txn_type": "receipt",
    "account_id": "b9ae50dc-9fef-474c-93e2-738b84b21f77",
    "created_at": "2026-10-20T12:20:02",
    "attachments": [],
    "contract_id": null,
    "our_entity_id": "b8a068ff-298d-40de-aede-4e9893dd6024",
    "txn_direction": "in",
    "counterparty_id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
    "employee_user_id": null,
    "reconcile_status": "unreconciled",
    "related_object_id": null,
    "created_by_user_id": "bdae2ab7-d19e-4976-b662-a300627c1179",
    "related_object_type": null
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status_in",
    "expected": [
      400,
      422
    ],
    "actual": 200,
    "passed": false
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "unexpectedly_saved",
  "missing": [],
  "expected": {
    "purpose": "   "
  },
  "observed": {
    "purpose": "   "
  },
  "mismatches": {},
  "read_route": "/finance/transactions/b2b2e395-59ab-416d-a287-15e741b56d08",
  "expected_action": "reject_whitespace_without_saving"
}
```

### 未对账测试交易 新增 / 首尾空格（用例4311，执行记录20833）
结果：failed；Bug类别：leading_trailing_spaces_not_fully_removed
请求：POST http://14.103.229.153:15173/api/v1/finance/transactions
手动字段：purpose

实际输入参数：
```json
{
  "body": {
    "amount": "1.00",
    "purpose": "  STR3_1792470002974_111608  ",
    "currency": "CNY",
    "txn_date": "2026-10-20",
    "txn_type": "receipt",
    "account_id": "b9ae50dc-9fef-474c-93e2-738b84b21f77",
    "our_entity_id": "b8a068ff-298d-40de-aede-4e9893dd6024",
    "txn_direction": "in",
    "counterparty_id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
    "reconcile_status": "unreconciled"
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "eb33ddd2-44f3-4a38-9df6-3c4d3c8e59f8",
    "amount": "1.00",
    "voided": false,
    "purpose": "  STR3_1792470002974_111608  ",
    "currency": "CNY",
    "txn_date": "2026-10-20",
    "txn_type": "receipt",
    "account_id": "b9ae50dc-9fef-474c-93e2-738b84b21f77",
    "created_at": "2026-10-20T12:20:04",
    "attachments": [],
    "contract_id": null,
    "our_entity_id": "b8a068ff-298d-40de-aede-4e9893dd6024",
    "txn_direction": "in",
    "counterparty_id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
    "employee_user_id": null,
    "reconcile_status": "unreconciled",
    "related_object_id": null,
    "created_by_user_id": "bdae2ab7-d19e-4976-b662-a300627c1179",
    "related_object_type": null
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status",
    "expected": 200,
    "actual": 200,
    "passed": true
  },
  {
    "path": "data.purpose",
    "type": "json_equals",
    "expected": "STR3_1792470002974_111608",
    "actual": "  STR3_1792470002974_111608  ",
    "passed": false
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "failed",
  "missing": [],
  "expected": {
    "purpose": "STR3_1792470002974_111608"
  },
  "observed": {
    "purpose": "  STR3_1792470002974_111608  "
  },
  "mismatches": {
    "purpose": {
      "actual": "  STR3_1792470002974_111608  ",
      "expected": "STR3_1792470002974_111608"
    }
  },
  "read_route": "/finance/transactions/eb33ddd2-44f3-4a38-9df6-3c4d3c8e59f8"
}
```
回查字段断言：
```json
[
  {
    "type": "stored_field_equals",
    "path": "purpose",
    "expected": "STR3_1792470002974_111608",
    "actual": "  STR3_1792470002974_111608  ",
    "passed": false
  }
]
```

### 未对账测试交易 新增 / 中间空格（用例4312，执行记录20834）
结果：passed；Bug类别：None
请求：POST http://14.103.229.153:15173/api/v1/finance/transactions
手动字段：purpose

实际输入参数：
```json
{
  "body": {
    "amount": "1.00",
    "purpose": "STR3_1792470004662_312724 A B",
    "currency": "CNY",
    "txn_date": "2026-10-20",
    "txn_type": "receipt",
    "account_id": "b9ae50dc-9fef-474c-93e2-738b84b21f77",
    "our_entity_id": "b8a068ff-298d-40de-aede-4e9893dd6024",
    "txn_direction": "in",
    "counterparty_id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
    "reconcile_status": "unreconciled"
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "3dabb4c3-e9f1-44b7-9db4-752cf3417845",
    "amount": "1.00",
    "voided": false,
    "purpose": "STR3_1792470004662_312724 A B",
    "currency": "CNY",
    "txn_date": "2026-10-20",
    "txn_type": "receipt",
    "account_id": "b9ae50dc-9fef-474c-93e2-738b84b21f77",
    "created_at": "2026-10-20T12:20:05",
    "attachments": [],
    "contract_id": null,
    "our_entity_id": "b8a068ff-298d-40de-aede-4e9893dd6024",
    "txn_direction": "in",
    "counterparty_id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
    "employee_user_id": null,
    "reconcile_status": "unreconciled",
    "related_object_id": null,
    "created_by_user_id": "bdae2ab7-d19e-4976-b662-a300627c1179",
    "related_object_type": null
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status",
    "expected": 200,
    "actual": 200,
    "passed": true
  },
  {
    "path": "data.purpose",
    "type": "json_equals",
    "expected": "STR3_1792470004662_312724 A B",
    "actual": "STR3_1792470004662_312724 A B",
    "passed": true
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "passed",
  "missing": [],
  "expected": {
    "purpose": "STR3_1792470004662_312724 A B"
  },
  "observed": {
    "purpose": "STR3_1792470004662_312724 A B"
  },
  "mismatches": {},
  "read_route": "/finance/transactions/3dabb4c3-e9f1-44b7-9db4-752cf3417845"
}
```
回查字段断言：
```json
[
  {
    "type": "stored_field_equals",
    "path": "purpose",
    "expected": "STR3_1792470004662_312724 A B",
    "actual": "STR3_1792470004662_312724 A B",
    "passed": true
  }
]
```

### 未对账测试交易 编辑 / 纯空格（用例4313，执行记录20835）
结果：failed；Bug类别：whitespace_only_saved
请求：PATCH http://14.103.229.153:15173/api/v1/finance/transactions/7c031496-7dc3-4dcb-b3cb-bc44a29d94e2
手动字段：purpose

实际输入参数：
```json
{
  "body": {
    "amount": "1.00",
    "purpose": "   ",
    "txn_date": "2026-10-20",
    "txn_type": "receipt",
    "txn_direction": "in",
    "counterparty_id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
    "reconcile_status": "unreconciled"
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "7c031496-7dc3-4dcb-b3cb-bc44a29d94e2",
    "amount": "1.00",
    "voided": false,
    "purpose": "   ",
    "currency": "CNY",
    "txn_date": "2026-10-20",
    "txn_type": "receipt",
    "account_id": "b9ae50dc-9fef-474c-93e2-738b84b21f77",
    "created_at": "2026-10-20T10:42:06",
    "attachments": [],
    "contract_id": null,
    "our_entity_id": "b8a068ff-298d-40de-aede-4e9893dd6024",
    "txn_direction": "in",
    "counterparty_id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
    "employee_user_id": null,
    "reconcile_status": "unreconciled",
    "related_object_id": null,
    "created_by_user_id": "bdae2ab7-d19e-4976-b662-a300627c1179",
    "related_object_type": null
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status_in",
    "expected": [
      400,
      422
    ],
    "actual": 200,
    "passed": false
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "unexpectedly_saved",
  "missing": [],
  "expected": {
    "purpose": "   "
  },
  "observed": {
    "purpose": "   "
  },
  "mismatches": {},
  "read_route": "/finance/transactions/7c031496-7dc3-4dcb-b3cb-bc44a29d94e2",
  "expected_action": "reject_whitespace_without_saving"
}
```

### 未对账测试交易 编辑 / 首尾空格（用例4314，执行记录20836）
结果：failed；Bug类别：leading_trailing_spaces_not_fully_removed
请求：PATCH http://14.103.229.153:15173/api/v1/finance/transactions/7c031496-7dc3-4dcb-b3cb-bc44a29d94e2
手动字段：purpose

实际输入参数：
```json
{
  "body": {
    "amount": "1.00",
    "purpose": "  STR3_1792470008797_497577  ",
    "txn_date": "2026-10-20",
    "txn_type": "receipt",
    "txn_direction": "in",
    "counterparty_id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
    "reconcile_status": "unreconciled"
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "7c031496-7dc3-4dcb-b3cb-bc44a29d94e2",
    "amount": "1.00",
    "voided": false,
    "purpose": "  STR3_1792470008797_497577  ",
    "currency": "CNY",
    "txn_date": "2026-10-20",
    "txn_type": "receipt",
    "account_id": "b9ae50dc-9fef-474c-93e2-738b84b21f77",
    "created_at": "2026-10-20T10:42:06",
    "attachments": [],
    "contract_id": null,
    "our_entity_id": "b8a068ff-298d-40de-aede-4e9893dd6024",
    "txn_direction": "in",
    "counterparty_id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
    "employee_user_id": null,
    "reconcile_status": "unreconciled",
    "related_object_id": null,
    "created_by_user_id": "bdae2ab7-d19e-4976-b662-a300627c1179",
    "related_object_type": null
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status",
    "expected": 200,
    "actual": 200,
    "passed": true
  },
  {
    "path": "data.purpose",
    "type": "json_equals",
    "expected": "STR3_1792470008797_497577",
    "actual": "  STR3_1792470008797_497577  ",
    "passed": false
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "failed",
  "missing": [],
  "expected": {
    "purpose": "STR3_1792470008797_497577"
  },
  "observed": {
    "purpose": "  STR3_1792470008797_497577  "
  },
  "mismatches": {
    "purpose": {
      "actual": "  STR3_1792470008797_497577  ",
      "expected": "STR3_1792470008797_497577"
    }
  },
  "read_route": "/finance/transactions/7c031496-7dc3-4dcb-b3cb-bc44a29d94e2"
}
```
回查字段断言：
```json
[
  {
    "type": "stored_field_equals",
    "path": "purpose",
    "expected": "STR3_1792470008797_497577",
    "actual": "  STR3_1792470008797_497577  ",
    "passed": false
  }
]
```

### 未对账测试交易 编辑 / 中间空格（用例4315，执行记录20837）
结果：passed；Bug类别：None
请求：PATCH http://14.103.229.153:15173/api/v1/finance/transactions/7c031496-7dc3-4dcb-b3cb-bc44a29d94e2
手动字段：purpose

实际输入参数：
```json
{
  "body": {
    "amount": "1.00",
    "purpose": "STR3_1792470010465_447622 A B",
    "txn_date": "2026-10-20",
    "txn_type": "receipt",
    "txn_direction": "in",
    "counterparty_id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
    "reconcile_status": "unreconciled"
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "7c031496-7dc3-4dcb-b3cb-bc44a29d94e2",
    "amount": "1.00",
    "voided": false,
    "purpose": "STR3_1792470010465_447622 A B",
    "currency": "CNY",
    "txn_date": "2026-10-20",
    "txn_type": "receipt",
    "account_id": "b9ae50dc-9fef-474c-93e2-738b84b21f77",
    "created_at": "2026-10-20T10:42:06",
    "attachments": [],
    "contract_id": null,
    "our_entity_id": "b8a068ff-298d-40de-aede-4e9893dd6024",
    "txn_direction": "in",
    "counterparty_id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
    "employee_user_id": null,
    "reconcile_status": "unreconciled",
    "related_object_id": null,
    "created_by_user_id": "bdae2ab7-d19e-4976-b662-a300627c1179",
    "related_object_type": null
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status",
    "expected": 200,
    "actual": 200,
    "passed": true
  },
  {
    "path": "data.purpose",
    "type": "json_equals",
    "expected": "STR3_1792470010465_447622 A B",
    "actual": "STR3_1792470010465_447622 A B",
    "passed": true
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "passed",
  "missing": [],
  "expected": {
    "purpose": "STR3_1792470010465_447622 A B"
  },
  "observed": {
    "purpose": "STR3_1792470010465_447622 A B"
  },
  "mismatches": {},
  "read_route": "/finance/transactions/7c031496-7dc3-4dcb-b3cb-bc44a29d94e2"
}
```
回查字段断言：
```json
[
  {
    "type": "stored_field_equals",
    "path": "purpose",
    "expected": "STR3_1792470010465_447622 A B",
    "actual": "STR3_1792470010465_447622 A B",
    "passed": true
  }
]
```

### 草稿合同 新增 / 纯空格（用例4316，执行记录20838）
结果：failed；Bug类别：whitespace_only_saved
请求：POST http://14.103.229.153:15173/api/v1/contract/contracts
手动字段：name

实际输入参数：
```json
{
  "body": {
    "name": "   ",
    "currency": "CNY",
    "sign_date": "2026-10-20",
    "party_a_id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
    "party_b_id": "48b300fe-5582-4edc-af68-5af147e2567e",
    "pm_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "contract_no": "CNT-1792470012042-409565",
    "expire_date": "2026-10-30",
    "amount_total": "1.00",
    "contract_type": "sales",
    "payment_plans": [],
    "effective_date": "2026-10-20"
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "dda5f74e-c2ea-448b-b6db-a4364f052879",
    "name": "   ",
    "status": "draft",
    "summary": null,
    "currency": "CNY",
    "sign_date": "2026-10-20",
    "created_at": "2026-10-20T12:20:13",
    "party_a_id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
    "party_b_id": "48b300fe-5582-4edc-af68-5af147e2567e",
    "party_c_id": null,
    "pm_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "updated_at": "2026-10-20T12:20:13",
    "attachments": [],
    "contract_no": "CNT-1792470012042-409565",
    "expire_date": "2026-10-30",
    "amount_total": "1.00",
    "contract_type": "sales",
    "owner_user_id": "bdae2ab7-d19e-4976-b662-a300627c1179",
    "effective_date": "2026-10-20",
    "pending_amount": "1.00"
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status_in",
    "expected": [
      400,
      422
    ],
    "actual": 200,
    "passed": false
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "unexpectedly_saved",
  "missing": [],
  "expected": {
    "name": "   "
  },
  "observed": {
    "name": "   "
  },
  "mismatches": {},
  "read_route": "/contract/contracts/dda5f74e-c2ea-448b-b6db-a4364f052879",
  "expected_action": "reject_whitespace_without_saving"
}
```

### 草稿合同 新增 / 首尾空格（用例4317，执行记录20839）
结果：failed；Bug类别：leading_trailing_spaces_not_fully_removed
请求：POST http://14.103.229.153:15173/api/v1/contract/contracts
手动字段：name

实际输入参数：
```json
{
  "body": {
    "name": "  STR3_1792470013646_827504  ",
    "currency": "CNY",
    "sign_date": "2026-10-20",
    "party_a_id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
    "party_b_id": "48b300fe-5582-4edc-af68-5af147e2567e",
    "pm_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "contract_no": "CNT-1792470013646-827504",
    "expire_date": "2026-10-30",
    "amount_total": "1.00",
    "contract_type": "sales",
    "payment_plans": [],
    "effective_date": "2026-10-20"
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "74ea80f9-dc72-4ba6-9d33-8cbdf01c934a",
    "name": "  STR3_1792470013646_827504  ",
    "status": "draft",
    "summary": null,
    "currency": "CNY",
    "sign_date": "2026-10-20",
    "created_at": "2026-10-20T12:20:14",
    "party_a_id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
    "party_b_id": "48b300fe-5582-4edc-af68-5af147e2567e",
    "party_c_id": null,
    "pm_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "updated_at": "2026-10-20T12:20:14",
    "attachments": [],
    "contract_no": "CNT-1792470013646-827504",
    "expire_date": "2026-10-30",
    "amount_total": "1.00",
    "contract_type": "sales",
    "owner_user_id": "bdae2ab7-d19e-4976-b662-a300627c1179",
    "effective_date": "2026-10-20",
    "pending_amount": "1.00"
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status",
    "expected": 200,
    "actual": 200,
    "passed": true
  },
  {
    "path": "data.name",
    "type": "json_equals",
    "expected": "STR3_1792470013646_827504",
    "actual": "  STR3_1792470013646_827504  ",
    "passed": false
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "failed",
  "missing": [],
  "expected": {
    "name": "STR3_1792470013646_827504"
  },
  "observed": {
    "name": "  STR3_1792470013646_827504  "
  },
  "mismatches": {
    "name": {
      "actual": "  STR3_1792470013646_827504  ",
      "expected": "STR3_1792470013646_827504"
    }
  },
  "read_route": "/contract/contracts/74ea80f9-dc72-4ba6-9d33-8cbdf01c934a"
}
```
回查字段断言：
```json
[
  {
    "type": "stored_field_equals",
    "path": "name",
    "expected": "STR3_1792470013646_827504",
    "actual": "  STR3_1792470013646_827504  ",
    "passed": false
  }
]
```

### 草稿合同 新增 / 中间空格（用例4318，执行记录20840）
结果：passed；Bug类别：None
请求：POST http://14.103.229.153:15173/api/v1/contract/contracts
手动字段：name

实际输入参数：
```json
{
  "body": {
    "name": "STR3_1792470015216_143717 A B",
    "currency": "CNY",
    "sign_date": "2026-10-20",
    "party_a_id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
    "party_b_id": "48b300fe-5582-4edc-af68-5af147e2567e",
    "pm_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "contract_no": "CNT-1792470015216-143717",
    "expire_date": "2026-10-30",
    "amount_total": "1.00",
    "contract_type": "sales",
    "payment_plans": [],
    "effective_date": "2026-10-20"
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "8306f490-7701-4717-acb9-666aa4f18390",
    "name": "STR3_1792470015216_143717 A B",
    "status": "draft",
    "summary": null,
    "currency": "CNY",
    "sign_date": "2026-10-20",
    "created_at": "2026-10-20T12:20:16",
    "party_a_id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
    "party_b_id": "48b300fe-5582-4edc-af68-5af147e2567e",
    "party_c_id": null,
    "pm_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "updated_at": "2026-10-20T12:20:16",
    "attachments": [],
    "contract_no": "CNT-1792470015216-143717",
    "expire_date": "2026-10-30",
    "amount_total": "1.00",
    "contract_type": "sales",
    "owner_user_id": "bdae2ab7-d19e-4976-b662-a300627c1179",
    "effective_date": "2026-10-20",
    "pending_amount": "1.00"
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status",
    "expected": 200,
    "actual": 200,
    "passed": true
  },
  {
    "path": "data.name",
    "type": "json_equals",
    "expected": "STR3_1792470015216_143717 A B",
    "actual": "STR3_1792470015216_143717 A B",
    "passed": true
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "passed",
  "missing": [],
  "expected": {
    "name": "STR3_1792470015216_143717 A B"
  },
  "observed": {
    "name": "STR3_1792470015216_143717 A B"
  },
  "mismatches": {},
  "read_route": "/contract/contracts/8306f490-7701-4717-acb9-666aa4f18390"
}
```
回查字段断言：
```json
[
  {
    "type": "stored_field_equals",
    "path": "name",
    "expected": "STR3_1792470015216_143717 A B",
    "actual": "STR3_1792470015216_143717 A B",
    "passed": true
  }
]
```

### 草稿合同 编辑 / 纯空格（用例4319，执行记录20841）
结果：failed；Bug类别：whitespace_only_saved
请求：PATCH http://14.103.229.153:15173/api/v1/contract/contracts/b38b3128-d32d-4adf-9d0d-8ff4d1f8ded1
手动字段：name

实际输入参数：
```json
{
  "body": {
    "name": "   ",
    "status": "draft",
    "currency": "CNY",
    "sign_date": "2026-10-20",
    "party_a_id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
    "party_b_id": "48b300fe-5582-4edc-af68-5af147e2567e",
    "pm_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "expire_date": "2026-10-30",
    "amount_total": "1.00",
    "contract_type": "sales",
    "effective_date": "2026-10-20"
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "b38b3128-d32d-4adf-9d0d-8ff4d1f8ded1",
    "name": "   ",
    "status": "draft",
    "summary": "STR3_1792467673841_138472 A B",
    "currency": "CNY",
    "sign_date": "2026-10-20",
    "created_at": "2026-10-20T10:44:08",
    "party_a_id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
    "party_b_id": "48b300fe-5582-4edc-af68-5af147e2567e",
    "party_c_id": null,
    "pm_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "updated_at": "2026-10-20T12:20:19",
    "attachments": [],
    "contract_no": "STR3_1792467673841_138472 A B",
    "expire_date": "2026-10-30",
    "amount_total": "1.00",
    "contract_type": "sales",
    "owner_user_id": "bdae2ab7-d19e-4976-b662-a300627c1179",
    "effective_date": "2026-10-20",
    "pending_amount": "1.00"
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status_in",
    "expected": [
      400,
      422
    ],
    "actual": 200,
    "passed": false
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "unexpectedly_saved",
  "missing": [],
  "expected": {
    "name": "   "
  },
  "observed": {
    "name": "   "
  },
  "mismatches": {},
  "read_route": "/contract/contracts/b38b3128-d32d-4adf-9d0d-8ff4d1f8ded1",
  "expected_action": "reject_whitespace_without_saving"
}
```

### 草稿合同 编辑 / 首尾空格（用例4320，执行记录20842）
结果：failed；Bug类别：leading_trailing_spaces_not_fully_removed
请求：PATCH http://14.103.229.153:15173/api/v1/contract/contracts/b38b3128-d32d-4adf-9d0d-8ff4d1f8ded1
手动字段：name

实际输入参数：
```json
{
  "body": {
    "name": "  STR3_1792470019728_652056  ",
    "status": "draft",
    "currency": "CNY",
    "sign_date": "2026-10-20",
    "party_a_id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
    "party_b_id": "48b300fe-5582-4edc-af68-5af147e2567e",
    "pm_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "expire_date": "2026-10-30",
    "amount_total": "1.00",
    "contract_type": "sales",
    "effective_date": "2026-10-20"
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "b38b3128-d32d-4adf-9d0d-8ff4d1f8ded1",
    "name": "  STR3_1792470019728_652056  ",
    "status": "draft",
    "summary": "STR3_1792467673841_138472 A B",
    "currency": "CNY",
    "sign_date": "2026-10-20",
    "created_at": "2026-10-20T10:44:08",
    "party_a_id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
    "party_b_id": "48b300fe-5582-4edc-af68-5af147e2567e",
    "party_c_id": null,
    "pm_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "updated_at": "2026-10-20T12:20:20",
    "attachments": [],
    "contract_no": "STR3_1792467673841_138472 A B",
    "expire_date": "2026-10-30",
    "amount_total": "1.00",
    "contract_type": "sales",
    "owner_user_id": "bdae2ab7-d19e-4976-b662-a300627c1179",
    "effective_date": "2026-10-20",
    "pending_amount": "1.00"
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status",
    "expected": 200,
    "actual": 200,
    "passed": true
  },
  {
    "path": "data.name",
    "type": "json_equals",
    "expected": "STR3_1792470019728_652056",
    "actual": "  STR3_1792470019728_652056  ",
    "passed": false
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "failed",
  "missing": [],
  "expected": {
    "name": "STR3_1792470019728_652056"
  },
  "observed": {
    "name": "  STR3_1792470019728_652056  "
  },
  "mismatches": {
    "name": {
      "actual": "  STR3_1792470019728_652056  ",
      "expected": "STR3_1792470019728_652056"
    }
  },
  "read_route": "/contract/contracts/b38b3128-d32d-4adf-9d0d-8ff4d1f8ded1"
}
```
回查字段断言：
```json
[
  {
    "type": "stored_field_equals",
    "path": "name",
    "expected": "STR3_1792470019728_652056",
    "actual": "  STR3_1792470019728_652056  ",
    "passed": false
  }
]
```

### 草稿合同 编辑 / 中间空格（用例4321，执行记录20843）
结果：passed；Bug类别：None
请求：PATCH http://14.103.229.153:15173/api/v1/contract/contracts/b38b3128-d32d-4adf-9d0d-8ff4d1f8ded1
手动字段：name

实际输入参数：
```json
{
  "body": {
    "name": "STR3_1792470021350_542053 A B",
    "status": "draft",
    "currency": "CNY",
    "sign_date": "2026-10-20",
    "party_a_id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
    "party_b_id": "48b300fe-5582-4edc-af68-5af147e2567e",
    "pm_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "expire_date": "2026-10-30",
    "amount_total": "1.00",
    "contract_type": "sales",
    "effective_date": "2026-10-20"
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "b38b3128-d32d-4adf-9d0d-8ff4d1f8ded1",
    "name": "STR3_1792470021350_542053 A B",
    "status": "draft",
    "summary": "STR3_1792467673841_138472 A B",
    "currency": "CNY",
    "sign_date": "2026-10-20",
    "created_at": "2026-10-20T10:44:08",
    "party_a_id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
    "party_b_id": "48b300fe-5582-4edc-af68-5af147e2567e",
    "party_c_id": null,
    "pm_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "updated_at": "2026-10-20T12:20:22",
    "attachments": [],
    "contract_no": "STR3_1792467673841_138472 A B",
    "expire_date": "2026-10-30",
    "amount_total": "1.00",
    "contract_type": "sales",
    "owner_user_id": "bdae2ab7-d19e-4976-b662-a300627c1179",
    "effective_date": "2026-10-20",
    "pending_amount": "1.00"
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status",
    "expected": 200,
    "actual": 200,
    "passed": true
  },
  {
    "path": "data.name",
    "type": "json_equals",
    "expected": "STR3_1792470021350_542053 A B",
    "actual": "STR3_1792470021350_542053 A B",
    "passed": true
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "passed",
  "missing": [],
  "expected": {
    "name": "STR3_1792470021350_542053 A B"
  },
  "observed": {
    "name": "STR3_1792470021350_542053 A B"
  },
  "mismatches": {},
  "read_route": "/contract/contracts/b38b3128-d32d-4adf-9d0d-8ff4d1f8ded1"
}
```
回查字段断言：
```json
[
  {
    "type": "stored_field_equals",
    "path": "name",
    "expected": "STR3_1792470021350_542053 A B",
    "actual": "STR3_1792470021350_542053 A B",
    "passed": true
  }
]
```

### 待批请假（有效额度重测） 新增 / 纯空格（用例4322，执行记录20844）
结果：failed；Bug类别：whitespace_only_saved
请求：POST http://14.103.229.153:15173/api/v1/todo/leaves
手动字段：reason

实际输入参数：
```json
{
  "body": {
    "end_at": "2026-10-22T17:00:00+08:00",
    "reason": "   ",
    "start_at": "2026-10-22T13:00:00+08:00",
    "leave_type": "annual"
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "4101dd0e-7a00-4d40-93cd-2c4285bf49b5",
    "end_at": "2026-10-22T17:00:00",
    "reason": "   ",
    "status": "pending",
    "start_at": "2026-10-22T13:00:00",
    "created_at": "2026-10-20T12:20:24",
    "leave_type": "annual",
    "updated_at": "2026-10-20T12:20:24",
    "approved_at": null,
    "our_entity_id": "14efc508-797d-4a29-b359-3d5b51424a84",
    "applicant_name": "test_user3",
    "review_comment": null,
    "applicant_user_id": "640d1a5c-bff5-4df0-9e02-cb42f8b46413",
    "approved_by_user_id": null
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status_in",
    "expected": [
      400,
      422
    ],
    "actual": 200,
    "passed": false
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "unexpectedly_saved",
  "missing": [],
  "expected": {
    "reason": "   "
  },
  "observed": {
    "reason": "   "
  },
  "mismatches": {},
  "read_route": "/todo/leaves/my?page_size=100",
  "expected_action": "reject_whitespace_without_saving"
}
```

### 待批请假（有效额度重测） 新增 / 首尾空格（用例4323，执行记录20845）
结果：failed；Bug类别：leading_trailing_spaces_not_fully_removed
请求：POST http://14.103.229.153:15173/api/v1/todo/leaves
手动字段：reason

实际输入参数：
```json
{
  "body": {
    "end_at": "2026-10-22T17:00:00+08:00",
    "reason": "  STR3_1792470024561_846979  ",
    "start_at": "2026-10-22T13:00:00+08:00",
    "leave_type": "annual"
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "70e88291-38e5-4682-9048-92164600595d",
    "end_at": "2026-10-22T17:00:00",
    "reason": "  STR3_1792470024561_846979  ",
    "status": "pending",
    "start_at": "2026-10-22T13:00:00",
    "created_at": "2026-10-20T12:20:25",
    "leave_type": "annual",
    "updated_at": "2026-10-20T12:20:25",
    "approved_at": null,
    "our_entity_id": "14efc508-797d-4a29-b359-3d5b51424a84",
    "applicant_name": "test_user3",
    "review_comment": null,
    "applicant_user_id": "640d1a5c-bff5-4df0-9e02-cb42f8b46413",
    "approved_by_user_id": null
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status",
    "expected": 200,
    "actual": 200,
    "passed": true
  },
  {
    "path": "data.reason",
    "type": "json_equals",
    "expected": "STR3_1792470024561_846979",
    "actual": "  STR3_1792470024561_846979  ",
    "passed": false
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "failed",
  "missing": [],
  "expected": {
    "reason": "STR3_1792470024561_846979"
  },
  "observed": {
    "reason": "  STR3_1792470024561_846979  "
  },
  "mismatches": {
    "reason": {
      "actual": "  STR3_1792470024561_846979  ",
      "expected": "STR3_1792470024561_846979"
    }
  },
  "read_route": "/todo/leaves/my?page_size=100"
}
```
回查字段断言：
```json
[
  {
    "type": "stored_field_equals",
    "path": "reason",
    "expected": "STR3_1792470024561_846979",
    "actual": "  STR3_1792470024561_846979  ",
    "passed": false
  }
]
```

### 待批请假（有效额度重测） 新增 / 中间空格（用例4324，执行记录20846）
结果：passed；Bug类别：None
请求：POST http://14.103.229.153:15173/api/v1/todo/leaves
手动字段：reason

实际输入参数：
```json
{
  "body": {
    "end_at": "2026-10-22T17:00:00+08:00",
    "reason": "STR3_1792470026256_412025 A B",
    "start_at": "2026-10-22T13:00:00+08:00",
    "leave_type": "annual"
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "ce2b0c9a-8cb7-416e-9c0f-614db583c68e",
    "end_at": "2026-10-22T17:00:00",
    "reason": "STR3_1792470026256_412025 A B",
    "status": "pending",
    "start_at": "2026-10-22T13:00:00",
    "created_at": "2026-10-20T12:20:27",
    "leave_type": "annual",
    "updated_at": "2026-10-20T12:20:27",
    "approved_at": null,
    "our_entity_id": "14efc508-797d-4a29-b359-3d5b51424a84",
    "applicant_name": "test_user3",
    "review_comment": null,
    "applicant_user_id": "640d1a5c-bff5-4df0-9e02-cb42f8b46413",
    "approved_by_user_id": null
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status",
    "expected": 200,
    "actual": 200,
    "passed": true
  },
  {
    "path": "data.reason",
    "type": "json_equals",
    "expected": "STR3_1792470026256_412025 A B",
    "actual": "STR3_1792470026256_412025 A B",
    "passed": true
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "passed",
  "missing": [],
  "expected": {
    "reason": "STR3_1792470026256_412025 A B"
  },
  "observed": {
    "reason": "STR3_1792470026256_412025 A B"
  },
  "mismatches": {},
  "read_route": "/todo/leaves/my?page_size=100"
}
```
回查字段断言：
```json
[
  {
    "type": "stored_field_equals",
    "path": "reason",
    "expected": "STR3_1792470026256_412025 A B",
    "actual": "STR3_1792470026256_412025 A B",
    "passed": true
  }
]
```

### 项目阶段 编辑 / 纯空格（用例4325，执行记录20847）
结果：failed；Bug类别：whitespace_only_saved
请求：PATCH http://14.103.229.153:15173/api/v1/project/projects/2efb27cb-7d26-42bc-89af-3949c79139d3/stages/915f954c-9c9b-485a-a555-1756e298e6a9
手动字段：deliverables

实际输入参数：
```json
{
  "body": {
    "status": "not_started",
    "deliverables": "   ",
    "feature_list": "[]",
    "planned_end_at": "2026-10-30",
    "planned_start_at": "2026-10-20"
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "915f954c-9c9b-485a-a555-1756e298e6a9",
    "status": "not_started",
    "created_at": "2026-10-20T12:17:21",
    "project_id": "2efb27cb-7d26-42bc-89af-3949c79139d3",
    "stage_code": "requirement_alignment",
    "stage_name": "需求对齐",
    "attachments": [],
    "sequence_no": 1,
    "skip_reason": null,
    "deliverables": "   ",
    "feature_list": "[]",
    "actual_end_at": null,
    "blocked_reason": null,
    "planned_end_at": "2026-10-30",
    "actual_start_at": null,
    "planned_start_at": "2026-10-20"
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status_in",
    "expected": [
      400,
      422
    ],
    "actual": 200,
    "passed": false
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "unexpectedly_saved",
  "missing": [],
  "expected": {
    "deliverables": "   "
  },
  "observed": {
    "deliverables": "   "
  },
  "mismatches": {},
  "read_route": "/project/projects/2efb27cb-7d26-42bc-89af-3949c79139d3/stages",
  "expected_action": "reject_whitespace_without_saving"
}
```

### 项目阶段 编辑 / 首尾空格（用例4326，执行记录20848）
结果：failed；Bug类别：leading_trailing_spaces_not_fully_removed
请求：PATCH http://14.103.229.153:15173/api/v1/project/projects/2efb27cb-7d26-42bc-89af-3949c79139d3/stages/915f954c-9c9b-485a-a555-1756e298e6a9
手动字段：deliverables

实际输入参数：
```json
{
  "body": {
    "status": "not_started",
    "deliverables": "  STR3_1792470031036_333691  ",
    "feature_list": "[]",
    "planned_end_at": "2026-10-30",
    "planned_start_at": "2026-10-20"
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "915f954c-9c9b-485a-a555-1756e298e6a9",
    "status": "not_started",
    "created_at": "2026-10-20T12:17:21",
    "project_id": "2efb27cb-7d26-42bc-89af-3949c79139d3",
    "stage_code": "requirement_alignment",
    "stage_name": "需求对齐",
    "attachments": [],
    "sequence_no": 1,
    "skip_reason": null,
    "deliverables": "  STR3_1792470031036_333691  ",
    "feature_list": "[]",
    "actual_end_at": null,
    "blocked_reason": null,
    "planned_end_at": "2026-10-30",
    "actual_start_at": null,
    "planned_start_at": "2026-10-20"
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status",
    "expected": 200,
    "actual": 200,
    "passed": true
  },
  {
    "path": "data.deliverables",
    "type": "json_equals",
    "expected": "STR3_1792470031036_333691",
    "actual": "  STR3_1792470031036_333691  ",
    "passed": false
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "failed",
  "missing": [],
  "expected": {
    "deliverables": "STR3_1792470031036_333691"
  },
  "observed": {
    "deliverables": "  STR3_1792470031036_333691  "
  },
  "mismatches": {
    "deliverables": {
      "actual": "  STR3_1792470031036_333691  ",
      "expected": "STR3_1792470031036_333691"
    }
  },
  "read_route": "/project/projects/2efb27cb-7d26-42bc-89af-3949c79139d3/stages"
}
```
回查字段断言：
```json
[
  {
    "type": "stored_field_equals",
    "path": "deliverables",
    "expected": "STR3_1792470031036_333691",
    "actual": "  STR3_1792470031036_333691  ",
    "passed": false
  }
]
```

### 项目阶段 编辑 / 中间空格（用例4327，执行记录20849）
结果：passed；Bug类别：None
请求：PATCH http://14.103.229.153:15173/api/v1/project/projects/2efb27cb-7d26-42bc-89af-3949c79139d3/stages/915f954c-9c9b-485a-a555-1756e298e6a9
手动字段：deliverables

实际输入参数：
```json
{
  "body": {
    "status": "not_started",
    "deliverables": "STR3_1792470032659_223383 A B",
    "feature_list": "[]",
    "planned_end_at": "2026-10-30",
    "planned_start_at": "2026-10-20"
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "915f954c-9c9b-485a-a555-1756e298e6a9",
    "status": "not_started",
    "created_at": "2026-10-20T12:17:21",
    "project_id": "2efb27cb-7d26-42bc-89af-3949c79139d3",
    "stage_code": "requirement_alignment",
    "stage_name": "需求对齐",
    "attachments": [],
    "sequence_no": 1,
    "skip_reason": null,
    "deliverables": "STR3_1792470032659_223383 A B",
    "feature_list": "[]",
    "actual_end_at": null,
    "blocked_reason": null,
    "planned_end_at": "2026-10-30",
    "actual_start_at": null,
    "planned_start_at": "2026-10-20"
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status",
    "expected": 200,
    "actual": 200,
    "passed": true
  },
  {
    "path": "data.deliverables",
    "type": "json_equals",
    "expected": "STR3_1792470032659_223383 A B",
    "actual": "STR3_1792470032659_223383 A B",
    "passed": true
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "passed",
  "missing": [],
  "expected": {
    "deliverables": "STR3_1792470032659_223383 A B"
  },
  "observed": {
    "deliverables": "STR3_1792470032659_223383 A B"
  },
  "mismatches": {},
  "read_route": "/project/projects/2efb27cb-7d26-42bc-89af-3949c79139d3/stages"
}
```
回查字段断言：
```json
[
  {
    "type": "stored_field_equals",
    "path": "deliverables",
    "expected": "STR3_1792470032659_223383 A B",
    "actual": "STR3_1792470032659_223383 A B",
    "passed": true
  }
]
```

### 项目任务计划 编辑 / 纯空格（用例4328，执行记录20853）
结果：passed；Bug类别：None
请求：POST http://14.103.229.153:15173/api/v1/project/projects/2efb27cb-7d26-42bc-89af-3949c79139d3/todos/1376784f-7e16-45e4-877d-6aec114eaafb/plan
手动字段：title, description

实际输入参数：
```json
{
  "body": {
    "title": "   ",
    "due_at": "2026-10-23T18:00:00+08:00",
    "dev_type": "dev_backend",
    "priority": "p2",
    "description": "   ",
    "estimated_hours": 0,
    "assignee_user_id": "640d1a5c-bff5-4df0-9e02-cb42f8b46413"
  },
  "query": {}
}
```
实际返回：HTTP 400
```json
{
  "code": 400,
  "errors": null,
  "message": "Task title cannot be empty"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status_in",
    "expected": [
      400,
      422
    ],
    "actual": 400,
    "passed": true
  }
]
```

### 项目任务计划 编辑 / 首尾空格（用例4329，执行记录20854）
结果：failed；Bug类别：leading_trailing_spaces_not_fully_removed
请求：POST http://14.103.229.153:15173/api/v1/project/projects/2efb27cb-7d26-42bc-89af-3949c79139d3/todos/1376784f-7e16-45e4-877d-6aec114eaafb/plan
手动字段：title, description

实际输入参数：
```json
{
  "body": {
    "title": "  STR3_1792470161000_214033  ",
    "due_at": "2026-10-23T18:00:00+08:00",
    "dev_type": "dev_backend",
    "priority": "p2",
    "description": "  STR3_1792470161000_214033  ",
    "estimated_hours": 0,
    "assignee_user_id": "640d1a5c-bff5-4df0-9e02-cb42f8b46413"
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "1376784f-7e16-45e4-877d-6aec114eaafb",
    "link": {
      "dev_type": "dev_backend",
      "project_id": "2efb27cb-7d26-42bc-89af-3949c79139d3",
      "project_name": "RUN3_PRE_20261020121719 project",
      "reviewer_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9"
    },
    "tags": [
      "dev_backend"
    ],
    "title": "STR3_1792470161000_214033",
    "due_at": "2026-10-23T18:00:00",
    "status": "open",
    "done_at": null,
    "priority": "p2",
    "start_at": null,
    "created_at": "2026-10-20T12:17:22",
    "updated_at": "2026-10-20T12:22:42",
    "description": "  STR3_1792470161000_214033  ",
    "creator_name": "test_user1",
    "submitted_at": null,
    "assignee_name": "test_user3",
    "reviewer_name": "test_user1",
    "blocked_reason": null,
    "dismiss_reason": null,
    "review_comment": null,
    "creator_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "estimated_hours": "0.00",
    "assignee_user_id": "640d1a5c-bff5-4df0-9e02-cb42f8b46413",
    "reviewed_by_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9"
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status",
    "expected": 200,
    "actual": 200,
    "passed": true
  },
  {
    "path": "data.title",
    "type": "json_equals",
    "expected": "STR3_1792470161000_214033",
    "actual": "STR3_1792470161000_214033",
    "passed": true
  },
  {
    "path": "data.description",
    "type": "json_equals",
    "expected": "STR3_1792470161000_214033",
    "actual": "  STR3_1792470161000_214033  ",
    "passed": false
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "failed",
  "missing": [],
  "expected": {
    "title": "STR3_1792470161000_214033",
    "description": "STR3_1792470161000_214033"
  },
  "observed": {
    "title": "STR3_1792470161000_214033",
    "description": "  STR3_1792470161000_214033  "
  },
  "mismatches": {
    "description": {
      "actual": "  STR3_1792470161000_214033  ",
      "expected": "STR3_1792470161000_214033"
    }
  },
  "read_route": "/todo/1376784f-7e16-45e4-877d-6aec114eaafb"
}
```
回查字段断言：
```json
[
  {
    "type": "stored_field_equals",
    "path": "title",
    "expected": "STR3_1792470161000_214033",
    "actual": "STR3_1792470161000_214033",
    "passed": true
  },
  {
    "type": "stored_field_equals",
    "path": "description",
    "expected": "STR3_1792470161000_214033",
    "actual": "  STR3_1792470161000_214033  ",
    "passed": false
  }
]
```

### 项目任务计划 编辑 / 中间空格（用例4330，执行记录20855）
结果：passed；Bug类别：None
请求：POST http://14.103.229.153:15173/api/v1/project/projects/2efb27cb-7d26-42bc-89af-3949c79139d3/todos/1376784f-7e16-45e4-877d-6aec114eaafb/plan
手动字段：title, description

实际输入参数：
```json
{
  "body": {
    "title": "STR3_1792470162628_783859 A B",
    "due_at": "2026-10-23T18:00:00+08:00",
    "dev_type": "dev_backend",
    "priority": "p2",
    "description": "STR3_1792470162628_783859 A B",
    "estimated_hours": 0,
    "assignee_user_id": "640d1a5c-bff5-4df0-9e02-cb42f8b46413"
  },
  "query": {}
}
```
实际返回：HTTP 200
```json
{
  "code": 0,
  "data": {
    "id": "1376784f-7e16-45e4-877d-6aec114eaafb",
    "link": {
      "dev_type": "dev_backend",
      "project_id": "2efb27cb-7d26-42bc-89af-3949c79139d3",
      "project_name": "RUN3_PRE_20261020121719 project",
      "reviewer_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9"
    },
    "tags": [
      "dev_backend"
    ],
    "title": "STR3_1792470162628_783859 A B",
    "due_at": "2026-10-23T18:00:00",
    "status": "open",
    "done_at": null,
    "priority": "p2",
    "start_at": null,
    "created_at": "2026-10-20T12:17:22",
    "updated_at": "2026-10-20T12:22:43",
    "description": "STR3_1792470162628_783859 A B",
    "creator_name": "test_user1",
    "submitted_at": null,
    "assignee_name": "test_user3",
    "reviewer_name": "test_user1",
    "blocked_reason": null,
    "dismiss_reason": null,
    "review_comment": null,
    "creator_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "estimated_hours": "0.00",
    "assignee_user_id": "640d1a5c-bff5-4df0-9e02-cb42f8b46413",
    "reviewed_by_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9"
  },
  "message": "success"
}
```
响应断言（含字段路径、预期值、实际值、是否通过）：
```json
[
  {
    "type": "status",
    "expected": 200,
    "actual": 200,
    "passed": true
  },
  {
    "path": "data.title",
    "type": "json_equals",
    "expected": "STR3_1792470162628_783859 A B",
    "actual": "STR3_1792470162628_783859 A B",
    "passed": true
  },
  {
    "path": "data.description",
    "type": "json_equals",
    "expected": "STR3_1792470162628_783859 A B",
    "actual": "STR3_1792470162628_783859 A B",
    "passed": true
  }
]
```
保存后立即回查（避免后续编辑覆盖后误判旧值）：
```json
{
  "status": "passed",
  "missing": [],
  "expected": {
    "title": "STR3_1792470162628_783859 A B",
    "description": "STR3_1792470162628_783859 A B"
  },
  "observed": {
    "title": "STR3_1792470162628_783859 A B",
    "description": "STR3_1792470162628_783859 A B"
  },
  "mismatches": {},
  "read_route": "/todo/1376784f-7e16-45e4-877d-6aec114eaafb"
}
```
回查字段断言：
```json
[
  {
    "type": "stored_field_equals",
    "path": "title",
    "expected": "STR3_1792470162628_783859 A B",
    "actual": "STR3_1792470162628_783859 A B",
    "passed": true
  },
  {
    "type": "stored_field_equals",
    "path": "description",
    "expected": "STR3_1792470162628_783859 A B",
    "actual": "STR3_1792470162628_783859 A B",
    "passed": true
  }
]
```

## 排除的前置无效记录

以下三条不计入78条最终有效用例结果，也不列为PunkRecord文本处理Bug。补齐本轮项目成员后已复测通过对应的权限前置。

### 记录20850 / 用例4328 / 纯空格
前置项目未加入受派测试员工，权限拦截早于目标文本校验；不计产品文本Bug，补齐成员关系后重测
实际请求参数：
```json
{
  "body": {
    "title": "   ",
    "due_at": "2026-10-23T18:00:00+08:00",
    "dev_type": "dev_backend",
    "priority": "p2",
    "description": "   ",
    "estimated_hours": 0,
    "assignee_user_id": "640d1a5c-bff5-4df0-9e02-cb42f8b46413"
  },
  "query": {}
}
```
返回：HTTP 403
```json
{
  "code": 403,
  "errors": null,
  "message": "只能指派给项目成员或项目经理"
}
```

### 记录20851 / 用例4329 / 首尾空格
前置项目未加入受派测试员工，权限拦截早于目标文本校验；不计产品文本Bug，补齐成员关系后重测
实际请求参数：
```json
{
  "body": {
    "title": "  STR3_1792470036397_990908  ",
    "due_at": "2026-10-23T18:00:00+08:00",
    "dev_type": "dev_backend",
    "priority": "p2",
    "description": "  STR3_1792470036397_990908  ",
    "estimated_hours": 0,
    "assignee_user_id": "640d1a5c-bff5-4df0-9e02-cb42f8b46413"
  },
  "query": {}
}
```
返回：HTTP 403
```json
{
  "code": 403,
  "errors": null,
  "message": "只能指派给项目成员或项目经理"
}
```

### 记录20852 / 用例4330 / 中间空格
前置项目未加入受派测试员工，权限拦截早于目标文本校验；不计产品文本Bug，补齐成员关系后重测
实际请求参数：
```json
{
  "body": {
    "title": "STR3_1792470038072_153387 A B",
    "due_at": "2026-10-23T18:00:00+08:00",
    "dev_type": "dev_backend",
    "priority": "p2",
    "description": "STR3_1792470038072_153387 A B",
    "estimated_hours": 0,
    "assignee_user_id": "640d1a5c-bff5-4df0-9e02-cb42f8b46413"
  },
  "query": {}
}
```
返回：HTTP 403
```json
{
  "code": 403,
  "errors": null,
  "message": "只能指派给项目成员或项目经理"
}
```

## 前置数据与保留情况

本轮额外创建的正常前置数据及项目成员关联，不计作78条文本用例：
```json
{
  "objects": {
    "todo": {
      "id": "0c07a499-a09a-4ee0-935e-5c1172b85532",
      "title": "RUN3_PRE_20261020121719 todo"
    },
    "stage": {
      "id": "915f954c-9c9b-485a-a555-1756e298e6a9",
      "stage_code": "requirement_alignment"
    },
    "project": {
      "id": "2efb27cb-7d26-42bc-89af-3949c79139d3",
      "name": "RUN3_PRE_20261020121719 project"
    },
    "plan_todo": {
      "id": "1376784f-7e16-45e4-877d-6aec114eaafb",
      "title": "RUN3_PRE_20261020121719 plan"
    }
  },
  "precondition_requests": [
    {
      "key": "project",
      "body": {
        "name": "RUN3_PRE_20261020121719 project",
        "due_at": "2026-10-30",
        "start_at": "2026-10-20",
        "pm_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
        "project_no": "RUN3_PRE_20261020121719",
        "description": "V3 rerun precondition project",
        "project_type": "b2b"
      },
      "http": 200,
      "path": "/project/projects",
      "method": "POST",
      "response": {
        "code": 0,
        "data": {
          "id": "2efb27cb-7d26-42bc-89af-3949c79139d3",
          "name": "RUN3_PRE_20261020121719 project",
          "due_at": "2026-10-30",
          "status": "draft",
          "pm_name": "test_user1",
          "progress": 0.0,
          "start_at": "2026-10-20",
          "created_at": "2026-10-20T12:17:21",
          "pm_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
          "project_no": "RUN3_PRE_20261020121719",
          "updated_at": "2026-10-20T12:17:21",
          "contract_id": null,
          "customer_id": null,
          "description": "V3 rerun precondition project",
          "project_type": "b2b",
          "our_entity_id": null,
          "owner_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
          "current_stage_code": "requirement_alignment"
        },
        "message": "success"
      }
    },
    {
      "key": "todo",
      "body": {
        "notes": "Only this run data",
        "title": "RUN3_PRE_20261020121719 todo",
        "due_at": "2026-10-23T18:00:00+08:00",
        "priority": "p2",
        "source_id": "",
        "action_type": "do",
        "description": "V3 rerun precondition task",
        "source_type": "custom",
        "estimated_hours": 0,
        "assignee_user_id": "640d1a5c-bff5-4df0-9e02-cb42f8b46413"
      },
      "http": 200,
      "path": "/todo",
      "method": "POST",
      "response": {
        "code": 0,
        "data": {
          "id": "0c07a499-a09a-4ee0-935e-5c1172b85532",
          "link": {},
          "tags": [],
          "notes": "Only this run data",
          "title": "RUN3_PRE_20261020121719 todo",
          "due_at": "2026-10-23T18:00:00",
          "status": "open",
          "done_at": null,
          "priority": "p2",
          "start_at": null,
          "source_id": "3d58971f-23b5-4113-8879-b2f68c36434c",
          "created_at": "2026-10-20T12:17:21",
          "updated_at": "2026-10-20T12:17:21",
          "action_type": "do",
          "description": "V3 rerun precondition task",
          "source_type": "custom",
          "creator_name": "test_user1",
          "submitted_at": null,
          "assignee_name": "test_user3",
          "our_entity_id": "14efc508-797d-4a29-b359-3d5b51424a84",
          "reviewer_name": null,
          "blocked_reason": null,
          "dismiss_reason": null,
          "review_comment": null,
          "creator_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
          "done_by_user_id": null,
          "estimated_hours": "0.00",
          "assignee_user_id": "640d1a5c-bff5-4df0-9e02-cb42f8b46413",
          "reviewed_by_user_id": null
        },
        "message": "success"
      }
    },
    {
      "key": "plan_todo",
      "body": {
        "link": {
          "project_id": "2efb27cb-7d26-42bc-89af-3949c79139d3",
          "project_name": "RUN3_PRE_20261020121719 project",
          "reviewer_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9"
        },
        "notes": "Only this run data",
        "title": "RUN3_PRE_20261020121719 plan",
        "due_at": "2026-10-23T18:00:00+08:00",
        "priority": "p2",
        "source_id": "2efb27cb-7d26-42bc-89af-3949c79139d3",
        "action_type": "do",
        "description": "V3 rerun project task",
        "source_type": "project_task",
        "estimated_hours": 0,
        "assignee_user_id": "640d1a5c-bff5-4df0-9e02-cb42f8b46413"
      },
      "http": 200,
      "path": "/todo",
      "method": "POST",
      "response": {
        "code": 0,
        "data": {
          "id": "1376784f-7e16-45e4-877d-6aec114eaafb",
          "link": {
            "project_id": "2efb27cb-7d26-42bc-89af-3949c79139d3",
            "project_name": "RUN3_PRE_20261020121719 project",
            "reviewer_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9"
          },
          "tags": [],
          "notes": "Only this run data",
          "title": "RUN3_PRE_20261020121719 plan",
          "due_at": "2026-10-23T18:00:00",
          "status": "open",
          "done_at": null,
          "priority": "p2",
          "start_at": null,
          "source_id": "2efb27cb-7d26-42bc-89af-3949c79139d3",
          "created_at": "2026-10-20T12:17:22",
          "updated_at": "2026-10-20T12:17:22",
          "action_type": "do",
          "description": "V3 rerun project task",
          "source_type": "project_task",
          "creator_name": "test_user1",
          "submitted_at": null,
          "assignee_name": "test_user3",
          "our_entity_id": "14efc508-797d-4a29-b359-3d5b51424a84",
          "reviewer_name": "test_user1",
          "blocked_reason": null,
          "dismiss_reason": null,
          "review_comment": null,
          "creator_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
          "done_by_user_id": null,
          "estimated_hours": "0.00",
          "assignee_user_id": "640d1a5c-bff5-4df0-9e02-cb42f8b46413",
          "reviewed_by_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9"
        },
        "message": "success"
      }
    },
    {
      "key": "project_member",
      "body": {
        "user_id": "640d1a5c-bff5-4df0-9e02-cb42f8b46413"
      },
      "path": "/project/projects/2efb27cb-7d26-42bc-89af-3949c79139d3/members",
      "method": "POST",
      "response": {
        "id": "1d5a2a2a-9b25-434b-b459-8f23910b2f62",
        "user_id": "640d1a5c-bff5-4df0-9e02-cb42f8b46413",
        "user_name": "test_user3",
        "created_at": "2026-10-20T12:22:35",
        "project_id": "2efb27cb-7d26-42bc-89af-3949c79139d3",
        "user_email": null,
        "role_in_project": "API Workflow Test"
      }
    }
  ]
}
```
文本用例新建保留记录：38条；另有3个正常前置对象及1个项目成员关系。
员工资料未变：True；测试账号贝利余额未变：True。

