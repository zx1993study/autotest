# 外勤小星客户与条件查询执行报告

项目：10；OpenAPI 快照：11942。

## 客户管理

覆盖 17 个 API，新增 95 条正式用例（含流程节点、策略及查询用例）。
核心流程 #15832：新增、按唯一名称定位、详情、编辑、批量编辑、删除及查询验证。
文件流程 #15836 停用，导入导出需真实文件及文件断言。状态变更、重新提审场景等待本次新建记录的审批前置条件。
客户名称使用自然门店名称加时间戳；未复制真实客户手机号或证件；未执行任何业务写请求。

## 条件查询

35 个查询 API，409 个场景，当前启用 404、停用 5。
首轮：{'failed': 85, 'success': 321}；失败项复测：{'success': 48, 'failed': 35}。
客户查询当前配置完整复验：{'success': 45, 'failed': 3}。
按每个场景最近一次历史证据合并（排除当前停用项）：{'success': 370, 'failed': 34}。
首轮通过项修正日期/前置条件后未全部重跑；历史合并不等于当前配置的全量复验。全部运行证据已保存在 API 功能管理对应流程的运行记录中。

## 仍需排查

以下为复测后仍不满足严格断言的场景，不自动归因于目标接口缺陷，也未改为成功断言。需继续核对字段是否实际支持筛选、区间含义和权限范围。

- 场景 #15885：条件查询 12121 - executeBeginTime，批次 #16271。
- 场景 #15904：条件查询 12122 - status，批次 #16271。
- 场景 #15911：条件查询 12122 - executeBeginTime，批次 #16271。
- 场景 #15924：条件查询 12122 - combined，批次 #16271。
- 场景 #15957：条件查询 12141 - cooperationStatus，批次 #16273。
- 场景 #15959：条件查询 12141 - productType，批次 #16273。
- 场景 #15981：条件查询 12158 - visitBeginTime，批次 #16275。
- 场景 #15987：条件查询 12158 - visitorUserName，批次 #16275。
- 场景 #15990：条件查询 12158 - visitPlanId，批次 #16275。
- 场景 #15999：条件查询 12184 - updateBy，批次 #16276。
- 场景 #16001：条件查询 12184 - createBy，批次 #16276。
- 场景 #16000：条件查询 12184 - createTime，批次 #16276。
- 场景 #16002：条件查询 12184 - remark，批次 #16276。
- 场景 #15998：条件查询 12184 - updateTime，批次 #16276。
- 场景 #16006：条件查询 12184 - adminUserId，批次 #16276。
- 场景 #16007：条件查询 12184 - managerPhone，批次 #16276。
- 场景 #16010：条件查询 12184 - customerName，批次 #16276。
- 场景 #16011：条件查询 12184 - customerId，批次 #16276。
- 场景 #16017：条件查询 12184 - combined，批次 #16276。
- 场景 #16053：条件查询 12204 - salesUserId，批次 #16278。
- 场景 #16065：条件查询 12207 - productCode，批次 #16278。
- 场景 #16068：条件查询 12207 - no_match，批次 #16278。
- 场景 #16074：条件查询 12211 - inboundBy，批次 #16279。
- 场景 #16078：条件查询 12211 - warehouseId，批次 #16279。
- 场景 #16094：条件查询 12212 - inboundBy，批次 #16279。
- 场景 #16098：条件查询 12212 - warehouseId，批次 #16279。
- 场景 #16121：条件查询 12219 - createBy，批次 #16280。
- 场景 #16134：条件查询 12226 - beginTime，批次 #16281。
- 场景 #16145：条件查询 12226 - businessNo，批次 #16281。
- 场景 #16144：条件查询 12226 - warehouseName，批次 #16281。
- 场景 #16160：条件查询 12236 - cooperationStatus，批次 #16282。
- 场景 #16206：条件查询 12083 - cooperationStatus，批次 #16287。
- 场景 #16209：条件查询 12083 - kolType，批次 #16287。
- 场景 #16227：条件查询 12083 - combined，批次 #16287。

## 覆盖边界

部分接口声明的参数缺少非空样本或可信结果映射，尚未形成独立可执行断言，列在下表；不声称每一个参数已覆盖。

| API | 尚无独立行级断言的参数 |
| --- | --- |
| 12105 | limit |
| 12106 | limit, reportType |
| 12115 | includeDisabled |
| 12128 | activity_id |
| 12129 | taskId |
| 12141 | deptId |
| 12149 | is_page |
| 12158 | endTime, beginTime, deptId, reportType |
| 12184 | userIds |
| 12204 | deptId |
| 12211 | hasTargetWarehouse |
| 12212 | hasTargetWarehouse |
| 12216 | endTime, beginTime, delFlag, updateTime, updateBy, createTime, createBy, remark, outboundBy, outboundTime, outboundStatus, totalQuantity, customerName, customerId, warehouseName, warehouseId, orderNo, orderId, sourceId, sourceType, outboundNo, outboundId |
| 12219 | deptId |
| 12236 | deptId |
| 12083 | deptId, directCustomerLevel, directCustomerType |
| 12093 | ignoreScope |
| 12095 | isTemporary |
| 12096 | customerType |
| 12098 | customerType |

当前启用场景均已校验引用与模板版本；原有增删改查场景显式跳过新增查询节点。
页面执行前需要重启实际后端以加载 json_query_result 新断言；本轮 CLI 使用当前源码。
