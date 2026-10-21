# 测试账号清理与固定复用

2026-10-19；仅针对远程PunkRecord本轮登记的测试账号。

删除33个重复停用测试账号，保留最近3个；原有员工账号未删除或更改。
删除前检查外键及关联记录归属，在单一事务内清理；没有关闭外键检查。
私有备份：`/home/xiaox/data/punkrecord-test-cleanup/20261019T065804Z-34b85bd88caa.json`（服务器当前用户可读，包含删除前测试数据）。

## 保留账号

- `case_20261019_144610_manager`：manager，运行结束恢复inactive。
- `case_20261019_144610_employee`：employee，运行结束恢复inactive。
- `case_20261019_144610_other`：other，运行结束恢复inactive。

## 后续规则

固定用户ID见test-account-pool.json；auto_create=false。
正常运行不创建用户或职位、不重置密码；账号缺失、身份不符或无凭据则直接报错。
密码仅保存在Windows CurrentUser DPAPI加密文件，不纳入Git；其他机器可用PUNKRECORD_TEST_PASSWORD环境变量。
initialize_account_pool.py只进行明确的一次性凭据初始化，正常测试不会调用它。
运行时临时启用固定账号，清理时恢复运行前状态，保留用户ID。

## 验证

9项本地脚本单元校验通过；不涉及本地PunkRecord业务测试。
远程连续2轮复用验证通过：账号总数每轮均为22→22；新增用户0、新增职位0、重置密码0。
33个删除ID均已从远程用户列表消失；3个保留账号存在且均恢复inactive。

## 早会流程

早会扣除贝利仍未执行，ATT-01至ATT-07保持未验证。本次账号维护不算早会流程测试。
共享环境的早会操作可能触发全员结算，需要隔离范围后另行执行，不能用商城手工扣款替代。
