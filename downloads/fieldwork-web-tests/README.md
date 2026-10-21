# 外勤小星管理端 Web 测试脚本

后续更新：登录功能 10013 已单独生成参数化脚本并更新原六条用例绑定，真实浏览器验证 6/6 通过。登录脚本见 [独立登录测试包](../fieldwork-login-tests/README.md)。本目录仍为严格只读的页面与查询脚本，历史 catalog 中的登录 blocked 状态不代表平台当前状态。

依据管理端源码、实际动态菜单和平台已有用例生成，不使用小程序 H5 代替管理端。Python / Pytest / Playwright；常规运行不调用 AI。

## 目录

```text
fieldwork-web-tests/
  conftest.py             # 浏览器运行配置与登录态
  pytest.ini
  requirements.txt
  pages/
    base_page.py          # 浏览器生命周期、严格只读网络保护
    list_page.py          # Element UI 查询、响应与过滤断言
  tests/
    test_existing_cases.py
    test_feature_smoke.py
  case_31.py              # 按平台已有用例 ID 独立运行；其他用例同名入口
  inputs.json             # 与操作分离的已有非敏感输入值
  catalog.json            # 原用例 ID、源码位置、步骤、阻塞条件
  scripts/               # 每个已生成页面功能的 steps JSON
  tools/                 # AST 索引和确定性生成器，不执行源码
  generation-report.md   # 逐功能及已有用例的生成状态
```

## 运行

在本目录安装依赖和 Chromium：

```powershell
python -m pip install -r requirements.txt
python -m playwright install chromium
python capture_auth.py --output .auth/state.json
python case_31.py --storage-state .auth/state.json
python -m pytest tests/test_existing_cases.py --storage-state .auth/state.json --junitxml=results/existing.xml
python -m pytest tests/test_feature_smoke.py --feature-smoke --storage-state .auth/state.json --junitxml=results/pages.xml
```

登录、验证码由人完成；登录态文件属于凭据，不上传、不提交。也可用 `FIELDWORK_WEB_TOKEN` 仅在进程内传递经授权的已有 Token；脚本不自动登录或导出 Token。可通过 `--base-url` 指定同版本测试环境，通过 `--browser-executable` 指定本机 Chromium/Chrome。

已有用例与页面冒烟是两个不同范围：前者保留用例 ID 和原查询值；后者只证明页面列表可展示、查询有合法响应，不能证明新增、审批、库存变化等业务成功。条件查询用例同时检查请求参数、HTTP=200、业务 code=200、每条返回记录匹配条件；无匹配记录明确失败，避免空结果误判通过。

所有非 GET/HEAD/OPTIONS 请求均在发出前阻止，WebSocket 和 Service Worker 关闭；页面若尝试写入会失败，不静默放行。无提交重试。未生成的写场景、登录预期不清、缺少本批次对象 ID 的删除、不可解析控件等均为 blocked / pytest skipped，不算通过。不会为了生成脚本删去原场景的业务动作，也不会选择历史表格第一行执行删除。

平台发布复用已有 `WebFeatureTestingService`：只创建 draft 脚本版本；已有版本有差异时保留。适配成功的原查询用例以同一 ID 固定新版本，并保留原始步骤供追溯，不复制用例。源码生成不是运行验证，版本不自动改成 verified。

## 重新生成

维护脚本位于测试平台仓库 `scripts/fieldwork_web_snapshot.py`、`scripts/fieldwork_web_publish.py`。先只读生成 `platform-snapshot.json`，再执行：

```powershell
node tools/index.cjs D:/project/Fieldwork-management
python tools/build.py
```

索引器使用 Vue/TypeScript AST，不通过正则猜路由、不执行下载源码。独立重建需 `npm.cmd install` 安装 package.json 的生成依赖；在测试平台工作区会复用现有依赖。`generation-summary.json` 和 `publish-results.json` 分别记录生成与平台保存结果；`results/` 记录真实回放，二者不能混为测试通过报告。
