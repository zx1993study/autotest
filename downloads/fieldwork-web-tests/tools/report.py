"""Package generated scripts and distinguish generation from real replay results."""

import json
from collections import Counter
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]


def read(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8-sig"))


def report():
    generated = read("generation-summary.json")
    published = read("publish-results.json")
    replay = read("results/read-only-verification.json")
    integrity = read("results/integrity-check.json")
    counts = Counter(row["status"] for row in replay)
    lines = ["# 外勤小星管理端 Web 脚本交付", "", "交付日期：2026-10-19（Asia/Shanghai）", "",
        f"源码已下载至 `D:\\project\\Fieldwork-management`，版本 `{generated['commit']}`。", "",
        "## 生成与保存", "",
        f"- 核对现有 287 个页面功能，生成 {generated['features'].get('source_ready', 0)} 份页面展示/查询脚本。",
        f"- 平台保存 {len(published['results'])} 份 draft 版本，不把源码生成等同运行验证。",
        f"- 正式用例保存前后均为 {published['cases_after']} 条；没有新建或删除用例。",
        "- 原仓库查询用例 #31 保持 ID、名称、优先级和 WH001 输入，绑定当前统一条件查询组件；保留旧步骤追溯。",
        "- 其他 10 条已有用例保持原样。236 个未生成完整脚本的页面功能已逐项列出阻塞原因。", "",
        "## 实际回放", "",
        f"只读抽查 {len(replay)} 项，结果：{dict(counts)}。未执行新增、编辑、删除、审批等写场景。",
        "| 功能 ID | 用例 ID | 范围 | 结果 |", "|---:|---:|---|---|"]
    scope_names = {"query_filter": "原条件查询：请求参数、业务码、逐条过滤和重置", "page_list_smoke": "列表查询冒烟，非完整业务链路"}
    lines += [f"| {row['feature_id']} | {row.get('case_id') or '-'} | {scope_names.get(row.get('scope'), row.get('scope', '-'))} | {row['status']} |" for row in replay]
    lines += ["", "## 仍需补充", "",
        "- 登录用例需确认各自预期结果、账号密码参数与人工验证码；不绕过验证码。",
        "- 旧仓库删除用例没有本轮对象 ID 和精确行范围，不能据此删除历史仓库。",
        "- 仓库新增录制包含空下拉值，且部分路径以取消结束；需要确认业务期望后再形成新增成功脚本。",
        "- 活动模板新增在平台被标成 page 类型且录制含不完整定位，不能替换为列表展示冒充新增验证。",
        "- 旧路径、动态参数和自定义控件均不猜测；见 generation-report.md。", "",
        "## 文件", "",
        "- README.md：目录与运行命令。",
        "- generation-report.md：全部功能和已有用例的生成状态。",
        "- publish-results.json：平台脚本版本和原用例 ID。",
        "- results/read-only-verification.json：真实只读回放结果，不含 Token、截图或客户响应明细。",
        f"- 持久化完整性：{integrity}。", "",
        "脚本只读模式阻止非 GET/HEAD/OPTIONS 请求，不消费 AI Token。平台版本仍保留 draft；其余脚本尚未逐一真实回放，不报告为全部通过。"]
    (ROOT / "delivery-report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    target = ROOT.parent / "fieldwork-web-tests.zip"
    allowed = {".py", ".json", ".md", ".txt", ".ini", ".cjs"}
    with ZipFile(target, "w", ZIP_DEFLATED) as archive:
        for file in sorted(ROOT.rglob("*")):
            if not file.is_file() or file.suffix not in allowed:
                continue
            if any(part in {"node_modules", "__pycache__", ".pytest_cache", ".auth"} for part in file.relative_to(ROOT).parts):
                continue
            archive.write(file, Path("fieldwork-web-tests") / file.relative_to(ROOT))
    print(json.dumps({"bundle": str(target), "bytes": target.stat().st_size,
                      "replay": dict(counts), "generated": generated["features"]}))


if __name__ == "__main__":
    report()
