# 自动化测试平台

这是一个面向 API、Web、App 自动化测试的软件原型。

## 当前能力

- 后端 FastAPI 骨架。
- 前端 Vue3 + Vite + TypeScript 骨架。
- 系统管理、项目管理、API 测试、Web 测试、App 测试、执行管理、执行报告页面路由。
- 后端采用 `API 入口 -> Service -> Repository 接口 -> SQLAlchemy` 分层。
- 默认使用 MySQL 持久化页面数据。
- API 参数、草稿和正式用例归入 API 详情；App 测试采用功能、场景、步骤与证据三级页面。
- 远程平台处理业务与持久化，桌面客户端显示远程页面，本地 Agent 执行设备操作。

## 后端启动

```bash
python -m venv .venv
.venv\Scripts\pip install -r backend\requirements-dev.txt
cd backend
..\.venv\Scripts\python -m alembic upgrade head
..\.venv\Scripts\python -m uvicorn app.main:app --reload
```

复制配置文件并填写 MySQL 连接信息：

```bash
copy backend\.env.example backend\.env
```

也可以直接设置 `DATABASE_URL`，它的优先级高于 `MYSQL_*`：

```bash
set DATABASE_URL=mysql+pymysql://user:password@host:3306/autotest?charset=utf8mb4
```

启动默认只检查已存在数据库的连接，不创建库表、不执行结构升级或写入默认数据。新环境先手动执行迁移，并保持：

```bash
set AUTO_CREATE_SCHEMA=false
```

## 前端启动

```bash
cd frontend
npm install
npm run dev
```

## 桌面客户端与 Agent

客户端不再打包或启动本地 FastAPI、数据库和 AI 服务。旧单机打包入口已删除，仅保留以下构建入口。手机执行包直接调用 WDA，不需要 Appium 服务；Web 和 AI Web 能力按构建配置选择。

```powershell
powershell -ExecutionPolicy Bypass -File packaging\desktop\build.ps1 `
  -Python .\.venv\Scripts\python.exe `
  -BuildAgent -AgentProfile mobile
```

产物位于 `packaging/desktop/dist/AutotestPlatform` 和 `AutotestAgent`。安装包需另装 Inno Setup 并添加 `-BuildInstaller`。托盘入口为 `AutotestAgent.exe --tray`，不再单独生成 Tray.exe。

部署、持久化目录和升级边界见 [分离架构](docs/remote-desktop-agent.md)，Agent 配置见 [Agent README](agent/README.md)。

## 设计文档

- `docs/autotest-platform-design.md`
- `docs/implementation-rules.md`
- `docs/test-domain-file-map.md`
- `docs/refactoring-plan.md`

## 验证

```bash
cd backend
..\.venv\Scripts\python -m pytest
..\.venv\Scripts\python -m ruff check app tests

cd ..\frontend
npm run build
```
