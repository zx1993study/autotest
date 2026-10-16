# 外勤小星添加接口核对报告

范围：仅业务管理下的添加接口。业务数据库只读；不执行编辑、删除、审批或出入库接口。

正式用例 193 条，已执行 193 条，通过 167 条，失败 26 条。

正常添加断言：HTTP=200 且 code=200。异常用例必须合理拒绝；内部异常不视为通过。

仅对已经逐条确认的业务拒绝提示允许 code=500；使用完整消息白名单，不接受 SQL 或内部异常。

正常添加：14/14 通过。另有 17 条无效字段相关用例已停用，历史记录保留。

## 正常添加

| 接口 ID | 正式用例 | 记录 ID | HTTP | code | 结果 | 信息 |
|---|---|---|---|---|---|---|
| 12110 | #84 [正常] | #15777 | 200 | 200 | success | 新增成功 |
| 12186 | #104 [正常] | #15767 | 200 | 200 | success | 新增成功 |
| 12102 | #121 [正常] | #15766 | 200 | 200 | success | 新增成功 |
| 12119 | #149 [正常] | #15769 | 200 | 200 | success | 新增成功 |
| 12126 | #159 [正常] | #15788 | 200 | 200 | success | 申请成功，共1个客户 |
| 12137 | #179 [正常] | #15768 | 200 | 200 | success | 督办任务创建成功，共1条 |
| 12143 | #194 [正常] | #15775 | 200 | 200 | success | 新增成功 |
| 12144 | #210 [正常] | #15776 | 200 | 200 | success | 成功提交1个拜访计划 |
| 12156 | #220 [正常] | #15773 | 200 | 200 | success | 操作成功 |
| 12167 | #232 [正常] | #15774 | 200 | 200 | success | 临时拜访上报成功 |
| 12199 | #242 [正常] | #15764 | 200 | 200 | success | 新增成功，但审批流程启动失败:  |
| 12205 | #253 [正常] | #15772 | 200 | 200 | success | 创建成功 |
| 12221 | #261 [正常] | #15790 | 200 | 200 | success | 新增成功，直接进入审核中状态 |
| 12244 | #269 [正常] | #15770 | 200 | 200 | success | 新增成功 |

## 未通过用例

| 接口 ID | 正式用例 | 记录 ID | HTTP | code | 结果 | 信息 |
|---|---|---|---|---|---|---|
| 12110 | #86 [格式错误] endTime (date-time) | #15569 | 200 | 500 | failed | (asyncmy.errors.OperationalError) (1292, "Incorrect datetime value: 'not-a-valid-value' for column 'end_time' at row 1") [SQL: INSERT INTO activity (activity_name, activity_type, approval_status, approval_instance_id, visible_dept_ids, visible_user_i |
| 12110 | #87 [类型错误] endTime | #15570 | 200 | 200 | failed | 新增成功 |
| 12110 | #89 [格式错误] startTime (date-time) | #15573 | 200 | 500 | failed | (asyncmy.errors.OperationalError) (1292, "Incorrect datetime value: 'not-a-valid-value' for column 'start_time' at row 1") [SQL: INSERT INTO activity (activity_name, activity_type, approval_status, approval_instance_id, visible_dept_ids, visible_user |
| 12110 | #90 [类型错误] startTime | #15572 | 200 | 200 | failed | 新增成功 |
| 12110 | #99 [低于最小长度] activityName | #15582 | 200 | 200 | failed | 新增成功 |
| 12110 | #101 [超过最大长度] activityName | #15584 | 200 | 500 | failed | (asyncmy.errors.DataError) (1406, "Data too long for column 'activity_name' at row 1") [SQL: INSERT INTO activity (activity_name, activity_type, approval_status, approval_instance_id, visible_dept_ids, visible_user_ids, paid_items, product_scope, pro |
| 12186 | #111 [缺失必填] warehouseName | #15592 | 200 | 500 | failed | (asyncmy.errors.IntegrityError) (1048, "Column 'warehouse_name' cannot be null") [SQL: INSERT INTO warehouse (warehouse_code, warehouse_name, warehouse_type, customer_id, customer_name, address, manager_name, manager_phone, admin_user_id, status, rem |
| 12186 | #113 [低于最小长度] warehouseName | #15594 | 200 | 200 | failed | 新增成功 |
| 12186 | #115 [超过最大长度] warehouseName | #15597 | 200 | 500 | failed | (asyncmy.errors.DataError) (1406, "Data too long for column 'warehouse_name' at row 1") [SQL: INSERT INTO warehouse (warehouse_code, warehouse_name, warehouse_type, customer_id, customer_name, address, manager_name, manager_phone, admin_user_id, stat |
| 12102 | #144 [低于最小长度] productName | #15625 | 200 | 200 | failed | 新增成功 |
| 12102 | #146 [超过最大长度] productName | #15627 | 200 | 500 | failed | (asyncmy.errors.DataError) (1406, "Data too long for column 'product_name' at row 1") [SQL: INSERT INTO product (product_name, product_code, product_spec, product_spec_first, product_spec_second, product_type, product_brand, unit, barcode, product_im |
| 12119 | #156 [超过最大长度] activityTypeName | #15636 | 200 | 500 | failed | (asyncmy.errors.DataError) (1406, "Data too long for column 'activity_type_name' at row 1") [SQL: INSERT INTO activity_type_config (activity_type, activity_type_name, need_execute_report, need_payment_report, sort, status, create_by, create_time, upd |
| 12126 | #167 [格式错误] endTime (date-time) | #15646 | 200 | 500 | failed | (asyncmy.errors.OperationalError) (1292, "Incorrect datetime value: 'not-a-valid-value' for column 'end_time' at row 1") [SQL: INSERT INTO activity_apply (activity_id, activity_name, activity_type, template_snapshot, start_time, end_time, expected_pa |
| 12126 | #168 [类型错误] endTime | #15648 | 200 | 200 | failed | 申请成功，共1个客户 |
| 12126 | #170 [格式错误] startTime (date-time) | #15649 | 200 | 500 | failed | (asyncmy.errors.OperationalError) (1292, "Incorrect datetime value: 'not-a-valid-value' for column 'start_time' at row 1") [SQL: INSERT INTO activity_apply (activity_id, activity_name, activity_type, template_snapshot, start_time, end_time, expected_ |
| 12126 | #171 [类型错误] startTime | #15651 | 200 | 200 | failed | 申请成功，共1个客户 |
| 12126 | #174 [少于最少元素] customers | #15652 | 200 | 200 | failed | 申请成功，共0个客户 |
| 12137 | #185 [格式错误] requiredFinishTime (date-time) | #15663 | 200 | 500 | failed | (asyncmy.errors.OperationalError) (1292, "Incorrect datetime value: 'not-a-valid-value' for column 'required_finish_time' at row 1") [SQL: INSERT INTO activity_supervision_task (customer_ids, customer_names, responsible_user_id, responsible_user_name |
| 12137 | #186 [类型错误] requiredFinishTime | #15665 | 200 | 200 | failed | 督办任务创建成功，共1条 |
| 12143 | #196 [超过最大长度] remark | #15673 | 200 | 500 | failed | (asyncmy.errors.DataError) (1406, "Data too long for column 'remark' at row 1") [SQL: INSERT INTO visit_plan (visitor_user_id, visitor_user_name, template_id, report_config_snapshot, customer_type, customer_id, customer_name, terminal_type, visit_dat |
| 12143 | #199 [格式错误] visitDate (date-time) | #15677 | 200 | 500 | failed | (asyncmy.errors.OperationalError) (1292, "Incorrect datetime value: 'not-a-valid-value' for column 'visit_date' at row 1") [SQL: INSERT INTO visit_plan (visitor_user_id, visitor_user_name, template_id, report_config_snapshot, customer_type, customer_ |
| 12143 | #200 [类型错误] visitDate | #15676 | 200 | 200 | failed | 新增成功 |
| 12144 | #213 [少于最少元素] visitPlans | #15688 | 200 | 200 | failed | 拜访计划列表不能为空 |
| 12156 | #227 [低于最小长度] templateName | #15702 | 200 | 200 | failed | 操作成功 |
| 12156 | #229 [超过最大长度] templateName | #15704 | 200 | 500 | failed | (asyncmy.errors.DataError) (1406, "Data too long for column 'template_name' at row 1") [SQL: INSERT INTO visit_template (template_name, user_id, distributor_id, remark, del_flag, create_by, create_time, update_by, update_time) VALUES (%s, %s, %s, %s, |
| 12167 | #236 [超过最大长度] remark | #15711 | 200 | 500 | failed | (asyncmy.errors.DataError) (1406, "Data too long for column 'remark' at row 1") [SQL: INSERT INTO visit_report (visit_plan_id, report_type, product_id, product_name, inventory_quantity, images, remark, report_time, address, customer_name, check_in_lo |

## 参数基线

- 输入为自然业务名称；自由文本追加毫秒时间戳与场景后缀，保持长度约束。
- 枚举、时间、图片地址与关联名称不追加时间戳。
- 可选主键、审计字段、展示字段与审批输出字段不发送。
- 执行证据及每次实际请求参数保存在 executions.json；不包含认证头或数据库密钥。

## 已修正

- 活动类型配置：补充数据库已存在且字段库支持的申请、执行模板；不复制主键和审计字段。
- 活动申请：日期使用 YYYY-MM-DD HH:mm:ss；依据实际模板仅发送活动 ID、客户和起止时间。当前模板未配置的备注、人数、商品、费用等字段已剔除。关联活动排除测试产生的 1970 年异常日期数据。
- 督办添加：客户改为当前身份已经具有督办权限、审核通过的客户；客户 ID 与名称同步保留。
- 数组正向边界：保留正常基线中经过数据库确认的商品、客户 ID，不再生成 ID=1 的占位数据。
- 编号：warehouseCode、productCode、orderNo 由服务端生成，不再发送或测试其输入长度。
- 异常断言：六条已逐项确认的业务校验提示使用完整消息白名单允许 code=500；内部错误和正常添加 code=500 仍失败。
- 退货添加：单头总数量为 1，总金额为数据库商品销售价 300，与商品明细保持一致；已重新执行正常和正向边界用例。

## 服务端待处理

- 14 条异常策略直接暴露数据库错误：非法日期、超长字符串、仓库名称缺失。建议业务服务端补充写库前校验，避免返回 SQL、参数和内部异常详情。
- 12 条异常策略返回 code=200：数值日期被转换为 1970 年日期、空名称、空客户列表或空拜访列表等。部分非空边界属于业务规则建议，需确认后补齐 OpenAPI 的 minLength/minItems；不能仅把断言改成期待成功。
- 采购正常添加虽返回 code=200 并保存草稿，但提示审批流程启动失败。数据库中流程 #11 为非默认、发起角色 #2；执行管理员只有角色 #1。存在流程/角色匹配风险，具体异常仍需服务端日志确认，不在本批次擅自改审批配置。
- 历史执行记录 #15723 出现采购自动编号唯一键冲突。疑似并发编号生成问题，需要服务端核查；对应自动编号输入场景已停用，原始冲突证据仍保留。
- 退货添加本身会自动进入审核中；未调用额外审批接口，不代表添加没有工作流状态变化。
- 外勤小星业务服务端实现不在当前仓库，剩余问题不能在测试平台代码中直接修复。失败用例和原始执行记录保留用于回归。

## 范围说明

- 仅当前模块目录中归属业务管理的 13 个模块、14 个添加接口。已经归入客户管理的终端客户添加不在本批次。
- 业务数据库使用专用只读账号；没有通过 SQL 修改、删除或清理任何业务数据。添加接口产生的新测试数据保留。
- 没有生成或执行编辑、删除、审批、出入库、库存调整等其他接口用例；少量只读 GET 仅用于校验依赖。
- 落库核对在 db-verification.json。存在唯一名称或响应主键的接口按唯一标识匹配；批量拜访、销售和退货记录标记为最近匹配候选，不声称候选 ID 是严格唯一归属证明。
- 正常添加 14/14 通过，193 条有效正式用例已执行；167 条通过，26 条异常策略保留为失败。另 17 条已停用场景保留历史记录。
