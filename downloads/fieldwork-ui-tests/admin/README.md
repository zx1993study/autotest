# 管理端与服务端待补

## 2026-10-19 更新

管理端仓库权限已恢复，源码已下载至 `D:\project\Fieldwork-management`，当前版本 `250b6bc4d4e56f1e5136f701e1344590fd24e849`。管理端 Web 脚本与生成、回放说明见同级测试交付目录 `downloads/fieldwork-web-tests/README.md`、`delivery-report.md`。下文的管理端访问失败是历史记录，不再代表当前状态；本次未下载服务端仓库。

目标仓库：

- https://github.com/xnous-ai/Fieldwork-management
- https://github.com/xnous-ai/Fieldwork-Service

已分别用匿名及本机缓存的 GitHub 账号只读检查，均返回 `Repository not found`。这无法区分仓库地址错误、私有仓库或账号权限不足；不据此断言仓库不存在。

用户指定下载位置为 `D:\project`。预期源码目录为 `D:\project\Fieldwork-management`、`D:\project\Fieldwork-Service`；目前尚未下载，不能声称已经覆盖管理端页面。

继续条件：通过 GitHub 官方设备登录授权，并确认账号具有这两个仓库的读取权限，或提供本地源码。不要在用例文件或对话中提供 Token。

获取源码后补充实际管理端路由、菜单与权限、Vue页面控件、字段校验、字典和服务端状态流转。管理端脚本继续使用 Python/Pytest + Playwright 的页面对象结构，不用小程序 H5 充当管理端覆盖。复杂审批和库存链路必须以真实详情中的节点、关联单、角色及本批次数据实现。

本目录当前仅记录缺失条件，不包含猜测的选择器和假成功脚本。
