"""Read-only API report UI checks using mocked historical evidence endpoints."""

import argparse
from pathlib import Path

from api_report_fixture import ApiReportFixture
from playwright.sync_api import expect, sync_playwright


def filter_reports(browser_page, fixture, label, value, **params):
    count = len(fixture.report_queries)
    browser_page.get_by_role("combobox", name=label, exact=True).select_option(value)
    expect(browser_page.locator(".report-table-wrap")).to_have_attribute("aria-busy", "false")
    assert len(fixture.report_queries) == count + 1, fixture.report_queries[count:]
    assert all(fixture.report_queries[-1].get(key) == str(value) for key, value in params.items())


def check_filters(page, fixture, output):
    expect(page.get_by_role("heading", name="API 报告", exact=True)).to_be_visible()
    expect(page.locator("tbody tr")).to_have_count(20)
    assert len(fixture.report_queries) == 1 and fixture.report_queries[0]["project_id"] == "10"
    assert not fixture.details and not fixture.run_reads and not fixture.case_queries
    assert page.locator("th").all_text_contents() == ["API 路径 / 流程名称", "字段 / 场景", "测试点", "是否通过", "操作"]
    page.screenshot(path=str(output / "api-reports-mixed-desktop.png"), animations="disabled")
    page.get_by_role("button", name="下一页", exact=True).click()
    expect(page.locator("tbody tr")).to_have_count(7)
    filter_reports(page, fixture, "按报告类型筛选", "api", kind="api", page=1)
    filter_reports(page, fixture, "按报告状态筛选", "failed", status="failed", kind="api", page=1)
    page.get_by_role("searchbox", name="搜索 API 报告").fill("warehouseType")
    count = len(fixture.report_queries)
    page.get_by_role("button", name="查询", exact=True).click()
    expect(page.locator("tbody tr")).to_have_count(1)
    assert len(fixture.report_queries) == count + 1 and fixture.report_queries[-1]["keyword"] == "warehouseType"
    expect(page.get_by_role("cell", name="未通过", exact=True)).to_be_visible()
    page.screenshot(path=str(output / "api-reports-desktop.png"), animations="disabled")


def check_api_detail(page, fixture):
    queries = len(fixture.report_queries)
    tabs = page.locator(".page-tab").count()
    page.get_by_role("button", name="查看结果", exact=True).click()
    dialog = page.get_by_role("dialog")
    expect(dialog.locator(".record-title")).to_contain_text("#4 Run failed")
    expect(dialog.locator(".evidence-card")).to_have_count(3)
    expect(dialog.locator('[data-outcome="failed"]')).to_have_count(1)
    assert fixture.details == [4] and not fixture.run_reads
    assert "hidden-" not in dialog.inner_text()
    page.keyboard.press("Escape")
    expect(dialog).to_have_count(0)
    assert len(fixture.report_queries) == queries and page.locator(".page-tab").count() == tabs
    expect(page.get_by_role("searchbox", name="搜索 API 报告")).to_have_value("warehouseType")
    expect(page.get_by_role("combobox", name="按报告状态筛选")).to_have_value("failed")


def check_flow_detail(page, fixture, output):
    page.get_by_role("searchbox", name="搜索 API 报告").fill("")
    page.get_by_role("button", name="查询", exact=True).click()
    filter_reports(page, fixture, "按报告类型筛选", "flow", kind="flow")
    filter_reports(page, fixture, "按报告状态筛选", "", kind="flow")
    expect(page.get_by_role("cell", name="通过", exact=True)).to_be_visible()
    queries = len(fixture.report_queries)
    page.get_by_role("button", name="查看结果", exact=True).click()
    dialog = page.get_by_role("dialog")
    expect(dialog.get_by_role("alert")).to_contain_text("Run temporarily unavailable")
    dialog.get_by_role("button", name="重试", exact=True).click()
    expect(dialog).to_have_class("api-flow flow-dialog flow-run-result-dialog")
    expect(dialog.locator(".flow-scene-node.active")).to_contain_text("审批通过")
    expect(dialog.get_by_text("审批节点", exact=True)).to_be_visible()
    expect(dialog.get_by_role("button", name="取消执行", exact=True)).to_have_count(0)
    dialog.locator("details.flow-node-evidence summary").click()
    assert "hidden-flow" not in dialog.inner_text()
    assert fixture.run_reads == [800, 800]
    page.screenshot(path=str(output / "api-report-flow-result.png"), animations="disabled")
    page.set_viewport_size({"width": 390, "height": 900})
    bounds = dialog.bounding_box()
    assert bounds and bounds["x"] >= 0 and bounds["x"] + bounds["width"] <= 390, bounds
    page.screenshot(path=str(output / "api-report-flow-mobile.png"), animations="disabled")
    page.get_by_role("button", name="关闭运行结果").click()
    expect(dialog).to_have_count(0)
    assert len(fixture.report_queries) == queries
    page.screenshot(path=str(output / "api-reports-mobile.png"), animations="disabled")
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), "Viewport overflow"
    page.set_viewport_size({"width": 1440, "height": 960})


def check_empty_error_and_races(page, fixture):
    filter_reports(page, fixture, "按报告类型筛选", "", page=1)
    fixture.hold_report = True
    page.get_by_role("combobox", name="按报告状态筛选").select_option("failed")
    expect(page.locator(".report-table-wrap")).to_have_attribute("aria-busy", "true")
    filter_reports(page, fixture, "按报告状态筛选", "success", status="success")
    expect(page.get_by_role("cell", name="通过", exact=True)).to_be_visible()
    fixture.release_reports()
    expect(page.get_by_role("cell", name="通过", exact=True)).to_be_visible()
    filter_reports(page, fixture, "按项目筛选", "20", project_id=20, status="success")
    expect(page.get_by_role("cell", name="暂无报告", exact=True)).to_be_visible()
    fixture.fail_report = True
    page.get_by_role("button", name="刷新报告", exact=True).click()
    expect(page.get_by_role("alert")).to_contain_text("Report temporarily unavailable")
    page.get_by_role("button", name="重试", exact=True).click()
    expect(page.get_by_role("alert")).to_have_count(0)
    expect(page.get_by_role("cell", name="暂无报告", exact=True)).to_be_visible()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:5173")
    parser.add_argument("--output", default="frontend/node_modules/.cache/ui-checks/api-reports")
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(viewport={"width": 1440, "height": 960})
        context.add_init_script("sessionStorage.setItem('autotest.session./access_token','api-reports-ui-check')")
        fixture = ApiReportFixture()
        context.route("**/api/v1/**", fixture.intercept)
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(args.url + "/api/reports")
        check_filters(page, fixture, output)
        check_api_detail(page, fixture)
        check_flow_detail(page, fixture, output)
        check_empty_error_and_races(page, fixture)
        assert not errors and not fixture.writes and not fixture.unexpected, (errors, fixture.writes, fixture.unexpected)
        assert not fixture.navigation.writes and not fixture.navigation.unexpected
        assert len(context.pages) == 1
        context.close()
        browser.close()
    print("PASS: API report filters/pagination; exact historical API dialog; original flow dialog + scenario selection; lazy reads; stale request cancellation; retry; mobile; no writes")


if __name__ == "__main__":
    main()
