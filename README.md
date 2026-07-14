# 自动化测试平台

这是一个面向 API、Web、App 自动化测试的软件原型。

## 当前能力

- 后端 FastAPI 骨架。
- 前端 Vue3 + Vite + TypeScript 骨架。
- 系统管理、项目管理、API 测试、Web 测试、App 测试、执行管理、执行报告页面路由。
- 后端采用 `API 入口 -> Service -> Repository 接口 -> SQLAlchemy` 分层。
- 默认使用 MySQL 持久化页面数据。
- API/Web/App 测试域均保持 4 个前端页面和 4 个后端路由文件。

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

新环境完成迁移后建议设置：

```bash
set AUTO_CREATE_SCHEMA=false
```

## 前端启动

```bash
cd frontend
npm install
npm run dev
```

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
