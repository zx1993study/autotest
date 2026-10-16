# Autotest Local Agent

本地 Agent 领取远程平台任务，执行 WDA 手机操作、局域网设备扫描和本机 Web 自动化，回传结果、截图和视频。它不承载平台后端，不连接业务数据库。

## 配置

源码运行默认读取 `~/.autotest-agent/config.json`。Windows 安装包优先读取 `%LOCALAPPDATA%\AutotestAgent\config.json`，其次读取 Agent 程序旁的 `config.json`；环境变量可覆盖路径。

```json
{
  "server_url": "https://your-autotest.example.com",
  "agent_token": "平台生成的 Agent 专用 token",
  "node_key": "local-win-01",
  "node_name": "本机 Windows 调试节点",
  "poll_interval_sec": 3,
  "heartbeat_interval_sec": 15,
  "artifacts_dir": "D:/autotest-agent-artifacts",
  "plugins": ["mobile"]
}
```

可用环境变量：

- `AUTOTEST_SERVER_URL`
- `AUTOTEST_AGENT_TOKEN`
- `AUTOTEST_AGENT_NODE_KEY`
- `AUTOTEST_AGENT_NODE_NAME`
- `AUTOTEST_AGENT_CONFIG`
- `AUTOTEST_AGENT_ARTIFACTS_DIR`

## Agent Token

进入平台“执行管理 / 执行节点”，点击“生成 Token”，填写节点标识和节点名称。平台只保存 token 哈希，明文 token 只展示一次，需要写入本地 `config.json` 的 `agent_token`。

如果重置 Token，旧 token 会立即失效；本地 Agent 需要更新配置后重新启动。

## 本地运行

```bash
cd agent
python -m agent_app.main --config ~/.autotest-agent/config.json
```

只领取并执行一次任务：

```bash
python -m agent_app.main --config ~/.autotest-agent/config.json --once
```

## Playwright 依赖

本地有头执行需要安装 Playwright 和浏览器：

```bash
pip install playwright
python -m playwright install chromium
```

## 打包与运行

统一构建入口为 `packaging/desktop/build.ps1 -BuildAgent -AgentProfile mobile`，可选 `core/mobile/web/ai-web/full`。能力根据插件配置与实际依赖计算，不能通过伪造 capabilities 获得。

`AutotestAgent.exe --tray` 打开托盘；`AutotestAgent.exe --check-runtime` 检查当前包的能力。桌面关闭后 Agent 仍可运行。停止/重启期间若有正在执行或回传的任务会拒绝操作。

## 当前能力

- 注册节点
- 心跳
- 领取 `case_execution` 任务
- 执行 Web 正式用例
- 直接执行 iOS WDA 结构化步骤，复用同设备 Session；异常不自动重放写操作
- WDA 截图采样生成 MP4，非原生高帧率录屏
- 打开本地有头 Chromium
- 通过任务专用短期 auth snapshot 获取 Cookie/storage state，不直接同步远程 `storage/auth`
- 回传 execution record payload，由平台写入 `execution_records`
- Windows 托盘启动、停止、重启本地 Agent
- 执行时持续心跳与续租；结果本地落盘，断网后仅重试回传，不重执行
- 一个 onedir 程序同时支持工作进程与托盘，统一 Inno Setup 安装包
