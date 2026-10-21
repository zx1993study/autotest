# 外勤小星页面与小程序测试用例

源码：https://github.com/dpush-io/FieldNovaMini @ 9c44251c78f7c865c8d28272f6340bbad47942cf

已注册页面 82；用例 244；可脚本执行 86；人工/待数据适配 158。

状态均为“未执行”。H5 指小程序同源 H5，不是管理端；管理端及服务端等待源码访问。

## 页面覆盖

| 页面 | 路由 | 页面定位 | 查询条件数 | 字段规则数 |
| --- | --- | --- | --- | --- |
| 工作台 | pages/workbench/index | .workbench-container | 0 | 0 |
| 登录 | pages/login/index | .login-container | 0 | 0 |
| 数据统计 | pages/data/index | .data-container | 0 | 0 |
| 我的 | pages/profile/index | .profile-container | 0 | 0 |
| 个人信息 | pages/profile/personal-info | .personal-info-container | 0 | 0 |
| 我的组织 | pages/profile/organization | .organization-container | 0 | 0 |
| 员工详情 | pages/profile/employee-details | .employee-details-container | 0 | 0 |
| 选择位置 | pages/subpages/common/map | .map-container | 0 | 0 |
| 水印相机 | pages/subpages/common/watermark-camera | .camera-container | 0 | 0 |
| 活动方案 | pages/subpages/activityApply/scheme/list | .scheme-list-container | 6 | 0 |
| 活动方案审批 | pages/subpages/activityApply/scheme/detail | .scheme-detail | 0 | 0 |
| 活动申请 | pages/subpages/activityApply/apply/form | .apply-form | 0 | 0 |
| 活动申请 | pages/subpages/activityApply/apply/list | .apply-list-container | 11 | 0 |
| 申请详情 | pages/subpages/activityApply/apply/detail | .apply-detail | 0 | 0 |
| 活动执行 | pages/subpages/activityApply/execute/list | .task-list-container | 12 | 0 |
| 活动执行上报 | pages/subpages/activityApply/execute/report | .exec-report | 0 | 0 |
| 活动兑付 | pages/subpages/activityApply/payment/list | .task-list-container | 11 | 0 |
| 活动兑付上报 | pages/subpages/activityApply/payment/report | .pay-report | 0 | 0 |
| 活动上报 | pages/subpages/activity/activityReport | .activity-report-container | 0 | 0 |
| 陈列上报 | pages/subpages/activity/displayReport | .display-report-container | 0 | 0 |
| 兑付上报 | pages/subpages/activity/paymentReport | .payment-report-container | 0 | 0 |
| 活动中心 | pages/subpages/activity/list | 待适配 | 0 | 0 |
| 活动记录 | pages/subpages/activity/activityReportList | .activity-report-list-container | 0 | 0 |
| 申请活动 | pages/subpages/activity/applyActivity | .apply-activity-container | 0 | 0 |
| 参与客户 | pages/subpages/activity/participantList | .participant-list-container | 0 | 0 |
| 前端客户 | pages/subpages/customer/business/index | .customer-business-container | 13 | 0 |
| 新增客户 | pages/subpages/customer/business/form | .customer-form-container | 0 | 18 |
| 客户详情 | pages/subpages/customer/business/info | .customer-info-container | 0 | 0 |
| 直营客户 | pages/subpages/customer/directly/index | .customer-directly-container | 12 | 0 |
| 新增直营客户 | pages/subpages/customer/directly/form | .customer-form-container | 0 | 14 |
| 直营客户详情 | pages/subpages/customer/directly/info | .customer-info-container | 0 | 0 |
| KOL客户 | pages/subpages/customer/kol/index | .customer-kol-container | 12 | 0 |
| 新增KOL客户 | pages/subpages/customer/kol/form | .customer-form-container | 0 | 13 |
| KOL客户详情 | pages/subpages/customer/kol/info | .customer-info-container | 0 | 0 |
| 选择客户 | pages/subpages/customer/selectCustomer | .customer-select-container | 4 | 0 |
| 选择客户 | pages/subpages/customer/selectCustomersMulti | .multi-select-container | 0 | 0 |
| 拜访计划 | pages/subpages/visitPlan/index | .visit-plan-index-container | 9 | 0 |
| 新增计划 | pages/subpages/visitPlan/addPlan | .add-plan-container | 0 | 0 |
| 拜访计划详情 | pages/subpages/visitPlan/info | .visit-plan-info-container | 0 | 0 |
| 拜访上报 | pages/subpages/visitPlan/visitReport | .visit-report-container | 0 | 0 |
| 库存上报 | pages/subpages/visitPlan/visitReport/inventory | .inventory-report-container | 0 | 0 |
| 陈列上报 | pages/subpages/visitPlan/visitReport/display | .display-report-container | 0 | 0 |
| 其他上报 | pages/subpages/visitPlan/visitReport/other | .other-report-container | 0 | 0 |
| 异常签退 | pages/subpages/visitPlan/visitReport/abnormalCheckOut | .abnormal-checkout-container | 0 | 0 |
| 拜访记录 | pages/subpages/visitPlan/visitRecords | .visit-records-container | 9 | 0 |
| 新增计划外拜访 | pages/subpages/visitPlan/addTempVisitPlan | .add-temp-plan-container | 0 | 0 |
| 拜访路线 | pages/subpages/visitPlan/template/index | .visit-template-container | 3 | 0 |
| 拜访详情 | pages/subpages/visitPlan/template/detail | .visit-template-detail-container | 0 | 0 |
| 临时拜访 | pages/subpages/visitPlan/visitReport/tempVisit | .temp-visit-container | 0 | 0 |
| 选择商品 | pages/subpages/product/index | .product-page | 0 | 0 |
| 销售订单 | pages/subpages/business/salesOrder/index | .sales-order-container | 9 | 0 |
| 新增销售订单 | pages/subpages/business/salesOrder/form | .sales-order-form | 0 | 0 |
| 选择销售订单 | pages/subpages/business/salesOrder/select | .sales-order-select-container | 0 | 0 |
| 销售订单详情 | pages/subpages/business/salesOrder/info | .order-info-container | 0 | 0 |
| 退货订单 | pages/subpages/business/returnOrder/index | .sales-order-container | 9 | 0 |
| 新增退货订单 | pages/subpages/business/returnOrder/form | .return-order-form | 0 | 0 |
| 退货订单详情 | pages/subpages/business/returnOrder/info | .order-info-container | 0 | 0 |
| 入库确认 | pages/subpages/business/stockInOrder/index | .stock-in-order-container | 9 | 0 |
| 入库订单详情 | pages/subpages/business/stockInOrder/info | .order-info-container | 0 | 0 |
| 出库信息 | pages/subpages/business/stockOutOrder/index | .stock-out-order-container | 8 | 0 |
| 出库订单详情 | pages/subpages/business/stockOutOrder/info | .order-info-container | 0 | 0 |
| 采购入库 | pages/subpages/business/purchaseOrder/index | .purchase-order-container | 3 | 0 |
| 采购入库详情 | pages/subpages/business/purchaseOrder/info | .order-info-container | 0 | 0 |
| 新增采购入库 | pages/subpages/business/purchaseOrder/form | .purchase-order-form-container | 0 | 0 |
| 仓库信息 | pages/subpages/warehouse/productList | .warehouse-product-container | 2 | 0 |
| 拆箱补件 | pages/subpages/warehouse/inventoryConvert | .convert-container | 0 | 0 |
| 商品详情 | pages/subpages/warehouse/productDetail | .product-detail-container | 0 | 0 |
| 选择仓库 | pages/subpages/warehouse/select | .warehouse-select-container | 1 | 0 |
| 消息通知 | pages/subpages/messageCenter/index | .message-center | 0 | 0 |
| 待办理 | pages/subpages/messageCenter/todo | .todo-page-container | 0 | 0 |
| 待审批 | pages/subpages/messageCenter/approval | .approval-page-container | 0 | 0 |
| 我的审批 | pages/subpages/messageCenter/myApproval | .approval-page-container | 0 | 0 |
| 线上拜访 | pages/subpages/onlineVisit/index | .online-visit-container | 4 | 0 |
| 新增线上拜访 | pages/subpages/onlineVisit/form | .online-visit-form | 0 | 0 |
| 任务清单 | pages/subpages/supervision/list | .list-page | 2 | 0 |
| 发布任务 | pages/subpages/supervision/create | .create-page | 0 | 0 |
| 任务详情 | pages/subpages/supervision/detail | .detail-page | 0 | 0 |
| 上报工作 | pages/subpages/supervision/report | .report-page | 0 | 0 |
| 选择员工 | pages/subpages/supervision/selectUsers | .user-select | 0 | 0 |
| 客户列表 | pages/subpages/data/customerList | .customer-summary-container | 0 | 0 |
| 销售订单 | pages/subpages/data/salesOrderList | .sales-order-container | 0 | 0 |
| 退货订单 | pages/subpages/data/returnOrderList | .sales-order-container | 0 | 0 |

## 用例明细

### MINI-001-页面呈现 工作台：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/workbench/index`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/workbench/index 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/workbench/index.vue:2

### MINI-002-页面呈现 登录：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/login/index`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/login/index 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/login/index.vue:2

### MINI-003-页面呈现 数据统计：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/data/index`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/data/index 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/data/index.vue:2

### MINI-004-页面呈现 我的：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/profile/index`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/profile/index 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/profile/index.vue:2

### MINI-005-页面呈现 个人信息：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/profile/personal-info`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/profile/personal-info 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/profile/personal-info.vue:2

### MINI-006-页面呈现 我的组织：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/profile/organization`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/profile/organization 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/profile/organization.vue:2

### MINI-007-页面呈现 员工详情：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/profile/employee-details`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/profile/employee-details 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/profile/employee-details.vue:2

### MINI-008-页面呈现 选择位置：页面呈现

- 平台：mp-weixin-real-device；级别：P1；执行：manual_native；风险：read
- 路由：`/pages/subpages/common/map`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/common/map 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/common/map.vue:2

### MINI-009-页面呈现 水印相机：页面呈现

- 平台：mp-weixin-real-device；级别：P1；执行：manual_native；风险：read
- 路由：`/pages/subpages/common/watermark-camera`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/common/watermark-camera 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/common/watermark-camera.vue:2

### MINI-010-页面呈现 活动方案：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/activityApply/scheme/list`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/activityApply/scheme/list 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/activityApply/scheme/list.vue:2

### MINI-010-条件查询合并场景 活动方案：条件查询合并场景

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：read
- 路由：`/pages/subpages/activityApply/scheme/list`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 准备本批次正反例及可核对的非空基线；2. 先单独验证关键字及全部条件：活动类型(activityType)、可申请日期(applyBeginTime)、活动ID(activityId)、付费项目(paidItems)、兑付方式(paymentType)、创建时间(createTime)；3. 再组合多个条件，翻页，清空条件并返回列表；整个流程保存在一个场景中
- 预期：HTTP成功和业务成功之外，还要逐条核对筛选条件；多选字段按包含关系比较；非空正例必须命中预期ID；反例不得混入；空结果不能凭空判定过滤正确；改变条件重置分页；清空恢复基线；过期请求不覆盖新条件结果
- 依据：src/pages/subpages/activityApply/scheme/list.vue:2, src/config/mobileSearchConfig.ts:1

### MINI-011-页面呈现 活动方案审批：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/activityApply/scheme/detail`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/activityApply/scheme/detail 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/activityApply/scheme/detail.vue:2

### MINI-012-页面呈现 活动申请：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/activityApply/apply/form`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/activityApply/apply/form 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/activityApply/apply/form.vue:2

### MINI-013-页面呈现 活动申请：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/activityApply/apply/list`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/activityApply/apply/list 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/activityApply/apply/list.vue:2

### MINI-013-条件查询合并场景 活动申请：条件查询合并场景

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：read
- 路由：`/pages/subpages/activityApply/apply/list`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 准备本批次正反例及可核对的非空基线；2. 先单独验证关键字及全部条件：活动类型(activityType)、执行时间(executeTime)、参与客户(customerName)、活动ID(activityId)、营销代表(createByName)、执行地点(executionLocation)、我方人员参加(hasOurStaff)、执行完成度(executionStatus)、兑付完成度(paymentStatus)、创建时间(createTime)、备注(remark)；3. 再组合多个条件，翻页，清空条件并返回列表；整个流程保存在一个场景中
- 预期：HTTP成功和业务成功之外，还要逐条核对筛选条件；多选字段按包含关系比较；非空正例必须命中预期ID；反例不得混入；空结果不能凭空判定过滤正确；改变条件重置分页；清空恢复基线；过期请求不覆盖新条件结果
- 依据：src/pages/subpages/activityApply/apply/list.vue:2, src/config/mobileSearchConfig.ts:1

### MINI-014-页面呈现 申请详情：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/activityApply/apply/detail`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/activityApply/apply/detail 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/activityApply/apply/detail.vue:2

### MINI-015-页面呈现 活动执行：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/activityApply/execute/list`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/activityApply/execute/list 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/activityApply/execute/list.vue:2

### MINI-015-条件查询合并场景 活动执行：条件查询合并场景

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：read
- 路由：`/pages/subpages/activityApply/execute/list`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 准备本批次正反例及可核对的非空基线；2. 先单独验证关键字及全部条件：执行月份(periodMonth)、活动类型(activityType)、客户名称(customerName)、活动ID(activityId)、客户类型(customerType)、营销代表(createByName)、执行时间(executeTime)、完成时间(reportTime)、执行地点(executionLocation)、上报位置(reportLocation)、我方人员参加(hasOurStaff)、备注(remark)；3. 再组合多个条件，翻页，清空条件并返回列表；整个流程保存在一个场景中
- 预期：HTTP成功和业务成功之外，还要逐条核对筛选条件；多选字段按包含关系比较；非空正例必须命中预期ID；反例不得混入；空结果不能凭空判定过滤正确；改变条件重置分页；清空恢复基线；过期请求不覆盖新条件结果
- 依据：src/pages/subpages/activityApply/execute/list.vue:2, src/config/mobileSearchConfig.ts:1

### MINI-016-页面呈现 活动执行上报：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/activityApply/execute/report`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/activityApply/execute/report 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/activityApply/execute/report.vue:2

### MINI-017-页面呈现 活动兑付：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/activityApply/payment/list`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/activityApply/payment/list 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/activityApply/payment/list.vue:2

### MINI-017-条件查询合并场景 活动兑付：条件查询合并场景

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：read
- 路由：`/pages/subpages/activityApply/payment/list`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 准备本批次正反例及可核对的非空基线；2. 先单独验证关键字及全部条件：兑付月份(paymentMonth)、活动类型(activityType)、客户名称(customerName)、活动ID(activityId)、客户类型(customerType)、营销代表(createByName)、执行时间(executeTime)、完成时间(reportTime)、执行地点(executionLocation)、我方人员参加(hasOurStaff)、备注(remark)；3. 再组合多个条件，翻页，清空条件并返回列表；整个流程保存在一个场景中
- 预期：HTTP成功和业务成功之外，还要逐条核对筛选条件；多选字段按包含关系比较；非空正例必须命中预期ID；反例不得混入；空结果不能凭空判定过滤正确；改变条件重置分页；清空恢复基线；过期请求不覆盖新条件结果
- 依据：src/pages/subpages/activityApply/payment/list.vue:2, src/config/mobileSearchConfig.ts:1

### MINI-018-页面呈现 活动兑付上报：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/activityApply/payment/report`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/activityApply/payment/report 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/activityApply/payment/report.vue:2

### MINI-019-页面呈现 活动上报：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/activity/activityReport`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/activity/activityReport 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/activity/activityReport.vue:2

### MINI-020-页面呈现 陈列上报：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/activity/displayReport`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/activity/displayReport 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/activity/displayReport.vue:2

### MINI-021-页面呈现 兑付上报：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/activity/paymentReport`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/activity/paymentReport 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/activity/paymentReport.vue:2

### MINI-022-页面呈现 活动中心：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：manual；风险：read
- 路由：`/pages/subpages/activity/list`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/activity/list 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/activity/list.vue:1

### MINI-023-页面呈现 活动记录：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/activity/activityReportList`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/activity/activityReportList 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/activity/activityReportList.vue:2

### MINI-024-页面呈现 申请活动：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/activity/applyActivity`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/activity/applyActivity 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/activity/applyActivity.vue:2

### MINI-025-页面呈现 参与客户：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/activity/participantList`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/activity/participantList 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/activity/participantList.vue:2

### MINI-026-页面呈现 前端客户：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/customer/business/index`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/customer/business/index 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/customer/business/index.vue:2

### MINI-026-条件查询合并场景 前端客户：条件查询合并场景

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：read
- 路由：`/pages/subpages/customer/business/index`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 准备本批次正反例及可核对的非空基线；2. 先单独验证关键字及全部条件：客户经理(managerId)、客户手机号(phone)、客户联系人手机号(contactPhone)、收货人手机号(consigneePhone)、合作状态(cooperationStatus)、状态(status)、创建时间(createTime)、销售区域(salesArea)、拜访频率(visitFrequency)、客户类型(terminalType)、客户标签(terminalTags)、产品名称(productType)、客户等级(customerLevel)；3. 再组合多个条件，翻页，清空条件并返回列表；整个流程保存在一个场景中
- 预期：HTTP成功和业务成功之外，还要逐条核对筛选条件；多选字段按包含关系比较；非空正例必须命中预期ID；反例不得混入；空结果不能凭空判定过滤正确；改变条件重置分页；清空恢复基线；过期请求不覆盖新条件结果
- 依据：src/pages/subpages/customer/business/index.vue:2, src/config/mobileSearchConfig.ts:1

### MINI-027-页面呈现 新增客户：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/customer/business/form`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/customer/business/form 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/customer/business/form.vue:2

### MINI-027-字段校验-customerName-1 新增客户：客户名称 / 请输入客户名称

- 平台：h5, mp-weixin；级别：P1；执行：manual；风险：read
- 路由：`/pages/subpages/customer/business/form`
- 前置：除被测字段外，其余必填及条件字段均有效；编辑模式仅使用本批次记录
- 步骤：1. 单独清空被测字段并失焦/提交；随后输入有效值再次校验
- 预期：不合法值显示“请输入客户名称”并阻止无效业务提交；有效边界可通过该字段校验
- 依据：src/pages/subpages/customer/business/form.vue:580

### MINI-027-字段校验-managerIds-2 新增客户：客户经理 / 请选择客户经理

- 平台：h5, mp-weixin；级别：P1；执行：manual；风险：read
- 路由：`/pages/subpages/customer/business/form`
- 前置：除被测字段外，其余必填及条件字段均有效；编辑模式仅使用本批次记录
- 步骤：1. 按源码自定义规则准备不合法值、合法值及允许为空的边界；分别验证条件启用和禁用；单独触发该字段校验
- 预期：不合法值显示“请选择客户经理”并阻止无效业务提交；有效边界可通过该字段校验
- 依据：src/pages/subpages/customer/business/form.vue:583

### MINI-027-字段校验-terminalType-3 新增客户：客户类型 / 请选择终端类型

- 平台：h5, mp-weixin；级别：P1；执行：manual；风险：read
- 路由：`/pages/subpages/customer/business/form`
- 前置：除被测字段外，其余必填及条件字段均有效；编辑模式仅使用本批次记录
- 步骤：1. 按源码自定义规则准备不合法值、合法值及允许为空的边界；分别验证条件启用和禁用；单独触发该字段校验
- 预期：不合法值显示“请选择终端类型”并阻止无效业务提交；有效边界可通过该字段校验
- 依据：src/pages/subpages/customer/business/form.vue:593

### MINI-027-字段校验-productType-4 新增客户：产品类型 / 请选择产品类型

- 平台：h5, mp-weixin；级别：P1；执行：manual；风险：read
- 路由：`/pages/subpages/customer/business/form`
- 前置：除被测字段外，其余必填及条件字段均有效；编辑模式仅使用本批次记录
- 步骤：1. 单独清空被测字段并失焦/提交；随后输入有效值再次校验
- 预期：不合法值显示“请选择产品类型”并阻止无效业务提交；有效边界可通过该字段校验
- 依据：src/pages/subpages/customer/business/form.vue:603

### MINI-027-字段校验-salesArea-5 新增客户：salesArea / 请选择销售区域

- 平台：h5, mp-weixin；级别：P1；执行：manual；风险：read
- 路由：`/pages/subpages/customer/business/form`
- 前置：除被测字段外，其余必填及条件字段均有效；编辑模式仅使用本批次记录
- 步骤：1. 单独清空被测字段并失焦/提交；随后输入有效值再次校验
- 预期：不合法值显示“请选择销售区域”并阻止无效业务提交；有效边界可通过该字段校验
- 依据：src/pages/subpages/customer/business/form.vue:606

### MINI-027-字段校验-customerLevel-6 新增客户：customerLevel / 请选择客户级别

- 平台：h5, mp-weixin；级别：P1；执行：manual；风险：read
- 路由：`/pages/subpages/customer/business/form`
- 前置：除被测字段外，其余必填及条件字段均有效；编辑模式仅使用本批次记录
- 步骤：1. 单独清空被测字段并失焦/提交；随后输入有效值再次校验
- 预期：不合法值显示“请选择客户级别”并阻止无效业务提交；有效边界可通过该字段校验
- 依据：src/pages/subpages/customer/business/form.vue:609

### MINI-027-字段校验-contactName-7 新增客户：客户联系人姓名 / 请输入联系人名称

- 平台：h5, mp-weixin；级别：P1；执行：manual；风险：read
- 路由：`/pages/subpages/customer/business/form`
- 前置：除被测字段外，其余必填及条件字段均有效；编辑模式仅使用本批次记录
- 步骤：1. 单独清空被测字段并失焦/提交；随后输入有效值再次校验
- 预期：不合法值显示“请输入联系人名称”并阻止无效业务提交；有效边界可通过该字段校验
- 依据：src/pages/subpages/customer/business/form.vue:612

### MINI-027-字段校验-contactName-8 新增客户：客户联系人姓名 / 联系人姓名不能超过30个字符

- 平台：h5, mp-weixin；级别：P1；执行：manual；风险：read
- 路由：`/pages/subpages/customer/business/form`
- 前置：除被测字段外，其余必填及条件字段均有效；编辑模式仅使用本批次记录
- 步骤：1. 分别输入29、30、31个字符并触发校验
- 预期：不合法值显示“联系人姓名不能超过30个字符”并阻止无效业务提交；有效边界可通过该字段校验
- 依据：src/pages/subpages/customer/business/form.vue:613

### MINI-027-字段校验-contactPhone-9 新增客户：客户联系人手机 / 请输入联系人手机号

- 平台：h5, mp-weixin；级别：P1；执行：manual；风险：read
- 路由：`/pages/subpages/customer/business/form`
- 前置：除被测字段外，其余必填及条件字段均有效；编辑模式仅使用本批次记录
- 步骤：1. 单独清空被测字段并失焦/提交；随后输入有效值再次校验
- 预期：不合法值显示“请输入联系人手机号”并阻止无效业务提交；有效边界可通过该字段校验
- 依据：src/pages/subpages/customer/business/form.vue:616

### MINI-027-字段校验-contactPhone-10 新增客户：客户联系人手机 / 手机号或座机号不正确

- 平台：h5, mp-weixin；级别：P1；执行：manual；风险：read
- 路由：`/pages/subpages/customer/business/form`
- 前置：除被测字段外，其余必填及条件字段均有效；编辑模式仅使用本批次记录
- 步骤：1. 按源码自定义规则准备不合法值、合法值及允许为空的边界；分别验证条件启用和禁用；单独触发该字段校验
- 预期：不合法值显示“手机号或座机号不正确”并阻止无效业务提交；有效边界可通过该字段校验
- 依据：src/pages/subpages/customer/business/form.vue:617

### MINI-027-字段校验-latitude-11 新增客户：标注位置 / 请标注位置

- 平台：h5, mp-weixin；级别：P1；执行：manual；风险：read
- 路由：`/pages/subpages/customer/business/form`
- 前置：除被测字段外，其余必填及条件字段均有效；编辑模式仅使用本批次记录
- 步骤：1. 按源码自定义规则准备不合法值、合法值及允许为空的边界；分别验证条件启用和禁用；单独触发该字段校验
- 预期：不合法值显示“请标注位置”并阻止无效业务提交；有效边界可通过该字段校验
- 依据：src/pages/subpages/customer/business/form.vue:629

### MINI-027-字段校验-phone-12 新增客户：客户手机号 / 手机号或座机号不正确

- 平台：h5, mp-weixin；级别：P1；执行：manual；风险：read
- 路由：`/pages/subpages/customer/business/form`
- 前置：除被测字段外，其余必填及条件字段均有效；编辑模式仅使用本批次记录
- 步骤：1. 按源码自定义规则准备不合法值、合法值及允许为空的边界；分别验证条件启用和禁用；单独触发该字段校验
- 预期：不合法值显示“手机号或座机号不正确”并阻止无效业务提交；有效边界可通过该字段校验
- 依据：src/pages/subpages/customer/business/form.vue:642

### MINI-027-字段校验-terminalTags-13 新增客户：客户标签 / 请选择客户标签

- 平台：h5, mp-weixin；级别：P1；执行：manual；风险：read
- 路由：`/pages/subpages/customer/business/form`
- 前置：除被测字段外，其余必填及条件字段均有效；编辑模式仅使用本批次记录
- 步骤：1. 单独清空被测字段并失焦/提交；随后输入有效值再次校验
- 预期：不合法值显示“请选择客户标签”并阻止无效业务提交；有效边界可通过该字段校验
- 依据：src/pages/subpages/customer/business/form.vue:654

### MINI-027-字段校验-cooperationStatus-14 新增客户：合作状态 / 请选择合作状态

- 平台：h5, mp-weixin；级别：P1；执行：manual；风险：read
- 路由：`/pages/subpages/customer/business/form`
- 前置：除被测字段外，其余必填及条件字段均有效；编辑模式仅使用本批次记录
- 步骤：1. 按源码自定义规则准备不合法值、合法值及允许为空的边界；分别验证条件启用和禁用；单独触发该字段校验
- 预期：不合法值显示“请选择合作状态”并阻止无效业务提交；有效边界可通过该字段校验
- 依据：src/pages/subpages/customer/business/form.vue:657

### MINI-027-字段校验-businessRegistrationNumber-15 新增客户：工商注册号 / 工商注册号不能超过30个字符

- 平台：h5, mp-weixin；级别：P1；执行：manual；风险：read
- 路由：`/pages/subpages/customer/business/form`
- 前置：除被测字段外，其余必填及条件字段均有效；编辑模式仅使用本批次记录
- 步骤：1. 分别输入29、30、31个字符并触发校验
- 预期：不合法值显示“工商注册号不能超过30个字符”并阻止无效业务提交；有效边界可通过该字段校验
- 依据：src/pages/subpages/customer/business/form.vue:665

### MINI-027-字段校验-operatorName-16 新增客户：经营者 / 经营者姓名不能超过30个字符

- 平台：h5, mp-weixin；级别：P1；执行：manual；风险：read
- 路由：`/pages/subpages/customer/business/form`
- 前置：除被测字段外，其余必填及条件字段均有效；编辑模式仅使用本批次记录
- 步骤：1. 分别输入29、30、31个字符并触发校验
- 预期：不合法值显示“经营者姓名不能超过30个字符”并阻止无效业务提交；有效边界可通过该字段校验
- 依据：src/pages/subpages/customer/business/form.vue:669

### MINI-027-字段校验-consigneeName-17 新增客户：收货人姓名 / 收货人姓名不能超过30个字符

- 平台：h5, mp-weixin；级别：P1；执行：manual；风险：read
- 路由：`/pages/subpages/customer/business/form`
- 前置：除被测字段外，其余必填及条件字段均有效；编辑模式仅使用本批次记录
- 步骤：1. 分别输入29、30、31个字符并触发校验
- 预期：不合法值显示“收货人姓名不能超过30个字符”并阻止无效业务提交；有效边界可通过该字段校验
- 依据：src/pages/subpages/customer/business/form.vue:673

### MINI-027-字段校验-consigneePhone-18 新增客户：收货人手机 / 手机号或座机号不正确

- 平台：h5, mp-weixin；级别：P1；执行：manual；风险：read
- 路由：`/pages/subpages/customer/business/form`
- 前置：除被测字段外，其余必填及条件字段均有效；编辑模式仅使用本批次记录
- 步骤：1. 按源码自定义规则准备不合法值、合法值及允许为空的边界；分别验证条件启用和禁用；单独触发该字段校验
- 预期：不合法值显示“手机号或座机号不正确”并阻止无效业务提交；有效边界可通过该字段校验
- 依据：src/pages/subpages/customer/business/form.vue:677

### MINI-028-页面呈现 客户详情：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/customer/business/info`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/customer/business/info 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/customer/business/info.vue:2

### MINI-029-页面呈现 直营客户：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/customer/directly/index`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/customer/directly/index 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/customer/directly/index.vue:2

### MINI-029-条件查询合并场景 直营客户：条件查询合并场景

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：read
- 路由：`/pages/subpages/customer/directly/index`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 准备本批次正反例及可核对的非空基线；2. 先单独验证关键字及全部条件：客户经理(managerId)、客户手机号(phone)、客户联系人手机号(contactPhone)、收货人手机号(consigneePhone)、合作状态(cooperationStatus)、状态(status)、创建时间(createTime)、销售区域(salesArea)、拜访频率(visitFrequency)、客户类型(directCustomerType)、产品名称(directProductType)、客户等级(directCustomerLevel)；3. 再组合多个条件，翻页，清空条件并返回列表；整个流程保存在一个场景中
- 预期：HTTP成功和业务成功之外，还要逐条核对筛选条件；多选字段按包含关系比较；非空正例必须命中预期ID；反例不得混入；空结果不能凭空判定过滤正确；改变条件重置分页；清空恢复基线；过期请求不覆盖新条件结果
- 依据：src/pages/subpages/customer/directly/index.vue:2, src/config/mobileSearchConfig.ts:1

### MINI-030-页面呈现 新增直营客户：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/customer/directly/form`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/customer/directly/form 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/customer/directly/form.vue:2

### MINI-030-字段校验-customerName-1 新增直营客户：直营商名称 / 请输入客户名称

- 平台：h5, mp-weixin；级别：P1；执行：manual；风险：read
- 路由：`/pages/subpages/customer/directly/form`
- 前置：除被测字段外，其余必填及条件字段均有效；编辑模式仅使用本批次记录
- 步骤：1. 单独清空被测字段并失焦/提交；随后输入有效值再次校验
- 预期：不合法值显示“请输入客户名称”并阻止无效业务提交；有效边界可通过该字段校验
- 依据：src/pages/subpages/customer/directly/form.vue:541

### MINI-030-字段校验-managerIds-2 新增直营客户：客户经理 / 请选择客户经理

- 平台：h5, mp-weixin；级别：P1；执行：manual；风险：read
- 路由：`/pages/subpages/customer/directly/form`
- 前置：除被测字段外，其余必填及条件字段均有效；编辑模式仅使用本批次记录
- 步骤：1. 按源码自定义规则准备不合法值、合法值及允许为空的边界；分别验证条件启用和禁用；单独触发该字段校验
- 预期：不合法值显示“请选择客户经理”并阻止无效业务提交；有效边界可通过该字段校验
- 依据：src/pages/subpages/customer/directly/form.vue:544

### MINI-030-字段校验-directCustomerType-3 新增直营客户：directCustomerType / 请选择客户类型

- 平台：h5, mp-weixin；级别：P1；执行：manual；风险：read
- 路由：`/pages/subpages/customer/directly/form`
- 前置：除被测字段外，其余必填及条件字段均有效；编辑模式仅使用本批次记录
- 步骤：1. 单独清空被测字段并失焦/提交；随后输入有效值再次校验
- 预期：不合法值显示“请选择客户类型”并阻止无效业务提交；有效边界可通过该字段校验
- 依据：src/pages/subpages/customer/directly/form.vue:554

### MINI-030-字段校验-directCustomerLevel-4 新增直营客户：directCustomerLevel / 请选择客户级别

- 平台：h5, mp-weixin；级别：P1；执行：manual；风险：read
- 路由：`/pages/subpages/customer/directly/form`
- 前置：除被测字段外，其余必填及条件字段均有效；编辑模式仅使用本批次记录
- 步骤：1. 单独清空被测字段并失焦/提交；随后输入有效值再次校验
- 预期：不合法值显示“请选择客户级别”并阻止无效业务提交；有效边界可通过该字段校验
- 依据：src/pages/subpages/customer/directly/form.vue:557

### MINI-030-字段校验-directProductType-5 新增直营客户：产品类型 / 请选择产品类型

- 平台：h5, mp-weixin；级别：P1；执行：manual；风险：read
- 路由：`/pages/subpages/customer/directly/form`
- 前置：除被测字段外，其余必填及条件字段均有效；编辑模式仅使用本批次记录
- 步骤：1. 单独清空被测字段并失焦/提交；随后输入有效值再次校验
- 预期：不合法值显示“请选择产品类型”并阻止无效业务提交；有效边界可通过该字段校验
- 依据：src/pages/subpages/customer/directly/form.vue:560

### MINI-030-字段校验-salesArea-6 新增直营客户：salesArea / 请选择销售区域

- 平台：h5, mp-weixin；级别：P1；执行：manual；风险：read
- 路由：`/pages/subpages/customer/directly/form`
- 前置：除被测字段外，其余必填及条件字段均有效；编辑模式仅使用本批次记录
- 步骤：1. 单独清空被测字段并失焦/提交；随后输入有效值再次校验
- 预期：不合法值显示“请选择销售区域”并阻止无效业务提交；有效边界可通过该字段校验
- 依据：src/pages/subpages/customer/directly/form.vue:563

### MINI-030-字段校验-cooperationStatus-7 新增直营客户：合作状态 / 请选择合作状态

- 平台：h5, mp-weixin；级别：P1；执行：manual；风险：read
- 路由：`/pages/subpages/customer/directly/form`
- 前置：除被测字段外，其余必填及条件字段均有效；编辑模式仅使用本批次记录
- 步骤：1. 按源码自定义规则准备不合法值、合法值及允许为空的边界；分别验证条件启用和禁用；单独触发该字段校验
- 预期：不合法值显示“请选择合作状态”并阻止无效业务提交；有效边界可通过该字段校验
- 依据：src/pages/subpages/customer/directly/form.vue:566

### MINI-030-字段校验-latitude-8 新增直营客户：标注位置 / 请标注位置

- 平台：h5, mp-weixin；级别：P1；执行：manual；风险：read
- 路由：`/pages/subpages/customer/directly/form`
- 前置：除被测字段外，其余必填及条件字段均有效；编辑模式仅使用本批次记录
- 步骤：1. 按源码自定义规则准备不合法值、合法值及允许为空的边界；分别验证条件启用和禁用；单独触发该字段校验
- 预期：不合法值显示“请标注位置”并阻止无效业务提交；有效边界可通过该字段校验
- 依据：src/pages/subpages/customer/directly/form.vue:573

### MINI-030-字段校验-phone-9 新增直营客户：客户手机号 / 请输入客户手机号

- 平台：h5, mp-weixin；级别：P1；执行：manual；风险：read
- 路由：`/pages/subpages/customer/directly/form`
- 前置：除被测字段外，其余必填及条件字段均有效；编辑模式仅使用本批次记录
- 步骤：1. 单独清空被测字段并失焦/提交；随后输入有效值再次校验
- 预期：不合法值显示“请输入客户手机号”并阻止无效业务提交；有效边界可通过该字段校验
- 依据：src/pages/subpages/customer/directly/form.vue:586

### MINI-030-字段校验-phone-10 新增直营客户：客户手机号 / 手机号或座机号不正确

- 平台：h5, mp-weixin；级别：P1；执行：manual；风险：read
- 路由：`/pages/subpages/customer/directly/form`
- 前置：除被测字段外，其余必填及条件字段均有效；编辑模式仅使用本批次记录
- 步骤：1. 按源码自定义规则准备不合法值、合法值及允许为空的边界；分别验证条件启用和禁用；单独触发该字段校验
- 预期：不合法值显示“手机号或座机号不正确”并阻止无效业务提交；有效边界可通过该字段校验
- 依据：src/pages/subpages/customer/directly/form.vue:587

### MINI-030-字段校验-contactPhone-11 新增直营客户：客户联系人手机 / 请输入客户联系人手机

- 平台：h5, mp-weixin；级别：P1；执行：manual；风险：read
- 路由：`/pages/subpages/customer/directly/form`
- 前置：除被测字段外，其余必填及条件字段均有效；编辑模式仅使用本批次记录
- 步骤：1. 单独清空被测字段并失焦/提交；随后输入有效值再次校验
- 预期：不合法值显示“请输入客户联系人手机”并阻止无效业务提交；有效边界可通过该字段校验
- 依据：src/pages/subpages/customer/directly/form.vue:600

### MINI-030-字段校验-contactPhone-12 新增直营客户：客户联系人手机 / 手机号或座机号不正确

- 平台：h5, mp-weixin；级别：P1；执行：manual；风险：read
- 路由：`/pages/subpages/customer/directly/form`
- 前置：除被测字段外，其余必填及条件字段均有效；编辑模式仅使用本批次记录
- 步骤：1. 按源码自定义规则准备不合法值、合法值及允许为空的边界；分别验证条件启用和禁用；单独触发该字段校验
- 预期：不合法值显示“手机号或座机号不正确”并阻止无效业务提交；有效边界可通过该字段校验
- 依据：src/pages/subpages/customer/directly/form.vue:601

### MINI-030-字段校验-consigneePhone-13 新增直营客户：收货人手机 / 手机号或座机号不正确

- 平台：h5, mp-weixin；级别：P1；执行：manual；风险：read
- 路由：`/pages/subpages/customer/directly/form`
- 前置：除被测字段外，其余必填及条件字段均有效；编辑模式仅使用本批次记录
- 步骤：1. 按源码自定义规则准备不合法值、合法值及允许为空的边界；分别验证条件启用和禁用；单独触发该字段校验
- 预期：不合法值显示“手机号或座机号不正确”并阻止无效业务提交；有效边界可通过该字段校验
- 依据：src/pages/subpages/customer/directly/form.vue:614

### MINI-030-字段校验-businessLicenseName-14 新增直营客户：营业执照名称 / 请输入营业执照名称

- 平台：h5, mp-weixin；级别：P1；执行：manual；风险：read
- 路由：`/pages/subpages/customer/directly/form`
- 前置：除被测字段外，其余必填及条件字段均有效；编辑模式仅使用本批次记录
- 步骤：1. 单独清空被测字段并失焦/提交；随后输入有效值再次校验
- 预期：不合法值显示“请输入营业执照名称”并阻止无效业务提交；有效边界可通过该字段校验
- 依据：src/pages/subpages/customer/directly/form.vue:627

### MINI-031-页面呈现 直营客户详情：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/customer/directly/info`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/customer/directly/info 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/customer/directly/info.vue:2

### MINI-032-页面呈现 KOL客户：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/customer/kol/index`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/customer/kol/index 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/customer/kol/index.vue:2

### MINI-032-条件查询合并场景 KOL客户：条件查询合并场景

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：read
- 路由：`/pages/subpages/customer/kol/index`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 准备本批次正反例及可核对的非空基线；2. 先单独验证关键字及全部条件：客户经理(managerId)、客户手机号(phone)、客户联系人手机号(contactPhone)、收货人手机号(consigneePhone)、合作状态(cooperationStatus)、状态(status)、创建时间(createTime)、销售区域(salesArea)、拜访频率(visitFrequency)、客户类型(kolType)、产品名称(kolProductType)、公司名称(companyName)；3. 再组合多个条件，翻页，清空条件并返回列表；整个流程保存在一个场景中
- 预期：HTTP成功和业务成功之外，还要逐条核对筛选条件；多选字段按包含关系比较；非空正例必须命中预期ID；反例不得混入；空结果不能凭空判定过滤正确；改变条件重置分页；清空恢复基线；过期请求不覆盖新条件结果
- 依据：src/pages/subpages/customer/kol/index.vue:2, src/config/mobileSearchConfig.ts:1

### MINI-033-页面呈现 新增KOL客户：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/customer/kol/form`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/customer/kol/form 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/customer/kol/form.vue:2

### MINI-033-字段校验-companyName-1 新增KOL客户：公司名称 / 请输入公司名称

- 平台：h5, mp-weixin；级别：P1；执行：manual；风险：read
- 路由：`/pages/subpages/customer/kol/form`
- 前置：除被测字段外，其余必填及条件字段均有效；编辑模式仅使用本批次记录
- 步骤：1. 按源码自定义规则准备不合法值、合法值及允许为空的边界；分别验证条件启用和禁用；单独触发该字段校验
- 预期：不合法值显示“请输入公司名称”并阻止无效业务提交；有效边界可通过该字段校验
- 依据：src/pages/subpages/customer/kol/form.vue:548

### MINI-033-字段校验-companyName-2 新增KOL客户：公司名称 / 公司名称不能超过30个字符

- 平台：h5, mp-weixin；级别：P1；执行：manual；风险：read
- 路由：`/pages/subpages/customer/kol/form`
- 前置：除被测字段外，其余必填及条件字段均有效；编辑模式仅使用本批次记录
- 步骤：1. 分别输入29、30、31个字符并触发校验
- 预期：不合法值显示“公司名称不能超过30个字符”并阻止无效业务提交；有效边界可通过该字段校验
- 依据：src/pages/subpages/customer/kol/form.vue:556

### MINI-033-字段校验-managerIds-3 新增KOL客户：客户经理 / 请选择客户经理

- 平台：h5, mp-weixin；级别：P1；执行：manual；风险：read
- 路由：`/pages/subpages/customer/kol/form`
- 前置：除被测字段外，其余必填及条件字段均有效；编辑模式仅使用本批次记录
- 步骤：1. 按源码自定义规则准备不合法值、合法值及允许为空的边界；分别验证条件启用和禁用；单独触发该字段校验
- 预期：不合法值显示“请选择客户经理”并阻止无效业务提交；有效边界可通过该字段校验
- 依据：src/pages/subpages/customer/kol/form.vue:559

### MINI-033-字段校验-kolType-4 新增KOL客户：客户类型 / 请选择客户类型

- 平台：h5, mp-weixin；级别：P1；执行：manual；风险：read
- 路由：`/pages/subpages/customer/kol/form`
- 前置：除被测字段外，其余必填及条件字段均有效；编辑模式仅使用本批次记录
- 步骤：1. 单独清空被测字段并失焦/提交；随后输入有效值再次校验
- 预期：不合法值显示“请选择客户类型”并阻止无效业务提交；有效边界可通过该字段校验
- 依据：src/pages/subpages/customer/kol/form.vue:569

### MINI-033-字段校验-cooperationStatus-5 新增KOL客户：合作状态 / 请选择合作状态

- 平台：h5, mp-weixin；级别：P1；执行：manual；风险：read
- 路由：`/pages/subpages/customer/kol/form`
- 前置：除被测字段外，其余必填及条件字段均有效；编辑模式仅使用本批次记录
- 步骤：1. 按源码自定义规则准备不合法值、合法值及允许为空的边界；分别验证条件启用和禁用；单独触发该字段校验
- 预期：不合法值显示“请选择合作状态”并阻止无效业务提交；有效边界可通过该字段校验
- 依据：src/pages/subpages/customer/kol/form.vue:572

### MINI-033-字段校验-kolProductType-6 新增KOL客户：产品类型 / 请选择产品类型

- 平台：h5, mp-weixin；级别：P1；执行：manual；风险：read
- 路由：`/pages/subpages/customer/kol/form`
- 前置：除被测字段外，其余必填及条件字段均有效；编辑模式仅使用本批次记录
- 步骤：1. 按源码自定义规则准备不合法值、合法值及允许为空的边界；分别验证条件启用和禁用；单独触发该字段校验
- 预期：不合法值显示“请选择产品类型”并阻止无效业务提交；有效边界可通过该字段校验
- 依据：src/pages/subpages/customer/kol/form.vue:579

### MINI-033-字段校验-gender-7 新增KOL客户：gender / 请选择性别

- 平台：h5, mp-weixin；级别：P1；执行：manual；风险：read
- 路由：`/pages/subpages/customer/kol/form`
- 前置：除被测字段外，其余必填及条件字段均有效；编辑模式仅使用本批次记录
- 步骤：1. 单独清空被测字段并失焦/提交；随后输入有效值再次校验
- 预期：不合法值显示“请选择性别”并阻止无效业务提交；有效边界可通过该字段校验
- 依据：src/pages/subpages/customer/kol/form.vue:589

### MINI-033-字段校验-phone-8 新增KOL客户：客户手机 / 请输入客户手机号

- 平台：h5, mp-weixin；级别：P1；执行：manual；风险：read
- 路由：`/pages/subpages/customer/kol/form`
- 前置：除被测字段外，其余必填及条件字段均有效；编辑模式仅使用本批次记录
- 步骤：1. 单独清空被测字段并失焦/提交；随后输入有效值再次校验
- 预期：不合法值显示“请输入客户手机号”并阻止无效业务提交；有效边界可通过该字段校验
- 依据：src/pages/subpages/customer/kol/form.vue:592

### MINI-033-字段校验-phone-9 新增KOL客户：客户手机 / 请输入正确的手机号或座机号格式

- 平台：h5, mp-weixin；级别：P1；执行：manual；风险：read
- 路由：`/pages/subpages/customer/kol/form`
- 前置：除被测字段外，其余必填及条件字段均有效；编辑模式仅使用本批次记录
- 步骤：1. 按源码自定义规则准备不合法值、合法值及允许为空的边界；分别验证条件启用和禁用；单独触发该字段校验
- 预期：不合法值显示“请输入正确的手机号或座机号格式”并阻止无效业务提交；有效边界可通过该字段校验
- 依据：src/pages/subpages/customer/kol/form.vue:593

### MINI-033-字段校验-latitude-10 新增KOL客户：标注位置 / 请标注位置

- 平台：h5, mp-weixin；级别：P1；执行：manual；风险：read
- 路由：`/pages/subpages/customer/kol/form`
- 前置：除被测字段外，其余必填及条件字段均有效；编辑模式仅使用本批次记录
- 步骤：1. 按源码自定义规则准备不合法值、合法值及允许为空的边界；分别验证条件启用和禁用；单独触发该字段校验
- 预期：不合法值显示“请标注位置”并阻止无效业务提交；有效边界可通过该字段校验
- 依据：src/pages/subpages/customer/kol/form.vue:605

### MINI-033-字段校验-consigneePhone-11 新增KOL客户：收货人手机 / 请输入正确的手机号或座机号格式

- 平台：h5, mp-weixin；级别：P1；执行：manual；风险：read
- 路由：`/pages/subpages/customer/kol/form`
- 前置：除被测字段外，其余必填及条件字段均有效；编辑模式仅使用本批次记录
- 步骤：1. 按源码自定义规则准备不合法值、合法值及允许为空的边界；分别验证条件启用和禁用；单独触发该字段校验
- 预期：不合法值显示“请输入正确的手机号或座机号格式”并阻止无效业务提交；有效边界可通过该字段校验
- 依据：src/pages/subpages/customer/kol/form.vue:618

### MINI-033-字段校验-customerName-12 新增KOL客户：客户姓名 / 请输入联系人名称

- 平台：h5, mp-weixin；级别：P1；执行：manual；风险：read
- 路由：`/pages/subpages/customer/kol/form`
- 前置：除被测字段外，其余必填及条件字段均有效；编辑模式仅使用本批次记录
- 步骤：1. 单独清空被测字段并失焦/提交；随后输入有效值再次校验
- 预期：不合法值显示“请输入联系人名称”并阻止无效业务提交；有效边界可通过该字段校验
- 依据：src/pages/subpages/customer/kol/form.vue:630

### MINI-033-字段校验-customerName-13 新增KOL客户：客户姓名 / 联系人姓名不能超过30个字符

- 平台：h5, mp-weixin；级别：P1；执行：manual；风险：read
- 路由：`/pages/subpages/customer/kol/form`
- 前置：除被测字段外，其余必填及条件字段均有效；编辑模式仅使用本批次记录
- 步骤：1. 分别输入29、30、31个字符并触发校验
- 预期：不合法值显示“联系人姓名不能超过30个字符”并阻止无效业务提交；有效边界可通过该字段校验
- 依据：src/pages/subpages/customer/kol/form.vue:631

### MINI-034-页面呈现 KOL客户详情：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/customer/kol/info`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/customer/kol/info 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/customer/kol/info.vue:2

### MINI-035-页面呈现 选择客户：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/customer/selectCustomer`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/customer/selectCustomer 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/customer/selectCustomer.vue:2

### MINI-035-条件查询合并场景 选择客户：条件查询合并场景

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：read
- 路由：`/pages/subpages/customer/selectCustomer`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 准备本批次正反例及可核对的非空基线；2. 先单独验证关键字及全部条件：合作状态(cooperationStatus)、销售区域(salesArea)、客户等级(customerLevel)、拜访频率(visitFrequency)；3. 再组合多个条件，翻页，清空条件并返回列表；整个流程保存在一个场景中
- 预期：HTTP成功和业务成功之外，还要逐条核对筛选条件；多选字段按包含关系比较；非空正例必须命中预期ID；反例不得混入；空结果不能凭空判定过滤正确；改变条件重置分页；清空恢复基线；过期请求不覆盖新条件结果
- 依据：src/pages/subpages/customer/selectCustomer.vue:2, src/config/mobileSearchConfig.ts:1

### MINI-036-页面呈现 选择客户：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/customer/selectCustomersMulti`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/customer/selectCustomersMulti 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/customer/selectCustomersMulti.vue:2

### MINI-036-条件查询合并场景 选择客户：条件查询合并场景

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：read
- 路由：`/pages/subpages/customer/selectCustomersMulti`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 准备本批次正反例及可核对的非空基线；2. 先单独验证关键字及全部条件：；3. 再组合多个条件，翻页，清空条件并返回列表；整个流程保存在一个场景中
- 预期：HTTP成功和业务成功之外，还要逐条核对筛选条件；多选字段按包含关系比较；非空正例必须命中预期ID；反例不得混入；空结果不能凭空判定过滤正确；改变条件重置分页；清空恢复基线；过期请求不覆盖新条件结果
- 依据：src/pages/subpages/customer/selectCustomersMulti.vue:2, src/config/mobileSearchConfig.ts:1

### MINI-037-页面呈现 拜访计划：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/visitPlan/index`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/visitPlan/index 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/visitPlan/index.vue:2

### MINI-037-条件查询合并场景 拜访计划：条件查询合并场景

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：read
- 路由：`/pages/subpages/visitPlan/index`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 准备本批次正反例及可核对的非空基线；2. 先单独验证关键字及全部条件：拜访日期(visitDate)、责任人(visitorUserId)、拜访路线(templateId)、客户类型(customerType)、合作状态(cooperationStatus)、客户标签(terminalTags)、客户地址(customerAddress)、产品名称(productType)、计划类型(isTemporary)；3. 再组合多个条件，翻页，清空条件并返回列表；整个流程保存在一个场景中
- 预期：HTTP成功和业务成功之外，还要逐条核对筛选条件；多选字段按包含关系比较；非空正例必须命中预期ID；反例不得混入；空结果不能凭空判定过滤正确；改变条件重置分页；清空恢复基线；过期请求不覆盖新条件结果
- 依据：src/pages/subpages/visitPlan/index.vue:2, src/config/mobileSearchConfig.ts:1

### MINI-038-页面呈现 新增计划：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/visitPlan/addPlan`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/visitPlan/addPlan 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/visitPlan/addPlan.vue:2

### MINI-039-页面呈现 拜访计划详情：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/visitPlan/info`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/visitPlan/info 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/visitPlan/info.vue:2

### MINI-040-页面呈现 拜访上报：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/visitPlan/visitReport`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/visitPlan/visitReport 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/visitPlan/visitReport.vue:2

### MINI-041-页面呈现 库存上报：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/visitPlan/visitReport/inventory`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/visitPlan/visitReport/inventory 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/visitPlan/visitReport/inventory.vue:2

### MINI-042-页面呈现 陈列上报：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/visitPlan/visitReport/display`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/visitPlan/visitReport/display 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/visitPlan/visitReport/display.vue:2

### MINI-043-页面呈现 其他上报：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/visitPlan/visitReport/other`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/visitPlan/visitReport/other 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/visitPlan/visitReport/other.vue:2

### MINI-044-页面呈现 异常签退：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/visitPlan/visitReport/abnormalCheckOut`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/visitPlan/visitReport/abnormalCheckOut 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/visitPlan/visitReport/abnormalCheckOut.vue:2

### MINI-045-页面呈现 拜访记录：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/visitPlan/visitRecords`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/visitPlan/visitRecords 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/visitPlan/visitRecords.vue:2

### MINI-045-条件查询合并场景 拜访记录：条件查询合并场景

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：read
- 路由：`/pages/subpages/visitPlan/visitRecords`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 准备本批次正反例及可核对的非空基线；2. 先单独验证关键字及全部条件：上报时间(reportTime)、拜访人(visitorUserName)、客户类型(customerType)、上报任务(reportType)、计划拜访日期(visitDate)、合作状态(cooperationStatus)、客户标签(terminalTags)、上报地址(address)、上报备注(remark)；3. 再组合多个条件，翻页，清空条件并返回列表；整个流程保存在一个场景中
- 预期：HTTP成功和业务成功之外，还要逐条核对筛选条件；多选字段按包含关系比较；非空正例必须命中预期ID；反例不得混入；空结果不能凭空判定过滤正确；改变条件重置分页；清空恢复基线；过期请求不覆盖新条件结果
- 依据：src/pages/subpages/visitPlan/visitRecords.vue:2, src/config/mobileSearchConfig.ts:1

### MINI-046-页面呈现 新增计划外拜访：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/visitPlan/addTempVisitPlan`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/visitPlan/addTempVisitPlan 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/visitPlan/addTempVisitPlan.vue:2

### MINI-047-页面呈现 拜访路线：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/visitPlan/template/index`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/visitPlan/template/index 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/visitPlan/template/index.vue:2

### MINI-047-条件查询合并场景 拜访路线：条件查询合并场景

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：read
- 路由：`/pages/subpages/visitPlan/template/index`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 准备本批次正反例及可核对的非空基线；2. 先单独验证关键字及全部条件：责任人(userId)、创建时间(createTime)、备注(remark)；3. 再组合多个条件，翻页，清空条件并返回列表；整个流程保存在一个场景中
- 预期：HTTP成功和业务成功之外，还要逐条核对筛选条件；多选字段按包含关系比较；非空正例必须命中预期ID；反例不得混入；空结果不能凭空判定过滤正确；改变条件重置分页；清空恢复基线；过期请求不覆盖新条件结果
- 依据：src/pages/subpages/visitPlan/template/index.vue:2, src/config/mobileSearchConfig.ts:1

### MINI-048-页面呈现 拜访详情：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/visitPlan/template/detail`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/visitPlan/template/detail 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/visitPlan/template/detail.vue:2

### MINI-049-页面呈现 临时拜访：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/visitPlan/visitReport/tempVisit`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/visitPlan/visitReport/tempVisit 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/visitPlan/visitReport/tempVisit.vue:2

### MINI-050-页面呈现 选择商品：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/product/index`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/product/index 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/product/index.vue:2

### MINI-051-页面呈现 销售订单：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/business/salesOrder/index`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/business/salesOrder/index 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/business/salesOrder/index.vue:2

### MINI-051-条件查询合并场景 销售订单：条件查询合并场景

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：read
- 路由：`/pages/subpages/business/salesOrder/index`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 准备本批次正反例及可核对的非空基线；2. 先单独验证关键字及全部条件：仓库(warehouseId)、销售人员(createBy)、下单时间(createTime)、出入库状态(inboundStatus)、订单编号(orderNo)、客户名称(customerName)、客户类型(customerType)、销售类型(salesType)、备注(remark)；3. 再组合多个条件，翻页，清空条件并返回列表；整个流程保存在一个场景中
- 预期：HTTP成功和业务成功之外，还要逐条核对筛选条件；多选字段按包含关系比较；非空正例必须命中预期ID；反例不得混入；空结果不能凭空判定过滤正确；改变条件重置分页；清空恢复基线；过期请求不覆盖新条件结果
- 依据：src/pages/subpages/business/salesOrder/index.vue:2, src/config/mobileSearchConfig.ts:1

### MINI-052-页面呈现 新增销售订单：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/business/salesOrder/form`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/business/salesOrder/form 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/business/salesOrder/form.vue:2

### MINI-053-页面呈现 选择销售订单：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/business/salesOrder/select`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/business/salesOrder/select 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/business/salesOrder/select.vue:2

### MINI-053-条件查询合并场景 选择销售订单：条件查询合并场景

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：read
- 路由：`/pages/subpages/business/salesOrder/select`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 准备本批次正反例及可核对的非空基线；2. 先单独验证关键字及全部条件：；3. 再组合多个条件，翻页，清空条件并返回列表；整个流程保存在一个场景中
- 预期：HTTP成功和业务成功之外，还要逐条核对筛选条件；多选字段按包含关系比较；非空正例必须命中预期ID；反例不得混入；空结果不能凭空判定过滤正确；改变条件重置分页；清空恢复基线；过期请求不覆盖新条件结果
- 依据：src/pages/subpages/business/salesOrder/select.vue:2, src/config/mobileSearchConfig.ts:1

### MINI-054-页面呈现 销售订单详情：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/business/salesOrder/info`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/business/salesOrder/info 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/business/salesOrder/info.vue:2

### MINI-055-页面呈现 退货订单：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/business/returnOrder/index`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/business/returnOrder/index 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/business/returnOrder/index.vue:2

### MINI-055-条件查询合并场景 退货订单：条件查询合并场景

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：read
- 路由：`/pages/subpages/business/returnOrder/index`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 准备本批次正反例及可核对的非空基线；2. 先单独验证关键字及全部条件：退货类型(returnOrderType)、销售人员(createBy)、退货日期(createTime)、客户名称(customerName)、原销售订单号(salesOrderNo)、退货仓库(warehouseId)、入库状态(inboundStatus)、客户类型(customerType)、备注(remark)；3. 再组合多个条件，翻页，清空条件并返回列表；整个流程保存在一个场景中
- 预期：HTTP成功和业务成功之外，还要逐条核对筛选条件；多选字段按包含关系比较；非空正例必须命中预期ID；反例不得混入；空结果不能凭空判定过滤正确；改变条件重置分页；清空恢复基线；过期请求不覆盖新条件结果
- 依据：src/pages/subpages/business/returnOrder/index.vue:2, src/config/mobileSearchConfig.ts:1

### MINI-056-页面呈现 新增退货订单：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/business/returnOrder/form`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/business/returnOrder/form 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/business/returnOrder/form.vue:2

### MINI-057-页面呈现 退货订单详情：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/business/returnOrder/info`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/business/returnOrder/info 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/business/returnOrder/info.vue:2

### MINI-058-页面呈现 入库确认：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/business/stockInOrder/index`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/business/stockInOrder/index 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/business/stockInOrder/index.vue:2

### MINI-058-条件查询合并场景 入库确认：条件查询合并场景

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：read
- 路由：`/pages/subpages/business/stockInOrder/index`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 准备本批次正反例及可核对的非空基线；2. 先单独验证关键字及全部条件：来源类型(sourceType)、创建时间(createTime)、入库单号(inboundNo)、客户名称(customerName)、客户类型(customerType)、出库仓库(warehouseName)、入库仓库(targetWarehouseName)、入库时间(inboundTime)、入库确认人(inboundBy)；3. 再组合多个条件，翻页，清空条件并返回列表；整个流程保存在一个场景中
- 预期：HTTP成功和业务成功之外，还要逐条核对筛选条件；多选字段按包含关系比较；非空正例必须命中预期ID；反例不得混入；空结果不能凭空判定过滤正确；改变条件重置分页；清空恢复基线；过期请求不覆盖新条件结果
- 依据：src/pages/subpages/business/stockInOrder/index.vue:2, src/config/mobileSearchConfig.ts:1

### MINI-059-页面呈现 入库订单详情：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/business/stockInOrder/info`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/business/stockInOrder/info 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/business/stockInOrder/info.vue:2

### MINI-060-页面呈现 出库信息：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/business/stockOutOrder/index`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/business/stockOutOrder/index 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/business/stockOutOrder/index.vue:2

### MINI-060-条件查询合并场景 出库信息：条件查询合并场景

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：read
- 路由：`/pages/subpages/business/stockOutOrder/index`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 准备本批次正反例及可核对的非空基线；2. 先单独验证关键字及全部条件：订单类型(sourceType)、创建时间(createTime)、出库单号(inboundNo)、客户名称(customerName)、客户类型(customerType)、出库仓库(warehouseName)、出库时间(inboundTime)、出库确认人(inboundBy)；3. 再组合多个条件，翻页，清空条件并返回列表；整个流程保存在一个场景中
- 预期：HTTP成功和业务成功之外，还要逐条核对筛选条件；多选字段按包含关系比较；非空正例必须命中预期ID；反例不得混入；空结果不能凭空判定过滤正确；改变条件重置分页；清空恢复基线；过期请求不覆盖新条件结果
- 依据：src/pages/subpages/business/stockOutOrder/index.vue:2, src/config/mobileSearchConfig.ts:1

### MINI-061-页面呈现 出库订单详情：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/business/stockOutOrder/info`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/business/stockOutOrder/info 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/business/stockOutOrder/info.vue:2

### MINI-062-页面呈现 采购入库：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/business/purchaseOrder/index`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/business/purchaseOrder/index 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/business/purchaseOrder/index.vue:2

### MINI-062-条件查询合并场景 采购入库：条件查询合并场景

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：read
- 路由：`/pages/subpages/business/purchaseOrder/index`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 准备本批次正反例及可核对的非空基线；2. 先单独验证关键字及全部条件：入库仓库(warehouseId)、审批状态(status)、创建时间(createTime)；3. 再组合多个条件，翻页，清空条件并返回列表；整个流程保存在一个场景中
- 预期：HTTP成功和业务成功之外，还要逐条核对筛选条件；多选字段按包含关系比较；非空正例必须命中预期ID；反例不得混入；空结果不能凭空判定过滤正确；改变条件重置分页；清空恢复基线；过期请求不覆盖新条件结果
- 依据：src/pages/subpages/business/purchaseOrder/index.vue:2, src/config/mobileSearchConfig.ts:1

### MINI-063-页面呈现 采购入库详情：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/business/purchaseOrder/info`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/business/purchaseOrder/info 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/business/purchaseOrder/info.vue:2

### MINI-064-页面呈现 新增采购入库：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/business/purchaseOrder/form`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/business/purchaseOrder/form 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/business/purchaseOrder/form.vue:2

### MINI-065-页面呈现 仓库信息：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/warehouse/productList`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/warehouse/productList 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/warehouse/productList.vue:2

### MINI-065-条件查询合并场景 仓库信息：条件查询合并场景

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：read
- 路由：`/pages/subpages/warehouse/productList`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 准备本批次正反例及可核对的非空基线；2. 先单独验证关键字及全部条件：仓库名称(warehouseId)、商品品牌(productBrand)；3. 再组合多个条件，翻页，清空条件并返回列表；整个流程保存在一个场景中
- 预期：HTTP成功和业务成功之外，还要逐条核对筛选条件；多选字段按包含关系比较；非空正例必须命中预期ID；反例不得混入；空结果不能凭空判定过滤正确；改变条件重置分页；清空恢复基线；过期请求不覆盖新条件结果
- 依据：src/pages/subpages/warehouse/productList.vue:2, src/config/mobileSearchConfig.ts:1

### MINI-066-页面呈现 拆箱补件：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/warehouse/inventoryConvert`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/warehouse/inventoryConvert 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/warehouse/inventoryConvert.vue:2

### MINI-067-页面呈现 商品详情：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：manual；风险：read
- 路由：`/pages/subpages/warehouse/productDetail`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/warehouse/productDetail 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/warehouse/productDetail.vue:2

### MINI-068-页面呈现 选择仓库：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/warehouse/select`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/warehouse/select 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/warehouse/select.vue:2

### MINI-068-条件查询合并场景 选择仓库：条件查询合并场景

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：read
- 路由：`/pages/subpages/warehouse/select`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 准备本批次正反例及可核对的非空基线；2. 先单独验证关键字及全部条件：仓库类型(warehouseType)；3. 再组合多个条件，翻页，清空条件并返回列表；整个流程保存在一个场景中
- 预期：HTTP成功和业务成功之外，还要逐条核对筛选条件；多选字段按包含关系比较；非空正例必须命中预期ID；反例不得混入；空结果不能凭空判定过滤正确；改变条件重置分页；清空恢复基线；过期请求不覆盖新条件结果
- 依据：src/pages/subpages/warehouse/select.vue:2, src/config/mobileSearchConfig.ts:1

### MINI-069-页面呈现 消息通知：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/messageCenter/index`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/messageCenter/index 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/messageCenter/index.vue:2

### MINI-070-页面呈现 待办理：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/messageCenter/todo`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/messageCenter/todo 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/messageCenter/todo.vue:2

### MINI-071-页面呈现 待审批：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/messageCenter/approval`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/messageCenter/approval 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/messageCenter/approval.vue:2

### MINI-072-页面呈现 我的审批：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/messageCenter/myApproval`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/messageCenter/myApproval 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/messageCenter/myApproval.vue:2

### MINI-073-页面呈现 线上拜访：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/onlineVisit/index`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/onlineVisit/index 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/onlineVisit/index.vue:2

### MINI-073-条件查询合并场景 线上拜访：条件查询合并场景

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：read
- 路由：`/pages/subpages/onlineVisit/index`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 准备本批次正反例及可核对的非空基线；2. 先单独验证关键字及全部条件：拜访类型(visitMethod)、拜访人(visitorUserId)、拜访时间(visitTime)、客户类型(customerType)；3. 再组合多个条件，翻页，清空条件并返回列表；整个流程保存在一个场景中
- 预期：HTTP成功和业务成功之外，还要逐条核对筛选条件；多选字段按包含关系比较；非空正例必须命中预期ID；反例不得混入；空结果不能凭空判定过滤正确；改变条件重置分页；清空恢复基线；过期请求不覆盖新条件结果
- 依据：src/pages/subpages/onlineVisit/index.vue:2, src/config/mobileSearchConfig.ts:1

### MINI-074-页面呈现 新增线上拜访：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/onlineVisit/form`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/onlineVisit/form 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/onlineVisit/form.vue:2

### MINI-075-页面呈现 任务清单：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/supervision/list`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/supervision/list 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/supervision/list.vue:2

### MINI-075-条件查询合并场景 任务清单：条件查询合并场景

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：read
- 路由：`/pages/subpages/supervision/list`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 准备本批次正反例及可核对的非空基线；2. 先单独验证关键字及全部条件：任务状态(status)、创建时间(createTime)；3. 再组合多个条件，翻页，清空条件并返回列表；整个流程保存在一个场景中
- 预期：HTTP成功和业务成功之外，还要逐条核对筛选条件；多选字段按包含关系比较；非空正例必须命中预期ID；反例不得混入；空结果不能凭空判定过滤正确；改变条件重置分页；清空恢复基线；过期请求不覆盖新条件结果
- 依据：src/pages/subpages/supervision/list.vue:2, src/config/mobileSearchConfig.ts:1

### MINI-076-页面呈现 发布任务：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/supervision/create`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/supervision/create 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/supervision/create.vue:2

### MINI-077-页面呈现 任务详情：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/supervision/detail`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/supervision/detail 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/supervision/detail.vue:2

### MINI-078-页面呈现 上报工作：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/supervision/report`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/supervision/report 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/supervision/report.vue:2

### MINI-079-页面呈现 选择员工：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/supervision/selectUsers`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/supervision/selectUsers 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/supervision/selectUsers.vue:2

### MINI-080-页面呈现 客户列表：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/data/customerList`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/data/customerList 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/data/customerList.vue:2

### MINI-081-页面呈现 销售订单：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/data/salesOrderList`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/data/salesOrderList 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/data/salesOrderList.vue:2

### MINI-082-页面呈现 退货订单：页面呈现

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/data/returnOrderList`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开 /pages/subpages/data/returnOrderList 并等待页面根元素；2. 确认没有重定向到登录或其他页面
- 预期：路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确
- 依据：src/pages/subpages/data/returnOrderList.vue:2

### MINI-002-空账号密码 登录：空账号密码

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/login/index`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 设置账号和密码为空账号密码组合；2. 观察登录按钮，不提交登录请求
- 预期：登录按钮禁用；不产生登录请求
- 依据：src/pages/login/index.vue:2

### MINI-002-仅账号 登录：仅账号

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/login/index`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 设置账号和密码为仅账号组合；2. 观察登录按钮，不提交登录请求
- 预期：登录按钮禁用；不产生登录请求
- 依据：src/pages/login/index.vue:2

### MINI-002-仅密码 登录：仅密码

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/login/index`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 设置账号和密码为仅密码组合；2. 观察登录按钮，不提交登录请求
- 预期：登录按钮禁用；不产生登录请求
- 依据：src/pages/login/index.vue:2

### MINI-002-全空白账号 登录：全空白账号

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/login/index`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 设置账号和密码为全空白账号组合；2. 观察登录按钮，不提交登录请求
- 预期：登录按钮禁用；不产生登录请求
- 依据：src/pages/login/index.vue:2

### MINI-002-全空白密码 登录：全空白密码

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/login/index`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 设置账号和密码为全空白密码组合；2. 观察登录按钮，不提交登录请求
- 预期：登录按钮禁用；不产生登录请求
- 依据：src/pages/login/index.vue:2

### MINI-002-密码显隐 登录：密码显隐

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/login/index`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 输入非真实密码样例；2. 点击一次显隐按钮，再点击一次
- 预期：默认隐藏；一次点击显示，再次隐藏；内容不丢失、不自动提交
- 依据：src/pages/login/index.vue:2

### MINI-052-空表单提交拦截 新增销售订单：空表单提交拦截

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/business/salesOrder/form`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开全新空表单；2. 不选择客户，点击提交
- 预期：提示“请选择客户”；不创建订单
- 依据：src/pages/subpages/business/salesOrder/form.vue:2

### MINI-056-空表单提交拦截 新增退货订单：空表单提交拦截

- 平台：h5, mp-weixin；级别：P1；执行：scripted；风险：read
- 路由：`/pages/subpages/business/returnOrder/form`
- 前置：专用测试环境；已登录具有对应功能权限的账号；依赖ID从本批次测试数据中获取，不使用固定历史ID
- 步骤：1. 打开全新空表单；2. 不选择客户，点击提交
- 预期：提示“请选择客户”；不创建订单
- 依据：src/pages/subpages/business/returnOrder/form.vue:2

### BIZ-login-normal 有效账号登录

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：session
- 路由：`/pages/login/index`
- 前置：仅专用测试账号；不在用例或日志中写入真实凭据；验证码人工完成
- 步骤：1. 使用专用测试账号登录；2. 服务启用验证码时由人工填写；3. 进入工作台并读取个人信息
- 预期：成功获取会话且身份正确；密码经公钥加密后提交；不记录密码、验证码和Token
- 依据：src/pages/login/index.vue:2

### BIZ-login-invalid 错误账号或密码

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：session
- 路由：`/pages/login/index`
- 前置：仅专用测试账号；不在用例或日志中写入真实凭据；验证码人工完成
- 步骤：1. 使用专用账号和一次错误密码；2. 提交一次；3. 观察登录结果
- 预期：停留登录页并明确提示；不残留失败会话；不得反复尝试触发账号锁定
- 依据：src/pages/login/index.vue:2

### BIZ-login-captcha 验证码启停、刷新与失效

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：session
- 路由：`/pages/login/index`
- 前置：仅专用测试账号；不在用例或日志中写入真实凭据；验证码人工完成
- 步骤：1. 在测试环境切换验证码配置；2. 检查必填；3. 刷新后提交旧验证码再提交新验证码
- 预期：开启才显示并必填；旧验证码被拒绝；刷新uuid与图片同步；不绕过验证
- 依据：src/pages/login/index.vue:2

### BIZ-login-public-key 登录公钥接口失败和重复提交

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：session
- 路由：`/pages/login/index`
- 前置：仅专用测试账号；不在用例或日志中写入真实凭据；验证码人工完成
- 步骤：1. 模拟公钥读取失败；2. 恢复后快速重复点击登录
- 预期：失败不发送明文密码且loading恢复；正常时只发起一次登录；错误不会误显示成功
- 依据：src/pages/login/index.vue:2

### BIZ-terminal-create 前端客户新增与详情回读

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/customer/business/form`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 按字段规则填写有效数据，名称使用自然业务名称加批次时间戳；2. 选择字典、客户经理和位置；3. 提交并记录客户ID；4. 打开本次客户详情
- 预期：HTTP与业务结果均成功；详情字段与输入一致；审批存在时为待审批，无审批时按配置生效
- 依据：src/pages/subpages/customer/business/form.vue:2

### BIZ-terminal-edit 前端客户编辑及返回刷新

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/customer/business/form`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 从本轮客户详情进入编辑；2. 仅修改本轮客户联系人和备注；3. 保存后返回列表再打开详情
- 预期：ID不变且修改持久化；列表与详情一致；返回保持筛选与滚动位置
- 依据：src/pages/subpages/customer/business/form.vue:2

### BIZ-terminal-approve-pass 前端客户审批通过

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/customer/business/info`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 创建本轮客户并读取详情审批信息；2. 使用当前节点真实审批人登录；3. 审批通过并回读客户和审批日志
- 预期：客户审批通过且可正常使用；审批人、节点与日志一致；重复提交不重复执行
- 依据：src/pages/subpages/customer/business/info.vue:2

### BIZ-terminal-approve-reject 前端客户审批拒绝

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/customer/business/info`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 创建本轮客户并读取详情审批信息；2. 使用当前节点真实审批人登录；3. 审批拒绝并回读客户和审批日志
- 预期：客户被拒绝且不能被当作审批通过客户使用；拒绝原因与日志保留
- 依据：src/pages/subpages/customer/business/info.vue:2

### BIZ-terminal-resubmit 前端客户拒绝后修改并重新提交

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/customer/business/info`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 创建并拒绝本轮客户；2. 修改符合规则的内容；3. 重新提交；4. 读取新的审批节点
- 预期：新一轮审批启动；旧审批日志保留；不得沿用旧节点ID审批
- 依据：src/pages/subpages/customer/business/info.vue:2

### BIZ-terminal-delete-cancel 前端客户删除取消

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/customer/business/info`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 打开本轮未关联业务的客户；2. 点击删除；3. 在二次确认中取消；4. 重新查看列表与详情
- 预期：没有删除请求或业务变更；客户仍存在
- 依据：src/pages/subpages/customer/business/info.vue:2

### BIZ-terminal-delete 前端客户删除与关联限制

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/customer/business/info`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 删除本轮可删除客户并回读；2. 另建关联本轮订单的客户后尝试删除
- 预期：允许删除的数据在列表不再出现；存在关联时按已确认业务规则拒绝且不破坏关联
- 依据：src/pages/subpages/customer/business/info.vue:2

### BIZ-terminal-cooperation 前端客户合作状态包含匹配

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：read
- 路由：`/pages/subpages/customer/business/index`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 准备至少两个合作状态的本轮客户；2. 选择其中一个状态过滤；3. 逐条核对返回记录
- 预期：每条记录的合作状态集合包含所选值即通过，不要求整个字段字符串等于单个值；无匹配时为空列表
- 依据：src/pages/subpages/customer/business/index.vue:2

### BIZ-direct-create 直营客户新增与详情回读

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/customer/directly/form`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 按字段规则填写有效数据，名称使用自然业务名称加批次时间戳；2. 选择字典、客户经理和位置；3. 提交并记录客户ID；4. 打开本次客户详情
- 预期：HTTP与业务结果均成功；详情字段与输入一致；审批存在时为待审批，无审批时按配置生效
- 依据：src/pages/subpages/customer/directly/form.vue:2

### BIZ-direct-edit 直营客户编辑及返回刷新

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/customer/directly/form`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 从本轮客户详情进入编辑；2. 仅修改本轮客户联系人和备注；3. 保存后返回列表再打开详情
- 预期：ID不变且修改持久化；列表与详情一致；返回保持筛选与滚动位置
- 依据：src/pages/subpages/customer/directly/form.vue:2

### BIZ-direct-approve-pass 直营客户审批通过

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/customer/directly/info`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 创建本轮客户并读取详情审批信息；2. 使用当前节点真实审批人登录；3. 审批通过并回读客户和审批日志
- 预期：客户审批通过且可正常使用；审批人、节点与日志一致；重复提交不重复执行
- 依据：src/pages/subpages/customer/directly/info.vue:2

### BIZ-direct-approve-reject 直营客户审批拒绝

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/customer/directly/info`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 创建本轮客户并读取详情审批信息；2. 使用当前节点真实审批人登录；3. 审批拒绝并回读客户和审批日志
- 预期：客户被拒绝且不能被当作审批通过客户使用；拒绝原因与日志保留
- 依据：src/pages/subpages/customer/directly/info.vue:2

### BIZ-direct-resubmit 直营客户拒绝后修改并重新提交

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/customer/directly/info`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 创建并拒绝本轮客户；2. 修改符合规则的内容；3. 重新提交；4. 读取新的审批节点
- 预期：新一轮审批启动；旧审批日志保留；不得沿用旧节点ID审批
- 依据：src/pages/subpages/customer/directly/info.vue:2

### BIZ-direct-delete-cancel 直营客户删除取消

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/customer/directly/info`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 打开本轮未关联业务的客户；2. 点击删除；3. 在二次确认中取消；4. 重新查看列表与详情
- 预期：没有删除请求或业务变更；客户仍存在
- 依据：src/pages/subpages/customer/directly/info.vue:2

### BIZ-direct-delete 直营客户删除与关联限制

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/customer/directly/info`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 删除本轮可删除客户并回读；2. 另建关联本轮订单的客户后尝试删除
- 预期：允许删除的数据在列表不再出现；存在关联时按已确认业务规则拒绝且不破坏关联
- 依据：src/pages/subpages/customer/directly/info.vue:2

### BIZ-direct-cooperation 直营客户合作状态包含匹配

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：read
- 路由：`/pages/subpages/customer/directly/index`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 准备至少两个合作状态的本轮客户；2. 选择其中一个状态过滤；3. 逐条核对返回记录
- 预期：每条记录的合作状态集合包含所选值即通过，不要求整个字段字符串等于单个值；无匹配时为空列表
- 依据：src/pages/subpages/customer/directly/index.vue:2

### BIZ-kol-create KOL客户新增与详情回读

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/customer/kol/form`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 按字段规则填写有效数据，名称使用自然业务名称加批次时间戳；2. 选择字典、客户经理和位置；3. 提交并记录客户ID；4. 打开本次客户详情
- 预期：HTTP与业务结果均成功；详情字段与输入一致；审批存在时为待审批，无审批时按配置生效
- 依据：src/pages/subpages/customer/kol/form.vue:2

### BIZ-kol-edit KOL客户编辑及返回刷新

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/customer/kol/form`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 从本轮客户详情进入编辑；2. 仅修改本轮客户联系人和备注；3. 保存后返回列表再打开详情
- 预期：ID不变且修改持久化；列表与详情一致；返回保持筛选与滚动位置
- 依据：src/pages/subpages/customer/kol/form.vue:2

### BIZ-kol-approve-pass KOL客户审批通过

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/customer/kol/info`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 创建本轮客户并读取详情审批信息；2. 使用当前节点真实审批人登录；3. 审批通过并回读客户和审批日志
- 预期：客户审批通过且可正常使用；审批人、节点与日志一致；重复提交不重复执行
- 依据：src/pages/subpages/customer/kol/info.vue:2

### BIZ-kol-approve-reject KOL客户审批拒绝

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/customer/kol/info`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 创建本轮客户并读取详情审批信息；2. 使用当前节点真实审批人登录；3. 审批拒绝并回读客户和审批日志
- 预期：客户被拒绝且不能被当作审批通过客户使用；拒绝原因与日志保留
- 依据：src/pages/subpages/customer/kol/info.vue:2

### BIZ-kol-resubmit KOL客户拒绝后修改并重新提交

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/customer/kol/info`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 创建并拒绝本轮客户；2. 修改符合规则的内容；3. 重新提交；4. 读取新的审批节点
- 预期：新一轮审批启动；旧审批日志保留；不得沿用旧节点ID审批
- 依据：src/pages/subpages/customer/kol/info.vue:2

### BIZ-kol-delete-cancel KOL客户删除取消

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/customer/kol/info`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 打开本轮未关联业务的客户；2. 点击删除；3. 在二次确认中取消；4. 重新查看列表与详情
- 预期：没有删除请求或业务变更；客户仍存在
- 依据：src/pages/subpages/customer/kol/info.vue:2

### BIZ-kol-delete KOL客户删除与关联限制

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/customer/kol/info`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 删除本轮可删除客户并回读；2. 另建关联本轮订单的客户后尝试删除
- 预期：允许删除的数据在列表不再出现；存在关联时按已确认业务规则拒绝且不破坏关联
- 依据：src/pages/subpages/customer/kol/info.vue:2

### BIZ-kol-cooperation KOL客户合作状态包含匹配

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：read
- 路由：`/pages/subpages/customer/kol/index`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 准备至少两个合作状态的本轮客户；2. 选择其中一个状态过滤；3. 逐条核对返回记录
- 预期：每条记录的合作状态集合包含所选值即通过，不要求整个字段字符串等于单个值；无匹配时为空列表
- 依据：src/pages/subpages/customer/kol/index.vue:2

### BIZ-sales-head-terminal-pass 总仓销售给前端客户：审批、锁库和扣库

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/business/salesOrder/info`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 记录总仓商品实际/锁定/可用库存；2. 给本轮前端客户创建正数量销售订单；3. 审批前回读库存；4. 读取详情审批并由真实审批人通过；5. 读取关联出入库订单；6. 有待确认单则由对应仓管确认，无则直接回读；7. 核对订单及库存
- 预期：审批前库存不因本销售单锁定；审批通过后锁库；待确认时实际量不变、可用量按数量减少；确认后或自动完成时实际量扣减且锁定释放；订单与库存流水一致，不将自动完成硬编码为待确认状态
- 依据：src/pages/subpages/business/salesOrder/info.vue:2

### BIZ-sales-head-terminal-reject 总仓销售给前端客户：审批拒绝

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/business/salesOrder/info`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 记录初始库存；2. 创建本轮订单；3. 查询审批节点并拒绝；4. 回读库存和订单
- 预期：订单被拒绝；实际、锁定、可用库存均与基线一致；无完成的出入库单
- 依据：src/pages/subpages/business/salesOrder/info.vue:2

### BIZ-sales-head-terminal-oversell 总仓销售给前端客户：超可用库存与无库存商品

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/business/salesOrder/form`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 准备库存固定的白名单商品；2. 分别选择超过可用量的数量和仓库无库存的商品；3. 提交并回读订单和库存
- 预期：页面限制或服务业务拒绝均可，但必须包含正确原因；不生成成功订单；库存不变；SQL异常、未登录等不算预期业务拒绝
- 依据：src/pages/subpages/business/salesOrder/form.vue:2

### BIZ-sales-head-direct-pass 总仓销售给直营客户：审批、锁库和扣库

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/business/salesOrder/info`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 记录总仓商品实际/锁定/可用库存；2. 给本轮直营客户创建正数量销售订单；3. 审批前回读库存；4. 读取详情审批并由真实审批人通过；5. 读取关联出入库订单；6. 有待确认单则由对应仓管确认，无则直接回读；7. 核对订单及库存
- 预期：审批前库存不因本销售单锁定；审批通过后锁库；待确认时实际量不变、可用量按数量减少；确认后或自动完成时实际量扣减且锁定释放；订单与库存流水一致，不将自动完成硬编码为待确认状态
- 依据：src/pages/subpages/business/salesOrder/info.vue:2

### BIZ-sales-head-direct-reject 总仓销售给直营客户：审批拒绝

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/business/salesOrder/info`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 记录初始库存；2. 创建本轮订单；3. 查询审批节点并拒绝；4. 回读库存和订单
- 预期：订单被拒绝；实际、锁定、可用库存均与基线一致；无完成的出入库单
- 依据：src/pages/subpages/business/salesOrder/info.vue:2

### BIZ-sales-head-direct-oversell 总仓销售给直营客户：超可用库存与无库存商品

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/business/salesOrder/form`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 准备库存固定的白名单商品；2. 分别选择超过可用量的数量和仓库无库存的商品；3. 提交并回读订单和库存
- 预期：页面限制或服务业务拒绝均可，但必须包含正确原因；不生成成功订单；库存不变；SQL异常、未登录等不算预期业务拒绝
- 依据：src/pages/subpages/business/salesOrder/form.vue:2

### BIZ-sales-head-kol-pass 总仓销售给KOL客户：审批、锁库和扣库

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/business/salesOrder/info`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 记录总仓商品实际/锁定/可用库存；2. 给本轮KOL客户创建正数量销售订单；3. 审批前回读库存；4. 读取详情审批并由真实审批人通过；5. 读取关联出入库订单；6. 有待确认单则由对应仓管确认，无则直接回读；7. 核对订单及库存
- 预期：审批前库存不因本销售单锁定；审批通过后锁库；待确认时实际量不变、可用量按数量减少；确认后或自动完成时实际量扣减且锁定释放；订单与库存流水一致，不将自动完成硬编码为待确认状态
- 依据：src/pages/subpages/business/salesOrder/info.vue:2

### BIZ-sales-head-kol-reject 总仓销售给KOL客户：审批拒绝

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/business/salesOrder/info`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 记录初始库存；2. 创建本轮订单；3. 查询审批节点并拒绝；4. 回读库存和订单
- 预期：订单被拒绝；实际、锁定、可用库存均与基线一致；无完成的出入库单
- 依据：src/pages/subpages/business/salesOrder/info.vue:2

### BIZ-sales-head-kol-oversell 总仓销售给KOL客户：超可用库存与无库存商品

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/business/salesOrder/form`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 准备库存固定的白名单商品；2. 分别选择超过可用量的数量和仓库无库存的商品；3. 提交并回读订单和库存
- 预期：页面限制或服务业务拒绝均可，但必须包含正确原因；不生成成功订单；库存不变；SQL异常、未登录等不算预期业务拒绝
- 依据：src/pages/subpages/business/salesOrder/form.vue:2

### BIZ-sales-direct-terminal-pass 直营仓销售给前端客户：审批、锁库和扣库

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/business/salesOrder/info`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 记录直营仓商品实际/锁定/可用库存；2. 给本轮前端客户创建正数量销售订单；3. 审批前回读库存；4. 读取详情审批并由真实审批人通过；5. 读取关联出入库订单；6. 有待确认单则由对应仓管确认，无则直接回读；7. 核对订单及库存
- 预期：审批前库存不因本销售单锁定；审批通过后锁库；待确认时实际量不变、可用量按数量减少；确认后或自动完成时实际量扣减且锁定释放；订单与库存流水一致，不将自动完成硬编码为待确认状态
- 依据：src/pages/subpages/business/salesOrder/info.vue:2

### BIZ-sales-direct-terminal-reject 直营仓销售给前端客户：审批拒绝

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/business/salesOrder/info`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 记录初始库存；2. 创建本轮订单；3. 查询审批节点并拒绝；4. 回读库存和订单
- 预期：订单被拒绝；实际、锁定、可用库存均与基线一致；无完成的出入库单
- 依据：src/pages/subpages/business/salesOrder/info.vue:2

### BIZ-sales-direct-terminal-oversell 直营仓销售给前端客户：超可用库存与无库存商品

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/business/salesOrder/form`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 准备库存固定的白名单商品；2. 分别选择超过可用量的数量和仓库无库存的商品；3. 提交并回读订单和库存
- 预期：页面限制或服务业务拒绝均可，但必须包含正确原因；不生成成功订单；库存不变；SQL异常、未登录等不算预期业务拒绝
- 依据：src/pages/subpages/business/salesOrder/form.vue:2

### BIZ-sales-direct-direct-pass 直营仓销售给直营客户：审批、锁库和扣库

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/business/salesOrder/info`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 记录直营仓商品实际/锁定/可用库存；2. 给本轮直营客户创建正数量销售订单；3. 审批前回读库存；4. 读取详情审批并由真实审批人通过；5. 读取关联出入库订单；6. 有待确认单则由对应仓管确认，无则直接回读；7. 核对订单及库存
- 预期：审批前库存不因本销售单锁定；审批通过后锁库；待确认时实际量不变、可用量按数量减少；确认后或自动完成时实际量扣减且锁定释放；订单与库存流水一致，不将自动完成硬编码为待确认状态
- 依据：src/pages/subpages/business/salesOrder/info.vue:2

### BIZ-sales-direct-direct-reject 直营仓销售给直营客户：审批拒绝

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/business/salesOrder/info`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 记录初始库存；2. 创建本轮订单；3. 查询审批节点并拒绝；4. 回读库存和订单
- 预期：订单被拒绝；实际、锁定、可用库存均与基线一致；无完成的出入库单
- 依据：src/pages/subpages/business/salesOrder/info.vue:2

### BIZ-sales-direct-direct-oversell 直营仓销售给直营客户：超可用库存与无库存商品

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/business/salesOrder/form`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 准备库存固定的白名单商品；2. 分别选择超过可用量的数量和仓库无库存的商品；3. 提交并回读订单和库存
- 预期：页面限制或服务业务拒绝均可，但必须包含正确原因；不生成成功订单；库存不变；SQL异常、未登录等不算预期业务拒绝
- 依据：src/pages/subpages/business/salesOrder/form.vue:2

### BIZ-sales-direct-kol-pass 直营仓销售给KOL客户：审批、锁库和扣库

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/business/salesOrder/info`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 记录直营仓商品实际/锁定/可用库存；2. 给本轮KOL客户创建正数量销售订单；3. 审批前回读库存；4. 读取详情审批并由真实审批人通过；5. 读取关联出入库订单；6. 有待确认单则由对应仓管确认，无则直接回读；7. 核对订单及库存
- 预期：审批前库存不因本销售单锁定；审批通过后锁库；待确认时实际量不变、可用量按数量减少；确认后或自动完成时实际量扣减且锁定释放；订单与库存流水一致，不将自动完成硬编码为待确认状态
- 依据：src/pages/subpages/business/salesOrder/info.vue:2

### BIZ-sales-direct-kol-reject 直营仓销售给KOL客户：审批拒绝

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/business/salesOrder/info`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 记录初始库存；2. 创建本轮订单；3. 查询审批节点并拒绝；4. 回读库存和订单
- 预期：订单被拒绝；实际、锁定、可用库存均与基线一致；无完成的出入库单
- 依据：src/pages/subpages/business/salesOrder/info.vue:2

### BIZ-sales-direct-kol-oversell 直营仓销售给KOL客户：超可用库存与无库存商品

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/business/salesOrder/form`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 准备库存固定的白名单商品；2. 分别选择超过可用量的数量和仓库无库存的商品；3. 提交并回读订单和库存
- 预期：页面限制或服务业务拒绝均可，但必须包含正确原因；不生成成功订单；库存不变；SQL异常、未登录等不算预期业务拒绝
- 依据：src/pages/subpages/business/salesOrder/form.vue:2

### BIZ-sales-sellout 销售刚好卖完、可用为0但实际不为0

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/business/salesOrder/info`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 使用会生成待确认单的组合；2. 订单数量等于可用库存；3. 审批通过但不确认；4. 读取库存；5. 同商品再次下单；6. 确认原订单；7. 再次读取库存
- 预期：待确认时可用=0、实际>0、锁定=销售量；新单因可用不足拒绝；确认后实际扣减、锁定释放、可用不负数
- 依据：src/pages/subpages/business/salesOrder/info.vue:2

### BIZ-sales-zero-negative 销售数量0、负数、小数与重复提交

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/business/salesOrder/form`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 分别输入0、负数、规格不支持的小数；2. 在有效订单提交时快速重复点击；3. 查询本批次订单
- 预期：非法数量不产生有效订单且库存不变；重复点击只生成一单或返回明确幂等拒绝；不能把服务接受非法量改成通过
- 依据：src/pages/subpages/business/salesOrder/form.vue:2

### BIZ-sales-gift-price 销售商品、赠品与金额汇总

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/business/salesOrder/form`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 添加不同单价的多个商品和赠品；2. 修改数量、移除一项；3. 分别选择直营及非直营客户
- 预期：总数量含赠品；金额按计价规则精确至2位且不多计赠品；直营客户金额展示遵循页面分支
- 依据：src/pages/subpages/business/salesOrder/form.vue:2

### BIZ-purchase-pass 采购审批通过及库存节点

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/business/purchaseOrder/info`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 记录白名单库存；2. 新建采购单并上传有效凭证；3. 读取详情审批流程；4. 有审批时由节点审批人通过；5. 查询是否生成待确认入库单；6. 需要确认时由仓管确认；7. 逐节点读取库存
- 预期：存在待确认单时确认后才增加实际与可用库存；没有确认环节时按业务流程直接入库；每个节点只增加一次
- 依据：src/pages/subpages/business/purchaseOrder/info.vue:2

### BIZ-purchase-reject 采购审批拒绝及库存节点

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/business/purchaseOrder/info`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 记录白名单库存；2. 新建采购单并上传有效凭证；3. 读取详情审批流程；4. 有审批时由节点审批人拒绝；5. 查询是否生成待确认入库单；6. 需要确认时由仓管确认；7. 逐节点读取库存
- 预期：有审批的采购拒绝后库存不变；无审批配置时本拒绝分支标记不适用，不伪造节点
- 依据：src/pages/subpages/business/purchaseOrder/info.vue:2

### BIZ-purchase-no-approval 采购无审批流程与重复确认

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/business/purchaseOrder/info`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 在已核准无审批配置中创建采购单；2. 查看真实关联入库单并完成需要的确认；3. 重复确认
- 预期：不伪造审批；有待确认单则确认后入库，无则直接入库；重复操作不重复增加库存
- 依据：src/pages/subpages/business/purchaseOrder/info.vue:2

### BIZ-purchase-voucher 采购凭证类型、上传失败与重试

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/business/purchaseOrder/form`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 上传有效图片、PDF；2. 尝试超限类型和体积；3. 模拟上传失败后重试；4. 移除凭证
- 预期：类型及数量限制符合页面和服务配置；失败有提示且不能引用未成功文件；删除后提交不残留旧URL
- 依据：src/pages/subpages/business/purchaseOrder/form.vue:2

### BIZ-return-related-pass 关联原销售单：审批及入库确认

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/business/returnOrder/info`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 使用本轮完成销售单及收货仓库记录库存；2. 创建关联原销售单退货；3. 读详情审批信息；4. 有审批时通过，无审批不伪造；5. 读取待确认入库单；6. 存在时由收货仓管确认；7. 回读库存
- 预期：有审批先通过；有待确认单确认后才增加库存，无则直接入库；完好退货实际/可用增加正确且只增加一次
- 依据：src/pages/subpages/business/returnOrder/info.vue:2

### BIZ-return-related-reject 关联原销售单：审批拒绝与库存不变

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/business/returnOrder/info`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 在有审批配置中创建本轮退货单；2. 读取当前节点并拒绝；3. 核对库存与关联单
- 预期：拒绝后不入库；实际与可用库存不变；不会出现已完成入库单
- 依据：src/pages/subpages/business/returnOrder/info.vue:2

### BIZ-return-related-quantity 关联原销售单：异常退货数量

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/business/returnOrder/form`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 分别输入0、负数、超过可退数量；2. 针对本轮销售重复退货；3. 查看订单和库存
- 预期：不合法退货被明确拒绝；累计退货不超过可退量；不出现SQL异常和重复入库
- 依据：src/pages/subpages/business/returnOrder/form.vue:2

### BIZ-return-direct-pass 直接退货：审批及入库确认

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/business/returnOrder/info`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 使用本轮完成销售单及收货仓库记录库存；2. 创建直接退货退货；3. 读详情审批信息；4. 有审批时通过，无审批不伪造；5. 读取待确认入库单；6. 存在时由收货仓管确认；7. 回读库存
- 预期：有审批先通过；有待确认单确认后才增加库存，无则直接入库；完好退货实际/可用增加正确且只增加一次
- 依据：src/pages/subpages/business/returnOrder/info.vue:2

### BIZ-return-direct-reject 直接退货：审批拒绝与库存不变

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/business/returnOrder/info`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 在有审批配置中创建本轮退货单；2. 读取当前节点并拒绝；3. 核对库存与关联单
- 预期：拒绝后不入库；实际与可用库存不变；不会出现已完成入库单
- 依据：src/pages/subpages/business/returnOrder/info.vue:2

### BIZ-return-direct-quantity 直接退货：异常退货数量

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/business/returnOrder/form`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 分别输入0、负数、超过可退数量；2. 针对本轮销售重复退货；3. 查看订单和库存
- 预期：不合法退货被明确拒绝；累计退货不超过可退量；不出现SQL异常和重复入库
- 依据：src/pages/subpages/business/returnOrder/form.vue:2

### BIZ-return-related-fields 关联退货切换为直接退货后的字段清理

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/business/returnOrder/form`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 先选择本轮销售单；2. 切换直接退货并选择另一客户和仓库；3. 再切回关联退货
- 预期：客户、仓库、商品和可退量随模式重新计算；不带上一次模式隐藏字段提交
- 依据：src/pages/subpages/business/returnOrder/form.vue:2

### BIZ-convert-ratio 固定装箱规格换算

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/warehouse/inventoryConvert`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 选择装箱规格为1*N的源商品与1*1目标商品；2. 输入源数量Q；3. 提交一次；4. 回读两种商品库存
- 预期：目标量必须=Q*N；源实际/可用减Q、目标加Q*N；无需审批或确认且立即生效
- 依据：src/pages/subpages/warehouse/inventoryConvert.vue:2

### BIZ-convert-stock 拆箱超库存及可用为0

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/warehouse/inventoryConvert`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 使用库存不足或已全部锁定的源商品；2. 尝试转换
- 预期：明确库存不足拒绝；实际、锁定、可用与目标库存均不变
- 依据：src/pages/subpages/warehouse/inventoryConvert.vue:2

### BIZ-convert-target 非1*1目标、同商品与不匹配规格

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/warehouse/inventoryConvert`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 尝试选择非1*1、同源商品、与源不匹配的目标商品
- 预期：不能成功转换不合法组合；不得接受人为目标数量绕过固定比例
- 依据：src/pages/subpages/warehouse/inventoryConvert.vue:2

### BIZ-convert-bad-spec 缺失或异常装箱规格

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/warehouse/inventoryConvert`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 使用缺失、非数字、零、负值及非整数装箱规格的测试商品
- 预期：页面禁止提交或返回清晰错误；不产生库存变更
- 依据：src/pages/subpages/warehouse/inventoryConvert.vue:2

### BIZ-convert-boundary 拆箱刚好耗尽及重复点击

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/warehouse/inventoryConvert`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 源数量等于可用量；2. 快速连续提交；3. 查询流水和库存
- 预期：源不为负且只转换一次；目标累计量与有效流水一致
- 依据：src/pages/subpages/warehouse/inventoryConvert.vue:2

### BIZ-convert-lifecycle 销售、退货、拆箱连续库存核对

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/warehouse/inventoryConvert`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 完成一次拆箱；2. 销售转换后的商品并按真实流程审批确认；3. 对本轮销售退货并按真实流程入库
- 预期：每个节点实际/可用/锁定均与独立台账一致；最终库存守恒，无重复扣加
- 依据：src/pages/subpages/warehouse/inventoryConvert.vue:2

### BIZ-visit-normal 正常签到、上报和签退

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/visitPlan/visitReport`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 创建本轮拜访计划；2. 真实定位在范围内签到；3. 按要求上报库存/陈列/其他；4. 满足最短时长后签退
- 预期：签到与签退时间位置正确；步骤状态及拜访记录一致
- 依据：src/pages/subpages/visitPlan/visitReport.vue:2

### BIZ-visit-distance 超距签到与异常签退

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/visitPlan/visitReport`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 使用专用定位测试环境在范围外签到或签退；2. 填写异常说明和留证
- 预期：异常有标识；必填说明与留证校验生效；记录可只读回看
- 依据：src/pages/subpages/visitPlan/visitReport.vue:2

### BIZ-visit-duration 最短拜访时间与倒计时

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/visitPlan/visitReport`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 签到后立即尝试签退；2. 前后台切换；3. 超过规定时长后再次签退
- 预期：时长未到禁止正常签退；倒计时不重置、不漂移；时长满足后可操作
- 依据：src/pages/subpages/visitPlan/visitReport.vue:2

### BIZ-visit-offline 上报断网、恢复与重复操作

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/visitPlan/visitReport`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 上报时断网；2. 恢复网络后重试；3. 连续点击签到/上报/签退
- 预期：失败不显示业务成功；恢复后不丢失输入；无重复记录和重复附件
- 依据：src/pages/subpages/visitPlan/visitReport.vue:2

### BIZ-visit-readonly 完成记录只读及步骤文案

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/visitPlan/visitReport`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 完成本轮拜访后重开记录；2. 查看未填写步骤与异常记录
- 预期：已签退未填步骤显示未填写；历史记录不可误编辑；异常证据保留
- 依据：src/pages/subpages/visitPlan/visitReport.vue:2

### BIZ-visit-plan 拜访计划批量客户、日期与路线

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/visitPlan/addPlan`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 选择本轮客户和拜访人员；2. 选择日期和路线；3. 批量创建；4. 回读计划；5. 从详情返回列表
- 预期：计划数量与客户选择一致；人员、日期与路线正确；返回不重复加载、不丢失位置
- 依据：src/pages/subpages/visitPlan/addPlan.vue:2

### BIZ-online-visit 电话及微信线上拜访

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/onlineVisit/form`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 分别选电话和微信方式；2. 填写本轮客户、时间和记录；3. 测试必填缺失后有效提交
- 预期：缺失字段有提示；保存与详情一致；取消拨号、离开微信不会自动报告拜访成功
- 依据：src/pages/subpages/onlineVisit/form.vue:2

### BIZ-activity-scheme 活动方案审批通过与拒绝

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/activityApply/scheme/detail`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 由管理端创建本轮模板及类型业务工作流；2. 创建活动方案；3. 详情读取审批；4. 分别通过和拒绝
- 预期：节点及审批人来自详情；通过后才进入后续可执行状态；拒绝不派生有效任务
- 依据：src/pages/subpages/activityApply/scheme/detail.vue:2

### BIZ-activity-apply 活动申请动态字段及条件必填

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/activityApply/apply/form`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 选择不同本轮活动类型；2. 切换条件字段；3. 填写有效值及空值；4. 提交申请
- 预期：动态字段与所选模板一致；隐藏字段不残留；条件必填生效
- 依据：src/pages/subpages/activityApply/apply/form.vue:2

### BIZ-activity-apply-approval 活动申请审批与撤回重提

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/activityApply/apply/detail`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 创建本轮申请；2. 按实际节点分别通过/拒绝；3. 在允许状态撤回并重提
- 预期：审批与任务状态同步；不使用过期节点；重复操作不重复派任务
- 依据：src/pages/subpages/activityApply/apply/detail.vue:2

### BIZ-activity-execute 活动执行上报与时间窗口

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/activityApply/execute/report`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 准备未开始/可执行/逾期/已完成任务；2. 上传要求证据；3. 提交并回看
- 预期：只有合法状态允许提交；必填证据生效；重复提交不重复完成
- 依据：src/pages/subpages/activityApply/execute/report.vue:2

### BIZ-activity-payment 活动兑付凭证与金额

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/activityApply/payment/report`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 使用本轮满足条件任务；2. 填写金额和凭证；3. 测试0、负数、超额、重复兑付
- 预期：金额与额度规则一致；非法值拒绝；有效兑付只记账一次，不进行真实支付
- 依据：src/pages/subpages/activityApply/payment/report.vue:2

### BIZ-activity-old-activity 活动中心旧入口与新活动流程一致性

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/activity/applyActivity`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 从活动中心申请本轮活动；2. 在新活动申请列表和详情查询
- 预期：入口间记录关联正确；模板、参与客户和审批信息一致
- 依据：src/pages/subpages/activity/applyActivity.vue:2

### BIZ-supervision-create 督办任务发布与人员多选

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/supervision/create`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 选择本轮任务接收员工、截止时间与报告要求；2. 提交任务
- 预期：每个员工收到准确任务；必填校验生效；截止时间前后状态正确
- 依据：src/pages/subpages/supervision/create.vue:2

### BIZ-supervision-report 督办上报、附件及重复提交

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/supervision/report`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 本轮接收人打开任务；2. 上传合法附件并上报；3. 重复提交；4. 回看详情
- 预期：报告关联本轮任务；附件可访问；无重复完成和错误关联
- 依据：src/pages/subpages/supervision/report.vue:2

### BIZ-supervision-return 督办详情返回刷新及超期处理

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/supervision/detail`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 查看本轮任务；2. 从上报页返回详情；3. 跨截止时间刷新
- 预期：详情刷新一次且列表状态一致；超期与已完成区分正确
- 依据：src/pages/subpages/supervision/detail.vue:2

### BIZ-notifications 消息已读、待办和审批跳转

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：write
- 路由：`/pages/subpages/messageCenter/index`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 产生本轮业务通知；2. 打开消息；3. 切换待办及审批；4. 进入关联本轮单据后返回
- 预期：跳转ID和业务类型正确；徽标与已读状态同步；不将历史未读消息批量标为已读
- 依据：src/pages/subpages/messageCenter/index.vue:2

### BIZ-profile-logout 退出登录及会话清理

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：session
- 路由：`/pages/profile/index`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 使用专用测试账号；2. 退出登录；3. 返回受保护页面；4. 重新登录另一角色
- 预期：清理旧会话并回登录页；不同角色不残留旧菜单、组织或缓存
- 依据：src/pages/profile/index.vue:2

### BIZ-statistics 统计范围、时间区间和下钻

- 平台：h5, mp-weixin；级别：P0；执行：manual；风险：read
- 路由：`/pages/data/index`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 使用固定测试时区和本轮数据；2. 切换今日/月度/自选区间；3. 进入客户及订单明细
- 预期：汇总与相同条件明细一致；区间边界不重复/漏计；下钻携带条件且返回保持状态
- 依据：src/pages/data/index.vue:2

### BIZ-native-camera 相机权限、定位水印与连续拍照

- 平台：mp-weixin-real-device；级别：P0；执行：manual_native；风险：native
- 路由：`/pages/subpages/common/watermark-camera`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 真机分别允许/拒绝相机及定位权限；2. 前后台切换；3. 连续拍照并返回上报页
- 预期：拒绝可恢复且不误上传；照片水印时间位置准确；分包切换不崩溃、无持续内存上涨
- 依据：src/pages/subpages/common/watermark-camera.vue:2

### BIZ-native-map 地图选点、取消及隐私授权

- 平台：mp-weixin-real-device；级别：P0；执行：manual_native；风险：native
- 路由：`/pages/subpages/common/map`
- 前置：使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID；仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点
- 步骤：1. 真机允许/拒绝定位；2. 搜索并选点；3. 取消选择；4. 返回客户表单
- 预期：坐标与地址一致且取消不覆盖原位置；授权提示符合平台规则
- 依据：src/pages/subpages/common/map.vue:2

