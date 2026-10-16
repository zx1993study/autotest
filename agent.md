# Agent 工作约定

本文件用于约定在本仓库中由 Agent 编写、修改、审查代码时必须遵守的工作方式。适用范围为整个仓库。

当约定冲突时，优先级为：用户明确要求 > 本文件 > `docs/implementation-rules.md` > 其他项目文档 > 现有代码风格。若仍不确定，先按现有实现中最保守、影响面最小的方式处理，并在交付说明中写明假设。

## 1. 工作顺序

每次修改按以下顺序推进：

1. 先读上下文：阅读相关 README、`docs/implementation-rules.md`、`docs/test-domain-file-map.md`、相关路由、Service、组件、类型和测试。
2. 明确归属：判断需求属于后端、前端、本地 Agent、脚本、文档或跨模块联动，避免把代码放到方便但错误的位置。
3. 最小设计：优先复用已有 Service、Repository、通用组件、类型、常量和工具函数；只有现有结构无法表达新业务时才新增抽象。
4. 分层实现：后端严格按本节“后端编码顺序”落地；前端先补类型和请求封装，再写组件或页面，最后补测试与文档。
5. 本地验证：优先运行与本次改动最相关的测试、构建或静态检查。
6. 自查 diff：检查是否有无关改动、调试输出、硬编码密钥、生成物、日志和临时文件。
7. 交付说明：说明改了什么、验证了什么、未验证原因和剩余风险。

### 后端编码顺序

新增后端业务或涉及数据库表的功能，必须按以下顺序编写，不得先把业务逻辑堆进 API 再回补分层：

1. 定义 Schema：先在 `backend/app/schemas/` 中明确创建、更新、查询、列表和响应结构，以及字段类型、必填项、默认值和校验规则。
2. 定义 Model 和 Migration：根据 Schema 落数据库模型；有表结构变化时同步创建 migration，并确认默认值、索引、唯一约束、外键和回滚逻辑。
3. 实现 Repository：补齐持久化接口和 SQLAlchemy 实现，只处理查询与写入，不承载业务规则。
4. 实现 Service：以 Schema 为输入输出边界，完成业务校验、状态流转、事务组织和 Repository 调用。
5. 实现 API：最后增加路由、参数接收、依赖注入、权限校验和统一响应；API handler 不得绕过 Service 直接调用 Repository 或 Session。
6. 补后端测试：按 `Schema -> Repository -> Service -> API` 的边界覆盖正常流程、校验失败、资源不存在、权限和状态冲突。
7. 接入前端：先同步 TypeScript 类型和 service/API client，再实现组件与页面交互，最后执行构建和必要的页面验收。

局部修改只执行本次涉及的步骤，但顺序不变。例如仅新增接口字段时，也应先修改 Schema 和类型，再修改 Service、API 与前端。运行时调用方向仍为 `API -> Service -> Repository -> SQLAlchemy/数据库`，不要把编码顺序误解为调用方向。

## 2. 放置位置

### 后端

- API 路由放在 `backend/app/api/v1/`，只负责路由、参数接收、依赖注入和统一响应。
- 请求与响应结构放在 `backend/app/schemas/`。
- 业务规则放在 `backend/app/services/`。
- Repository 接口放在 `backend/app/repositories/interfaces.py`，SQLAlchemy 实现优先放在 `backend/app/repositories/sqlalchemy_resource_repository.py`。
- 数据模型放在 `backend/app/models/`。
- 枚举放在 `backend/app/enums/`，常量放在 `backend/app/constants/`。
- 通用异常、响应、配置、日志放在 `backend/app/core/`。
- 可复用工具放在 `backend/app/utils/`，不要把业务流程藏进 utils。
- 调度任务放在 `backend/app/scheduler/`。
- 数据库结构变更放在 `backend/migrations/versions/`，并保证迁移可重复执行、可回滚。
- 后端测试放在 `backend/tests/`，文件名使用 `test_*.py`。

后台必须保持 `API 入口 -> Service 服务层 -> Repository 持久化接口 -> SQLAlchemy/数据库实现` 的调用链。路由中不得写数据库查询、执行器逻辑、文件处理逻辑或大段业务规则；Service 中不得直接写 SQL。

### 表与文件一一对应

- 每个新建业务表必须有且只有一个主 Schema 文件、一个主 Service 文件和一个主 API 路由文件；已有模块在被实质修改时逐步对齐，不为满足命名规则单独做全仓迁移。
- 同一业务名必须贯穿各层。表名使用复数 `snake_case`；Model、Schema、Service 文件使用单数业务名；API 文件使用复数业务名。例如 `execution_plans` 对应 `models/execution_plan.py`、`schemas/execution_plan.py`、`services/execution_plan_service.py` 和 `api/v1/execution_plans.py`。
- 一个主 Service 只负责一个业务表的 CRUD 和该表自身业务规则，不得直接承接多个互不从属表的增删改查；跨表操作通过调用各表 Service 完成。
- 一个主 API 文件只暴露一个业务表对应资源的路由，不得把多个独立资源的接口集中到同一个路由文件。
- 联表查询、跨表事务或流程编排归属于发起该业务动作的主 Service；复杂到无法明确归属时，可增加名称具体的 orchestration/query Service，但不得取代各表自己的主 Service 和主 API 文件。
- 纯关联表、框架内部表、审计明细表等没有独立业务入口的表可以不提供公开 API，但必须明确归属某个主 Service，并在设计或提审说明中记录例外原因。
- 新增表时，应在同一需求中同时补齐对应的 Model、Schema、Service、API、路由注册、Migration 和测试，禁止只建表或只建 API 留待后续补层。

### 前端

- 页面放在 `frontend/src/views/`，按业务域分目录，例如 `api-testing`、`web-testing`、`app-testing`、`execution`、`system`。
- 通用组件放在 `frontend/src/components/`，业务组件可按业务子目录归类。
- API 请求封装放在 `frontend/src/services/` 或 `frontend/src/api/`，页面不要直接拼 axios 细节。
- 类型定义放在 `frontend/src/types/`。
- 资源表单和列表 schema 放在 `frontend/src/resource-schemas/`。
- 路由、导航、枚举等稳定配置放在 `frontend/src/constants/`。
- 全局样式、设计 token、reset 放在 `frontend/src/styles/`；单页面样式优先使用 `<style scoped>`。

一个菜单页面对应一个 `.vue` 文件。页面优先组合 `ResourcePage`、`CaseDraftPage`、`TestCasePage` 等通用组件，不重复实现列表、表单、删除、分页等通用逻辑。

### 本地 Agent

- 本地 Agent 源码放在 `agent/agent_app/`。
- 服务端 API 调用封装放在 `agent/agent_app/api/`。
- 轮询、心跳、生命周期、任务运行流程放在 `agent/agent_app/runtime/`。
- 任务执行器放在 `agent/agent_app/executors/`。
- 鉴权缓存放在 `agent/agent_app/auth/`。
- 本地运行工具函数放在 `agent/agent_app/utils/`。
- Windows 托盘、安装、打包脚本放在 `agent/windows/`。
- Agent 测试放在 `agent/tests/`。

不要手动修改 `agent/build/`、`agent/dist/` 中的打包产物，除非任务明确要求处理发布包。

### 文档、脚本和生成物

- 设计和流程文档放在 `docs/`。
- 开发脚本放在 `scripts/`。
- 日志目录 `logs/`、缓存目录 `.pytest_cache/`、运行期存储和临时文件不要作为功能改动提交。
- `backend/storage/` 只放运行期需要的存储样例或明确要求保留的文件；截图、任务详情等运行产物默认不纳入功能改动。

## 3. 命名规则

### Python

- 模块、函数、变量使用 `snake_case`。
- 类名使用 `PascalCase`。
- 常量使用 `UPPER_SNAKE_CASE`。
- 私有辅助函数使用前导下划线，例如 `_normalize_payload`。
- 测试文件命名为 `test_xxx.py`，测试函数命名为 `test_should_do_something` 或遵循现有 unittest 风格。
- 业务表名和资源表名使用小写复数 `snake_case`，例如 `agent_tasks`、`web_elements`。

### TypeScript 和 Vue

- 变量、函数、ref、computed 使用 `camelCase`。
- 类型、接口、枚举、组件名使用 `PascalCase`。
- Vue 页面文件使用 `PascalCase + Page.vue`，例如 `ExecutionAgentsPage.vue`。
- 弹窗、表格、选择器等组件使用明确后缀，例如 `Dialog.vue`、`Table.vue`、`Select.vue`、`Modal.vue`。
- service 文件使用业务名加 `.service.ts`，例如 `agent.service.ts`。
- API URL 使用 kebab-case，参数名按后端约定使用 snake_case。

### 业务域

- API、Web、App 测试域必须遵守 `docs/test-domain-file-map.md` 的四文件映射。
- 导入、扫描、录制、执行、批量生成等动作应归属到已有页面、弹窗、Tab 或子接口，不随意新增第 5 个测试域页面或路由。
- 若需要新增业务域，先补文档映射，再按前后端同构方式落文件。

## 4. 代码编写规范

### 通用原则

- 让改动紧贴需求，不做无关重构、格式化扫全仓或目录搬迁。
- 先复用已有模式，再考虑新增抽象。
- 保持函数短小、命名直接、错误信息可定位。
- 不引入隐藏依赖；新增依赖必须说明用途，并更新安装或部署文档。
- 不提交密钥、token、账号密码、真实生产地址或个人本地路径。
- 不保留 `print`、`console.log`、临时注释、调试开关和一次性脚本。
- 中文用户可见文案要简洁明确；代码标识符优先使用英文。

### 后端细则

- API 返回使用 `success()`、`page_result()` 等统一响应。
- 业务异常使用项目内异常类型，例如 `BusinessRuleError`、`ResourceNotFoundError`。
- Service 负责校验业务规则、组织流程、调用 Repository 和其他 Service。
- Repository 负责持久化读写；Service 不直接依赖 SQLAlchemy Session。
- 涉及时间时优先使用带时区的 UTC 时间，并保持序列化格式一致。
- 涉及文件写入时必须限制路径、校验文件名、控制大小，避免路径穿越和大文件写入。
- 涉及 token、鉴权快照、Cookie、截图 payload 时，不在日志或响应中泄露敏感明文。
- 数据库结构变化必须补 migration；仅修改 `data`/`data_json` 扩展字段时也要确认兼容旧数据。

### 前端细则

- Vue 使用 `<script setup lang="ts">`。
- 页面组件负责状态组织和业务交互，重复逻辑下沉到通用组件、service、类型或工具函数。
- 请求统一走 service/API client，不在组件里散落请求前缀和响应结构处理。
- loading、error、success、empty 等状态要完整；破坏性操作需要确认。
- 表单字段、资源 schema、后端 schema 和类型定义要保持一致。
- 新 UI 要适配窄屏，避免文字溢出、按钮挤压和布局重叠。
- 样式优先局部化；只有设计 token、reset、基础布局才改全局 CSS。

### 本地 Agent 细则

- Agent 只承担本机执行能力，不承载平台后端职责。
- Runtime API 必须使用 Agent token 认证，不混用用户 JWT。
- capability 字符串要稳定，例如 `case_execution`、`stagehand`。
- 本地路径、浏览器路径、配置路径要兼容 Windows，并允许环境变量或配置文件覆盖。
- 执行结果回传要可重试、可定位；截图等 artifact 要控制大小并避免泄露本机绝对路径。
- 打包脚本、托盘程序和源码运行路径要分开考虑，避免只在开发态可用。

## 5. 文件长度和复杂度

新增代码必须控制方法大小和文件大小，避免出现难以审查、难以测试的超大文件。目标值用于日常设计，硬上限用于提审拦截；超过硬上限必须先拆分，确有例外时需在提审说明中写明原因和后续拆分计划。

### 方法大小

- 普通函数、方法、Vue 事件处理函数目标不超过 40 行，硬上限 80 行。
- API handler、computed、watch、生命周期函数目标不超过 30 行，硬上限 60 行。
- 单个函数如果同时做校验、查询、转换、写入和响应组装，应立即拆分为私有辅助函数、组合函数或独立 Service。
- 函数参数目标不超过 5 个；超过时优先使用 request schema、配置对象或上下文对象。
- 分支嵌套目标不超过 3 层；超过时使用提前返回、策略函数、映射表或拆分函数。

### 文件大小

- 后端路由文件目标不超过 80 行，硬上限 120 行。
- 后端 Service 文件目标不超过 250 行，硬上限 400 行；超过目标值时抽取命名明确的校验器、转换器、查询对象或流程编排器，单表 CRUD 的公开入口仍保留在该表唯一的主 Service 中。
- 后端 Repository、executor、scheduler job、utils 文件目标不超过 250 行，硬上限 400 行。
- Python schema、enum、constant 文件目标不超过 200 行，硬上限 300 行。
- Vue 页面文件目标不超过 160 行，硬上限 260 行；复杂表格、弹窗、步骤编辑器、详情区必须拆到 `components/`。
- Vue 通用组件目标不超过 250 行，硬上限 400 行；超过目标值时按子组件、composable 或纯工具函数拆分。
- TypeScript service、types、schema、constants、utils 文件目标不超过 200 行，硬上限 300 行。
- 测试文件目标不超过 300 行，硬上限 500 行；重复 setup 使用 fixture、factory 或 helper。
- 新增文件如果预计超过目标值，先拆目录和模块再实现，不先写成大文件再事后整理。

### 拆分优先级

- 后端优先按 `API -> Service -> Repository -> utils` 的职责拆分。
- 前端优先按 `Page -> business component -> common component -> service/type/schema` 拆分。
- 本地 Agent 优先按 `runtime -> api -> executor -> auth/utils` 拆分。
- 抽离后的函数或组件必须有清晰命名，不能只用 `helper`、`common`、`misc` 这类含糊名称。

## 6. 测试和验证

按改动范围选择最小但有效的验证：

- 后端单元测试：`cd backend` 后运行 `..\.venv\Scripts\python -m pytest`。
- 后端静态检查：`cd backend` 后运行 `..\.venv\Scripts\python -m ruff check app tests`。
- Agent 测试：`cd agent` 后优先运行 `.\.venv\Scripts\python -m pytest`；若本地环境不同，使用可用的 Python 环境并说明。
- 前端构建：`cd frontend` 后运行 `npm run build`。
- 前端本地预览：需要人工验收交互时运行 `npm run dev`。
- 数据库变更：运行或说明 `alembic upgrade head` 的验证情况。

如果依赖、数据库、浏览器或环境变量缺失导致无法验证，必须在交付说明中写清楚：尝试过的命令、失败原因、对风险的判断。

## 7. 提审要求

提审前必须完成以下自查：

- `git diff` 中只包含本次需求相关改动。
- 没有提交 `.env`、token、账号密码、真实 Cookie、日志、缓存、截图临时文件和打包生成物。
- 后端改动有对应测试或明确说明无需测试的原因。
- 前端改动已通过 `npm run build` 或说明未执行原因。
- 新增或修改的函数、组件、Service、页面没有超过第 5 节硬上限；超过时已拆分或写明例外原因。
- 后端代码按 `Schema -> Model/Migration -> Repository -> Service -> API -> Test` 顺序实现，API 中没有临时业务逻辑或直接数据库访问。
- 每个新增业务表都有对应的主 Schema、主 Service 和主 API 文件；跨表或无公开 API 的例外已说明归属和原因。
- API 结构、字段名、枚举值、状态流转保持前后端一致。
- 数据库结构变化包含 migration，且不破坏已有数据。
- 用户可见文案、错误提示和空状态可理解。
- 涉及 UI 的改动需说明主要页面和交互路径；必要时附截图或手工验证步骤。

提审说明建议包含：

- 变更摘要。
- 影响范围。
- 验证结果。
- 兼容性或迁移说明。
- 已知风险或后续事项。

## 8. 完成标准

一个任务只有同时满足以下条件才算完成：

- 功能实现符合需求，并放在正确模块中。
- 代码遵守现有架构分层，没有绕过通用 Service、Repository、组件或 API client。
- 后端各层按约定顺序完成，新增业务表与主 Schema、主 Service、主 API 文件保持一一对应。
- 命名、类型、错误处理、状态流转和边界条件清晰。
- 方法大小、文件大小、嵌套深度和参数数量符合第 5 节约定。
- 相关测试、构建或静态检查已执行并通过；不能执行时已说明原因。
- 文档、schema、枚举、迁移和示例配置已按需更新。
- 没有无关改动、敏感信息、临时文件和调试输出。
- 交付说明能让 reviewer 快速知道改了什么、如何验证、哪里需要特别关注。
