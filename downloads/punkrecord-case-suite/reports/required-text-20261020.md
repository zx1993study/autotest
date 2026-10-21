# PunkRecord 手动必填文本补测

执行入口：http://127.0.0.1:5173/api/v1
业务目标：http://14.103.229.153:15173/（项目保存的测试地址）

{"operations": 23, "validation": 91, "validation_passed": 54, "validation_failed": 37, "auxiliary_passed": 27, "selected_records": 118, "excluded_preliminary": 8}

仅测试页面手动输入的必填普通字符串；每个接口按输入形式组合，不逐字段展开。
排除自动生成编号、枚举、关联下拉、日期/金额/证件等特殊格式及可选备注描述。
JSON null 和空文本/纯空格分别处理；Form 无 JSON null，因此不建立该场景。
局部更新缺失/null允许保留原值；交易方编辑与商品编辑采用完整模型，缺失/null应拒绝。
未创建员工账号；员工新增未执行，遵守不重复建号限制。员工编辑姓名已恢复；未改变岗位、余额与上下级。
自动编号保持有效正常值；测试数据保留；未启动或修改本地 PunkRecord。

## 异常汇总

| 功能 | API | 字段 | 空文本 | 纯空格 |
|---|---|---|---|---|
|职位 新增|POST /api/v1/iam/job-titles|name|#20859|#20860|
|职位 编辑|PATCH /api/v1/iam/job-titles/{id}|name|#20864|#20865|
|部门 新增|POST /api/v1/iam/departments|name|#20869|#20870|
|部门 编辑|PATCH /api/v1/iam/departments/{id}|name|#20874|#20875|
|交易方 新增|POST /api/v1/contract/counterparties|name|#20889|#20890|
|交易方 编辑|PATCH /api/v1/contract/counterparties/{id}|name|#20894|#20895|
|任务 新增|POST /api/v1/todo|title|#20899|#20900|
|任务 编辑|PATCH /api/v1/todo/{id}|title|#20904|#20905|
|项目 新增|POST /api/v1/project/projects|name|#20909|#20910|
|项目 编辑|PATCH /api/v1/project/projects/{id}|name|#20914|#20915|
|下架商品 新增|POST /api/v1/beli/products|name|通过|#20920|
|下架商品 编辑|PUT /api/v1/beli/products/{id}|name|通过|#20925|
|更新日志 新增|POST /api/v1/changelog/entries|version, title, content|#20929|#20930|
|更新日志 编辑|PATCH /api/v1/changelog/entries/{id}|version, title, content|#20934|#20935|
|非业务会议 新增|POST /api/v1/meeting/records|title|通过|#20940|
|独立财务账户 新增|POST /api/v1/finance/accounts|account_name|#20944|#20945|
|独立财务账户 编辑|PATCH /api/v1/finance/accounts/{id}|account_name|#20949|#20950|
|草稿合同 新增|POST /api/v1/contract/contracts|name|#20954|#20955|
|草稿合同 编辑|PATCH /api/v1/contract/contracts/{id}|name|#20959|#20960|
|员工 编辑|PATCH /api/v1/iam/users/{id}|display_name|#20976|#20977|

所有异常均返回 HTTP 200、code=0，api_rejection(validation) 断言失败。

## 全部执行明细

### 职位 新增 / control / 用例 4331 / 记录 #20856
结果：success；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/iam/job-titles",
  "body": {
    "name": "REQ_20261020_140754_1792476475176_522761 name",
    "description": "REQ_20261020_140754_1792476475176_522761 description"
  },
  "path": "/iam/job-titles",
  "query": {},
  "method": "POST",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "d289f723-4a45-4254-a48d-90d4a0409696",
    "name": "REQ_20261020_140754_1792476475176_522761 name",
    "description": "REQ_20261020_140754_1792476475176_522761 description",
    "created_at": "2026-10-20T14:07:56"
  }
}
```
断言
```json
[
  {
    "type": "status",
    "actual": 200,
    "passed": true,
    "expected": 200
  },
  {
    "type": "json_equals",
    "actual": 0,
    "passed": true,
    "expected": 0
  }
]
```

### 职位 新增 / missing / 用例 4332 / 记录 #20857
结果：success；HTTP：422

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/iam/job-titles",
  "body": {
    "description": "REQ_20261020_140754_1792476476268_075303 description"
  },
  "path": "/iam/job-titles",
  "query": {},
  "method": "POST",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "body",
        "name"
      ],
      "msg": "Field required",
      "input": {
        "description": "REQ_20261020_140754_1792476476268_075303 description"
      }
    }
  ]
}
```
断言
```json
[
  {
    "type": "api_rejection",
    "actual": {
      "code": null,
      "http_status": 422
    },
    "passed": true,
    "message": "{\"detail\":[{\"type\":\"missing\",\"loc\":[\"body\",\"name\"],\"msg\":\"Field required\",\"input\":{\"description\":\"REQ_20261020_140754_1792476476268_075303 description\"}}]}",
    "expected": "validation"
  }
]
```

### 职位 新增 / null / 用例 4333 / 记录 #20858
结果：success；HTTP：422

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/iam/job-titles",
  "body": {
    "name": null,
    "description": "REQ_20261020_140754_1792476477230_287698 description"
  },
  "path": "/iam/job-titles",
  "query": {},
  "method": "POST",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "detail": [
    {
      "type": "string_type",
      "loc": [
        "body",
        "name"
      ],
      "msg": "Input should be a valid string",
      "input": null
    }
  ]
}
```
断言
```json
[
  {
    "type": "api_rejection",
    "actual": {
      "code": null,
      "http_status": 422
    },
    "passed": true,
    "message": "{\"detail\":[{\"type\":\"string_type\",\"loc\":[\"body\",\"name\"],\"msg\":\"Input should be a valid string\",\"input\":null}]}",
    "expected": "validation"
  }
]
```

### 职位 新增 / empty / 用例 4334 / 记录 #20859
结果：failed；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/iam/job-titles",
  "body": {
    "name": "",
    "description": "REQ_20261020_140754_1792476478186_632765 description"
  },
  "path": "/iam/job-titles",
  "query": {},
  "method": "POST",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "770f6827-963c-4dd3-9eda-5a92a061a61e",
    "name": "",
    "description": "REQ_20261020_140754_1792476478186_632765 description",
    "created_at": "2026-10-20T14:07:59"
  }
}
```
断言
```json
[
  {
    "type": "api_rejection",
    "actual": {
      "code": 0,
      "http_status": 200
    },
    "passed": false,
    "message": "success",
    "expected": "validation"
  }
]
```

### 职位 新增 / spaces / 用例 4335 / 记录 #20860
结果：failed；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/iam/job-titles",
  "body": {
    "name": "   ",
    "description": "REQ_20261020_140754_1792476479178_912180 description"
  },
  "path": "/iam/job-titles",
  "query": {},
  "method": "POST",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "80ad9a43-e4c0-4bc8-937f-df7f15d2da0a",
    "name": "   ",
    "description": "REQ_20261020_140754_1792476479178_912180 description",
    "created_at": "2026-10-20T14:08:00"
  }
}
```
断言
```json
[
  {
    "type": "api_rejection",
    "actual": {
      "code": 0,
      "http_status": 200
    },
    "passed": false,
    "message": "success",
    "expected": "validation"
  }
]
```

### 职位 编辑 / control / 用例 4336 / 记录 #20861
结果：success；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/iam/job-titles/d289f723-4a45-4254-a48d-90d4a0409696",
  "body": {
    "name": "REQ_20261020_140754_1792476501107_965540 name",
    "description": "REQ_20261020_140754_1792476501107_965540 description"
  },
  "path": "/iam/job-titles/d289f723-4a45-4254-a48d-90d4a0409696",
  "query": {},
  "method": "PATCH",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "d289f723-4a45-4254-a48d-90d4a0409696",
    "name": "REQ_20261020_140754_1792476501107_965540 name",
    "description": "REQ_20261020_140754_1792476501107_965540 description",
    "created_at": "2026-10-20T14:07:56"
  }
}
```
断言
```json
[
  {
    "type": "status",
    "actual": 200,
    "passed": true,
    "expected": 200
  },
  {
    "type": "json_equals",
    "actual": 0,
    "passed": true,
    "expected": 0
  }
]
```

### 职位 编辑 / missing / 用例 4337 / 记录 #20862
结果：success；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/iam/job-titles/d289f723-4a45-4254-a48d-90d4a0409696",
  "body": {
    "description": "REQ_20261020_140754_1792476502150_897765 description"
  },
  "path": "/iam/job-titles/d289f723-4a45-4254-a48d-90d4a0409696",
  "query": {},
  "method": "PATCH",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "d289f723-4a45-4254-a48d-90d4a0409696",
    "name": "REQ_20261020_140754_1792476501107_965540 name",
    "description": "REQ_20261020_140754_1792476502150_897765 description",
    "created_at": "2026-10-20T14:07:56"
  }
}
```
断言
```json
[
  {
    "type": "status",
    "actual": 200,
    "passed": true,
    "expected": 200
  },
  {
    "type": "json_equals",
    "actual": "REQ_20261020_140754_1792476501107_965540 name",
    "passed": true,
    "expected": "REQ_20261020_140754_1792476501107_965540 name"
  }
]
```

### 职位 编辑 / null / 用例 4338 / 记录 #20863
结果：success；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/iam/job-titles/d289f723-4a45-4254-a48d-90d4a0409696",
  "body": {
    "name": null,
    "description": "REQ_20261020_140754_1792476503290_374534 description"
  },
  "path": "/iam/job-titles/d289f723-4a45-4254-a48d-90d4a0409696",
  "query": {},
  "method": "PATCH",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "d289f723-4a45-4254-a48d-90d4a0409696",
    "name": "REQ_20261020_140754_1792476501107_965540 name",
    "description": "REQ_20261020_140754_1792476503290_374534 description",
    "created_at": "2026-10-20T14:07:56"
  }
}
```
断言
```json
[
  {
    "type": "status",
    "actual": 200,
    "passed": true,
    "expected": 200
  },
  {
    "type": "json_equals",
    "actual": "REQ_20261020_140754_1792476501107_965540 name",
    "passed": true,
    "expected": "REQ_20261020_140754_1792476501107_965540 name"
  }
]
```

### 职位 编辑 / empty / 用例 4339 / 记录 #20864
结果：failed；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/iam/job-titles/d289f723-4a45-4254-a48d-90d4a0409696",
  "body": {
    "name": "",
    "description": "REQ_20261020_140754_1792476504364_957879 description"
  },
  "path": "/iam/job-titles/d289f723-4a45-4254-a48d-90d4a0409696",
  "query": {},
  "method": "PATCH",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "d289f723-4a45-4254-a48d-90d4a0409696",
    "name": "",
    "description": "REQ_20261020_140754_1792476504364_957879 description",
    "created_at": "2026-10-20T14:07:56"
  }
}
```
断言
```json
[
  {
    "type": "api_rejection",
    "actual": {
      "code": 0,
      "http_status": 200
    },
    "passed": false,
    "message": "success",
    "expected": "validation"
  }
]
```

### 职位 编辑 / spaces / 用例 4340 / 记录 #20865
结果：failed；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/iam/job-titles/d289f723-4a45-4254-a48d-90d4a0409696",
  "body": {
    "name": "   ",
    "description": "REQ_20261020_140754_1792476505520_250519 description"
  },
  "path": "/iam/job-titles/d289f723-4a45-4254-a48d-90d4a0409696",
  "query": {},
  "method": "PATCH",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "d289f723-4a45-4254-a48d-90d4a0409696",
    "name": "   ",
    "description": "REQ_20261020_140754_1792476505520_250519 description",
    "created_at": "2026-10-20T14:07:56"
  }
}
```
断言
```json
[
  {
    "type": "api_rejection",
    "actual": {
      "code": 0,
      "http_status": 200
    },
    "passed": false,
    "message": "success",
    "expected": "validation"
  }
]
```

### 部门 新增 / control / 用例 4341 / 记录 #20866
结果：success；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/iam/departments",
  "body": {
    "name": "REQ_20261020_140754_1792476506612_675419 name",
    "description": "REQ_20261020_140754_1792476506612_675419 description"
  },
  "path": "/iam/departments",
  "query": {},
  "method": "POST",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "d0275279-b84a-4b03-a64c-fe4284713e16",
    "name": "REQ_20261020_140754_1792476506612_675419 name",
    "description": "REQ_20261020_140754_1792476506612_675419 description",
    "parent_org_unit_id": null,
    "member_count": 0,
    "children": [],
    "created_at": "2026-10-20T14:08:27"
  }
}
```
断言
```json
[
  {
    "type": "status",
    "actual": 200,
    "passed": true,
    "expected": 200
  },
  {
    "type": "json_equals",
    "actual": 0,
    "passed": true,
    "expected": 0
  }
]
```

### 部门 新增 / missing / 用例 4342 / 记录 #20867
结果：success；HTTP：422

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/iam/departments",
  "body": {
    "description": "REQ_20261020_140754_1792476507572_560876 description"
  },
  "path": "/iam/departments",
  "query": {},
  "method": "POST",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "body",
        "name"
      ],
      "msg": "Field required",
      "input": {
        "description": "REQ_20261020_140754_1792476507572_560876 description"
      }
    }
  ]
}
```
断言
```json
[
  {
    "type": "api_rejection",
    "actual": {
      "code": null,
      "http_status": 422
    },
    "passed": true,
    "message": "{\"detail\":[{\"type\":\"missing\",\"loc\":[\"body\",\"name\"],\"msg\":\"Field required\",\"input\":{\"description\":\"REQ_20261020_140754_1792476507572_560876 description\"}}]}",
    "expected": "validation"
  }
]
```

### 部门 新增 / null / 用例 4343 / 记录 #20868
结果：success；HTTP：422

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/iam/departments",
  "body": {
    "name": null,
    "description": "REQ_20261020_140754_1792476508535_673190 description"
  },
  "path": "/iam/departments",
  "query": {},
  "method": "POST",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "detail": [
    {
      "type": "string_type",
      "loc": [
        "body",
        "name"
      ],
      "msg": "Input should be a valid string",
      "input": null
    }
  ]
}
```
断言
```json
[
  {
    "type": "api_rejection",
    "actual": {
      "code": null,
      "http_status": 422
    },
    "passed": true,
    "message": "{\"detail\":[{\"type\":\"string_type\",\"loc\":[\"body\",\"name\"],\"msg\":\"Input should be a valid string\",\"input\":null}]}",
    "expected": "validation"
  }
]
```

### 部门 新增 / empty / 用例 4344 / 记录 #20869
结果：failed；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/iam/departments",
  "body": {
    "name": "",
    "description": "REQ_20261020_140754_1792476509515_356250 description"
  },
  "path": "/iam/departments",
  "query": {},
  "method": "POST",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "7ce26fa5-bb40-4b13-81e5-db9322e49f79",
    "name": "",
    "description": "REQ_20261020_140754_1792476509515_356250 description",
    "parent_org_unit_id": null,
    "member_count": 0,
    "children": [],
    "created_at": "2026-10-20T14:08:30"
  }
}
```
断言
```json
[
  {
    "type": "api_rejection",
    "actual": {
      "code": 0,
      "http_status": 200
    },
    "passed": false,
    "message": "success",
    "expected": "validation"
  }
]
```

### 部门 新增 / spaces / 用例 4345 / 记录 #20870
结果：failed；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/iam/departments",
  "body": {
    "name": "   ",
    "description": "REQ_20261020_140754_1792476510708_753234 description"
  },
  "path": "/iam/departments",
  "query": {},
  "method": "POST",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "a5885261-a30e-4a73-a685-1f7e3b84c633",
    "name": "   ",
    "description": "REQ_20261020_140754_1792476510708_753234 description",
    "parent_org_unit_id": null,
    "member_count": 0,
    "children": [],
    "created_at": "2026-10-20T14:08:32"
  }
}
```
断言
```json
[
  {
    "type": "api_rejection",
    "actual": {
      "code": 0,
      "http_status": 200
    },
    "passed": false,
    "message": "success",
    "expected": "validation"
  }
]
```

### 部门 编辑 / control / 用例 4346 / 记录 #20871
结果：success；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/iam/departments/d0275279-b84a-4b03-a64c-fe4284713e16",
  "body": {
    "name": "REQ_20261020_140754_1792476511685_297455 name",
    "description": "REQ_20261020_140754_1792476511685_297455 description"
  },
  "path": "/iam/departments/d0275279-b84a-4b03-a64c-fe4284713e16",
  "query": {},
  "method": "PATCH",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "d0275279-b84a-4b03-a64c-fe4284713e16",
    "name": "REQ_20261020_140754_1792476511685_297455 name",
    "description": "REQ_20261020_140754_1792476511685_297455 description",
    "parent_org_unit_id": null,
    "member_count": 0,
    "children": [],
    "created_at": "2026-10-20T14:08:27"
  }
}
```
断言
```json
[
  {
    "type": "status",
    "actual": 200,
    "passed": true,
    "expected": 200
  },
  {
    "type": "json_equals",
    "actual": 0,
    "passed": true,
    "expected": 0
  }
]
```

### 部门 编辑 / missing / 用例 4347 / 记录 #20872
结果：success；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/iam/departments/d0275279-b84a-4b03-a64c-fe4284713e16",
  "body": {
    "description": "REQ_20261020_140754_1792476512690_295978 description"
  },
  "path": "/iam/departments/d0275279-b84a-4b03-a64c-fe4284713e16",
  "query": {},
  "method": "PATCH",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "d0275279-b84a-4b03-a64c-fe4284713e16",
    "name": "REQ_20261020_140754_1792476511685_297455 name",
    "description": "REQ_20261020_140754_1792476512690_295978 description",
    "parent_org_unit_id": null,
    "member_count": 0,
    "children": [],
    "created_at": "2026-10-20T14:08:27"
  }
}
```
断言
```json
[
  {
    "type": "status",
    "actual": 200,
    "passed": true,
    "expected": 200
  },
  {
    "type": "json_equals",
    "actual": "REQ_20261020_140754_1792476511685_297455 name",
    "passed": true,
    "expected": "REQ_20261020_140754_1792476511685_297455 name"
  }
]
```

### 部门 编辑 / null / 用例 4348 / 记录 #20873
结果：success；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/iam/departments/d0275279-b84a-4b03-a64c-fe4284713e16",
  "body": {
    "name": null,
    "description": "REQ_20261020_140754_1792476514540_576347 description"
  },
  "path": "/iam/departments/d0275279-b84a-4b03-a64c-fe4284713e16",
  "query": {},
  "method": "PATCH",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "d0275279-b84a-4b03-a64c-fe4284713e16",
    "name": "REQ_20261020_140754_1792476511685_297455 name",
    "description": "REQ_20261020_140754_1792476514540_576347 description",
    "parent_org_unit_id": null,
    "member_count": 0,
    "children": [],
    "created_at": "2026-10-20T14:08:27"
  }
}
```
断言
```json
[
  {
    "type": "status",
    "actual": 200,
    "passed": true,
    "expected": 200
  },
  {
    "type": "json_equals",
    "actual": "REQ_20261020_140754_1792476511685_297455 name",
    "passed": true,
    "expected": "REQ_20261020_140754_1792476511685_297455 name"
  }
]
```

### 部门 编辑 / empty / 用例 4349 / 记录 #20874
结果：failed；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/iam/departments/d0275279-b84a-4b03-a64c-fe4284713e16",
  "body": {
    "name": "",
    "description": "REQ_20261020_140754_1792476516750_829140 description"
  },
  "path": "/iam/departments/d0275279-b84a-4b03-a64c-fe4284713e16",
  "query": {},
  "method": "PATCH",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "d0275279-b84a-4b03-a64c-fe4284713e16",
    "name": "",
    "description": "REQ_20261020_140754_1792476516750_829140 description",
    "parent_org_unit_id": null,
    "member_count": 0,
    "children": [],
    "created_at": "2026-10-20T14:08:27"
  }
}
```
断言
```json
[
  {
    "type": "api_rejection",
    "actual": {
      "code": 0,
      "http_status": 200
    },
    "passed": false,
    "message": "success",
    "expected": "validation"
  }
]
```

### 部门 编辑 / spaces / 用例 4350 / 记录 #20875
结果：failed；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/iam/departments/d0275279-b84a-4b03-a64c-fe4284713e16",
  "body": {
    "name": "   ",
    "description": "REQ_20261020_140754_1792476518114_454336 description"
  },
  "path": "/iam/departments/d0275279-b84a-4b03-a64c-fe4284713e16",
  "query": {},
  "method": "PATCH",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "d0275279-b84a-4b03-a64c-fe4284713e16",
    "name": "   ",
    "description": "REQ_20261020_140754_1792476518114_454336 description",
    "parent_org_unit_id": null,
    "member_count": 0,
    "children": [],
    "created_at": "2026-10-20T14:08:27"
  }
}
```
断言
```json
[
  {
    "type": "api_rejection",
    "actual": {
      "code": 0,
      "http_status": 200
    },
    "passed": false,
    "message": "success",
    "expected": "validation"
  }
]
```

### 停用贝利规则 新增 / control / 用例 4351 / 记录 #20876
结果：success；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/iam/beli-rules",
  "body": {
    "name": "REQ_20261020_140754_1792476519117_559427 name",
    "note": "REQ_20261020_140754_1792476519117_559427 note",
    "enabled": false,
    "late_days": 0,
    "rule_type": "task_timeliness",
    "early_days": 0,
    "reward_beili": 0,
    "penalty_beili": 0
  },
  "path": "/iam/beli-rules",
  "query": {},
  "method": "POST",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "5408e1b2-5a76-494f-bb54-f7baaf53f2c1",
    "name": "REQ_20261020_140754_1792476519117_559427 name",
    "rule_type": "task_timeliness",
    "enabled": false,
    "early_days": 0,
    "reward_beili": 0.0,
    "late_days": 0,
    "penalty_beili": 0.0,
    "note": "REQ_20261020_140754_1792476519117_559427 note",
    "created_at": "2026-10-20T14:08:40",
    "updated_at": "2026-10-20T14:08:40"
  }
}
```
断言
```json
[
  {
    "type": "status",
    "actual": 200,
    "passed": true,
    "expected": 200
  },
  {
    "type": "json_equals",
    "actual": 0,
    "passed": true,
    "expected": 0
  }
]
```

### 停用贝利规则 新增 / missing / 用例 4352 / 记录 #20877
结果：success；HTTP：422

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/iam/beli-rules",
  "body": {
    "note": "REQ_20261020_140754_1792476520120_588110 note",
    "enabled": false,
    "late_days": 0,
    "rule_type": "task_timeliness",
    "early_days": 0,
    "reward_beili": 0,
    "penalty_beili": 0
  },
  "path": "/iam/beli-rules",
  "query": {},
  "method": "POST",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "body",
        "name"
      ],
      "msg": "Field required",
      "input": {
        "note": "REQ_20261020_140754_1792476520120_588110 note",
        "enabled": false,
        "late_days": 0,
        "rule_type": "task_timeliness",
        "early_days": 0,
        "reward_beili": 0,
        "penalty_beili": 0
      }
    }
  ]
}
```
断言
```json
[
  {
    "type": "api_rejection",
    "actual": {
      "code": null,
      "http_status": 422
    },
    "passed": true,
    "message": "{\"detail\":[{\"type\":\"missing\",\"loc\":[\"body\",\"name\"],\"msg\":\"Field required\",\"input\":{\"note\":\"REQ_20261020_140754_1792476520120_588110 note\",\"enabled\":false,\"late_days\":0,\"rule_type\":\"task_timeliness\",\"early_days\":0,\"reward_beili\":0,\"penalty_beili\":0}}]}",
    "expected": "validation"
  }
]
```

### 停用贝利规则 新增 / null / 用例 4353 / 记录 #20878
结果：success；HTTP：422

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/iam/beli-rules",
  "body": {
    "name": null,
    "note": "REQ_20261020_140754_1792476521089_700638 note",
    "enabled": false,
    "late_days": 0,
    "rule_type": "task_timeliness",
    "early_days": 0,
    "reward_beili": 0,
    "penalty_beili": 0
  },
  "path": "/iam/beli-rules",
  "query": {},
  "method": "POST",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "detail": [
    {
      "type": "string_type",
      "loc": [
        "body",
        "name"
      ],
      "msg": "Input should be a valid string",
      "input": null
    }
  ]
}
```
断言
```json
[
  {
    "type": "api_rejection",
    "actual": {
      "code": null,
      "http_status": 422
    },
    "passed": true,
    "message": "{\"detail\":[{\"type\":\"string_type\",\"loc\":[\"body\",\"name\"],\"msg\":\"Input should be a valid string\",\"input\":null}]}",
    "expected": "validation"
  }
]
```

### 停用贝利规则 新增 / empty / 用例 4354 / 记录 #20879
结果：success；HTTP：400

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/iam/beli-rules",
  "body": {
    "name": "",
    "note": "REQ_20261020_140754_1792476522040_613364 note",
    "enabled": false,
    "late_days": 0,
    "rule_type": "task_timeliness",
    "early_days": 0,
    "reward_beili": 0,
    "penalty_beili": 0
  },
  "path": "/iam/beli-rules",
  "query": {},
  "method": "POST",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 400,
  "message": "规则名称不能为空",
  "errors": null
}
```
断言
```json
[
  {
    "type": "api_rejection",
    "actual": {
      "code": 400,
      "http_status": 400
    },
    "passed": true,
    "message": "规则名称不能为空",
    "expected": "validation"
  }
]
```

### 停用贝利规则 新增 / spaces / 用例 4355 / 记录 #20880
结果：success；HTTP：400

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/iam/beli-rules",
  "body": {
    "name": "   ",
    "note": "REQ_20261020_140754_1792476523039_453117 note",
    "enabled": false,
    "late_days": 0,
    "rule_type": "task_timeliness",
    "early_days": 0,
    "reward_beili": 0,
    "penalty_beili": 0
  },
  "path": "/iam/beli-rules",
  "query": {},
  "method": "POST",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 400,
  "message": "规则名称不能为空",
  "errors": null
}
```
断言
```json
[
  {
    "type": "api_rejection",
    "actual": {
      "code": 400,
      "http_status": 400
    },
    "passed": true,
    "message": "规则名称不能为空",
    "expected": "validation"
  }
]
```

### 停用贝利规则 编辑 / control / 用例 4356 / 记录 #20881
结果：success；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/iam/beli-rules/5408e1b2-5a76-494f-bb54-f7baaf53f2c1",
  "body": {
    "name": "REQ_20261020_140754_1792476524023_003762 name",
    "note": "REQ_20261020_140754_1792476524023_003762 note",
    "enabled": false,
    "late_days": 0,
    "rule_type": "task_timeliness",
    "early_days": 0,
    "reward_beili": 0,
    "penalty_beili": 0
  },
  "path": "/iam/beli-rules/5408e1b2-5a76-494f-bb54-f7baaf53f2c1",
  "query": {},
  "method": "PATCH",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "5408e1b2-5a76-494f-bb54-f7baaf53f2c1",
    "name": "REQ_20261020_140754_1792476524023_003762 name",
    "rule_type": "task_timeliness",
    "enabled": false,
    "early_days": 0,
    "reward_beili": 0.0,
    "late_days": 0,
    "penalty_beili": 0.0,
    "note": "REQ_20261020_140754_1792476524023_003762 note",
    "created_at": "2026-10-20T14:08:40",
    "updated_at": "2026-10-20T14:08:40"
  }
}
```
断言
```json
[
  {
    "type": "status",
    "actual": 200,
    "passed": true,
    "expected": 200
  },
  {
    "type": "json_equals",
    "actual": 0,
    "passed": true,
    "expected": 0
  }
]
```

### 停用贝利规则 编辑 / missing / 用例 4357 / 记录 #20882
结果：success；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/iam/beli-rules/5408e1b2-5a76-494f-bb54-f7baaf53f2c1",
  "body": {
    "note": "REQ_20261020_140754_1792476525157_843017 note",
    "enabled": false,
    "late_days": 0,
    "rule_type": "task_timeliness",
    "early_days": 0,
    "reward_beili": 0,
    "penalty_beili": 0
  },
  "path": "/iam/beli-rules/5408e1b2-5a76-494f-bb54-f7baaf53f2c1",
  "query": {},
  "method": "PATCH",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "5408e1b2-5a76-494f-bb54-f7baaf53f2c1",
    "name": "REQ_20261020_140754_1792476524023_003762 name",
    "rule_type": "task_timeliness",
    "enabled": false,
    "early_days": 0,
    "reward_beili": 0.0,
    "late_days": 0,
    "penalty_beili": 0.0,
    "note": "REQ_20261020_140754_1792476525157_843017 note",
    "created_at": "2026-10-20T14:08:40",
    "updated_at": "2026-10-20T14:08:40"
  }
}
```
断言
```json
[
  {
    "type": "status",
    "actual": 200,
    "passed": true,
    "expected": 200
  },
  {
    "type": "json_equals",
    "actual": "REQ_20261020_140754_1792476524023_003762 name",
    "passed": true,
    "expected": "REQ_20261020_140754_1792476524023_003762 name"
  }
]
```

### 停用贝利规则 编辑 / null / 用例 4358 / 记录 #20883
结果：success；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/iam/beli-rules/5408e1b2-5a76-494f-bb54-f7baaf53f2c1",
  "body": {
    "name": null,
    "note": "REQ_20261020_140754_1792476526101_743444 note",
    "enabled": false,
    "late_days": 0,
    "rule_type": "task_timeliness",
    "early_days": 0,
    "reward_beili": 0,
    "penalty_beili": 0
  },
  "path": "/iam/beli-rules/5408e1b2-5a76-494f-bb54-f7baaf53f2c1",
  "query": {},
  "method": "PATCH",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "5408e1b2-5a76-494f-bb54-f7baaf53f2c1",
    "name": "REQ_20261020_140754_1792476524023_003762 name",
    "rule_type": "task_timeliness",
    "enabled": false,
    "early_days": 0,
    "reward_beili": 0.0,
    "late_days": 0,
    "penalty_beili": 0.0,
    "note": "REQ_20261020_140754_1792476526101_743444 note",
    "created_at": "2026-10-20T14:08:40",
    "updated_at": "2026-10-20T14:08:40"
  }
}
```
断言
```json
[
  {
    "type": "status",
    "actual": 200,
    "passed": true,
    "expected": 200
  },
  {
    "type": "json_equals",
    "actual": "REQ_20261020_140754_1792476524023_003762 name",
    "passed": true,
    "expected": "REQ_20261020_140754_1792476524023_003762 name"
  }
]
```

### 停用贝利规则 编辑 / empty / 用例 4359 / 记录 #20884
结果：success；HTTP：400

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/iam/beli-rules/5408e1b2-5a76-494f-bb54-f7baaf53f2c1",
  "body": {
    "name": "",
    "note": "REQ_20261020_140754_1792476527058_109464 note",
    "enabled": false,
    "late_days": 0,
    "rule_type": "task_timeliness",
    "early_days": 0,
    "reward_beili": 0,
    "penalty_beili": 0
  },
  "path": "/iam/beli-rules/5408e1b2-5a76-494f-bb54-f7baaf53f2c1",
  "query": {},
  "method": "PATCH",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 400,
  "message": "规则名称不能为空",
  "errors": null
}
```
断言
```json
[
  {
    "type": "api_rejection",
    "actual": {
      "code": 400,
      "http_status": 400
    },
    "passed": true,
    "message": "规则名称不能为空",
    "expected": "validation"
  }
]
```

### 停用贝利规则 编辑 / spaces / 用例 4360 / 记录 #20885
结果：success；HTTP：400

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/iam/beli-rules/5408e1b2-5a76-494f-bb54-f7baaf53f2c1",
  "body": {
    "name": "   ",
    "note": "REQ_20261020_140754_1792476528150_949089 note",
    "enabled": false,
    "late_days": 0,
    "rule_type": "task_timeliness",
    "early_days": 0,
    "reward_beili": 0,
    "penalty_beili": 0
  },
  "path": "/iam/beli-rules/5408e1b2-5a76-494f-bb54-f7baaf53f2c1",
  "query": {},
  "method": "PATCH",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 400,
  "message": "规则名称不能为空",
  "errors": null
}
```
断言
```json
[
  {
    "type": "api_rejection",
    "actual": {
      "code": 400,
      "http_status": 400
    },
    "passed": true,
    "message": "规则名称不能为空",
    "expected": "validation"
  }
]
```

### 交易方 新增 / control / 用例 4361 / 记录 #20886
结果：success；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/contract/counterparties",
  "body": {
    "name": "REQ_20261020_140754_1792476529171_242575 name",
    "type": "customer",
    "phone": "13800138000",
    "address": "REQ_20261020_140754_1792476529171_242575 address",
    "bank_name": "REQ_20261020_140754_1792476529171_242575 bank_name",
    "identifier": "RQ1792476529171242575",
    "bank_account": "6222000012345678"
  },
  "path": "/contract/counterparties",
  "query": {},
  "method": "POST",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "05731497-a7b3-471c-9332-c3b103cb239b",
    "name": "REQ_20261020_140754_1792476529171_242575 name",
    "type": "customer",
    "identifier": "RQ1792476529171242575",
    "address": "REQ_20261020_140754_1792476529171_242575 address",
    "phone": "13800138000",
    "bank_name": "REQ_20261020_140754_1792476529171_242575 bank_name",
    "bank_account": "6222000012345678",
    "created_at": "2026-10-20T14:08:50"
  }
}
```
断言
```json
[
  {
    "type": "status",
    "actual": 200,
    "passed": true,
    "expected": 200
  },
  {
    "type": "json_equals",
    "actual": 0,
    "passed": true,
    "expected": 0
  }
]
```

### 交易方 新增 / missing / 用例 4362 / 记录 #20887
结果：success；HTTP：422

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/contract/counterparties",
  "body": {
    "type": "customer",
    "phone": "13800138000",
    "address": "REQ_20261020_140754_1792476530441_174309 address",
    "bank_name": "REQ_20261020_140754_1792476530441_174309 bank_name",
    "identifier": "RQ1792476530441174309",
    "bank_account": "6222000012345678"
  },
  "path": "/contract/counterparties",
  "query": {},
  "method": "POST",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "body",
        "name"
      ],
      "msg": "Field required",
      "input": {
        "type": "customer",
        "phone": "13800138000",
        "address": "REQ_20261020_140754_1792476530441_174309 address",
        "bank_name": "REQ_20261020_140754_1792476530441_174309 bank_name",
        "identifier": "RQ1792476530441174309",
        "bank_account": "6222000012345678"
      }
    }
  ]
}
```
断言
```json
[
  {
    "type": "api_rejection",
    "actual": {
      "code": null,
      "http_status": 422
    },
    "passed": true,
    "message": "{\"detail\":[{\"type\":\"missing\",\"loc\":[\"body\",\"name\"],\"msg\":\"Field required\",\"input\":{\"type\":\"customer\",\"phone\":\"13800138000\",\"address\":\"REQ_20261020_140754_1792476530441_174309 address\",\"bank_name\":\"REQ_20261020_140754_1792476530441_174309 bank_name\",\"identifier\":\"RQ1792476530441174309\",\"bank_account\":\"6222000012345678\"}}]}",
    "expected": "validation"
  }
]
```

### 交易方 新增 / null / 用例 4363 / 记录 #20888
结果：success；HTTP：422

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/contract/counterparties",
  "body": {
    "name": null,
    "type": "customer",
    "phone": "13800138000",
    "address": "REQ_20261020_140754_1792476531501_958292 address",
    "bank_name": "REQ_20261020_140754_1792476531501_958292 bank_name",
    "identifier": "RQ1792476531501958292",
    "bank_account": "6222000012345678"
  },
  "path": "/contract/counterparties",
  "query": {},
  "method": "POST",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "detail": [
    {
      "type": "string_type",
      "loc": [
        "body",
        "name"
      ],
      "msg": "Input should be a valid string",
      "input": null
    }
  ]
}
```
断言
```json
[
  {
    "type": "api_rejection",
    "actual": {
      "code": null,
      "http_status": 422
    },
    "passed": true,
    "message": "{\"detail\":[{\"type\":\"string_type\",\"loc\":[\"body\",\"name\"],\"msg\":\"Input should be a valid string\",\"input\":null}]}",
    "expected": "validation"
  }
]
```

### 交易方 新增 / empty / 用例 4364 / 记录 #20889
结果：failed；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/contract/counterparties",
  "body": {
    "name": "",
    "type": "customer",
    "phone": "13800138000",
    "address": "REQ_20261020_140754_1792476532499_246165 address",
    "bank_name": "REQ_20261020_140754_1792476532499_246165 bank_name",
    "identifier": "RQ1792476532499246165",
    "bank_account": "6222000012345678"
  },
  "path": "/contract/counterparties",
  "query": {},
  "method": "POST",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "53482448-121f-425d-a180-ff34a8f28c05",
    "name": "",
    "type": "customer",
    "identifier": "RQ1792476532499246165",
    "address": "REQ_20261020_140754_1792476532499_246165 address",
    "phone": "13800138000",
    "bank_name": "REQ_20261020_140754_1792476532499_246165 bank_name",
    "bank_account": "6222000012345678",
    "created_at": "2026-10-20T14:08:53"
  }
}
```
断言
```json
[
  {
    "type": "api_rejection",
    "actual": {
      "code": 0,
      "http_status": 200
    },
    "passed": false,
    "message": "success",
    "expected": "validation"
  }
]
```

### 交易方 新增 / spaces / 用例 4365 / 记录 #20890
结果：failed；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/contract/counterparties",
  "body": {
    "name": "   ",
    "type": "customer",
    "phone": "13800138000",
    "address": "REQ_20261020_140754_1792476533533_030969 address",
    "bank_name": "REQ_20261020_140754_1792476533533_030969 bank_name",
    "identifier": "RQ1792476533533030969",
    "bank_account": "6222000012345678"
  },
  "path": "/contract/counterparties",
  "query": {},
  "method": "POST",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "1c6c223b-2522-4b46-99d8-77a78636ddc7",
    "name": "   ",
    "type": "customer",
    "identifier": "RQ1792476533533030969",
    "address": "REQ_20261020_140754_1792476533533_030969 address",
    "phone": "13800138000",
    "bank_name": "REQ_20261020_140754_1792476533533_030969 bank_name",
    "bank_account": "6222000012345678",
    "created_at": "2026-10-20T14:08:54"
  }
}
```
断言
```json
[
  {
    "type": "api_rejection",
    "actual": {
      "code": 0,
      "http_status": 200
    },
    "passed": false,
    "message": "success",
    "expected": "validation"
  }
]
```

### 交易方 编辑 / control / 用例 4366 / 记录 #20891
结果：success；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/contract/counterparties/05731497-a7b3-471c-9332-c3b103cb239b",
  "body": {
    "name": "REQ_20261020_140754_1792476534619_743434 name",
    "type": "customer",
    "phone": "13800138000",
    "address": "REQ_20261020_140754_1792476534619_743434 address",
    "bank_name": "REQ_20261020_140754_1792476534619_743434 bank_name",
    "identifier": "RQ1792476534619743434",
    "bank_account": "6222000012345678"
  },
  "path": "/contract/counterparties/05731497-a7b3-471c-9332-c3b103cb239b",
  "query": {},
  "method": "PATCH",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "05731497-a7b3-471c-9332-c3b103cb239b",
    "name": "REQ_20261020_140754_1792476534619_743434 name",
    "type": "customer",
    "identifier": "RQ1792476534619743434",
    "address": "REQ_20261020_140754_1792476534619_743434 address",
    "phone": "13800138000",
    "bank_name": "REQ_20261020_140754_1792476534619_743434 bank_name",
    "bank_account": "6222000012345678",
    "created_at": "2026-10-20T14:08:50"
  }
}
```
断言
```json
[
  {
    "type": "status",
    "actual": 200,
    "passed": true,
    "expected": 200
  },
  {
    "type": "json_equals",
    "actual": 0,
    "passed": true,
    "expected": 0
  }
]
```

### 交易方 编辑 / empty / 用例 4369 / 记录 #20894
结果：failed；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/contract/counterparties/05731497-a7b3-471c-9332-c3b103cb239b",
  "body": {
    "name": "",
    "type": "customer",
    "phone": "13800138000",
    "address": "REQ_20261020_140754_1792476537742_391715 address",
    "bank_name": "REQ_20261020_140754_1792476537742_391715 bank_name",
    "identifier": "RQ1792476537742391715",
    "bank_account": "6222000012345678"
  },
  "path": "/contract/counterparties/05731497-a7b3-471c-9332-c3b103cb239b",
  "query": {},
  "method": "PATCH",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "05731497-a7b3-471c-9332-c3b103cb239b",
    "name": "",
    "type": "customer",
    "identifier": "RQ1792476537742391715",
    "address": "REQ_20261020_140754_1792476537742_391715 address",
    "phone": "13800138000",
    "bank_name": "REQ_20261020_140754_1792476537742_391715 bank_name",
    "bank_account": "6222000012345678",
    "created_at": "2026-10-20T14:08:50"
  }
}
```
断言
```json
[
  {
    "type": "api_rejection",
    "actual": {
      "code": 0,
      "http_status": 200
    },
    "passed": false,
    "message": "success",
    "expected": "validation"
  }
]
```

### 交易方 编辑 / spaces / 用例 4370 / 记录 #20895
结果：failed；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/contract/counterparties/05731497-a7b3-471c-9332-c3b103cb239b",
  "body": {
    "name": "   ",
    "type": "customer",
    "phone": "13800138000",
    "address": "REQ_20261020_140754_1792476538715_686799 address",
    "bank_name": "REQ_20261020_140754_1792476538715_686799 bank_name",
    "identifier": "RQ1792476538715686799",
    "bank_account": "6222000012345678"
  },
  "path": "/contract/counterparties/05731497-a7b3-471c-9332-c3b103cb239b",
  "query": {},
  "method": "PATCH",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "05731497-a7b3-471c-9332-c3b103cb239b",
    "name": "   ",
    "type": "customer",
    "identifier": "RQ1792476538715686799",
    "address": "REQ_20261020_140754_1792476538715_686799 address",
    "phone": "13800138000",
    "bank_name": "REQ_20261020_140754_1792476538715_686799 bank_name",
    "bank_account": "6222000012345678",
    "created_at": "2026-10-20T14:08:50"
  }
}
```
断言
```json
[
  {
    "type": "api_rejection",
    "actual": {
      "code": 0,
      "http_status": 200
    },
    "passed": false,
    "message": "success",
    "expected": "validation"
  }
]
```

### 任务 新增 / control / 用例 4371 / 记录 #20896
结果：success；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/todo",
  "body": {
    "tags": [
      "STR_20261020_102732"
    ],
    "notes": "REQ_20261020_140754_1792476539778_649057 notes",
    "title": "REQ_20261020_140754_1792476539778_649057 title",
    "due_at": "2026-10-23T18:00:00+08:00",
    "priority": "p2",
    "start_at": "2026-10-21T09:00:00+08:00",
    "source_id": "",
    "action_type": "do",
    "description": "REQ_20261020_140754_1792476539778_649057 description",
    "source_type": "custom",
    "estimated_hours": 0,
    "assignee_user_id": "640d1a5c-bff5-4df0-9e02-cb42f8b46413"
  },
  "path": "/todo",
  "query": {},
  "method": "POST",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "c0ae4386-6671-40d2-a937-bdcfb2c9ca18",
    "our_entity_id": "14efc508-797d-4a29-b359-3d5b51424a84",
    "assignee_user_id": "640d1a5c-bff5-4df0-9e02-cb42f8b46413",
    "assignee_name": "test_user3",
    "creator_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "creator_name": "test_user1",
    "title": "REQ_20261020_140754_1792476539778_649057 title",
    "description": "REQ_20261020_140754_1792476539778_649057 description",
    "notes": "REQ_20261020_140754_1792476539778_649057 notes",
    "source_type": "custom",
    "source_id": "c63fec20-027a-4285-bfac-b2a952286289",
    "action_type": "do",
    "priority": "p2",
    "status": "open",
    "due_at": "2026-10-23T18:00:00",
    "estimated_hours": "0.00",
    "submitted_at": null,
    "start_at": "2026-10-21T09:00:00",
    "tags": [
      "STR_20261020_102732"
    ],
    "link": {},
    "blocked_reason": null,
    "done_at": null,
    "done_by_user_id": null,
    "dismiss_reason": null,
    "review_comment": null,
    "reviewed_by_user_id": null,
    "reviewer_name": null,
    "created_at": "2026-10-20T14:09:01",
    "updated_at": "2026-10-20T14:09:01"
  }
}
```
断言
```json
[
  {
    "type": "status",
    "actual": 200,
    "passed": true,
    "expected": 200
  },
  {
    "type": "json_equals",
    "actual": 0,
    "passed": true,
    "expected": 0
  }
]
```

### 任务 新增 / missing / 用例 4372 / 记录 #20897
结果：success；HTTP：422

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/todo",
  "body": {
    "tags": [
      "STR_20261020_102732"
    ],
    "notes": "REQ_20261020_140754_1792476540846_061505 notes",
    "due_at": "2026-10-23T18:00:00+08:00",
    "priority": "p2",
    "start_at": "2026-10-21T09:00:00+08:00",
    "source_id": "",
    "action_type": "do",
    "description": "REQ_20261020_140754_1792476540846_061505 description",
    "source_type": "custom",
    "estimated_hours": 0,
    "assignee_user_id": "640d1a5c-bff5-4df0-9e02-cb42f8b46413"
  },
  "path": "/todo",
  "query": {},
  "method": "POST",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "body",
        "title"
      ],
      "msg": "Field required",
      "input": {
        "tags": [
          "STR_20261020_102732"
        ],
        "notes": "REQ_20261020_140754_1792476540846_061505 notes",
        "due_at": "2026-10-23T18:00:00+08:00",
        "priority": "p2",
        "start_at": "2026-10-21T09:00:00+08:00",
        "source_id": "",
        "action_type": "do",
        "description": "REQ_20261020_140754_1792476540846_061505 description",
        "source_type": "custom",
        "estimated_hours": 0,
        "assignee_user_id": "640d1a5c-bff5-4df0-9e02-cb42f8b46413"
      }
    }
  ]
}
```
断言
```json
[
  {
    "type": "api_rejection",
    "actual": {
      "code": null,
      "http_status": 422
    },
    "passed": true,
    "message": "{\"detail\":[{\"type\":\"missing\",\"loc\":[\"body\",\"title\"],\"msg\":\"Field required\",\"input\":{\"tags\":[\"STR_20261020_102732\"],\"notes\":\"REQ_20261020_140754_1792476540846_061505 notes\",\"due_at\":\"2026-10-23T18:00:00+08:00\",\"priority\":\"p2\",\"start_at\":\"2026-10-21T09:00:00+08:00\",\"source_id\":\"\",\"action_type\":\"do\",\"description\":\"REQ_20261020_140754_1792476540846_061505 description\",\"source_type\":\"custom\",\"estimated_hours\":0,\"assignee_user_id\":\"640d1a5c-bff5-4df0-9e02-cb42f8b46413\"}}]}",
    "expected": "validation"
  }
]
```

### 任务 新增 / null / 用例 4373 / 记录 #20898
结果：success；HTTP：422

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/todo",
  "body": {
    "tags": [
      "STR_20261020_102732"
    ],
    "notes": "REQ_20261020_140754_1792476541816_629756 notes",
    "title": null,
    "due_at": "2026-10-23T18:00:00+08:00",
    "priority": "p2",
    "start_at": "2026-10-21T09:00:00+08:00",
    "source_id": "",
    "action_type": "do",
    "description": "REQ_20261020_140754_1792476541816_629756 description",
    "source_type": "custom",
    "estimated_hours": 0,
    "assignee_user_id": "640d1a5c-bff5-4df0-9e02-cb42f8b46413"
  },
  "path": "/todo",
  "query": {},
  "method": "POST",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "detail": [
    {
      "type": "string_type",
      "loc": [
        "body",
        "title"
      ],
      "msg": "Input should be a valid string",
      "input": null
    }
  ]
}
```
断言
```json
[
  {
    "type": "api_rejection",
    "actual": {
      "code": null,
      "http_status": 422
    },
    "passed": true,
    "message": "{\"detail\":[{\"type\":\"string_type\",\"loc\":[\"body\",\"title\"],\"msg\":\"Input should be a valid string\",\"input\":null}]}",
    "expected": "validation"
  }
]
```

### 任务 新增 / empty / 用例 4374 / 记录 #20899
结果：failed；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/todo",
  "body": {
    "tags": [
      "STR_20261020_102732"
    ],
    "notes": "REQ_20261020_140754_1792476542776_923129 notes",
    "title": "",
    "due_at": "2026-10-23T18:00:00+08:00",
    "priority": "p2",
    "start_at": "2026-10-21T09:00:00+08:00",
    "source_id": "",
    "action_type": "do",
    "description": "REQ_20261020_140754_1792476542776_923129 description",
    "source_type": "custom",
    "estimated_hours": 0,
    "assignee_user_id": "640d1a5c-bff5-4df0-9e02-cb42f8b46413"
  },
  "path": "/todo",
  "query": {},
  "method": "POST",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "cd0cc1b1-8fc4-4b68-9c36-6acfe86c870a",
    "our_entity_id": "14efc508-797d-4a29-b359-3d5b51424a84",
    "assignee_user_id": "640d1a5c-bff5-4df0-9e02-cb42f8b46413",
    "assignee_name": "test_user3",
    "creator_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "creator_name": "test_user1",
    "title": "",
    "description": "REQ_20261020_140754_1792476542776_923129 description",
    "notes": "REQ_20261020_140754_1792476542776_923129 notes",
    "source_type": "custom",
    "source_id": "6cdc15d3-f951-46c6-9995-17dab6070b75",
    "action_type": "do",
    "priority": "p2",
    "status": "open",
    "due_at": "2026-10-23T18:00:00",
    "estimated_hours": "0.00",
    "submitted_at": null,
    "start_at": "2026-10-21T09:00:00",
    "tags": [
      "STR_20261020_102732"
    ],
    "link": {},
    "blocked_reason": null,
    "done_at": null,
    "done_by_user_id": null,
    "dismiss_reason": null,
    "review_comment": null,
    "reviewed_by_user_id": null,
    "reviewer_name": null,
    "created_at": "2026-10-20T14:09:04",
    "updated_at": "2026-10-20T14:09:04"
  }
}
```
断言
```json
[
  {
    "type": "api_rejection",
    "actual": {
      "code": 0,
      "http_status": 200
    },
    "passed": false,
    "message": "success",
    "expected": "validation"
  }
]
```

### 任务 新增 / spaces / 用例 4375 / 记录 #20900
结果：failed；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/todo",
  "body": {
    "tags": [
      "STR_20261020_102732"
    ],
    "notes": "REQ_20261020_140754_1792476543831_800287 notes",
    "title": "   ",
    "due_at": "2026-10-23T18:00:00+08:00",
    "priority": "p2",
    "start_at": "2026-10-21T09:00:00+08:00",
    "source_id": "",
    "action_type": "do",
    "description": "REQ_20261020_140754_1792476543831_800287 description",
    "source_type": "custom",
    "estimated_hours": 0,
    "assignee_user_id": "640d1a5c-bff5-4df0-9e02-cb42f8b46413"
  },
  "path": "/todo",
  "query": {},
  "method": "POST",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "8cdde5ac-613e-4a3f-b5c0-eece1292a43a",
    "our_entity_id": "14efc508-797d-4a29-b359-3d5b51424a84",
    "assignee_user_id": "640d1a5c-bff5-4df0-9e02-cb42f8b46413",
    "assignee_name": "test_user3",
    "creator_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "creator_name": "test_user1",
    "title": "   ",
    "description": "REQ_20261020_140754_1792476543831_800287 description",
    "notes": "REQ_20261020_140754_1792476543831_800287 notes",
    "source_type": "custom",
    "source_id": "7f77be94-9ed1-48ab-bf66-c4f3b3708662",
    "action_type": "do",
    "priority": "p2",
    "status": "open",
    "due_at": "2026-10-23T18:00:00",
    "estimated_hours": "0.00",
    "submitted_at": null,
    "start_at": "2026-10-21T09:00:00",
    "tags": [
      "STR_20261020_102732"
    ],
    "link": {},
    "blocked_reason": null,
    "done_at": null,
    "done_by_user_id": null,
    "dismiss_reason": null,
    "review_comment": null,
    "reviewed_by_user_id": null,
    "reviewer_name": null,
    "created_at": "2026-10-20T14:09:05",
    "updated_at": "2026-10-20T14:09:05"
  }
}
```
断言
```json
[
  {
    "type": "api_rejection",
    "actual": {
      "code": 0,
      "http_status": 200
    },
    "passed": false,
    "message": "success",
    "expected": "validation"
  }
]
```

### 任务 编辑 / control / 用例 4376 / 记录 #20901
结果：success；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/todo/c0ae4386-6671-40d2-a937-bdcfb2c9ca18",
  "body": {
    "tags": [
      "STR_20261020_102732"
    ],
    "notes": "REQ_20261020_140754_1792476544954_712657 notes",
    "title": "REQ_20261020_140754_1792476544954_712657 title",
    "due_at": "2026-10-23T18:00:00+08:00",
    "priority": "p2",
    "start_at": "2026-10-21T09:00:00+08:00",
    "description": "REQ_20261020_140754_1792476544954_712657 description",
    "estimated_hours": 0,
    "assignee_user_id": "640d1a5c-bff5-4df0-9e02-cb42f8b46413"
  },
  "path": "/todo/c0ae4386-6671-40d2-a937-bdcfb2c9ca18",
  "query": {},
  "method": "PATCH",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "c0ae4386-6671-40d2-a937-bdcfb2c9ca18",
    "our_entity_id": "14efc508-797d-4a29-b359-3d5b51424a84",
    "assignee_user_id": "640d1a5c-bff5-4df0-9e02-cb42f8b46413",
    "assignee_name": "test_user3",
    "creator_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "creator_name": "test_user1",
    "title": "REQ_20261020_140754_1792476544954_712657 title",
    "description": "REQ_20261020_140754_1792476544954_712657 description",
    "notes": "REQ_20261020_140754_1792476544954_712657 notes",
    "source_type": "custom",
    "source_id": "c63fec20-027a-4285-bfac-b2a952286289",
    "action_type": "do",
    "priority": "p2",
    "status": "open",
    "due_at": "2026-10-23T18:00:00",
    "estimated_hours": "0.00",
    "submitted_at": null,
    "start_at": "2026-10-21T09:00:00",
    "tags": [
      "STR_20261020_102732"
    ],
    "link": {},
    "blocked_reason": null,
    "done_at": null,
    "done_by_user_id": null,
    "dismiss_reason": null,
    "review_comment": null,
    "reviewed_by_user_id": null,
    "reviewer_name": null,
    "created_at": "2026-10-20T14:09:01",
    "updated_at": "2026-10-20T14:09:06"
  }
}
```
断言
```json
[
  {
    "type": "status",
    "actual": 200,
    "passed": true,
    "expected": 200
  },
  {
    "type": "json_equals",
    "actual": 0,
    "passed": true,
    "expected": 0
  }
]
```

### 任务 编辑 / missing / 用例 4377 / 记录 #20902
结果：success；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/todo/c0ae4386-6671-40d2-a937-bdcfb2c9ca18",
  "body": {
    "tags": [
      "STR_20261020_102732"
    ],
    "notes": "REQ_20261020_140754_1792476546095_291322 notes",
    "due_at": "2026-10-23T18:00:00+08:00",
    "priority": "p2",
    "start_at": "2026-10-21T09:00:00+08:00",
    "description": "REQ_20261020_140754_1792476546095_291322 description",
    "estimated_hours": 0,
    "assignee_user_id": "640d1a5c-bff5-4df0-9e02-cb42f8b46413"
  },
  "path": "/todo/c0ae4386-6671-40d2-a937-bdcfb2c9ca18",
  "query": {},
  "method": "PATCH",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "c0ae4386-6671-40d2-a937-bdcfb2c9ca18",
    "our_entity_id": "14efc508-797d-4a29-b359-3d5b51424a84",
    "assignee_user_id": "640d1a5c-bff5-4df0-9e02-cb42f8b46413",
    "assignee_name": "test_user3",
    "creator_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "creator_name": "test_user1",
    "title": "REQ_20261020_140754_1792476544954_712657 title",
    "description": "REQ_20261020_140754_1792476546095_291322 description",
    "notes": "REQ_20261020_140754_1792476546095_291322 notes",
    "source_type": "custom",
    "source_id": "c63fec20-027a-4285-bfac-b2a952286289",
    "action_type": "do",
    "priority": "p2",
    "status": "open",
    "due_at": "2026-10-23T18:00:00",
    "estimated_hours": "0.00",
    "submitted_at": null,
    "start_at": "2026-10-21T09:00:00",
    "tags": [
      "STR_20261020_102732"
    ],
    "link": {},
    "blocked_reason": null,
    "done_at": null,
    "done_by_user_id": null,
    "dismiss_reason": null,
    "review_comment": null,
    "reviewed_by_user_id": null,
    "reviewer_name": null,
    "created_at": "2026-10-20T14:09:01",
    "updated_at": "2026-10-20T14:09:07"
  }
}
```
断言
```json
[
  {
    "type": "status",
    "actual": 200,
    "passed": true,
    "expected": 200
  },
  {
    "type": "json_equals",
    "actual": "REQ_20261020_140754_1792476544954_712657 title",
    "passed": true,
    "expected": "REQ_20261020_140754_1792476544954_712657 title"
  }
]
```

### 任务 编辑 / null / 用例 4378 / 记录 #20903
结果：success；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/todo/c0ae4386-6671-40d2-a937-bdcfb2c9ca18",
  "body": {
    "tags": [
      "STR_20261020_102732"
    ],
    "notes": "REQ_20261020_140754_1792476547112_533185 notes",
    "title": null,
    "due_at": "2026-10-23T18:00:00+08:00",
    "priority": "p2",
    "start_at": "2026-10-21T09:00:00+08:00",
    "description": "REQ_20261020_140754_1792476547112_533185 description",
    "estimated_hours": 0,
    "assignee_user_id": "640d1a5c-bff5-4df0-9e02-cb42f8b46413"
  },
  "path": "/todo/c0ae4386-6671-40d2-a937-bdcfb2c9ca18",
  "query": {},
  "method": "PATCH",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "c0ae4386-6671-40d2-a937-bdcfb2c9ca18",
    "our_entity_id": "14efc508-797d-4a29-b359-3d5b51424a84",
    "assignee_user_id": "640d1a5c-bff5-4df0-9e02-cb42f8b46413",
    "assignee_name": "test_user3",
    "creator_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "creator_name": "test_user1",
    "title": "REQ_20261020_140754_1792476544954_712657 title",
    "description": "REQ_20261020_140754_1792476547112_533185 description",
    "notes": "REQ_20261020_140754_1792476547112_533185 notes",
    "source_type": "custom",
    "source_id": "c63fec20-027a-4285-bfac-b2a952286289",
    "action_type": "do",
    "priority": "p2",
    "status": "open",
    "due_at": "2026-10-23T18:00:00",
    "estimated_hours": "0.00",
    "submitted_at": null,
    "start_at": "2026-10-21T09:00:00",
    "tags": [
      "STR_20261020_102732"
    ],
    "link": {},
    "blocked_reason": null,
    "done_at": null,
    "done_by_user_id": null,
    "dismiss_reason": null,
    "review_comment": null,
    "reviewed_by_user_id": null,
    "reviewer_name": null,
    "created_at": "2026-10-20T14:09:01",
    "updated_at": "2026-10-20T14:09:08"
  }
}
```
断言
```json
[
  {
    "type": "status",
    "actual": 200,
    "passed": true,
    "expected": 200
  },
  {
    "type": "json_equals",
    "actual": "REQ_20261020_140754_1792476544954_712657 title",
    "passed": true,
    "expected": "REQ_20261020_140754_1792476544954_712657 title"
  }
]
```

### 任务 编辑 / empty / 用例 4379 / 记录 #20904
结果：failed；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/todo/c0ae4386-6671-40d2-a937-bdcfb2c9ca18",
  "body": {
    "tags": [
      "STR_20261020_102732"
    ],
    "notes": "REQ_20261020_140754_1792476548126_608154 notes",
    "title": "",
    "due_at": "2026-10-23T18:00:00+08:00",
    "priority": "p2",
    "start_at": "2026-10-21T09:00:00+08:00",
    "description": "REQ_20261020_140754_1792476548126_608154 description",
    "estimated_hours": 0,
    "assignee_user_id": "640d1a5c-bff5-4df0-9e02-cb42f8b46413"
  },
  "path": "/todo/c0ae4386-6671-40d2-a937-bdcfb2c9ca18",
  "query": {},
  "method": "PATCH",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "c0ae4386-6671-40d2-a937-bdcfb2c9ca18",
    "our_entity_id": "14efc508-797d-4a29-b359-3d5b51424a84",
    "assignee_user_id": "640d1a5c-bff5-4df0-9e02-cb42f8b46413",
    "assignee_name": "test_user3",
    "creator_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "creator_name": "test_user1",
    "title": "",
    "description": "REQ_20261020_140754_1792476548126_608154 description",
    "notes": "REQ_20261020_140754_1792476548126_608154 notes",
    "source_type": "custom",
    "source_id": "c63fec20-027a-4285-bfac-b2a952286289",
    "action_type": "do",
    "priority": "p2",
    "status": "open",
    "due_at": "2026-10-23T18:00:00",
    "estimated_hours": "0.00",
    "submitted_at": null,
    "start_at": "2026-10-21T09:00:00",
    "tags": [
      "STR_20261020_102732"
    ],
    "link": {},
    "blocked_reason": null,
    "done_at": null,
    "done_by_user_id": null,
    "dismiss_reason": null,
    "review_comment": null,
    "reviewed_by_user_id": null,
    "reviewer_name": null,
    "created_at": "2026-10-20T14:09:01",
    "updated_at": "2026-10-20T14:09:09"
  }
}
```
断言
```json
[
  {
    "type": "api_rejection",
    "actual": {
      "code": 0,
      "http_status": 200
    },
    "passed": false,
    "message": "success",
    "expected": "validation"
  }
]
```

### 任务 编辑 / spaces / 用例 4380 / 记录 #20905
结果：failed；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/todo/c0ae4386-6671-40d2-a937-bdcfb2c9ca18",
  "body": {
    "tags": [
      "STR_20261020_102732"
    ],
    "notes": "REQ_20261020_140754_1792476549378_262160 notes",
    "title": "   ",
    "due_at": "2026-10-23T18:00:00+08:00",
    "priority": "p2",
    "start_at": "2026-10-21T09:00:00+08:00",
    "description": "REQ_20261020_140754_1792476549378_262160 description",
    "estimated_hours": 0,
    "assignee_user_id": "640d1a5c-bff5-4df0-9e02-cb42f8b46413"
  },
  "path": "/todo/c0ae4386-6671-40d2-a937-bdcfb2c9ca18",
  "query": {},
  "method": "PATCH",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "c0ae4386-6671-40d2-a937-bdcfb2c9ca18",
    "our_entity_id": "14efc508-797d-4a29-b359-3d5b51424a84",
    "assignee_user_id": "640d1a5c-bff5-4df0-9e02-cb42f8b46413",
    "assignee_name": "test_user3",
    "creator_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "creator_name": "test_user1",
    "title": "   ",
    "description": "REQ_20261020_140754_1792476549378_262160 description",
    "notes": "REQ_20261020_140754_1792476549378_262160 notes",
    "source_type": "custom",
    "source_id": "c63fec20-027a-4285-bfac-b2a952286289",
    "action_type": "do",
    "priority": "p2",
    "status": "open",
    "due_at": "2026-10-23T18:00:00",
    "estimated_hours": "0.00",
    "submitted_at": null,
    "start_at": "2026-10-21T09:00:00",
    "tags": [
      "STR_20261020_102732"
    ],
    "link": {},
    "blocked_reason": null,
    "done_at": null,
    "done_by_user_id": null,
    "dismiss_reason": null,
    "review_comment": null,
    "reviewed_by_user_id": null,
    "reviewer_name": null,
    "created_at": "2026-10-20T14:09:01",
    "updated_at": "2026-10-20T14:09:10"
  }
}
```
断言
```json
[
  {
    "type": "api_rejection",
    "actual": {
      "code": 0,
      "http_status": 200
    },
    "passed": false,
    "message": "success",
    "expected": "validation"
  }
]
```

### 项目 新增 / control / 用例 4381 / 记录 #20906
结果：success；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/project/projects",
  "body": {
    "name": "REQ_20261020_140754_1792476550519_697200 name",
    "due_at": "2026-10-30",
    "start_at": "2026-10-20",
    "pm_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "project_no": "PR-1792476550519-697200",
    "description": "REQ_20261020_140754_1792476550519_697200 description",
    "project_type": "b2b"
  },
  "path": "/project/projects",
  "query": {},
  "method": "POST",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "2e12b64b-e24a-4761-b083-d2e5e91c5a4c",
    "our_entity_id": null,
    "project_no": "PR-1792476550519-697200",
    "name": "REQ_20261020_140754_1792476550519_697200 name",
    "project_type": "b2b",
    "status": "draft",
    "owner_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "pm_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "pm_name": "test_user1",
    "customer_id": null,
    "contract_id": null,
    "start_at": "2026-10-20",
    "due_at": "2026-10-30",
    "current_stage_code": "requirement_alignment",
    "progress": 0.0,
    "description": "REQ_20261020_140754_1792476550519_697200 description",
    "created_at": "2026-10-20T14:09:11",
    "updated_at": "2026-10-20T14:09:11"
  }
}
```
断言
```json
[
  {
    "type": "status",
    "actual": 200,
    "passed": true,
    "expected": 200
  },
  {
    "type": "json_equals",
    "actual": 0,
    "passed": true,
    "expected": 0
  }
]
```

### 项目 新增 / missing / 用例 4382 / 记录 #20907
结果：success；HTTP：422

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/project/projects",
  "body": {
    "due_at": "2026-10-30",
    "start_at": "2026-10-20",
    "pm_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "project_no": "PR-1792476551579-162041",
    "description": "REQ_20261020_140754_1792476551579_162041 description",
    "project_type": "b2b"
  },
  "path": "/project/projects",
  "query": {},
  "method": "POST",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "body",
        "name"
      ],
      "msg": "Field required",
      "input": {
        "due_at": "2026-10-30",
        "start_at": "2026-10-20",
        "pm_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
        "project_no": "PR-1792476551579-162041",
        "description": "REQ_20261020_140754_1792476551579_162041 description",
        "project_type": "b2b"
      }
    }
  ]
}
```
断言
```json
[
  {
    "type": "api_rejection",
    "actual": {
      "code": null,
      "http_status": 422
    },
    "passed": true,
    "message": "{\"detail\":[{\"type\":\"missing\",\"loc\":[\"body\",\"name\"],\"msg\":\"Field required\",\"input\":{\"due_at\":\"2026-10-30\",\"start_at\":\"2026-10-20\",\"pm_user_id\":\"5b0b6d34-6b1e-434a-b553-e8f4ca919eb9\",\"project_no\":\"PR-1792476551579-162041\",\"description\":\"REQ_20261020_140754_1792476551579_162041 description\",\"project_type\":\"b2b\"}}]}",
    "expected": "validation"
  }
]
```

### 项目 新增 / null / 用例 4383 / 记录 #20908
结果：success；HTTP：422

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/project/projects",
  "body": {
    "name": null,
    "due_at": "2026-10-30",
    "start_at": "2026-10-20",
    "pm_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "project_no": "PR-1792476552658-249127",
    "description": "REQ_20261020_140754_1792476552658_249127 description",
    "project_type": "b2b"
  },
  "path": "/project/projects",
  "query": {},
  "method": "POST",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "detail": [
    {
      "type": "string_type",
      "loc": [
        "body",
        "name"
      ],
      "msg": "Input should be a valid string",
      "input": null
    }
  ]
}
```
断言
```json
[
  {
    "type": "api_rejection",
    "actual": {
      "code": null,
      "http_status": 422
    },
    "passed": true,
    "message": "{\"detail\":[{\"type\":\"string_type\",\"loc\":[\"body\",\"name\"],\"msg\":\"Input should be a valid string\",\"input\":null}]}",
    "expected": "validation"
  }
]
```

### 项目 新增 / empty / 用例 4384 / 记录 #20909
结果：failed；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/project/projects",
  "body": {
    "name": "",
    "due_at": "2026-10-30",
    "start_at": "2026-10-20",
    "pm_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "project_no": "PR-1792476553696-413558",
    "description": "REQ_20261020_140754_1792476553696_413558 description",
    "project_type": "b2b"
  },
  "path": "/project/projects",
  "query": {},
  "method": "POST",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "003cf5dc-3622-47b4-a031-b2bad7a202a8",
    "our_entity_id": null,
    "project_no": "PR-1792476553696-413558",
    "name": "",
    "project_type": "b2b",
    "status": "draft",
    "owner_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "pm_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "pm_name": "test_user1",
    "customer_id": null,
    "contract_id": null,
    "start_at": "2026-10-20",
    "due_at": "2026-10-30",
    "current_stage_code": "requirement_alignment",
    "progress": 0.0,
    "description": "REQ_20261020_140754_1792476553696_413558 description",
    "created_at": "2026-10-20T14:09:15",
    "updated_at": "2026-10-20T14:09:15"
  }
}
```
断言
```json
[
  {
    "type": "api_rejection",
    "actual": {
      "code": 0,
      "http_status": 200
    },
    "passed": false,
    "message": "success",
    "expected": "validation"
  }
]
```

### 项目 新增 / spaces / 用例 4385 / 记录 #20910
结果：failed；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/project/projects",
  "body": {
    "name": "   ",
    "due_at": "2026-10-30",
    "start_at": "2026-10-20",
    "pm_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "project_no": "PR-1792476554720-724999",
    "description": "REQ_20261020_140754_1792476554720_724999 description",
    "project_type": "b2b"
  },
  "path": "/project/projects",
  "query": {},
  "method": "POST",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "346acb29-b133-458f-b41e-557858aa9154",
    "our_entity_id": null,
    "project_no": "PR-1792476554720-724999",
    "name": "   ",
    "project_type": "b2b",
    "status": "draft",
    "owner_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "pm_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "pm_name": "test_user1",
    "customer_id": null,
    "contract_id": null,
    "start_at": "2026-10-20",
    "due_at": "2026-10-30",
    "current_stage_code": "requirement_alignment",
    "progress": 0.0,
    "description": "REQ_20261020_140754_1792476554720_724999 description",
    "created_at": "2026-10-20T14:09:16",
    "updated_at": "2026-10-20T14:09:16"
  }
}
```
断言
```json
[
  {
    "type": "api_rejection",
    "actual": {
      "code": 0,
      "http_status": 200
    },
    "passed": false,
    "message": "success",
    "expected": "validation"
  }
]
```

### 项目 编辑 / control / 用例 4386 / 记录 #20911
结果：success；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/project/projects/2e12b64b-e24a-4761-b083-d2e5e91c5a4c",
  "body": {
    "name": "REQ_20261020_140754_1792476555822_532677 name",
    "due_at": "2026-10-30",
    "status": "draft",
    "start_at": "2026-10-20",
    "pm_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "description": "REQ_20261020_140754_1792476555822_532677 description"
  },
  "path": "/project/projects/2e12b64b-e24a-4761-b083-d2e5e91c5a4c",
  "query": {},
  "method": "PATCH",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "2e12b64b-e24a-4761-b083-d2e5e91c5a4c",
    "our_entity_id": null,
    "project_no": "PR-1792476550519-697200",
    "name": "REQ_20261020_140754_1792476555822_532677 name",
    "project_type": "b2b",
    "status": "draft",
    "owner_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "pm_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "pm_name": "test_user1",
    "customer_id": null,
    "contract_id": null,
    "start_at": "2026-10-20",
    "due_at": "2026-10-30",
    "current_stage_code": "requirement_alignment",
    "progress": 0.0,
    "description": "REQ_20261020_140754_1792476555822_532677 description",
    "created_at": "2026-10-20T14:09:11",
    "updated_at": "2026-10-20T14:09:17"
  }
}
```
断言
```json
[
  {
    "type": "status",
    "actual": 200,
    "passed": true,
    "expected": 200
  },
  {
    "type": "json_equals",
    "actual": 0,
    "passed": true,
    "expected": 0
  }
]
```

### 项目 编辑 / missing / 用例 4387 / 记录 #20912
结果：success；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/project/projects/2e12b64b-e24a-4761-b083-d2e5e91c5a4c",
  "body": {
    "due_at": "2026-10-30",
    "status": "draft",
    "start_at": "2026-10-20",
    "pm_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "description": "REQ_20261020_140754_1792476556874_053370 description"
  },
  "path": "/project/projects/2e12b64b-e24a-4761-b083-d2e5e91c5a4c",
  "query": {},
  "method": "PATCH",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "2e12b64b-e24a-4761-b083-d2e5e91c5a4c",
    "our_entity_id": null,
    "project_no": "PR-1792476550519-697200",
    "name": "REQ_20261020_140754_1792476555822_532677 name",
    "project_type": "b2b",
    "status": "draft",
    "owner_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "pm_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "pm_name": "test_user1",
    "customer_id": null,
    "contract_id": null,
    "start_at": "2026-10-20",
    "due_at": "2026-10-30",
    "current_stage_code": "requirement_alignment",
    "progress": 0.0,
    "description": "REQ_20261020_140754_1792476556874_053370 description",
    "created_at": "2026-10-20T14:09:11",
    "updated_at": "2026-10-20T14:09:18"
  }
}
```
断言
```json
[
  {
    "type": "status",
    "actual": 200,
    "passed": true,
    "expected": 200
  },
  {
    "type": "json_equals",
    "actual": "REQ_20261020_140754_1792476555822_532677 name",
    "passed": true,
    "expected": "REQ_20261020_140754_1792476555822_532677 name"
  }
]
```

### 项目 编辑 / null / 用例 4388 / 记录 #20913
结果：success；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/project/projects/2e12b64b-e24a-4761-b083-d2e5e91c5a4c",
  "body": {
    "name": null,
    "due_at": "2026-10-30",
    "status": "draft",
    "start_at": "2026-10-20",
    "pm_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "description": "REQ_20261020_140754_1792476558028_995619 description"
  },
  "path": "/project/projects/2e12b64b-e24a-4761-b083-d2e5e91c5a4c",
  "query": {},
  "method": "PATCH",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "2e12b64b-e24a-4761-b083-d2e5e91c5a4c",
    "our_entity_id": null,
    "project_no": "PR-1792476550519-697200",
    "name": "REQ_20261020_140754_1792476555822_532677 name",
    "project_type": "b2b",
    "status": "draft",
    "owner_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "pm_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "pm_name": "test_user1",
    "customer_id": null,
    "contract_id": null,
    "start_at": "2026-10-20",
    "due_at": "2026-10-30",
    "current_stage_code": "requirement_alignment",
    "progress": 0.0,
    "description": "REQ_20261020_140754_1792476558028_995619 description",
    "created_at": "2026-10-20T14:09:11",
    "updated_at": "2026-10-20T14:09:19"
  }
}
```
断言
```json
[
  {
    "type": "status",
    "actual": 200,
    "passed": true,
    "expected": 200
  },
  {
    "type": "json_equals",
    "actual": "REQ_20261020_140754_1792476555822_532677 name",
    "passed": true,
    "expected": "REQ_20261020_140754_1792476555822_532677 name"
  }
]
```

### 项目 编辑 / empty / 用例 4389 / 记录 #20914
结果：failed；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/project/projects/2e12b64b-e24a-4761-b083-d2e5e91c5a4c",
  "body": {
    "name": "",
    "due_at": "2026-10-30",
    "status": "draft",
    "start_at": "2026-10-20",
    "pm_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "description": "REQ_20261020_140754_1792476559073_846078 description"
  },
  "path": "/project/projects/2e12b64b-e24a-4761-b083-d2e5e91c5a4c",
  "query": {},
  "method": "PATCH",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "2e12b64b-e24a-4761-b083-d2e5e91c5a4c",
    "our_entity_id": null,
    "project_no": "PR-1792476550519-697200",
    "name": "",
    "project_type": "b2b",
    "status": "draft",
    "owner_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "pm_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "pm_name": "test_user1",
    "customer_id": null,
    "contract_id": null,
    "start_at": "2026-10-20",
    "due_at": "2026-10-30",
    "current_stage_code": "requirement_alignment",
    "progress": 0.0,
    "description": "REQ_20261020_140754_1792476559073_846078 description",
    "created_at": "2026-10-20T14:09:11",
    "updated_at": "2026-10-20T14:09:20"
  }
}
```
断言
```json
[
  {
    "type": "api_rejection",
    "actual": {
      "code": 0,
      "http_status": 200
    },
    "passed": false,
    "message": "success",
    "expected": "validation"
  }
]
```

### 项目 编辑 / spaces / 用例 4390 / 记录 #20915
结果：failed；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/project/projects/2e12b64b-e24a-4761-b083-d2e5e91c5a4c",
  "body": {
    "name": "   ",
    "due_at": "2026-10-30",
    "status": "draft",
    "start_at": "2026-10-20",
    "pm_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "description": "REQ_20261020_140754_1792476560083_569799 description"
  },
  "path": "/project/projects/2e12b64b-e24a-4761-b083-d2e5e91c5a4c",
  "query": {},
  "method": "PATCH",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "2e12b64b-e24a-4761-b083-d2e5e91c5a4c",
    "our_entity_id": null,
    "project_no": "PR-1792476550519-697200",
    "name": "   ",
    "project_type": "b2b",
    "status": "draft",
    "owner_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "pm_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "pm_name": "test_user1",
    "customer_id": null,
    "contract_id": null,
    "start_at": "2026-10-20",
    "due_at": "2026-10-30",
    "current_stage_code": "requirement_alignment",
    "progress": 0.0,
    "description": "REQ_20261020_140754_1792476560083_569799 description",
    "created_at": "2026-10-20T14:09:11",
    "updated_at": "2026-10-20T14:09:21"
  }
}
```
断言
```json
[
  {
    "type": "api_rejection",
    "actual": {
      "code": 0,
      "http_status": 200
    },
    "passed": false,
    "message": "success",
    "expected": "validation"
  }
]
```

### 下架商品 新增 / control / 用例 4391 / 记录 #20916
结果：success；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/beli/products",
  "body": {
    "kind": "physical",
    "name": "REQ_20261020_140754_1792476561189_332574 name",
    "price": "1.23",
    "stock": 0,
    "active": false,
    "leave_type": "annual",
    "description": "REQ_20261020_140754_1792476561189_332574 description"
  },
  "path": "/beli/products",
  "query": {},
  "method": "POST",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "created_at": "2026-10-20T14:09:22",
    "name": "REQ_20261020_140754_1792476561189_332574 name",
    "kind": "physical",
    "stock": 0,
    "image_name": null,
    "leave_days": null,
    "description": "REQ_20261020_140754_1792476561189_332574 description",
    "updated_at": "2026-10-20T14:09:22",
    "id": "02855bd4-0c88-4625-b514-2093a8e3d21e",
    "price": "1.23",
    "active": false,
    "leave_type": "annual"
  }
}
```
断言
```json
[
  {
    "type": "status",
    "actual": 200,
    "passed": true,
    "expected": 200
  },
  {
    "type": "json_equals",
    "actual": 0,
    "passed": true,
    "expected": 0
  }
]
```

### 下架商品 新增 / missing / 用例 4392 / 记录 #20917
结果：success；HTTP：422

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/beli/products",
  "body": {
    "kind": "physical",
    "price": "1.23",
    "stock": 0,
    "active": false,
    "leave_type": "annual",
    "description": "REQ_20261020_140754_1792476562327_854627 description"
  },
  "path": "/beli/products",
  "query": {},
  "method": "POST",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "body",
        "name"
      ],
      "msg": "Field required",
      "input": {
        "kind": "physical",
        "price": "1.23",
        "stock": 0,
        "active": false,
        "leave_type": "annual",
        "description": "REQ_20261020_140754_1792476562327_854627 description"
      }
    }
  ]
}
```
断言
```json
[
  {
    "type": "api_rejection",
    "actual": {
      "code": null,
      "http_status": 422
    },
    "passed": true,
    "message": "{\"detail\":[{\"type\":\"missing\",\"loc\":[\"body\",\"name\"],\"msg\":\"Field required\",\"input\":{\"kind\":\"physical\",\"price\":\"1.23\",\"stock\":0,\"active\":false,\"leave_type\":\"annual\",\"description\":\"REQ_20261020_140754_1792476562327_854627 description\"}}]}",
    "expected": "validation"
  }
]
```

### 下架商品 新增 / null / 用例 4393 / 记录 #20918
结果：success；HTTP：422

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/beli/products",
  "body": {
    "kind": "physical",
    "name": null,
    "price": "1.23",
    "stock": 0,
    "active": false,
    "leave_type": "annual",
    "description": "REQ_20261020_140754_1792476563292_070243 description"
  },
  "path": "/beli/products",
  "query": {},
  "method": "POST",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "detail": [
    {
      "type": "string_type",
      "loc": [
        "body",
        "name"
      ],
      "msg": "Input should be a valid string",
      "input": null
    }
  ]
}
```
断言
```json
[
  {
    "type": "api_rejection",
    "actual": {
      "code": null,
      "http_status": 422
    },
    "passed": true,
    "message": "{\"detail\":[{\"type\":\"string_type\",\"loc\":[\"body\",\"name\"],\"msg\":\"Input should be a valid string\",\"input\":null}]}",
    "expected": "validation"
  }
]
```

### 下架商品 新增 / empty / 用例 4394 / 记录 #20919
结果：success；HTTP：422

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/beli/products",
  "body": {
    "kind": "physical",
    "name": "",
    "price": "1.23",
    "stock": 0,
    "active": false,
    "leave_type": "annual",
    "description": "REQ_20261020_140754_1792476564275_454769 description"
  },
  "path": "/beli/products",
  "query": {},
  "method": "POST",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "detail": [
    {
      "type": "string_too_short",
      "loc": [
        "body",
        "name"
      ],
      "msg": "String should have at least 1 character",
      "input": "",
      "ctx": {
        "min_length": 1
      }
    }
  ]
}
```
断言
```json
[
  {
    "type": "api_rejection",
    "actual": {
      "code": null,
      "http_status": 422
    },
    "passed": true,
    "message": "{\"detail\":[{\"type\":\"string_too_short\",\"loc\":[\"body\",\"name\"],\"msg\":\"String should have at least 1 character\",\"input\":\"\",\"ctx\":{\"min_length\":1}}]}",
    "expected": "validation"
  }
]
```

### 下架商品 新增 / spaces / 用例 4395 / 记录 #20920
结果：failed；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/beli/products",
  "body": {
    "kind": "physical",
    "name": "   ",
    "price": "1.23",
    "stock": 0,
    "active": false,
    "leave_type": "annual",
    "description": "REQ_20261020_140754_1792476565292_571437 description"
  },
  "path": "/beli/products",
  "query": {},
  "method": "POST",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "created_at": "2026-10-20T14:09:26",
    "name": "   ",
    "kind": "physical",
    "stock": 0,
    "image_name": null,
    "leave_days": null,
    "description": "REQ_20261020_140754_1792476565292_571437 description",
    "updated_at": "2026-10-20T14:09:26",
    "id": "707bfdd0-c107-4be1-90c9-09ee5a87b046",
    "price": "1.23",
    "active": false,
    "leave_type": "annual"
  }
}
```
断言
```json
[
  {
    "type": "api_rejection",
    "actual": {
      "code": 0,
      "http_status": 200
    },
    "passed": false,
    "message": "success",
    "expected": "validation"
  }
]
```

### 下架商品 编辑 / control / 用例 4396 / 记录 #20921
结果：success；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/beli/products/02855bd4-0c88-4625-b514-2093a8e3d21e",
  "body": {
    "kind": "physical",
    "name": "REQ_20261020_140754_1792476566239_320716 name",
    "price": "1.23",
    "stock": 0,
    "active": false,
    "leave_type": "annual",
    "description": "REQ_20261020_140754_1792476566239_320716 description"
  },
  "path": "/beli/products/02855bd4-0c88-4625-b514-2093a8e3d21e",
  "query": {},
  "method": "PUT",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "created_at": "2026-10-20T14:09:22",
    "name": "REQ_20261020_140754_1792476566239_320716 name",
    "kind": "physical",
    "stock": 0,
    "image_name": null,
    "leave_days": null,
    "description": "REQ_20261020_140754_1792476566239_320716 description",
    "updated_at": "2026-10-20T14:09:22",
    "id": "02855bd4-0c88-4625-b514-2093a8e3d21e",
    "price": "1.23",
    "active": false,
    "leave_type": "annual"
  }
}
```
断言
```json
[
  {
    "type": "status",
    "actual": 200,
    "passed": true,
    "expected": 200
  },
  {
    "type": "json_equals",
    "actual": 0,
    "passed": true,
    "expected": 0
  }
]
```

### 下架商品 编辑 / missing / 用例 4397 / 记录 #20922
结果：success；HTTP：422

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/beli/products/02855bd4-0c88-4625-b514-2093a8e3d21e",
  "body": {
    "kind": "physical",
    "price": "1.23",
    "stock": 0,
    "active": false,
    "leave_type": "annual",
    "description": "REQ_20261020_140754_1792476567289_343127 description"
  },
  "path": "/beli/products/02855bd4-0c88-4625-b514-2093a8e3d21e",
  "query": {},
  "method": "PUT",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "body",
        "name"
      ],
      "msg": "Field required",
      "input": {
        "kind": "physical",
        "price": "1.23",
        "stock": 0,
        "active": false,
        "leave_type": "annual",
        "description": "REQ_20261020_140754_1792476567289_343127 description"
      }
    }
  ]
}
```
断言
```json
[
  {
    "type": "api_rejection",
    "actual": {
      "code": null,
      "http_status": 422
    },
    "passed": true,
    "message": "{\"detail\":[{\"type\":\"missing\",\"loc\":[\"body\",\"name\"],\"msg\":\"Field required\",\"input\":{\"kind\":\"physical\",\"price\":\"1.23\",\"stock\":0,\"active\":false,\"leave_type\":\"annual\",\"description\":\"REQ_20261020_140754_1792476567289_343127 description\"}}]}",
    "expected": "validation"
  }
]
```

### 下架商品 编辑 / null / 用例 4398 / 记录 #20923
结果：success；HTTP：422

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/beli/products/02855bd4-0c88-4625-b514-2093a8e3d21e",
  "body": {
    "kind": "physical",
    "name": null,
    "price": "1.23",
    "stock": 0,
    "active": false,
    "leave_type": "annual",
    "description": "REQ_20261020_140754_1792476568221_105967 description"
  },
  "path": "/beli/products/02855bd4-0c88-4625-b514-2093a8e3d21e",
  "query": {},
  "method": "PUT",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "detail": [
    {
      "type": "string_type",
      "loc": [
        "body",
        "name"
      ],
      "msg": "Input should be a valid string",
      "input": null
    }
  ]
}
```
断言
```json
[
  {
    "type": "api_rejection",
    "actual": {
      "code": null,
      "http_status": 422
    },
    "passed": true,
    "message": "{\"detail\":[{\"type\":\"string_type\",\"loc\":[\"body\",\"name\"],\"msg\":\"Input should be a valid string\",\"input\":null}]}",
    "expected": "validation"
  }
]
```

### 下架商品 编辑 / empty / 用例 4399 / 记录 #20924
结果：success；HTTP：422

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/beli/products/02855bd4-0c88-4625-b514-2093a8e3d21e",
  "body": {
    "kind": "physical",
    "name": "",
    "price": "1.23",
    "stock": 0,
    "active": false,
    "leave_type": "annual",
    "description": "REQ_20261020_140754_1792476569199_382223 description"
  },
  "path": "/beli/products/02855bd4-0c88-4625-b514-2093a8e3d21e",
  "query": {},
  "method": "PUT",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "detail": [
    {
      "type": "string_too_short",
      "loc": [
        "body",
        "name"
      ],
      "msg": "String should have at least 1 character",
      "input": "",
      "ctx": {
        "min_length": 1
      }
    }
  ]
}
```
断言
```json
[
  {
    "type": "api_rejection",
    "actual": {
      "code": null,
      "http_status": 422
    },
    "passed": true,
    "message": "{\"detail\":[{\"type\":\"string_too_short\",\"loc\":[\"body\",\"name\"],\"msg\":\"String should have at least 1 character\",\"input\":\"\",\"ctx\":{\"min_length\":1}}]}",
    "expected": "validation"
  }
]
```

### 下架商品 编辑 / spaces / 用例 4400 / 记录 #20925
结果：failed；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/beli/products/02855bd4-0c88-4625-b514-2093a8e3d21e",
  "body": {
    "kind": "physical",
    "name": "   ",
    "price": "1.23",
    "stock": 0,
    "active": false,
    "leave_type": "annual",
    "description": "REQ_20261020_140754_1792476570256_413304 description"
  },
  "path": "/beli/products/02855bd4-0c88-4625-b514-2093a8e3d21e",
  "query": {},
  "method": "PUT",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "created_at": "2026-10-20T14:09:22",
    "name": "   ",
    "kind": "physical",
    "stock": 0,
    "image_name": null,
    "leave_days": null,
    "description": "REQ_20261020_140754_1792476570256_413304 description",
    "updated_at": "2026-10-20T14:09:22",
    "id": "02855bd4-0c88-4625-b514-2093a8e3d21e",
    "price": "1.23",
    "active": false,
    "leave_type": "annual"
  }
}
```
断言
```json
[
  {
    "type": "api_rejection",
    "actual": {
      "code": 0,
      "http_status": 200
    },
    "passed": false,
    "message": "success",
    "expected": "validation"
  }
]
```

### 更新日志 新增 / control / 用例 4401 / 记录 #20926
结果：success；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/changelog/entries",
  "body": {
    "title": "REQ_20261020_140754_1792476571398_985811 title",
    "content": "REQ_20261020_140754_1792476571398_985811 content",
    "version": "REQ_20261020_140754_1792476571398_985811 version"
  },
  "path": "/changelog/entries",
  "query": {},
  "method": "POST",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "f13f3928-d046-4c2c-9459-2edb741d8c6e",
    "version": "REQ_20261020_140754_1792476571398_985811 version",
    "title": "REQ_20261020_140754_1792476571398_985811 title"
  }
}
```
断言
```json
[
  {
    "type": "status",
    "actual": 200,
    "passed": true,
    "expected": 200
  },
  {
    "type": "json_equals",
    "actual": 0,
    "passed": true,
    "expected": 0
  }
]
```

### 更新日志 新增 / missing / 用例 4402 / 记录 #20927
结果：success；HTTP：422

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/changelog/entries",
  "body": {},
  "path": "/changelog/entries",
  "query": {},
  "method": "POST",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "body",
        "version"
      ],
      "msg": "Field required",
      "input": {}
    },
    {
      "type": "missing",
      "loc": [
        "body",
        "title"
      ],
      "msg": "Field required",
      "input": {}
    },
    {
      "type": "missing",
      "loc": [
        "body",
        "content"
      ],
      "msg": "Field required",
      "input": {}
    }
  ]
}
```
断言
```json
[
  {
    "type": "api_rejection",
    "actual": {
      "code": null,
      "http_status": 422
    },
    "passed": true,
    "message": "{\"detail\":[{\"type\":\"missing\",\"loc\":[\"body\",\"version\"],\"msg\":\"Field required\",\"input\":{}},{\"type\":\"missing\",\"loc\":[\"body\",\"title\"],\"msg\":\"Field required\",\"input\":{}},{\"type\":\"missing\",\"loc\":[\"body\",\"content\"],\"msg\":\"Field required\",\"input\":{}}]}",
    "expected": "validation"
  }
]
```

### 更新日志 新增 / null / 用例 4403 / 记录 #20928
结果：success；HTTP：422

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/changelog/entries",
  "body": {
    "title": null,
    "content": null,
    "version": null
  },
  "path": "/changelog/entries",
  "query": {},
  "method": "POST",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "detail": [
    {
      "type": "string_type",
      "loc": [
        "body",
        "version"
      ],
      "msg": "Input should be a valid string",
      "input": null
    },
    {
      "type": "string_type",
      "loc": [
        "body",
        "title"
      ],
      "msg": "Input should be a valid string",
      "input": null
    },
    {
      "type": "string_type",
      "loc": [
        "body",
        "content"
      ],
      "msg": "Input should be a valid string",
      "input": null
    }
  ]
}
```
断言
```json
[
  {
    "type": "api_rejection",
    "actual": {
      "code": null,
      "http_status": 422
    },
    "passed": true,
    "message": "{\"detail\":[{\"type\":\"string_type\",\"loc\":[\"body\",\"version\"],\"msg\":\"Input should be a valid string\",\"input\":null},{\"type\":\"string_type\",\"loc\":[\"body\",\"title\"],\"msg\":\"Input should be a valid string\",\"input\":null},{\"type\":\"string_type\",\"loc\":[\"body\",\"content\"],\"msg\":\"Input should be a valid string\",\"input\":null}]}",
    "expected": "validation"
  }
]
```

### 更新日志 新增 / empty / 用例 4404 / 记录 #20929
结果：failed；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/changelog/entries",
  "body": {
    "title": "",
    "content": "",
    "version": ""
  },
  "path": "/changelog/entries",
  "query": {},
  "method": "POST",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "596860f2-0d38-4521-a5f7-fefff8ee5c9a",
    "version": "",
    "title": ""
  }
}
```
断言
```json
[
  {
    "type": "api_rejection",
    "actual": {
      "code": 0,
      "http_status": 200
    },
    "passed": false,
    "message": "success",
    "expected": "validation"
  }
]
```

### 更新日志 新增 / spaces / 用例 4405 / 记录 #20930
结果：failed；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/changelog/entries",
  "body": {
    "title": "   ",
    "content": "   ",
    "version": "   "
  },
  "path": "/changelog/entries",
  "query": {},
  "method": "POST",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "97f961fc-92f5-4b50-8a18-6506e74b1f68",
    "version": "   ",
    "title": "   "
  }
}
```
断言
```json
[
  {
    "type": "api_rejection",
    "actual": {
      "code": 0,
      "http_status": 200
    },
    "passed": false,
    "message": "success",
    "expected": "validation"
  }
]
```

### 更新日志 编辑 / control / 用例 4406 / 记录 #20931
结果：success；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/changelog/entries/f13f3928-d046-4c2c-9459-2edb741d8c6e",
  "body": {
    "title": "REQ_20261020_140754_1792476576533_440453 title",
    "content": "REQ_20261020_140754_1792476576533_440453 content",
    "version": "REQ_20261020_140754_1792476576533_440453 version"
  },
  "path": "/changelog/entries/f13f3928-d046-4c2c-9459-2edb741d8c6e",
  "query": {},
  "method": "PATCH",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "f13f3928-d046-4c2c-9459-2edb741d8c6e",
    "version": "REQ_20261020_140754_1792476576533_440453 version",
    "title": "REQ_20261020_140754_1792476576533_440453 title"
  }
}
```
断言
```json
[
  {
    "type": "status",
    "actual": 200,
    "passed": true,
    "expected": 200
  },
  {
    "type": "json_equals",
    "actual": 0,
    "passed": true,
    "expected": 0
  }
]
```

### 更新日志 编辑 / missing / 用例 4407 / 记录 #20932
结果：success；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/changelog/entries/f13f3928-d046-4c2c-9459-2edb741d8c6e",
  "body": {},
  "path": "/changelog/entries/f13f3928-d046-4c2c-9459-2edb741d8c6e",
  "query": {},
  "method": "PATCH",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "f13f3928-d046-4c2c-9459-2edb741d8c6e",
    "version": "REQ_20261020_140754_1792476576533_440453 version",
    "title": "REQ_20261020_140754_1792476576533_440453 title"
  }
}
```
断言
```json
[
  {
    "type": "status",
    "actual": 200,
    "passed": true,
    "expected": 200
  },
  {
    "type": "json_equals",
    "actual": "REQ_20261020_140754_1792476576533_440453 version",
    "passed": true,
    "expected": "REQ_20261020_140754_1792476576533_440453 version"
  },
  {
    "type": "json_equals",
    "actual": "REQ_20261020_140754_1792476576533_440453 title",
    "passed": true,
    "expected": "REQ_20261020_140754_1792476576533_440453 title"
  }
]
```

### 更新日志 编辑 / null / 用例 4408 / 记录 #20933
结果：success；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/changelog/entries/f13f3928-d046-4c2c-9459-2edb741d8c6e",
  "body": {
    "title": null,
    "content": null,
    "version": null
  },
  "path": "/changelog/entries/f13f3928-d046-4c2c-9459-2edb741d8c6e",
  "query": {},
  "method": "PATCH",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "f13f3928-d046-4c2c-9459-2edb741d8c6e",
    "version": "REQ_20261020_140754_1792476576533_440453 version",
    "title": "REQ_20261020_140754_1792476576533_440453 title"
  }
}
```
断言
```json
[
  {
    "type": "status",
    "actual": 200,
    "passed": true,
    "expected": 200
  },
  {
    "type": "json_equals",
    "actual": "REQ_20261020_140754_1792476576533_440453 version",
    "passed": true,
    "expected": "REQ_20261020_140754_1792476576533_440453 version"
  },
  {
    "type": "json_equals",
    "actual": "REQ_20261020_140754_1792476576533_440453 title",
    "passed": true,
    "expected": "REQ_20261020_140754_1792476576533_440453 title"
  }
]
```

### 更新日志 编辑 / empty / 用例 4409 / 记录 #20934
结果：failed；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/changelog/entries/f13f3928-d046-4c2c-9459-2edb741d8c6e",
  "body": {
    "title": "",
    "content": "",
    "version": ""
  },
  "path": "/changelog/entries/f13f3928-d046-4c2c-9459-2edb741d8c6e",
  "query": {},
  "method": "PATCH",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "f13f3928-d046-4c2c-9459-2edb741d8c6e",
    "version": "",
    "title": ""
  }
}
```
断言
```json
[
  {
    "type": "api_rejection",
    "actual": {
      "code": 0,
      "http_status": 200
    },
    "passed": false,
    "message": "success",
    "expected": "validation"
  }
]
```

### 更新日志 编辑 / spaces / 用例 4410 / 记录 #20935
结果：failed；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/changelog/entries/f13f3928-d046-4c2c-9459-2edb741d8c6e",
  "body": {
    "title": "   ",
    "content": "   ",
    "version": "   "
  },
  "path": "/changelog/entries/f13f3928-d046-4c2c-9459-2edb741d8c6e",
  "query": {},
  "method": "PATCH",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "f13f3928-d046-4c2c-9459-2edb741d8c6e",
    "version": "   ",
    "title": "   "
  }
}
```
断言
```json
[
  {
    "type": "api_rejection",
    "actual": {
      "code": 0,
      "http_status": 200
    },
    "passed": false,
    "message": "success",
    "expected": "validation"
  }
]
```

### 非业务会议 新增 / control / 用例 4411 / 记录 #20936
结果：success；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/meeting/records",
  "body": {
    "title": "REQ_20261020_140754_1792476581927_892743 title",
    "meeting_date": "2026-10-15",
    "meeting_type": "project"
  },
  "path": "/meeting/records",
  "query": {},
  "method": "POST",
  "headers": {
    "Content-Type": "application/x-www-form-urlencoded",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "1f252722-be0e-494a-ad57-b1d4b43894cf",
    "title": "REQ_20261020_140754_1792476581927_892743 title",
    "meeting_type": "project",
    "meeting_date": "2026-10-15",
    "status": "transcribed",
    "created_at": "2026-10-20T14:09:43"
  }
}
```
断言
```json
[
  {
    "type": "status",
    "actual": 200,
    "passed": true,
    "expected": 200
  },
  {
    "type": "json_equals",
    "actual": 0,
    "passed": true,
    "expected": 0
  }
]
```

### 非业务会议 新增 / missing / 用例 4412 / 记录 #20937
结果：success；HTTP：422

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/meeting/records",
  "body": {
    "meeting_date": "2026-10-15",
    "meeting_type": "project"
  },
  "path": "/meeting/records",
  "query": {},
  "method": "POST",
  "headers": {
    "Content-Type": "application/x-www-form-urlencoded",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "body",
        "title"
      ],
      "msg": "Field required",
      "input": null
    }
  ]
}
```
断言
```json
[
  {
    "type": "api_rejection",
    "actual": {
      "code": null,
      "http_status": 422
    },
    "passed": true,
    "message": "{\"detail\":[{\"type\":\"missing\",\"loc\":[\"body\",\"title\"],\"msg\":\"Field required\",\"input\":null}]}",
    "expected": "validation"
  }
]
```

### 非业务会议 新增 / empty / 用例 4414 / 记录 #20939
结果：success；HTTP：422

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/meeting/records",
  "body": {
    "title": "",
    "meeting_date": "2026-10-15",
    "meeting_type": "project"
  },
  "path": "/meeting/records",
  "query": {},
  "method": "POST",
  "headers": {
    "Content-Type": "application/x-www-form-urlencoded",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "body",
        "title"
      ],
      "msg": "Field required",
      "input": null
    }
  ]
}
```
断言
```json
[
  {
    "type": "api_rejection",
    "actual": {
      "code": null,
      "http_status": 422
    },
    "passed": true,
    "message": "{\"detail\":[{\"type\":\"missing\",\"loc\":[\"body\",\"title\"],\"msg\":\"Field required\",\"input\":null}]}",
    "expected": "validation"
  }
]
```

### 非业务会议 新增 / spaces / 用例 4415 / 记录 #20940
结果：failed；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/meeting/records",
  "body": {
    "title": "   ",
    "meeting_date": "2026-10-15",
    "meeting_type": "project"
  },
  "path": "/meeting/records",
  "query": {},
  "method": "POST",
  "headers": {
    "Content-Type": "application/x-www-form-urlencoded",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "90a3ed12-8eb3-4ce6-ae01-dfa8476e9cc9",
    "title": "   ",
    "meeting_type": "project",
    "meeting_date": "2026-10-15",
    "status": "transcribed",
    "created_at": "2026-10-20T14:09:47"
  }
}
```
断言
```json
[
  {
    "type": "api_rejection",
    "actual": {
      "code": 0,
      "http_status": 200
    },
    "passed": false,
    "message": "success",
    "expected": "validation"
  }
]
```

### 独立财务账户 新增 / control / 用例 4416 / 记录 #20941
结果：success；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/finance/accounts",
  "body": {
    "currency": "CNY",
    "bank_name": "REQ_20261020_140754_1792476587441_376346 bank_name",
    "entity_id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
    "account_no": "6222000012345678",
    "is_default": false,
    "bank_branch": "REQ_20261020_140754_1792476587441_376346 bank_branch",
    "account_name": "REQ_20261020_140754_1792476587441_376346 account_name",
    "initial_balance": 0,
    "account_category": "public"
  },
  "path": "/finance/accounts",
  "query": {},
  "method": "POST",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "bd8dbb7d-635f-4f82-a444-cb5b65d19f92",
    "entity_id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
    "account_category": "public",
    "account_name": "REQ_20261020_140754_1792476587441_376346 account_name",
    "bank_name": "REQ_20261020_140754_1792476587441_376346 bank_name",
    "bank_branch": "REQ_20261020_140754_1792476587441_376346 bank_branch",
    "account_no_masked": "************5678",
    "currency": "CNY",
    "initial_balance": "0.00",
    "balance": 0,
    "status": "active",
    "is_default": false,
    "shareholder_user_id": null,
    "created_at": "2026-10-20T14:09:48"
  }
}
```
断言
```json
[
  {
    "type": "status",
    "actual": 200,
    "passed": true,
    "expected": 200
  },
  {
    "type": "json_equals",
    "actual": 0,
    "passed": true,
    "expected": 0
  }
]
```

### 独立财务账户 新增 / missing / 用例 4417 / 记录 #20942
结果：success；HTTP：422

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/finance/accounts",
  "body": {
    "currency": "CNY",
    "bank_name": "REQ_20261020_140754_1792476588437_307922 bank_name",
    "entity_id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
    "account_no": "6222000012345678",
    "is_default": false,
    "bank_branch": "REQ_20261020_140754_1792476588437_307922 bank_branch",
    "initial_balance": 0,
    "account_category": "public"
  },
  "path": "/finance/accounts",
  "query": {},
  "method": "POST",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "body",
        "account_name"
      ],
      "msg": "Field required",
      "input": {
        "currency": "CNY",
        "bank_name": "REQ_20261020_140754_1792476588437_307922 bank_name",
        "entity_id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
        "account_no": "6222000012345678",
        "is_default": false,
        "bank_branch": "REQ_20261020_140754_1792476588437_307922 bank_branch",
        "initial_balance": 0,
        "account_category": "public"
      }
    }
  ]
}
```
断言
```json
[
  {
    "type": "api_rejection",
    "actual": {
      "code": null,
      "http_status": 422
    },
    "passed": true,
    "message": "{\"detail\":[{\"type\":\"missing\",\"loc\":[\"body\",\"account_name\"],\"msg\":\"Field required\",\"input\":{\"currency\":\"CNY\",\"bank_name\":\"REQ_20261020_140754_1792476588437_307922 bank_name\",\"entity_id\":\"4952f6f1-9766-452e-a9a4-715e17fa87a0\",\"account_no\":\"6222000012345678\",\"is_default\":false,\"bank_branch\":\"REQ_20261020_140754_1792476588437_307922 bank_branch\",\"initial_balance\":0,\"account_category\":\"public\"}}]}",
    "expected": "validation"
  }
]
```

### 独立财务账户 新增 / null / 用例 4418 / 记录 #20943
结果：success；HTTP：422

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/finance/accounts",
  "body": {
    "currency": "CNY",
    "bank_name": "REQ_20261020_140754_1792476589406_158089 bank_name",
    "entity_id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
    "account_no": "6222000012345678",
    "is_default": false,
    "bank_branch": "REQ_20261020_140754_1792476589406_158089 bank_branch",
    "account_name": null,
    "initial_balance": 0,
    "account_category": "public"
  },
  "path": "/finance/accounts",
  "query": {},
  "method": "POST",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "detail": [
    {
      "type": "string_type",
      "loc": [
        "body",
        "account_name"
      ],
      "msg": "Input should be a valid string",
      "input": null
    }
  ]
}
```
断言
```json
[
  {
    "type": "api_rejection",
    "actual": {
      "code": null,
      "http_status": 422
    },
    "passed": true,
    "message": "{\"detail\":[{\"type\":\"string_type\",\"loc\":[\"body\",\"account_name\"],\"msg\":\"Input should be a valid string\",\"input\":null}]}",
    "expected": "validation"
  }
]
```

### 独立财务账户 新增 / empty / 用例 4419 / 记录 #20944
结果：failed；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/finance/accounts",
  "body": {
    "currency": "CNY",
    "bank_name": "REQ_20261020_140754_1792476590581_042453 bank_name",
    "entity_id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
    "account_no": "6222000012345678",
    "is_default": false,
    "bank_branch": "REQ_20261020_140754_1792476590581_042453 bank_branch",
    "account_name": "",
    "initial_balance": 0,
    "account_category": "public"
  },
  "path": "/finance/accounts",
  "query": {},
  "method": "POST",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "7d02dd0e-cf89-4ee7-b155-a3fa58843178",
    "entity_id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
    "account_category": "public",
    "account_name": "",
    "bank_name": "REQ_20261020_140754_1792476590581_042453 bank_name",
    "bank_branch": "REQ_20261020_140754_1792476590581_042453 bank_branch",
    "account_no_masked": "************5678",
    "currency": "CNY",
    "initial_balance": "0.00",
    "balance": 0,
    "status": "active",
    "is_default": false,
    "shareholder_user_id": null,
    "created_at": "2026-10-20T14:09:51"
  }
}
```
断言
```json
[
  {
    "type": "api_rejection",
    "actual": {
      "code": 0,
      "http_status": 200
    },
    "passed": false,
    "message": "success",
    "expected": "validation"
  }
]
```

### 独立财务账户 新增 / spaces / 用例 4420 / 记录 #20945
结果：failed；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/finance/accounts",
  "body": {
    "currency": "CNY",
    "bank_name": "REQ_20261020_140754_1792476591637_482598 bank_name",
    "entity_id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
    "account_no": "6222000012345678",
    "is_default": false,
    "bank_branch": "REQ_20261020_140754_1792476591637_482598 bank_branch",
    "account_name": "   ",
    "initial_balance": 0,
    "account_category": "public"
  },
  "path": "/finance/accounts",
  "query": {},
  "method": "POST",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "ea5211c6-91b3-46d0-970c-018e90309f48",
    "entity_id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
    "account_category": "public",
    "account_name": "   ",
    "bank_name": "REQ_20261020_140754_1792476591637_482598 bank_name",
    "bank_branch": "REQ_20261020_140754_1792476591637_482598 bank_branch",
    "account_no_masked": "************5678",
    "currency": "CNY",
    "initial_balance": "0.00",
    "balance": 0,
    "status": "active",
    "is_default": false,
    "shareholder_user_id": null,
    "created_at": "2026-10-20T14:09:52"
  }
}
```
断言
```json
[
  {
    "type": "api_rejection",
    "actual": {
      "code": 0,
      "http_status": 200
    },
    "passed": false,
    "message": "success",
    "expected": "validation"
  }
]
```

### 独立财务账户 编辑 / control / 用例 4421 / 记录 #20946
结果：success；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/finance/accounts/bd8dbb7d-635f-4f82-a444-cb5b65d19f92",
  "body": {
    "status": "active",
    "currency": "CNY",
    "bank_name": "REQ_20261020_140754_1792476592640_711574 bank_name",
    "entity_id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
    "account_no": "6222000012345678",
    "is_default": false,
    "bank_branch": "REQ_20261020_140754_1792476592640_711574 bank_branch",
    "account_name": "REQ_20261020_140754_1792476592640_711574 account_name",
    "initial_balance": 0,
    "account_category": "public"
  },
  "path": "/finance/accounts/bd8dbb7d-635f-4f82-a444-cb5b65d19f92",
  "query": {},
  "method": "PATCH",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "bd8dbb7d-635f-4f82-a444-cb5b65d19f92",
    "entity_id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
    "account_category": "public",
    "account_name": "REQ_20261020_140754_1792476592640_711574 account_name",
    "bank_name": "REQ_20261020_140754_1792476592640_711574 bank_name",
    "bank_branch": "REQ_20261020_140754_1792476592640_711574 bank_branch",
    "account_no_masked": "************5678",
    "currency": "CNY",
    "initial_balance": "0.00",
    "balance": 0,
    "status": "active",
    "is_default": false,
    "shareholder_user_id": null,
    "created_at": "2026-10-20T14:09:48"
  }
}
```
断言
```json
[
  {
    "type": "status",
    "actual": 200,
    "passed": true,
    "expected": 200
  },
  {
    "type": "json_equals",
    "actual": 0,
    "passed": true,
    "expected": 0
  }
]
```

### 独立财务账户 编辑 / missing / 用例 4422 / 记录 #20947
结果：success；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/finance/accounts/bd8dbb7d-635f-4f82-a444-cb5b65d19f92",
  "body": {
    "status": "active",
    "currency": "CNY",
    "bank_name": "REQ_20261020_140754_1792476593578_581976 bank_name",
    "entity_id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
    "account_no": "6222000012345678",
    "is_default": false,
    "bank_branch": "REQ_20261020_140754_1792476593578_581976 bank_branch",
    "initial_balance": 0,
    "account_category": "public"
  },
  "path": "/finance/accounts/bd8dbb7d-635f-4f82-a444-cb5b65d19f92",
  "query": {},
  "method": "PATCH",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "bd8dbb7d-635f-4f82-a444-cb5b65d19f92",
    "entity_id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
    "account_category": "public",
    "account_name": "REQ_20261020_140754_1792476592640_711574 account_name",
    "bank_name": "REQ_20261020_140754_1792476593578_581976 bank_name",
    "bank_branch": "REQ_20261020_140754_1792476593578_581976 bank_branch",
    "account_no_masked": "************5678",
    "currency": "CNY",
    "initial_balance": "0.00",
    "balance": 0,
    "status": "active",
    "is_default": false,
    "shareholder_user_id": null,
    "created_at": "2026-10-20T14:09:48"
  }
}
```
断言
```json
[
  {
    "type": "status",
    "actual": 200,
    "passed": true,
    "expected": 200
  },
  {
    "type": "json_equals",
    "actual": "REQ_20261020_140754_1792476592640_711574 account_name",
    "passed": true,
    "expected": "REQ_20261020_140754_1792476592640_711574 account_name"
  }
]
```

### 独立财务账户 编辑 / null / 用例 4423 / 记录 #20948
结果：success；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/finance/accounts/bd8dbb7d-635f-4f82-a444-cb5b65d19f92",
  "body": {
    "status": "active",
    "currency": "CNY",
    "bank_name": "REQ_20261020_140754_1792476594602_514854 bank_name",
    "entity_id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
    "account_no": "6222000012345678",
    "is_default": false,
    "bank_branch": "REQ_20261020_140754_1792476594602_514854 bank_branch",
    "account_name": null,
    "initial_balance": 0,
    "account_category": "public"
  },
  "path": "/finance/accounts/bd8dbb7d-635f-4f82-a444-cb5b65d19f92",
  "query": {},
  "method": "PATCH",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "bd8dbb7d-635f-4f82-a444-cb5b65d19f92",
    "entity_id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
    "account_category": "public",
    "account_name": "REQ_20261020_140754_1792476592640_711574 account_name",
    "bank_name": "REQ_20261020_140754_1792476594602_514854 bank_name",
    "bank_branch": "REQ_20261020_140754_1792476594602_514854 bank_branch",
    "account_no_masked": "************5678",
    "currency": "CNY",
    "initial_balance": "0.00",
    "balance": 0,
    "status": "active",
    "is_default": false,
    "shareholder_user_id": null,
    "created_at": "2026-10-20T14:09:48"
  }
}
```
断言
```json
[
  {
    "type": "status",
    "actual": 200,
    "passed": true,
    "expected": 200
  },
  {
    "type": "json_equals",
    "actual": "REQ_20261020_140754_1792476592640_711574 account_name",
    "passed": true,
    "expected": "REQ_20261020_140754_1792476592640_711574 account_name"
  }
]
```

### 独立财务账户 编辑 / empty / 用例 4424 / 记录 #20949
结果：failed；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/finance/accounts/bd8dbb7d-635f-4f82-a444-cb5b65d19f92",
  "body": {
    "status": "active",
    "currency": "CNY",
    "bank_name": "REQ_20261020_140754_1792476595549_031357 bank_name",
    "entity_id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
    "account_no": "6222000012345678",
    "is_default": false,
    "bank_branch": "REQ_20261020_140754_1792476595549_031357 bank_branch",
    "account_name": "",
    "initial_balance": 0,
    "account_category": "public"
  },
  "path": "/finance/accounts/bd8dbb7d-635f-4f82-a444-cb5b65d19f92",
  "query": {},
  "method": "PATCH",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "bd8dbb7d-635f-4f82-a444-cb5b65d19f92",
    "entity_id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
    "account_category": "public",
    "account_name": "",
    "bank_name": "REQ_20261020_140754_1792476595549_031357 bank_name",
    "bank_branch": "REQ_20261020_140754_1792476595549_031357 bank_branch",
    "account_no_masked": "************5678",
    "currency": "CNY",
    "initial_balance": "0.00",
    "balance": 0,
    "status": "active",
    "is_default": false,
    "shareholder_user_id": null,
    "created_at": "2026-10-20T14:09:48"
  }
}
```
断言
```json
[
  {
    "type": "api_rejection",
    "actual": {
      "code": 0,
      "http_status": 200
    },
    "passed": false,
    "message": "success",
    "expected": "validation"
  }
]
```

### 独立财务账户 编辑 / spaces / 用例 4425 / 记录 #20950
结果：failed；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/finance/accounts/bd8dbb7d-635f-4f82-a444-cb5b65d19f92",
  "body": {
    "status": "active",
    "currency": "CNY",
    "bank_name": "REQ_20261020_140754_1792476596609_038981 bank_name",
    "entity_id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
    "account_no": "6222000012345678",
    "is_default": false,
    "bank_branch": "REQ_20261020_140754_1792476596609_038981 bank_branch",
    "account_name": "   ",
    "initial_balance": 0,
    "account_category": "public"
  },
  "path": "/finance/accounts/bd8dbb7d-635f-4f82-a444-cb5b65d19f92",
  "query": {},
  "method": "PATCH",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "bd8dbb7d-635f-4f82-a444-cb5b65d19f92",
    "entity_id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
    "account_category": "public",
    "account_name": "   ",
    "bank_name": "REQ_20261020_140754_1792476596609_038981 bank_name",
    "bank_branch": "REQ_20261020_140754_1792476596609_038981 bank_branch",
    "account_no_masked": "************5678",
    "currency": "CNY",
    "initial_balance": "0.00",
    "balance": 0,
    "status": "active",
    "is_default": false,
    "shareholder_user_id": null,
    "created_at": "2026-10-20T14:09:48"
  }
}
```
断言
```json
[
  {
    "type": "api_rejection",
    "actual": {
      "code": 0,
      "http_status": 200
    },
    "passed": false,
    "message": "success",
    "expected": "validation"
  }
]
```

### 草稿合同 新增 / control / 用例 4426 / 记录 #20951
结果：success；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/contract/contracts",
  "body": {
    "name": "REQ_20261020_140754_1792476597677_641897 name",
    "currency": "CNY",
    "sign_date": "2026-10-20",
    "party_a_id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
    "party_b_id": "48b300fe-5582-4edc-af68-5af147e2567e",
    "pm_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "contract_no": "CNT-1792476597677-641897",
    "expire_date": "2026-10-30",
    "amount_total": "1.00",
    "contract_type": "sales",
    "payment_plans": [],
    "effective_date": "2026-10-20"
  },
  "path": "/contract/contracts",
  "query": {},
  "method": "POST",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "29bbf155-1012-4088-b9e7-4753e6b134e3",
    "contract_no": "CNT-1792476597677-641897",
    "name": "REQ_20261020_140754_1792476597677_641897 name",
    "contract_type": "sales",
    "status": "draft",
    "party_a_id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
    "party_b_id": "48b300fe-5582-4edc-af68-5af147e2567e",
    "party_c_id": null,
    "owner_user_id": "bdae2ab7-d19e-4976-b662-a300627c1179",
    "pm_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "amount_total": "1.00",
    "pending_amount": "1.00",
    "currency": "CNY",
    "sign_date": "2026-10-20",
    "effective_date": "2026-10-20",
    "expire_date": "2026-10-30",
    "summary": null,
    "attachments": [],
    "created_at": "2026-10-20T14:09:59",
    "updated_at": "2026-10-20T14:09:59"
  }
}
```
断言
```json
[
  {
    "type": "status",
    "actual": 200,
    "passed": true,
    "expected": 200
  },
  {
    "type": "json_equals",
    "actual": 0,
    "passed": true,
    "expected": 0
  }
]
```

### 草稿合同 新增 / missing / 用例 4427 / 记录 #20952
结果：success；HTTP：422

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/contract/contracts",
  "body": {
    "currency": "CNY",
    "sign_date": "2026-10-20",
    "party_a_id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
    "party_b_id": "48b300fe-5582-4edc-af68-5af147e2567e",
    "pm_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "contract_no": "CNT-1792476598737-316763",
    "expire_date": "2026-10-30",
    "amount_total": "1.00",
    "contract_type": "sales",
    "payment_plans": [],
    "effective_date": "2026-10-20"
  },
  "path": "/contract/contracts",
  "query": {},
  "method": "POST",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "body",
        "name"
      ],
      "msg": "Field required",
      "input": {
        "currency": "CNY",
        "sign_date": "2026-10-20",
        "party_a_id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
        "party_b_id": "48b300fe-5582-4edc-af68-5af147e2567e",
        "pm_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
        "contract_no": "CNT-1792476598737-316763",
        "expire_date": "2026-10-30",
        "amount_total": "1.00",
        "contract_type": "sales",
        "payment_plans": [],
        "effective_date": "2026-10-20"
      }
    }
  ]
}
```
断言
```json
[
  {
    "type": "api_rejection",
    "actual": {
      "code": null,
      "http_status": 422
    },
    "passed": true,
    "message": "{\"detail\":[{\"type\":\"missing\",\"loc\":[\"body\",\"name\"],\"msg\":\"Field required\",\"input\":{\"currency\":\"CNY\",\"sign_date\":\"2026-10-20\",\"party_a_id\":\"4952f6f1-9766-452e-a9a4-715e17fa87a0\",\"party_b_id\":\"48b300fe-5582-4edc-af68-5af147e2567e\",\"pm_user_id\":\"5b0b6d34-6b1e-434a-b553-e8f4ca919eb9\",\"contract_no\":\"CNT-1792476598737-316763\",\"expire_date\":\"2026-10-30\",\"amount_total\":\"1.00\",\"contract_type\":\"sales\",\"payment_plans\":[],\"effective_date\":\"2026-10-20\"}}]}",
    "expected": "validation"
  }
]
```

### 草稿合同 新增 / null / 用例 4428 / 记录 #20953
结果：success；HTTP：422

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/contract/contracts",
  "body": {
    "name": null,
    "currency": "CNY",
    "sign_date": "2026-10-20",
    "party_a_id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
    "party_b_id": "48b300fe-5582-4edc-af68-5af147e2567e",
    "pm_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "contract_no": "CNT-1792476599777-071525",
    "expire_date": "2026-10-30",
    "amount_total": "1.00",
    "contract_type": "sales",
    "payment_plans": [],
    "effective_date": "2026-10-20"
  },
  "path": "/contract/contracts",
  "query": {},
  "method": "POST",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "detail": [
    {
      "type": "string_type",
      "loc": [
        "body",
        "name"
      ],
      "msg": "Input should be a valid string",
      "input": null
    }
  ]
}
```
断言
```json
[
  {
    "type": "api_rejection",
    "actual": {
      "code": null,
      "http_status": 422
    },
    "passed": true,
    "message": "{\"detail\":[{\"type\":\"string_type\",\"loc\":[\"body\",\"name\"],\"msg\":\"Input should be a valid string\",\"input\":null}]}",
    "expected": "validation"
  }
]
```

### 草稿合同 新增 / empty / 用例 4429 / 记录 #20954
结果：failed；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/contract/contracts",
  "body": {
    "name": "",
    "currency": "CNY",
    "sign_date": "2026-10-20",
    "party_a_id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
    "party_b_id": "48b300fe-5582-4edc-af68-5af147e2567e",
    "pm_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "contract_no": "CNT-1792476600870-797009",
    "expire_date": "2026-10-30",
    "amount_total": "1.00",
    "contract_type": "sales",
    "payment_plans": [],
    "effective_date": "2026-10-20"
  },
  "path": "/contract/contracts",
  "query": {},
  "method": "POST",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "9c9135ad-2b5b-4528-bedb-ef9b1ad080ab",
    "contract_no": "CNT-1792476600870-797009",
    "name": "",
    "contract_type": "sales",
    "status": "draft",
    "party_a_id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
    "party_b_id": "48b300fe-5582-4edc-af68-5af147e2567e",
    "party_c_id": null,
    "owner_user_id": "bdae2ab7-d19e-4976-b662-a300627c1179",
    "pm_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "amount_total": "1.00",
    "pending_amount": "1.00",
    "currency": "CNY",
    "sign_date": "2026-10-20",
    "effective_date": "2026-10-20",
    "expire_date": "2026-10-30",
    "summary": null,
    "attachments": [],
    "created_at": "2026-10-20T14:10:02",
    "updated_at": "2026-10-20T14:10:02"
  }
}
```
断言
```json
[
  {
    "type": "api_rejection",
    "actual": {
      "code": 0,
      "http_status": 200
    },
    "passed": false,
    "message": "success",
    "expected": "validation"
  }
]
```

### 草稿合同 新增 / spaces / 用例 4430 / 记录 #20955
结果：failed；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/contract/contracts",
  "body": {
    "name": "   ",
    "currency": "CNY",
    "sign_date": "2026-10-20",
    "party_a_id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
    "party_b_id": "48b300fe-5582-4edc-af68-5af147e2567e",
    "pm_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "contract_no": "CNT-1792476601874-466508",
    "expire_date": "2026-10-30",
    "amount_total": "1.00",
    "contract_type": "sales",
    "payment_plans": [],
    "effective_date": "2026-10-20"
  },
  "path": "/contract/contracts",
  "query": {},
  "method": "POST",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "431cce4c-c61b-4818-9913-14a63176fc26",
    "contract_no": "CNT-1792476601874-466508",
    "name": "   ",
    "contract_type": "sales",
    "status": "draft",
    "party_a_id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
    "party_b_id": "48b300fe-5582-4edc-af68-5af147e2567e",
    "party_c_id": null,
    "owner_user_id": "bdae2ab7-d19e-4976-b662-a300627c1179",
    "pm_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "amount_total": "1.00",
    "pending_amount": "1.00",
    "currency": "CNY",
    "sign_date": "2026-10-20",
    "effective_date": "2026-10-20",
    "expire_date": "2026-10-30",
    "summary": null,
    "attachments": [],
    "created_at": "2026-10-20T14:10:03",
    "updated_at": "2026-10-20T14:10:03"
  }
}
```
断言
```json
[
  {
    "type": "api_rejection",
    "actual": {
      "code": 0,
      "http_status": 200
    },
    "passed": false,
    "message": "success",
    "expected": "validation"
  }
]
```

### 草稿合同 编辑 / control / 用例 4431 / 记录 #20956
结果：success；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/contract/contracts/29bbf155-1012-4088-b9e7-4753e6b134e3",
  "body": {
    "name": "REQ_20261020_140754_1792476602868_657522 name",
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
  "path": "/contract/contracts/29bbf155-1012-4088-b9e7-4753e6b134e3",
  "query": {},
  "method": "PATCH",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "29bbf155-1012-4088-b9e7-4753e6b134e3",
    "contract_no": "CNT-1792476597677-641897",
    "name": "REQ_20261020_140754_1792476602868_657522 name",
    "contract_type": "sales",
    "status": "draft",
    "party_a_id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
    "party_b_id": "48b300fe-5582-4edc-af68-5af147e2567e",
    "party_c_id": null,
    "owner_user_id": "bdae2ab7-d19e-4976-b662-a300627c1179",
    "pm_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "amount_total": "1.00",
    "pending_amount": "1.00",
    "currency": "CNY",
    "sign_date": "2026-10-20",
    "effective_date": "2026-10-20",
    "expire_date": "2026-10-30",
    "summary": null,
    "attachments": [],
    "created_at": "2026-10-20T14:09:59",
    "updated_at": "2026-10-20T14:10:04"
  }
}
```
断言
```json
[
  {
    "type": "status",
    "actual": 200,
    "passed": true,
    "expected": 200
  },
  {
    "type": "json_equals",
    "actual": 0,
    "passed": true,
    "expected": 0
  }
]
```

### 草稿合同 编辑 / missing / 用例 4432 / 记录 #20957
结果：success；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/contract/contracts/29bbf155-1012-4088-b9e7-4753e6b134e3",
  "body": {
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
  "path": "/contract/contracts/29bbf155-1012-4088-b9e7-4753e6b134e3",
  "query": {},
  "method": "PATCH",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "29bbf155-1012-4088-b9e7-4753e6b134e3",
    "contract_no": "CNT-1792476597677-641897",
    "name": "REQ_20261020_140754_1792476602868_657522 name",
    "contract_type": "sales",
    "status": "draft",
    "party_a_id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
    "party_b_id": "48b300fe-5582-4edc-af68-5af147e2567e",
    "party_c_id": null,
    "owner_user_id": "bdae2ab7-d19e-4976-b662-a300627c1179",
    "pm_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "amount_total": "1.00",
    "pending_amount": "1.00",
    "currency": "CNY",
    "sign_date": "2026-10-20",
    "effective_date": "2026-10-20",
    "expire_date": "2026-10-30",
    "summary": null,
    "attachments": [],
    "created_at": "2026-10-20T14:09:59",
    "updated_at": "2026-10-20T14:10:05"
  }
}
```
断言
```json
[
  {
    "type": "status",
    "actual": 200,
    "passed": true,
    "expected": 200
  },
  {
    "type": "json_equals",
    "actual": "REQ_20261020_140754_1792476602868_657522 name",
    "passed": true,
    "expected": "REQ_20261020_140754_1792476602868_657522 name"
  }
]
```

### 草稿合同 编辑 / null / 用例 4433 / 记录 #20958
结果：success；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/contract/contracts/29bbf155-1012-4088-b9e7-4753e6b134e3",
  "body": {
    "name": null,
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
  "path": "/contract/contracts/29bbf155-1012-4088-b9e7-4753e6b134e3",
  "query": {},
  "method": "PATCH",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "29bbf155-1012-4088-b9e7-4753e6b134e3",
    "contract_no": "CNT-1792476597677-641897",
    "name": "REQ_20261020_140754_1792476602868_657522 name",
    "contract_type": "sales",
    "status": "draft",
    "party_a_id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
    "party_b_id": "48b300fe-5582-4edc-af68-5af147e2567e",
    "party_c_id": null,
    "owner_user_id": "bdae2ab7-d19e-4976-b662-a300627c1179",
    "pm_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "amount_total": "1.00",
    "pending_amount": "1.00",
    "currency": "CNY",
    "sign_date": "2026-10-20",
    "effective_date": "2026-10-20",
    "expire_date": "2026-10-30",
    "summary": null,
    "attachments": [],
    "created_at": "2026-10-20T14:09:59",
    "updated_at": "2026-10-20T14:10:06"
  }
}
```
断言
```json
[
  {
    "type": "status",
    "actual": 200,
    "passed": true,
    "expected": 200
  },
  {
    "type": "json_equals",
    "actual": "REQ_20261020_140754_1792476602868_657522 name",
    "passed": true,
    "expected": "REQ_20261020_140754_1792476602868_657522 name"
  }
]
```

### 草稿合同 编辑 / empty / 用例 4434 / 记录 #20959
结果：failed；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/contract/contracts/29bbf155-1012-4088-b9e7-4753e6b134e3",
  "body": {
    "name": "",
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
  "path": "/contract/contracts/29bbf155-1012-4088-b9e7-4753e6b134e3",
  "query": {},
  "method": "PATCH",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "29bbf155-1012-4088-b9e7-4753e6b134e3",
    "contract_no": "CNT-1792476597677-641897",
    "name": "",
    "contract_type": "sales",
    "status": "draft",
    "party_a_id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
    "party_b_id": "48b300fe-5582-4edc-af68-5af147e2567e",
    "party_c_id": null,
    "owner_user_id": "bdae2ab7-d19e-4976-b662-a300627c1179",
    "pm_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "amount_total": "1.00",
    "pending_amount": "1.00",
    "currency": "CNY",
    "sign_date": "2026-10-20",
    "effective_date": "2026-10-20",
    "expire_date": "2026-10-30",
    "summary": null,
    "attachments": [],
    "created_at": "2026-10-20T14:09:59",
    "updated_at": "2026-10-20T14:10:07"
  }
}
```
断言
```json
[
  {
    "type": "api_rejection",
    "actual": {
      "code": 0,
      "http_status": 200
    },
    "passed": false,
    "message": "success",
    "expected": "validation"
  }
]
```

### 草稿合同 编辑 / spaces / 用例 4435 / 记录 #20960
结果：failed；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/contract/contracts/29bbf155-1012-4088-b9e7-4753e6b134e3",
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
  "path": "/contract/contracts/29bbf155-1012-4088-b9e7-4753e6b134e3",
  "query": {},
  "method": "PATCH",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "29bbf155-1012-4088-b9e7-4753e6b134e3",
    "contract_no": "CNT-1792476597677-641897",
    "name": "   ",
    "contract_type": "sales",
    "status": "draft",
    "party_a_id": "4952f6f1-9766-452e-a9a4-715e17fa87a0",
    "party_b_id": "48b300fe-5582-4edc-af68-5af147e2567e",
    "party_c_id": null,
    "owner_user_id": "bdae2ab7-d19e-4976-b662-a300627c1179",
    "pm_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "amount_total": "1.00",
    "pending_amount": "1.00",
    "currency": "CNY",
    "sign_date": "2026-10-20",
    "effective_date": "2026-10-20",
    "expire_date": "2026-10-30",
    "summary": null,
    "attachments": [],
    "created_at": "2026-10-20T14:09:59",
    "updated_at": "2026-10-20T14:10:08"
  }
}
```
断言
```json
[
  {
    "type": "api_rejection",
    "actual": {
      "code": 0,
      "http_status": 200
    },
    "passed": false,
    "message": "success",
    "expected": "validation"
  }
]
```

### 项目任务计划 编辑 / control / 用例 4436 / 记录 #20961
结果：success；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/project/projects/2efb27cb-7d26-42bc-89af-3949c79139d3/todos/1376784f-7e16-45e4-877d-6aec114eaafb/plan",
  "body": {
    "title": "REQ_20261020_140754_1792476607994_426713 title",
    "due_at": "2026-10-23T18:00:00+08:00",
    "dev_type": "dev_backend",
    "priority": "p2",
    "description": "REQ_20261020_140754_1792476607994_426713 description",
    "estimated_hours": 0,
    "assignee_user_id": "640d1a5c-bff5-4df0-9e02-cb42f8b46413"
  },
  "path": "/project/projects/2efb27cb-7d26-42bc-89af-3949c79139d3/todos/1376784f-7e16-45e4-877d-6aec114eaafb/plan",
  "query": {},
  "method": "POST",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "1376784f-7e16-45e4-877d-6aec114eaafb",
    "title": "REQ_20261020_140754_1792476607994_426713 title",
    "description": "REQ_20261020_140754_1792476607994_426713 description",
    "status": "open",
    "priority": "p2",
    "assignee_user_id": "640d1a5c-bff5-4df0-9e02-cb42f8b46413",
    "assignee_name": "test_user3",
    "creator_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "creator_name": "test_user1",
    "reviewed_by_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "reviewer_name": "test_user1",
    "due_at": "2026-10-23T18:00:00",
    "estimated_hours": "0.00",
    "submitted_at": null,
    "start_at": null,
    "done_at": null,
    "blocked_reason": null,
    "review_comment": null,
    "dismiss_reason": null,
    "link": {
      "dev_type": "dev_backend",
      "project_id": "2efb27cb-7d26-42bc-89af-3949c79139d3",
      "project_name": "RUN3_PRE_20261020121719 project",
      "reviewer_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9"
    },
    "tags": [
      "dev_backend"
    ],
    "created_at": "2026-10-20T12:17:22",
    "updated_at": "2026-10-20T14:10:09"
  }
}
```
断言
```json
[
  {
    "type": "status",
    "actual": 200,
    "passed": true,
    "expected": 200
  },
  {
    "type": "json_equals",
    "actual": 0,
    "passed": true,
    "expected": 0
  }
]
```

### 项目任务计划 编辑 / missing / 用例 4437 / 记录 #20962
结果：success；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/project/projects/2efb27cb-7d26-42bc-89af-3949c79139d3/todos/1376784f-7e16-45e4-877d-6aec114eaafb/plan",
  "body": {
    "due_at": "2026-10-23T18:00:00+08:00",
    "dev_type": "dev_backend",
    "priority": "p2",
    "description": "REQ_20261020_140754_1792476608967_900246 description",
    "estimated_hours": 0,
    "assignee_user_id": "640d1a5c-bff5-4df0-9e02-cb42f8b46413"
  },
  "path": "/project/projects/2efb27cb-7d26-42bc-89af-3949c79139d3/todos/1376784f-7e16-45e4-877d-6aec114eaafb/plan",
  "query": {},
  "method": "POST",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "1376784f-7e16-45e4-877d-6aec114eaafb",
    "title": "REQ_20261020_140754_1792476607994_426713 title",
    "description": "REQ_20261020_140754_1792476608967_900246 description",
    "status": "open",
    "priority": "p2",
    "assignee_user_id": "640d1a5c-bff5-4df0-9e02-cb42f8b46413",
    "assignee_name": "test_user3",
    "creator_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "creator_name": "test_user1",
    "reviewed_by_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "reviewer_name": "test_user1",
    "due_at": "2026-10-23T18:00:00",
    "estimated_hours": "0.00",
    "submitted_at": null,
    "start_at": null,
    "done_at": null,
    "blocked_reason": null,
    "review_comment": null,
    "dismiss_reason": null,
    "link": {
      "dev_type": "dev_backend",
      "project_id": "2efb27cb-7d26-42bc-89af-3949c79139d3",
      "project_name": "RUN3_PRE_20261020121719 project",
      "reviewer_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9"
    },
    "tags": [
      "dev_backend"
    ],
    "created_at": "2026-10-20T12:17:22",
    "updated_at": "2026-10-20T14:10:10"
  }
}
```
断言
```json
[
  {
    "type": "status",
    "actual": 200,
    "passed": true,
    "expected": 200
  },
  {
    "type": "json_equals",
    "actual": "REQ_20261020_140754_1792476607994_426713 title",
    "passed": true,
    "expected": "REQ_20261020_140754_1792476607994_426713 title"
  }
]
```

### 项目任务计划 编辑 / null / 用例 4438 / 记录 #20963
结果：success；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/project/projects/2efb27cb-7d26-42bc-89af-3949c79139d3/todos/1376784f-7e16-45e4-877d-6aec114eaafb/plan",
  "body": {
    "title": null,
    "due_at": "2026-10-23T18:00:00+08:00",
    "dev_type": "dev_backend",
    "priority": "p2",
    "description": "REQ_20261020_140754_1792476610201_808906 description",
    "estimated_hours": 0,
    "assignee_user_id": "640d1a5c-bff5-4df0-9e02-cb42f8b46413"
  },
  "path": "/project/projects/2efb27cb-7d26-42bc-89af-3949c79139d3/todos/1376784f-7e16-45e4-877d-6aec114eaafb/plan",
  "query": {},
  "method": "POST",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "1376784f-7e16-45e4-877d-6aec114eaafb",
    "title": "REQ_20261020_140754_1792476607994_426713 title",
    "description": "REQ_20261020_140754_1792476610201_808906 description",
    "status": "open",
    "priority": "p2",
    "assignee_user_id": "640d1a5c-bff5-4df0-9e02-cb42f8b46413",
    "assignee_name": "test_user3",
    "creator_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "creator_name": "test_user1",
    "reviewed_by_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
    "reviewer_name": "test_user1",
    "due_at": "2026-10-23T18:00:00",
    "estimated_hours": "0.00",
    "submitted_at": null,
    "start_at": null,
    "done_at": null,
    "blocked_reason": null,
    "review_comment": null,
    "dismiss_reason": null,
    "link": {
      "dev_type": "dev_backend",
      "project_id": "2efb27cb-7d26-42bc-89af-3949c79139d3",
      "project_name": "RUN3_PRE_20261020121719 project",
      "reviewer_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9"
    },
    "tags": [
      "dev_backend"
    ],
    "created_at": "2026-10-20T12:17:22",
    "updated_at": "2026-10-20T14:10:11"
  }
}
```
断言
```json
[
  {
    "type": "status",
    "actual": 200,
    "passed": true,
    "expected": 200
  },
  {
    "type": "json_equals",
    "actual": "REQ_20261020_140754_1792476607994_426713 title",
    "passed": true,
    "expected": "REQ_20261020_140754_1792476607994_426713 title"
  }
]
```

### 项目任务计划 编辑 / empty / 用例 4439 / 记录 #20964
结果：success；HTTP：400

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/project/projects/2efb27cb-7d26-42bc-89af-3949c79139d3/todos/1376784f-7e16-45e4-877d-6aec114eaafb/plan",
  "body": {
    "title": "",
    "due_at": "2026-10-23T18:00:00+08:00",
    "dev_type": "dev_backend",
    "priority": "p2",
    "description": "REQ_20261020_140754_1792476611190_047699 description",
    "estimated_hours": 0,
    "assignee_user_id": "640d1a5c-bff5-4df0-9e02-cb42f8b46413"
  },
  "path": "/project/projects/2efb27cb-7d26-42bc-89af-3949c79139d3/todos/1376784f-7e16-45e4-877d-6aec114eaafb/plan",
  "query": {},
  "method": "POST",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 400,
  "message": "Task title cannot be empty",
  "errors": null
}
```
断言
```json
[
  {
    "type": "api_rejection",
    "actual": {
      "code": 400,
      "http_status": 400
    },
    "passed": true,
    "message": "Task title cannot be empty",
    "expected": "validation"
  }
]
```

### 项目任务计划 编辑 / spaces / 用例 4440 / 记录 #20965
结果：success；HTTP：400

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/project/projects/2efb27cb-7d26-42bc-89af-3949c79139d3/todos/1376784f-7e16-45e4-877d-6aec114eaafb/plan",
  "body": {
    "title": "   ",
    "due_at": "2026-10-23T18:00:00+08:00",
    "dev_type": "dev_backend",
    "priority": "p2",
    "description": "REQ_20261020_140754_1792476612140_890643 description",
    "estimated_hours": 0,
    "assignee_user_id": "640d1a5c-bff5-4df0-9e02-cb42f8b46413"
  },
  "path": "/project/projects/2efb27cb-7d26-42bc-89af-3949c79139d3/todos/1376784f-7e16-45e4-877d-6aec114eaafb/plan",
  "query": {},
  "method": "POST",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 400,
  "message": "Task title cannot be empty",
  "errors": null
}
```
断言
```json
[
  {
    "type": "api_rejection",
    "actual": {
      "code": 400,
      "http_status": 400
    },
    "passed": true,
    "message": "Task title cannot be empty",
    "expected": "validation"
  }
]
```

### 交易方 编辑 / missing / 用例 4367 / 记录 #20966
结果：success；HTTP：422

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/contract/counterparties/05731497-a7b3-471c-9332-c3b103cb239b",
  "body": {
    "type": "customer",
    "phone": "13800138000",
    "address": "REQ_20261020_140754_1792476671597_579193 address",
    "bank_name": "REQ_20261020_140754_1792476671597_579193 bank_name",
    "identifier": "RQ1792476671597579193",
    "bank_account": "6222000012345678"
  },
  "path": "/contract/counterparties/05731497-a7b3-471c-9332-c3b103cb239b",
  "query": {},
  "method": "PATCH",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "body",
        "name"
      ],
      "msg": "Field required",
      "input": {
        "type": "customer",
        "phone": "13800138000",
        "address": "REQ_20261020_140754_1792476671597_579193 address",
        "bank_name": "REQ_20261020_140754_1792476671597_579193 bank_name",
        "identifier": "RQ1792476671597579193",
        "bank_account": "6222000012345678"
      }
    }
  ]
}
```
断言
```json
[
  {
    "type": "api_rejection",
    "actual": {
      "code": null,
      "http_status": 422
    },
    "passed": true,
    "message": "{\"detail\":[{\"type\":\"missing\",\"loc\":[\"body\",\"name\"],\"msg\":\"Field required\",\"input\":{\"type\":\"customer\",\"phone\":\"13800138000\",\"address\":\"REQ_20261020_140754_1792476671597_579193 address\",\"bank_name\":\"REQ_20261020_140754_1792476671597_579193 bank_name\",\"identifier\":\"RQ1792476671597579193\",\"bank_account\":\"6222000012345678\"}}]}",
    "expected": "validation"
  }
]
```

### 交易方 编辑 / null / 用例 4368 / 记录 #20967
结果：success；HTTP：422

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/contract/counterparties/05731497-a7b3-471c-9332-c3b103cb239b",
  "body": {
    "name": null,
    "type": "customer",
    "phone": "13800138000",
    "address": "REQ_20261020_140754_1792476672643_698755 address",
    "bank_name": "REQ_20261020_140754_1792476672643_698755 bank_name",
    "identifier": "RQ1792476672643698755",
    "bank_account": "6222000012345678"
  },
  "path": "/contract/counterparties/05731497-a7b3-471c-9332-c3b103cb239b",
  "query": {},
  "method": "PATCH",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "detail": [
    {
      "type": "string_type",
      "loc": [
        "body",
        "name"
      ],
      "msg": "Input should be a valid string",
      "input": null
    }
  ]
}
```
断言
```json
[
  {
    "type": "api_rejection",
    "actual": {
      "code": null,
      "http_status": 422
    },
    "passed": true,
    "message": "{\"detail\":[{\"type\":\"string_type\",\"loc\":[\"body\",\"name\"],\"msg\":\"Input should be a valid string\",\"input\":null}]}",
    "expected": "validation"
  }
]
```

### 员工 编辑 / read / 用例 4441 / 记录 #20968
结果：success；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/iam/users/b65fa560-e319-4363-84b0-5dbf9e2f2728",
  "body": {},
  "path": "/iam/users/b65fa560-e319-4363-84b0-5dbf9e2f2728",
  "query": {},
  "method": "GET",
  "headers": {
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "b65fa560-e319-4363-84b0-5dbf9e2f2728",
    "display_name": "test_requset_leave",
    "username": "test_user4",
    "email": null,
    "phone": null,
    "status": "active",
    "is_shareholder": false,
    "level": 2,
    "manager_user_id": "0830f805-3a2f-4ce2-a6d4-b0055a3b88f5",
    "manager_name": "test_user2",
    "job_title_id": "6e7b5c6d-5e51-465c-ae5e-c94416536349",
    "job_title_name": "API Workflow Test",
    "department_id": null,
    "department_name": null,
    "birthday": null,
    "id_number": null,
    "home_address": null,
    "graduation_school": null,
    "education_level": null,
    "id_card_image": null,
    "resume_file": null,
    "profile_completed": true,
    "must_change_password": false,
    "leave_annual_remaining": 0.0,
    "leave_maternity_remaining": 15.0,
    "leave_marriage_remaining": 3.0,
    "leave_personal_remaining": 3.0,
    "leave_sick_remaining": 3.0,
    "beili_balance": 0.0,
    "created_at": "2026-05-12T12:13:01"
  }
}
```
断言
```json
[
  {
    "type": "status",
    "actual": 200,
    "passed": true,
    "expected": 200
  }
]
```

### 员工 编辑 / missing / 用例 4442 / 记录 #20974
结果：success；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/iam/users/b65fa560-e319-4363-84b0-5dbf9e2f2728",
  "body": {},
  "path": "/iam/users/b65fa560-e319-4363-84b0-5dbf9e2f2728",
  "query": {},
  "method": "PATCH",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "b65fa560-e319-4363-84b0-5dbf9e2f2728",
    "display_name": "test_requset_leave",
    "username": "test_user4",
    "email": null,
    "phone": null,
    "status": "active",
    "is_shareholder": false,
    "level": 2,
    "manager_user_id": "0830f805-3a2f-4ce2-a6d4-b0055a3b88f5",
    "manager_name": "test_user2",
    "job_title_id": "6e7b5c6d-5e51-465c-ae5e-c94416536349",
    "job_title_name": "API Workflow Test",
    "department_id": null,
    "department_name": null,
    "birthday": null,
    "id_number": null,
    "home_address": null,
    "graduation_school": null,
    "education_level": null,
    "id_card_image": null,
    "resume_file": null,
    "profile_completed": true,
    "must_change_password": false,
    "leave_annual_remaining": 0.0,
    "leave_maternity_remaining": 15.0,
    "leave_marriage_remaining": 3.0,
    "leave_personal_remaining": 3.0,
    "leave_sick_remaining": 3.0,
    "beili_balance": 0.0,
    "created_at": "2026-05-12T12:13:01"
  }
}
```
断言
```json
[
  {
    "type": "status",
    "actual": 200,
    "passed": true,
    "expected": 200
  },
  {
    "type": "json_equals",
    "actual": "test_requset_leave",
    "passed": true,
    "expected": "test_requset_leave"
  }
]
```

### 员工 编辑 / null / 用例 4443 / 记录 #20975
结果：success；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/iam/users/b65fa560-e319-4363-84b0-5dbf9e2f2728",
  "body": {
    "display_name": null
  },
  "path": "/iam/users/b65fa560-e319-4363-84b0-5dbf9e2f2728",
  "query": {},
  "method": "PATCH",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "b65fa560-e319-4363-84b0-5dbf9e2f2728",
    "display_name": "test_requset_leave",
    "username": "test_user4",
    "email": null,
    "phone": null,
    "status": "active",
    "is_shareholder": false,
    "level": 2,
    "manager_user_id": "0830f805-3a2f-4ce2-a6d4-b0055a3b88f5",
    "manager_name": "test_user2",
    "job_title_id": "6e7b5c6d-5e51-465c-ae5e-c94416536349",
    "job_title_name": "API Workflow Test",
    "department_id": null,
    "department_name": null,
    "birthday": null,
    "id_number": null,
    "home_address": null,
    "graduation_school": null,
    "education_level": null,
    "id_card_image": null,
    "resume_file": null,
    "profile_completed": true,
    "must_change_password": false,
    "leave_annual_remaining": 0.0,
    "leave_maternity_remaining": 15.0,
    "leave_marriage_remaining": 3.0,
    "leave_personal_remaining": 3.0,
    "leave_sick_remaining": 3.0,
    "beili_balance": 0.0,
    "created_at": "2026-05-12T12:13:01"
  }
}
```
断言
```json
[
  {
    "type": "status",
    "actual": 200,
    "passed": true,
    "expected": 200
  },
  {
    "type": "json_equals",
    "actual": "test_requset_leave",
    "passed": true,
    "expected": "test_requset_leave"
  }
]
```

### 员工 编辑 / empty / 用例 4444 / 记录 #20976
结果：failed；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/iam/users/b65fa560-e319-4363-84b0-5dbf9e2f2728",
  "body": {
    "display_name": ""
  },
  "path": "/iam/users/b65fa560-e319-4363-84b0-5dbf9e2f2728",
  "query": {},
  "method": "PATCH",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "b65fa560-e319-4363-84b0-5dbf9e2f2728",
    "display_name": "",
    "username": "test_user4",
    "email": null,
    "phone": null,
    "status": "active",
    "is_shareholder": false,
    "level": 2,
    "manager_user_id": "0830f805-3a2f-4ce2-a6d4-b0055a3b88f5",
    "manager_name": "test_user2",
    "job_title_id": "6e7b5c6d-5e51-465c-ae5e-c94416536349",
    "job_title_name": "API Workflow Test",
    "department_id": null,
    "department_name": null,
    "birthday": null,
    "id_number": null,
    "home_address": null,
    "graduation_school": null,
    "education_level": null,
    "id_card_image": null,
    "resume_file": null,
    "profile_completed": true,
    "must_change_password": false,
    "leave_annual_remaining": 0.0,
    "leave_maternity_remaining": 15.0,
    "leave_marriage_remaining": 3.0,
    "leave_personal_remaining": 3.0,
    "leave_sick_remaining": 3.0,
    "beili_balance": 0.0,
    "created_at": "2026-05-12T12:13:01"
  }
}
```
断言
```json
[
  {
    "type": "api_rejection",
    "actual": {
      "code": 0,
      "http_status": 200
    },
    "passed": false,
    "message": "success",
    "expected": "validation"
  }
]
```

### 员工 编辑 / spaces / 用例 4445 / 记录 #20977
结果：failed；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/iam/users/b65fa560-e319-4363-84b0-5dbf9e2f2728",
  "body": {
    "display_name": "   "
  },
  "path": "/iam/users/b65fa560-e319-4363-84b0-5dbf9e2f2728",
  "query": {},
  "method": "PATCH",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "b65fa560-e319-4363-84b0-5dbf9e2f2728",
    "display_name": "   ",
    "username": "test_user4",
    "email": null,
    "phone": null,
    "status": "active",
    "is_shareholder": false,
    "level": 2,
    "manager_user_id": "0830f805-3a2f-4ce2-a6d4-b0055a3b88f5",
    "manager_name": "test_user2",
    "job_title_id": "6e7b5c6d-5e51-465c-ae5e-c94416536349",
    "job_title_name": "API Workflow Test",
    "department_id": null,
    "department_name": null,
    "birthday": null,
    "id_number": null,
    "home_address": null,
    "graduation_school": null,
    "education_level": null,
    "id_card_image": null,
    "resume_file": null,
    "profile_completed": true,
    "must_change_password": false,
    "leave_annual_remaining": 0.0,
    "leave_maternity_remaining": 15.0,
    "leave_marriage_remaining": 3.0,
    "leave_personal_remaining": 3.0,
    "leave_sick_remaining": 3.0,
    "beili_balance": 0.0,
    "created_at": "2026-05-12T12:13:01"
  }
}
```
断言
```json
[
  {
    "type": "api_rejection",
    "actual": {
      "code": 0,
      "http_status": 200
    },
    "passed": false,
    "message": "success",
    "expected": "validation"
  }
]
```

### 员工 编辑 / restore / 用例 4446 / 记录 #20978
结果：success；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/iam/users/b65fa560-e319-4363-84b0-5dbf9e2f2728",
  "body": {
    "display_name": "test_requset_leave"
  },
  "path": "/iam/users/b65fa560-e319-4363-84b0-5dbf9e2f2728",
  "query": {},
  "method": "PATCH",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "b65fa560-e319-4363-84b0-5dbf9e2f2728",
    "display_name": "test_requset_leave",
    "username": "test_user4",
    "email": null,
    "phone": null,
    "status": "active",
    "is_shareholder": false,
    "level": 2,
    "manager_user_id": "0830f805-3a2f-4ce2-a6d4-b0055a3b88f5",
    "manager_name": "test_user2",
    "job_title_id": "6e7b5c6d-5e51-465c-ae5e-c94416536349",
    "job_title_name": "API Workflow Test",
    "department_id": null,
    "department_name": null,
    "birthday": null,
    "id_number": null,
    "home_address": null,
    "graduation_school": null,
    "education_level": null,
    "id_card_image": null,
    "resume_file": null,
    "profile_completed": true,
    "must_change_password": false,
    "leave_annual_remaining": 0.0,
    "leave_maternity_remaining": 15.0,
    "leave_marriage_remaining": 3.0,
    "leave_personal_remaining": 3.0,
    "leave_sick_remaining": 3.0,
    "beili_balance": 0.0,
    "created_at": "2026-05-12T12:13:01"
  }
}
```
断言
```json
[
  {
    "type": "status",
    "actual": 200,
    "passed": true,
    "expected": 200
  },
  {
    "type": "json_equals",
    "actual": "test_requset_leave",
    "passed": true,
    "expected": "test_requset_leave"
  }
]
```

### 更新日志 回读 / readback / 用例 4447 / 记录 #20979
结果：success；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/changelog/entries?page_size=1&page=1",
  "body": {},
  "path": "/changelog/entries?page_size=1&page=1",
  "query": {},
  "method": "GET",
  "headers": {
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": "97f961fc-92f5-4b50-8a18-6506e74b1f68",
        "version": "   ",
        "title": "   ",
        "content": "   ",
        "published_by_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
        "published_by_name": "test_user1",
        "published_at": "2026-10-20T14:09:36",
        "created_at": "2026-10-20T14:09:36",
        "updated_at": "2026-10-20T14:09:36"
      }
    ],
    "total": 23,
    "page": 1,
    "page_size": 1
  }
}
```
断言
```json
[
  {
    "type": "status",
    "actual": 200,
    "passed": true,
    "expected": 200
  }
]
```

### 更新日志 回读 / readback / 用例 4448 / 记录 #20980
结果：success；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/changelog/entries?page_size=1&page=2",
  "body": {},
  "path": "/changelog/entries?page_size=1&page=2",
  "query": {},
  "method": "GET",
  "headers": {
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": "596860f2-0d38-4521-a5f7-fefff8ee5c9a",
        "version": "",
        "title": "",
        "content": "",
        "published_by_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
        "published_by_name": "test_user1",
        "published_at": "2026-10-20T14:09:35",
        "created_at": "2026-10-20T14:09:35",
        "updated_at": "2026-10-20T14:09:35"
      }
    ],
    "total": 23,
    "page": 2,
    "page_size": 1
  }
}
```
断言
```json
[
  {
    "type": "status",
    "actual": 200,
    "passed": true,
    "expected": 200
  }
]
```

### 更新日志 回读 / readback / 用例 4449 / 记录 #20981
结果：success；HTTP：200

请求参数
```json
{
  "url": "http://14.103.229.153:15173/api/v1/changelog/entries?page_size=1&page=3",
  "body": {},
  "path": "/changelog/entries?page_size=1&page=3",
  "query": {},
  "method": "GET",
  "headers": {
    "Authorization": "***"
  },
  "timeout": 30,
  "base_url": "http://14.103.229.153:15173/",
  "api_base_path": "/api/v1"
}
```
返回结果
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": "f13f3928-d046-4c2c-9459-2edb741d8c6e",
        "version": "   ",
        "title": "   ",
        "content": "   ",
        "published_by_user_id": "5b0b6d34-6b1e-434a-b553-e8f4ca919eb9",
        "published_by_name": "test_user1",
        "published_at": "2026-10-20T14:09:32",
        "created_at": "2026-10-20T14:09:32",
        "updated_at": "2026-10-20T14:09:42"
      }
    ],
    "total": 23,
    "page": 3,
    "page_size": 1
  }
}
```
断言
```json
[
  {
    "type": "status",
    "actual": 200,
    "passed": true,
    "expected": 200
  }
]
```
