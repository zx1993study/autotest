"""Combine latest per-scenario evidence without erasing failed historical runs."""
from datetime import datetime
import json
import os
from pathlib import Path
import requests

from case_suite_runner import HERE, SOURCE, BASE, PROJECT_ID, Platform, catalog, write_json, CN


def finalize():
    previous_summary_path = HERE / "case-coverage-final.json"
    previous_knowledge_ids = (json.loads(previous_summary_path.read_text(encoding="utf-8")).get("knowledge_ids", [])
                              if previous_summary_path.exists() else [])
    files = ["case-suite-results-primary.json", "case-suite-results-followup-1.json",
             "case-suite-results-followup-2.json", "case-suite-results-followup-3.json", "case-headed-results-primary.json", "case-headed-results-followup-1.json", "case-headed-results.json"]
    runs, latest = [], {}
    for name in files:
        path = HERE / name
        if not path.exists():
            continue
        run = json.loads(path.read_text(encoding="utf-8"))
        runs.append((name, run))
        for scene in run["scenarios"]:
            latest[scene["code"]] = {**scene, "run_file": name, "run_prefix": run["run_prefix"]}
    points = catalog()
    for point in points:
        scenes = [s for s in latest.values() if point["id"] in s["case_points"]]
        point["evidence"] = [s["code"] for s in scenes]
        point["remote_status"] = "partial" if scenes else "not_run"
        if any(s["status"] != "success" for s in scenes):
            point["remote_status"] = "has_failure"
        if point["id"] in {"DOC-01", "BELI-01", "BELI-02"} and scenes and all(s["status"] == "success" for s in scenes):
            point["remote_status"] = "verified"
    successful = [s for s in latest.values() if s["status"] == "success"]
    failed = [s for s in latest.values() if s["status"] != "success"]
    untouched = [p["id"] for p in points if p["remote_status"] == "not_run"]
    api_records = [e for _, run in runs for e in run.get("api_cases", [])]
    web_records = [w for _, run in runs for w in run.get("web_cases", [])]
    summary = {"target": BASE + "/", "project_id": PROJECT_ID, "source_commit": SOURCE,
        "generated_at": datetime.now(CN).isoformat(), "source_points": len(points),
        "latest_scenarios": len(latest), "latest_success": len(successful), "latest_failure": len(failed),
        "api_records_including_retests": len(api_records), "headed_cases": len({w['code'] for w in web_records}), "headed_records_including_retests": len(web_records),
        "touched_points": len(points) - len(untouched), "not_run_points": untouched,
        "catalog": points, "scenarios": list(latest.values()), "run_files": files}
    cleanup = []
    all_files = [*files, "case-suite-results-compatibility-aborted.json", "case-headed-results-setup-aborted.json", "case-headed-results-setup-aborted-2.json", "case-headed-results-evidence-aborted.json"]
    for name in all_files:
        path = HERE / name
        if not path.exists():
            continue
        run = json.loads(path.read_text(encoding="utf-8"))
        current = {}
        for entry in run.get("cleanup", []):
            current[(entry["type"], entry.get("id", ""))] = entry
        cleanup.extend({"run_file": name, **entry} for entry in current.values())
    summary["cleanup_latest_failures"] = [c for c in cleanup if c["status"] != "success"]
    summary["cleanup"] = cleanup
    session = requests.Session()
    login = session.post(BASE + "/api/v1/auth/login", json={"username": "admin", "password": os.environ["PUNKRECORD_PASSWORD"]}, timeout=25)
    login.raise_for_status()
    session.headers["Authorization"] = "Bearer " + login.json()["access_token"]
    products = session.get(BASE + "/api/v1/beli/products", timeout=25).json()["data"]
    product_by_id = {p["id"]: p for p in products}
    verified = {}
    for name in all_files:
        path = HERE / name
        if not path.exists():
            continue
        run = json.loads(path.read_text(encoding="utf-8"))
        for fixture in run.get("fixtures", []):
            kind, item_id = fixture["type"], fixture["id"]
            key = kind + ":" + item_id
            if kind == "user":
                response = session.get(BASE + f"/api/v1/iam/users/{item_id}", timeout=25)
                response.raise_for_status()
                ok = response.json()["data"]["status"] == "inactive"
            elif kind == "project":
                response = session.get(BASE + f"/api/v1/project/projects/{item_id}", timeout=25)
                ok = response.status_code == 404
            elif kind in {"meeting", "meeting_deleted"}:
                response = session.get(BASE + f"/api/v1/meeting/records/{item_id}", timeout=25)
                ok = response.status_code == 404
            elif kind == "product":
                ok = item_id in product_by_id and product_by_id[item_id]["active"] is False
            else:
                continue
            verified[key] = {"type": kind, "id": item_id, "verified": ok, "source_run": name}
    summary["cleanup_readonly_verification"] = list(verified.values())
    summary["cleanup_unverified"] = [v for v in verified.values() if not v["verified"]]
    write_json(HERE / "case-coverage-final.json", summary)
    write_json(HERE / "case-catalog.json", points)
    lines = ["# PunkRecord cases.md 远程验收补充报告", "", f"依据 origin/main `{SOURCE}` 的 `.agent/test/cases.md`；远程目标 {BASE}/；autotest 项目 PunkRecord ({PROJECT_ID})。",
        "", "## 原因与修正", "", "此前本地停在旧 dev 分支 a2ace19，未读取 main 新增的 .agent/test/cases.md。此前61条通用冒烟用例不是按该文件生成，不能代表该文件已覆盖。",
        "本次 fetch 后独立导出最新代码作静态参考，没有重置/切换脏工作区，也没有启动或测试本地PunkRecord。",
        "", "## 结果", "", f"原始测试点44项，逐项保留编号、场景、预期、现有脚本和缺口。最新细分场景 {len(latest)} 项：{len(successful)} 通过、{len(failed)} 未通过。",
        f"API累计执行记录（含本轮复测）{len(api_records)}条，有头页面用例{summary['headed_cases']}条、含复测执行{len(web_records)}次；页面任务逐条核对 local_headed 与 headless=false。",
        f"触达原测试点 {len(points) - len(untouched)}/44；触达包含部分覆盖，不是全量验收通过率。",
        "前期中止和脚本问题记录保留，不以重写历史结果代替复测。响应记录截断到8000字符时只读重新获取完整GET响应，不重放写请求。",
        "部分集合/敏感字段断言由场景脚本检查并写入JSON；不能只靠逐步API返回200判断场景成功。",
        "", "## 逐条覆盖", "", "| 原编号 | 原场景 | 最新状态 | 细分场景数 | 尚需补充/限制 |", "|---|---|---|---:|---|"]
    for point in points:
        limits = sorted({s.get("coverage_limit", "") for s in latest.values() if point["id"] in s["case_points"]} - {""})
        text = "；".join(limits) if limits else (point["remote_gap"] if point["remote_status"] == "not_run" else "仅覆盖已执行的细分场景；其他组合见脚本盘点")
        if point["remote_status"] == "verified":
            text = "本条列明的核心组合已验证；不代表相邻模块全部通过"
        lines.append(f"| {point['id']} | {point['scenario']} | {point['remote_status']} | {len(point['evidence'])} | {text} |")
    lines += ["", "## 最新场景证据", "", "| 场景 | 原编号 | 结果 | 平台执行记录 |", "|---|---|---|---|"]
    for scene in latest.values():
        ids = ",".join(str(e["record_id"]) for e in scene.get("evidence", []) if "record_id" in e)
        lines.append(f"| {scene['code']} {scene['title']} | {','.join(scene['case_points'])} | {scene['status']} | {ids} |")
    lines += ["", "## 未通过项", "", "TODO08-team：新建主管登录后，团队任务审核人下拉缺少当前主管，无法选择并继续核验卡片。",
        "平台最新有头任务19039、执行记录19040；对应只读API已返回本轮团队任务。远程源码线索：AuthContext保存user.name，TodoPage生成审核人选项却读取user.display_name。详见team-view-findings.md；未修改业务代码。",
        "", "## 未验证", "", "未执行编号：" + ", ".join(untouched) + "。",
        "考勤ATT系列会重算全体员工余额；历史缺失日期/提交时间/规则生效时间需隔离历史夹具；迁移和真实MySQL行锁并发不能在共享业务库上造数。",
        "真实微信绑定和推送、小程序、收费AI/ASR、后台跨日中断恢复未验证。标准桌面有头测试不等同于1440/390视口、暗色和全部跨端组合。",
        "没有运行仓库本地pytest、隔离SQLite浏览器测试或构建；仓库原报告的154 passed/3 skipped仅是旧报告，不计入本轮。",
        "", "## 清理与保留", "", f"按对象类型和ID归并后的最新清理失败数：{len(summary['cleanup_latest_failures'])}。",
        f"另以只读API复核 {len(verified)} 个新建账号/项目/会议/商品的最终状态，未符合清理条件 {len(summary['cleanup_unverified'])} 个。",
        "只按本轮登记ID清理。测试项目和非早会会议删除；已发奖测试任务先重开冲销再删除；未完成兑换取消解除冻结。",
        "测试账号停用、商品下架。无删除接口的普通任务撤销，订单/请假/奖励与余额审计流水保留，不删账本、不回滚历史业务。",
        "", "## 会议误报更正", "", "参会姓名的正确入口为转录文本中的说话人识别；实际使用的speaker_id经映射后同步参会人员。此前MEET-002查找独立参会人员输入框是脚本假设错误，不是入口缺失的业务缺陷。",
        "本次使用真实说话人输入框有头重测通过，具体结果及持久化证据见 case-headed-results-primary.json 的MEET02-speaker-corrected。",
        "", "## 文件与复跑", "", "case_suite_runner.py 为远程API场景；headed_case_runner.py 为平台Agent有头页面场景；case-script-audit.md 为已有脚本与缺口盘点；case-coverage-final.json保留精确记录关联。",
        "设置环境变量 AUTOTEST_PASSWORD、PUNKRECORD_PASSWORD 后运行脚本。不要单独复跑引用已清理ID的API步骤，应由脚本新建夹具。",
        "源码文档参考保存在 source-reference/.agent/test/；业务代码仅参考，远程地址为固定白名单。"]
    report = "\n".join(lines) + "\n"
    (HERE / "case-final-report.md").write_text(report, encoding="utf-8")
    api = Platform()
    cases = {}
    page = 1
    while True:
        batch = api.call("GET", f"/api-testing/cases?project_id={PROJECT_ID}&page={page}&pageSize=200")
        for case in batch["items"]:
            cases[case["id"]] = case
        if len(cases) >= batch["total"] or not batch["items"]:
            break
        page += 1
    used = {e["case_id"] for scene in latest.values() for e in scene.get("evidence", []) if e["case_id"] in cases}
    write_json(HERE / "case-native-api-cases.json", [cases[item_id] for item_id in sorted(used)])
    flow_ids = []
    existing_flows = api.call("GET", f"/execution/flows?project_id={PROJECT_ID}&pageSize=200")["items"]
    by_name = {f["name"]: f for f in existing_flows}
    scenario_endpoint_available = True
    if existing_flows:
        try:
            api.call("GET", f"/execution/flows/{existing_flows[0]['id']}/scenarios")
        except RuntimeError as exc:
            if "HTTP 404" not in str(exc):
                raise
            scenario_endpoint_available = False
    for scene in latest.values():
        evidence = [e for e in scene.get("evidence", []) if e["case_id"] in cases]
        if not evidence:
            continue
        nodes = [{"key": f"step_{index + 1}", "name": e["method"] + " " + e["path"].split("?")[0],
                  "api_id": cases[e["case_id"]]["source_id"], "case_id": e["case_id"],
                  "auth_id": cases[e["case_id"]].get("data", {}).get("auth_id"), "next": "auto"}
                 for index, e in enumerate(evidence)]
        name = "CASEMD " + scene["code"]
        description = ("来源 .agent/test/cases.md " + ",".join(scene["case_points"]) + "; " + scene["title"]
                       + "; 场景已由case_suite_runner按顺序调用平台原生执行器验证，结果=" + scene["status"]
                       + "; 已清理夹具，禁用归档以防单独重放旧ID。复跑需先脚本新建夹具。记录="
                       + ",".join(str(e["record_id"]) for e in evidence))
        old = by_name.get(name)
        flow = old or api.call("POST", "/execution/flows", {"project_id": PROJECT_ID, "name": name,
            "description": description, "status": "disabled", "data": {"version": 1, "inputs": {}, "nodes": nodes}})
        scenario_id = None
        if scenario_endpoint_available:
            existing = api.call("GET", f"/execution/flows/{flow['id']}/scenarios")
            scenario = next((item for item in existing if item["name"] == scene["title"]), None)
            scenario = scenario or api.call("POST", f"/execution/flows/{flow['id']}/scenarios", {
                "name": scene["title"], "description": description, "status": "disabled",
                "data": {"flow_id": flow["id"], "template_version": 1, "failure_policy": "stop", "nodes": {}}})
            scenario_id = scenario["id"]
        flow_ids.append({"code": scene["code"], "flow_id": flow["id"], "scenario_id": scenario_id})
        write_json(HERE / "case-scenario-flows.json", flow_ids)
    summary["archived_flows"] = flow_ids
    write_json(HERE / "case-scenario-flows.json", flow_ids)
    summary["scenario_endpoint_available"] = scenario_endpoint_available
    report += ("\n## 平台场景归档\n\n" + f"已将{len(flow_ids)}个API细分场景保存为禁用流程模板，关联最新原生用例。"
               + ("同时保存了流程场景。" if scenario_endpoint_available else "当前部署版本的流程场景子接口返回404，因此未创建子场景；完整编排已导出。")
               + "执行证据来自本次脚本顺序编排的原生执行记录；没有将其虚报为平台流程批次执行。夹具已清理，禁用避免误重放旧ID。\n")
    (HERE / "case-final-report.md").write_text(report, encoding="utf-8")
    knowledge_ids = []
    for index, (title, key, content) in enumerate([("cases.md最终覆盖与执行报告", "punkrecord.cases_md.final", report),
                                ("cases.md44条原测试点映射", "punkrecord.cases_md.final_catalog", json.dumps(points, ensure_ascii=False, indent=2))]):
        payload = {"project_id": PROJECT_ID, "name": title, "status": "active",
            "data": {"domain": "WEB", "kind": "test_coverage_review", "knowledge_key": key,
                     "content": content, "verification_status": "partial", "source_commit": SOURCE}}
        saved = (api.call("PUT", f"/project-knowledge/{previous_knowledge_ids[index]}", payload)
                 if index < len(previous_knowledge_ids) else api.call("POST", "/project-knowledge", payload))
        knowledge_ids.append(saved["id"])
    project = api.call("GET", f"/projects/{PROJECT_ID}")
    data = dict(project.get("data", {}))
    data.update(source_reference=SOURCE, cases_md_summary={k: summary[k] for k in (
        "source_points", "latest_scenarios", "latest_success", "latest_failure", "touched_points",
        "api_records_including_retests", "headed_cases", "not_run_points")}, cases_md_knowledge_ids=knowledge_ids)
    data["cases_md_summary"]["cleanup_latest_failures"] = len(summary["cleanup_latest_failures"])
    data.setdefault("remote_test_summary", {})["historical_meet002_correction"] = "原用例错误查找独立参会人员输入框，非业务缺陷；本次按说话人识别重测，见 cases_md_summary 与最终报告"
    api.call("PUT", f"/projects/{PROJECT_ID}", {"description": "远程 PunkRecord；已按 main .agent/test/cases.md 补充场景，覆盖仍为部分。历史MEET-002为脚本入口假设错误；以cases.md最终覆盖报告为准。", "data": data})
    summary["knowledge_ids"] = knowledge_ids
    old = api.call("GET", "/project-knowledge/18163")
    old_data = dict(old.get("data", {}))
    text = old_data.get("content", "")
    text = text.replace("UI参会人员入口缺失", "旧MEET-002错误查找独立输入框（脚本问题，非入口缺失业务缺陷）")
    text = text.replace("失败的MEET-002表示已设计并执行该测试点，但功能不通过，不能算已验收。", "旧MEET-002因脚本错误查找独立参会人员输入框而失败，不能据此认定业务不通过。最新应按说话人识别入口重测，并以 cases.md 最终报告为准。")
    if text.startswith("更正：此前未读取main的.agent/test/cases.md"):
        text = text.split("\n\n", 1)[-1]
    old_data["content"] = "更正：此前未读取main的.agent/test/cases.md，以下为旧冒烟评估，不是该文件的覆盖报告。参会人员入口的失败为脚本问题。最新报告知识ID：" + str(knowledge_ids[0]) + "。\n\n" + text
    api.call("PUT", "/project-knowledge/18163", {"data": old_data})
    write_json(HERE / "case-coverage-final.json", summary)
    print(json.dumps({k: v for k, v in summary.items() if k not in {"catalog", "scenarios", "cleanup", "cleanup_readonly_verification", "archived_flows"}}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    finalize()
