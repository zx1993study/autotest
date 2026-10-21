"""Verify result dialogs, exact historical records, privacy and responsive cards."""

import argparse
import re
from pathlib import Path

from execution_evidence_fixture import EvidenceFixture
from playwright.sync_api import expect, sync_playwright


def open_record(page, name):
    tabs = page.locator(".page-tab").count()
    page.get_by_role("row").filter(has=page.get_by_role("cell", name=name, exact=True)).get_by_role(
        "button", name="查看结果", exact=True).click()
    dialog = page.get_by_role("dialog")
    expect(dialog).to_be_visible()
    assert page.locator(".page-tab").count() == tabs
    return dialog


def check_grid(dialog, mobile=False):
    cards = dialog.locator(".evidence-card")
    expect(cards).to_have_count(3)
    boxes = [card.bounding_box() for card in cards.all()]
    assert all(boxes), boxes
    if mobile:
        assert boxes[0]["y"] < boxes[1]["y"] < boxes[2]["y"], boxes
    else:
        assert max(box["y"] for box in boxes) - min(box["y"] for box in boxes) <= 1, boxes
        assert max(box["width"] for box in boxes) - min(box["width"] for box in boxes) <= 1, boxes
        assert boxes[0]["x"] < boxes[1]["x"] < boxes[2]["x"], boxes
    assert dialog.evaluate("el => el.scrollWidth <= el.clientWidth"), "Dialog horizontal overflow"


def close_dialog(page):
    page.get_by_role("button", name="关闭详情", exact=True).click()
    expect(page.get_by_role("dialog")).to_have_count(0)


def check_unit_and_races(page, fixture, url):
    page.goto(url + "/tests/execution-evidence.html")
    expect(page.locator("main > p")).to_have_text("18 evidence checks passed")
    page.evaluate("openEvidence(899)")
    expect(page.get_by_role("dialog").get_by_role("status")).to_have_text("加载中...")
    page.evaluate("openEvidence(900)")
    expect(page.locator(".record-title")).to_contain_text("#900 Evidence 900")
    fixture.release()
    expect(page.locator(".record-title")).to_contain_text("#900 Evidence 900")
    expect(page.get_by_role("dialog")).to_have_count(1)
    page.keyboard.press("Escape")
    expect(page.get_by_role("dialog")).to_have_count(0)
    fixture.hold_case = True
    page.evaluate("item => showCaseEvidence(item)", fixture.navigation.cases[101])
    expect(page.get_by_role("status")).to_have_text("加载最近执行结果...")
    page.evaluate("item => showCaseEvidence(item)", fixture.navigation.cases[102])
    expect(page.locator(".record-title")).to_contain_text("暂无执行记录")
    fixture.release()
    expect(page.locator(".record-title")).to_contain_text("暂无执行记录")
    assert "Latest customer" not in page.locator("main").inner_text()
    page.evaluate("item => showCaseEvidence(item, false)", fixture.navigation.cases[101])
    expect(page.locator('[data-outcome="unknown"]')).to_have_count(1)
    expect(page.locator(".record-summary")).to_have_count(0)


def check_historical(page, fixture, url, output):
    page.goto(url + "/reports/records")
    status = page.get_by_role("combobox", name="按执行状态筛选", exact=True)
    status.select_option("failed")
    expect(page.get_by_role("cell", name="Run failed", exact=True)).to_be_visible()
    queries, case_queries, details = len(fixture.queries), len(fixture.case_queries), len(fixture.details)
    dialog = open_record(page, "Run failed")
    expect(dialog.locator(".record-title")).to_contain_text("#4 Run failed")
    expect(dialog.locator(".record-summary")).to_contain_text("HTTP 状态200")
    expect(dialog.locator(".record-summary")).to_contain_text("业务码500")
    expect(dialog.get_by_role("region", name="请求参数", exact=True)).to_contain_text("Historical customer")
    expect(dialog.locator('[data-outcome="passed"]')).to_have_count(1)
    expect(dialog.locator('[data-outcome="failed"]')).to_have_count(1)
    assert "hidden-" not in dialog.inner_text() and "Latest customer" not in dialog.inner_text()
    assert fixture.details[details:] == [4] and len(fixture.case_queries) == case_queries
    check_grid(dialog)
    assert dialog.locator(".evidence-card-content").nth(1).evaluate("el => el.scrollHeight > el.clientHeight")
    page.evaluate("window.copyEvidenceFails = true")
    dialog.get_by_role("button", name="复制请求参数", exact=True).click()
    expect(dialog.get_by_text("复制失败", exact=True)).to_be_visible()
    page.evaluate("window.copyEvidenceFails = false")
    for name in ("请求参数", "返回结果", "断言"):
        dialog.get_by_role("button", name="复制" + name, exact=True).click()
        expect(dialog.get_by_role("button", name="已复制" + name, exact=True)).to_be_visible()
        copied = page.evaluate("window.copiedEvidence")
        assert copied and "hidden-" not in copied
    page.screenshot(path=str(output / "record-evidence-desktop.png"), animations="disabled")
    page.set_viewport_size({"width": 390, "height": 900})
    check_grid(dialog, mobile=True)
    bounds = dialog.bounding_box()
    assert bounds and bounds["x"] >= 0 and bounds["x"] + bounds["width"] <= 390, bounds
    page.screenshot(path=str(output / "record-evidence-mobile.png"), animations="disabled")
    close_dialog(page)
    expect(status).to_have_value("failed")
    assert len(fixture.queries) == queries, fixture.queries
    page.set_viewport_size({"width": 1440, "height": 960})
    page.get_by_role("button", name="下一页", exact=True).click()
    expect(page.get_by_role("cell", name="Run failed 19", exact=True)).to_be_visible()
    queries = len(fixture.queries)
    open_record(page, "Run failed 19")
    expect(page.locator(".record-title")).to_contain_text("#29")
    close_dialog(page)
    assert len(fixture.queries) == queries and fixture.queries[-1]["page"] == "2"


def check_variants(page, fixture):
    page.get_by_role("combobox", name="按执行状态筛选", exact=True).select_option("")
    expect(page.get_by_role("cell", name="Run running", exact=True)).to_be_visible()
    dialog = open_record(page, "Run running")
    expect(dialog.get_by_role("region", name="返回结果", exact=True)).to_contain_text("Plain upstream response")
    expect(dialog.get_by_role("region", name="断言", exact=True)).to_contain_text("未记录断言")
    close_dialog(page)
    dialog = open_record(page, "Run success")
    expect(dialog.get_by_role("region", name="返回结果", exact=True)).to_contain_text("未记录返回结果")
    expect(dialog.get_by_role("region", name="断言", exact=True)).to_contain_text("未记录断言")
    close_dialog(page)
    dialog = open_record(page, "Run blocked")
    expect(dialog.locator('[data-outcome="unknown"]')).to_contain_text("未记录结果")
    expect(dialog.locator(".record-error")).to_have_text("页面元素未找到")
    assert "hidden-web" not in dialog.inner_text()
    close_dialog(page)
    count = len(fixture.details)
    dialog = open_record(page, "Run interrupted")
    expect(dialog.get_by_role("alert")).to_contain_text("Temporary record read error")
    dialog.get_by_role("button", name="重试", exact=True).click()
    expect(dialog.locator(".record-error")).to_have_text("设备离线")
    assert fixture.details[count:] == [6, 6]
    page.mouse.click(2, 2)
    expect(page.get_by_role("dialog")).to_have_count(0)


def check_api_dialogs(page, fixture, url, output):
    page.goto(url + "/api/interfaces/10?project_id=1&module_id=21")
    row = page.get_by_role("row").filter(has_text="新增客户正常用例")
    fixture.fail_case_once = True
    row.get_by_role("button", name="详情", exact=True).click()
    dialog = page.get_by_role("dialog")
    expect(dialog.get_by_role("alert")).to_contain_text("Temporary latest record error")
    expect(dialog.locator(".evidence-grid")).to_have_count(0)
    dialog.get_by_role("button", name="重试", exact=True).click()
    expect(dialog.locator(".record-title")).to_contain_text("#700 Latest execution")
    expect(dialog.get_by_role("region", name="请求参数", exact=True)).to_contain_text("Latest customer")
    expect(dialog.locator('[data-outcome="failed"]')).to_have_count(1)
    assert "hidden-" not in dialog.inner_text()
    assert fixture.case_queries[-1]["case_id"] == "101" and fixture.case_queries[-1]["pageSize"] == "1"
    check_grid(dialog)
    page.set_viewport_size({"width": 1024, "height": 900})
    check_grid(dialog)
    page.set_viewport_size({"width": 1440, "height": 960})
    page.screenshot(path=str(output / "api-case-evidence-desktop.png"), animations="disabled")
    page.set_viewport_size({"width": 390, "height": 900})
    check_grid(dialog, mobile=True)
    page.screenshot(path=str(output / "api-case-evidence-mobile.png"), animations="disabled")
    page.keyboard.press("Escape")
    expect(dialog).to_have_count(0)
    page.set_viewport_size({"width": 1440, "height": 960})
    page.get_by_role("tab", name=re.compile("用例草稿")).click()
    row = page.get_by_role("row").filter(has_text="客户新增草稿")
    row.get_by_role("button", name="详情", exact=True).click()
    dialog = page.get_by_role("dialog")
    expect(dialog.locator('[data-outcome="unknown"]')).to_have_count(1)
    expect(dialog.locator(".record-summary")).to_have_count(0)
    assert "hidden-case" not in dialog.inner_text()
    check_grid(dialog)
    close_dialog(page)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:5173")
    parser.add_argument("--output", default="frontend/node_modules/.cache/ui-checks/execution-evidence")
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(viewport={"width": 1440, "height": 960})
        context.add_init_script("""sessionStorage.setItem('autotest.session./access_token','evidence-ui-check');
            Object.defineProperty(navigator, 'clipboard', {value: {
                writeText: async text => {
                    if (window.copyEvidenceFails) throw new Error('Clipboard unavailable');
                    window.copiedEvidence = text;
                }
            }});""")
        fixture = EvidenceFixture()
        context.route("**/api/v1/**", fixture.intercept)
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        check_unit_and_races(page, fixture, args.url)
        check_historical(page, fixture, args.url, output)
        check_variants(page, fixture)
        check_api_dialogs(page, fixture, args.url, output)
        assert not errors and not fixture.writes and not fixture.unexpected, (errors, fixture.writes, fixture.unexpected)
        assert not fixture.navigation.writes and not fixture.navigation.unexpected
        assert len(context.pages) == 1
        context.close()
        browser.close()
    print("PASS: 18 data/privacy checks; historical/API dialogs; stale requests; retry; three columns; mobile; copy; filters; no writes")


if __name__ == "__main__":
    main()
