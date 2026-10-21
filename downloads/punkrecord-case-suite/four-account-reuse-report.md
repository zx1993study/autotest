# 测试账号清理与固定复用

2026-10-19；仅针对远程PunkRecord本轮登记的测试账号。

经用户明确授权删除旧CASE三个账号及关联历史测试数据，复用现有test_user1/2/3/4；不再创建员工。
删除前检查外键及关联记录归属，在单一事务内清理；没有关闭外键检查。
私有备份：`/home/xiaox/data/punkrecord-test-cleanup/20261019T085835Z-7b189e548213.json`（服务器当前用户可读，包含删除前测试数据）。

## 保留账号

- `test_user1`：manager，保持原有启用状态。
- `test_user2`：supervisor，保持原有启用状态。
- `test_user3`：employee，保持原有启用状态。
- `test_user4`：other，保持原有启用状态。

## 后续规则

固定用户ID见test-account-pool.json；auto_create=false。
正常运行不创建用户或职位、不重置密码；账号缺失、身份不符或无凭据则直接报错。
密码仅保存在Windows CurrentUser DPAPI加密文件，不纳入Git；其他机器可用PUNKRECORD_TEST_PASSWORD环境变量。
initialize_account_pool.py已禁止重置这四个用户提供的账号。
运行时临时启用固定账号，清理时恢复运行前状态，保留用户ID。

## 验证

9项本地脚本单元校验通过；不涉及本地PunkRecord业务测试。
远程连续2轮复用验证通过：账号总数每轮均为19→19；新增用户0、新增职位0、重置密码0。
旧CASE三个删除ID均已从远程用户列表消失；四个保留账号存在且均保持active。

## 早会流程

早会扣除贝利仍未执行，ATT-01至ATT-07保持未验证。本次账号维护不算早会流程测试。
共享环境的早会操作可能触发全员结算，需要隔离范围后另行执行，不能用商城手工扣款替代。
