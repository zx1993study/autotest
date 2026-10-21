# 外勤小星页面与小程序测试包

## 当前交付范围

依据 `dpush-io/FieldNovaMini` 提交 `9c44251c78f7c865c8d28272f6340bbad47942cf` 生成。

| 项目 | 当前结果 |
| --- | --- |
| 小程序源码 | 已下载至 `D:\project\FieldNovaMini`，未修改业务源码 |
| 已注册页面 | 82 个，包含主包及全部注册分包 |
| 测试用例 | 244 条，包含步骤、前置条件、预期、优先级和源码依据 |
| 有脚本定义的用例 | 86 条：页面呈现及不写业务数据的客户端校验 |
| 人工或待业务数据适配 | 158 条：字段规则、条件查询、审批、库存及真机能力 |
| 管理端与服务端 | 当前仓库访问返回 Repository not found，未伪造页面或定位器 |
| 执行状态 | 业务测试未执行；未写入测试平台数据库 |

**H5 脚本测试的是小程序同源 H5，不是管理端。** 86 条是脚本定义数量，不表示已执行通过；缺少会话或前置数据时明确跳过/阻塞。页面呈现通过不代表业务流程通过。

## 文件结构

```text
fieldwork-ui-tests/
  cases.md                   完整用例目录
  catalog.json               机器可读用例、步骤及预期
  source-inventory.json      页面、路由、字段规则、查询条件及源码哈希
  page-inputs.json            页面填写元素JSON，value留空待配置
  fixtures.example.json      本批次详情页参数配置，不含真实业务ID
  tools/                     可重复运行的源码解析与用例生成工具
  h5/
    conftest.py              浏览器配置、会话和请求保护
    pytest.ini
    requirements.txt
    capture_auth.py          人工登录后保存本地私有会话
    pages/source_page.py     页面操作对象
    tests/test_pages.py      参数化页面用例
  miniapp/
    run.cjs                  uni-automator执行入口
    source-page.cjs          小程序页面操作对象
    network-guard.cjs        只读请求保护及恢复
  checks/                    生成器、断言和安全保护自测
  admin/README.md            管理端待补项
```

## 覆盖原则

- 三类客户新增、编辑、删除、审批通过/拒绝、拒绝后重提；合作状态按包含关系比较。
- 每个列表的全部条件查询合并成一个场景，先单条件再组合条件，验证实际命中记录、分页及清空恢复，不只断言 HTTP 200。
- 总仓/直营仓与前端/直营/KOL客户销售组合；审批前不锁库，审批通过后锁库；有待确认单时确认后扣实际库存，无则按真实流程自动完成。
- 采购和退货先读取详情的审批与关联入库单；需要仓管确认时确认后入库，拒绝时库存不变。
- 拆箱按装箱规格固定换算，无审批和确认，提交立即生效；覆盖不足、售罄、重复操作和销售退货连续台账。库存场景不混入权限测试。
- 拜访签到签退、动态活动申请/执行/兑付、督办、通知、统计及会话切换。
- 定位、相机、水印、系统授权和内存压力单列真机人工用例，不用模拟器结果替代真机结论。
- 对 SQL 异常、空名称被接受、非法数量成功等真实缺陷，不修改预期使其通过。配置不支持的业务组合标记不适用，不擅自改换客户。

## H5 脚本

在本目录执行，安装独立测试依赖及 Chromium：

```powershell
python -m pip install -r h5/requirements.txt
python -m playwright install chromium
$env:FW_H5_BASE_URL = 'https://<小程序H5测试部署地址>'
python h5/capture_auth.py
$env:FW_AUTH_STATE = "$PWD\.auth\h5.json"
python -m pytest h5 -q
```

`capture_auth.py` 会打开浏览器，由你完成账号、密码及验证码输入，然后明确确认保存。会话文件含敏感登录状态，只放在本地 `.auth`，不上传或提交。该工具本身允许人工登录请求；正式检查脚本默认拦截全部非 GET/HEAD/OPTIONS 请求。

可设置 `FW_HEADED=1` 显示浏览器；`FW_CASE_IDS` 为逗号分隔的用例ID，例如 `MINI-002-空账号密码`。脚本当前按同源 H5 的 hash 路由执行。

## 微信小程序脚本

使用源码中**相同版本**的 `@dcloudio/uni-automator`，调用实际存在的 `new Automator().launch(...)`。不是 Playwright、WebView 或原生 App 的替代执行。

1. 安装微信开发者工具并登录有该小程序权限的账号，启用 CLI 服务端口。
2. 在 `FieldNovaMini` 源码目录安装其依赖，确认测试环境配置、合法域名和开发者工具 AppID 权限有效。不要运行上传发布命令。
3. 在本测试包目录安装依赖并执行：

```powershell
npm ci --ignore-scripts
$env:FW_MINI_SOURCE = 'D:\project\FieldNovaMini'
$env:FW_WECHAT_CLI = '<微信开发者工具cli.bat完整路径>'
$env:VITE_APP_ENV = 'test'
node miniapp/run.cjs --list
node miniapp/run.cjs
```

脚本会编译测试构建并启动开发者工具，自动化端口为本机 9520。专用测试账号已在开发者工具内人工登录后，设置 `FW_MINI_SESSION_READY=1` 才会尝试受保护页面；仍会核对真实路由、请求错误和业务拒绝，不能凭这个标记绕过服务鉴权。验证码始终由人工完成。

脚本只在执行客户端提示断言期间接管 `showToast` 以采集提示文案，不模拟接口成功、登录或库存。结束恢复提示函数与网络函数并断开连接。结果写入 `artifacts/miniapp-results.json`；缺少前置、失败后未运行和真实通过分开记录。

## 数据与请求保护

- 默认执行器不支持业务写入步骤，不存在一个环境变量即可放开所有写接口的开关。
- 拦截 POST/PUT/PATCH/DELETE 和小程序上传；保护未能正确安装或运行探针未被拦截则中止，不降级裸跑。
- HTTP 错误、HTTP 200 但业务拒绝和被拦截的写请求均不当作成功；不保存响应正文、请求Token或查询串。
- `fixtures.example.json` 是**人工审批声明**，不是数据库所有权证明。详情参数必须由准备脚本/人工核对为本批次新数据，不得拿历史ID填空。复制为 `local.fixtures.json`，填写批次与明确批准的页面参数后，设置 `FW_FIXTURES` 指向它。
- `page-inputs.json` 来自实际模板的 `v-model`、表单属性和规则；不是运行时实采定位结果。字典、关联对象、动态字段和敏感字段须在实际测试环境补齐，不能把空值直接提交。
- 商品详情依赖上一页 Pinia 数据，不能直接用URL参数替代；目前标为人工导航验证。地图、相机及系统授权同理。
- 复杂业务链路已提供详细用例，尚未生成伪装成可运行的全链路步骤。待管理端/服务端源码和隔离数据准备齐备后，再补齐真实元素操作、业务回读、台账和清理脚本。
- 常规脚本不调用 AI、不消耗模型Token。没有启用未经验证的 Stagehand 自动修复；需要定位修复时按平台既有“确认、回放验证、保存版本”流程处理。

## 重新生成与检查

```powershell
node tools/generate.cjs D:\project\FieldNovaMini
npm run check
python -m pytest checks/test_h5_guard.py -q
python -m pytest h5 --collect-only -q
```

生成器只解析 JSONC、Vue模板和 TypeScript 字面量，不执行仓库脚本；记录 commit 与页面哈希，重跑不会修改业务源码。

本轮校验：Node自测24项通过，Python请求保护自测6项通过；H5可收集86项，因未提供H5部署地址全部明确跳过。未启动微信开发者工具，未做小程序或真机实跑。

官方接口依据：[uni-app 自动化 API](https://uniapp.dcloud.net.cn/worktile/auto/api.html)、[快速开始](https://uniapp.dcloud.net.cn/worktile/auto/quick-start.html)。执行器另外核对了源码锁定版本的实际 npm 发布包导出，避免将其他库的 `connect` API 混用到本版本。
