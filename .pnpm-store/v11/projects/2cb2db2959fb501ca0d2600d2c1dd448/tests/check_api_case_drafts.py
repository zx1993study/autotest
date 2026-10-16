"""Draft deletion browser regression with mocked APIs and no real data changes."""

import argparse
from copy import deepcopy
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import expect, sync_playwright


class DraftFixture:
    def __init__(self):
        self.deletions, self.acceptances, self.confirmations = [], [], []
        self.confirm = True
        self.fail_delete = False
        self.reset()

    def reset(self):
        self.drafts = [{"id": 2000 + index, "name": f"draft_{index}", "project_id": 1,
                        "source_id": 30, "status": "draft" if index <= 11 else "accepted" if index == 12 else "rejected",
                        "data": {"priority": "P2"}, "updated_at": "2026-10-14T10:00:00"}
                       for index in range(1, 14)]

    def dialog(self, dialog):
        self.confirmations.append(dialog.message)
        dialog.accept() if self.confirm else dialog.dismiss()

    def intercept(self, route):
        request = route.request
        url = urlparse(request.url)
        endpoint = url.path.removeprefix("/api/v1")
        query = parse_qs(url.query)
        data = {"items": [], "total": 0, "page": 1, "pageSize": 10}
        if endpoint == "/api-testing/interfaces/30":
            data = {"id": 30, "name": "Mock API", "project_id": 1, "data": {"method": "POST", "path": "/mock"}}
        elif endpoint == "/api-testing/case-drafts":
            keyword, status = query.get("keyword", [""])[0], query.get("status", [""])[0]
            rows = [item for item in self.drafts if keyword in item["name"] and (not status or item["status"] == status)]
            page, size = int(query.get("page", [1])[0]), int(query.get("pageSize", [10])[0])
            data = {"items": deepcopy(rows[(page - 1) * size:page * size]), "total": len(rows), "page": page, "pageSize": size}
        elif endpoint.endswith("/batch-delete") or request.method == "DELETE":
            ids = request.post_data_json["ids"] if request.method == "POST" else [int(endpoint.split("/")[-1])]
            self.deletions.append(ids)
            if self.fail_delete:
                route.fulfill(json={"code": 1, "message": "模拟草稿删除失败", "data": None})
                return
            before = len(self.drafts)
            self.drafts = [item for item in self.drafts if item["id"] not in ids]
            data = {"deleted_count": before - len(self.drafts)} if request.method == "POST" else True
        elif endpoint == "/api-testing/case-drafts/accept":
            ids = request.post_data_json["ids"]
            self.acceptances.append(ids)
            for item in self.drafts:
                if item["id"] in ids:
                    assert item["status"] == "draft"
                    item["status"] = "accepted"
            data = {"accepted_count": len(ids), "skipped_count": 0}
        route.fulfill(json={"code": 0, "message": "success", "data": data})


def draft_row(page, index):
    return page.locator(".draft-table tbody tr").filter(has=page.get_by_role("checkbox", name=f"选择 draft_{index}", exact=True))


def open_drafts(page, url):
    page.goto(url + "/tests/api-workspace.html?detail")
    page.get_by_role("tab", name="用例草稿", exact=False).click()
    expect(draft_row(page, 1)).to_have_count(1)


def check_cancel_failure_and_batch_delete(page, fixture):
    for index in (1, 2):
        draft_row(page, index).get_by_role("checkbox").check()
    fixture.confirm = False
    page.get_by_role("button", name="删除选中（2）", exact=True).click()
    assert not fixture.deletions
    expect(draft_row(page, 1).get_by_role("checkbox")).to_be_checked()
    fixture.confirm = True
    fixture.fail_delete = True
    page.get_by_role("button", name="删除选中（2）", exact=True).click()
    expect(page.locator(".case-panel .error-text")).to_have_text("模拟草稿删除失败")
    expect(draft_row(page, 2).get_by_role("checkbox")).to_be_checked()
    fixture.fail_delete = False
    page.get_by_role("button", name="删除选中（2）", exact=True).click()
    expect(draft_row(page, 1)).to_have_count(0)
    expect(page.get_by_role("status")).to_have_text("已删除 2 条草稿")
    expect(page.get_by_role("button", name="删除选中（0）", exact=True)).to_be_disabled()
    assert fixture.deletions[-1] == [2001, 2002]
    assert "2 条草稿" in fixture.confirmations[-1]


def check_mixed_status_selection_and_layout(page, fixture, url, output):
    fixture.reset()
    open_drafts(page, url)
    page.get_by_role("combobox", name="按状态筛选用例草稿").select_option("")
    page.locator(".case-panel .pagination-controls select").select_option("20")
    expect(draft_row(page, 13)).to_have_count(1)
    page.get_by_role("checkbox", name="选择当前页全部草稿", exact=True).check()
    expect(page.get_by_role("button", name="删除选中（13）", exact=True)).to_be_enabled()
    expect(page.get_by_role("button", name="采纳选中（11）", exact=True)).to_be_enabled()
    for width in (1440, 390, 320):
        page.set_viewport_size({"width": width, "height": 960})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        assert page.locator(".case-toolbar:visible button").evaluate_all("buttons => buttons.every(button => button.scrollWidth <= button.clientWidth + 2)")
        page.screenshot(path=str(output / f"drafts-{width}.png"), full_page=True)
    page.set_viewport_size({"width": 1440, "height": 960})
    page.get_by_role("button", name="采纳选中（11）", exact=True).click()
    expect(page.get_by_role("status")).to_have_text("已采纳 11 条草稿")
    assert fixture.acceptances[-1] == list(range(2001, 2012))
    page.get_by_role("checkbox", name="选择当前页全部草稿", exact=True).check()
    expect(page.get_by_role("button", name="采纳选中（0）", exact=True)).to_be_disabled()
    page.get_by_role("button", name="删除选中（13）", exact=True).click()
    expect(page.get_by_text("暂无用例草稿", exact=True)).to_be_visible()
    assert fixture.deletions[-1] == list(range(2001, 2014))


def check_last_page_and_filters(page, fixture, url):
    fixture.reset()
    open_drafts(page, url)
    page.get_by_role("button", name="下一页", exact=True).click()
    expect(draft_row(page, 11)).to_have_count(1)
    page.get_by_role("checkbox", name="选择当前页全部草稿", exact=True).check()
    page.get_by_role("button", name="删除选中（1）", exact=True).click()
    expect(page.get_by_text("第 1 / 1 页", exact=True)).to_be_visible()
    expect(page.locator(".draft-table tbody tr")).to_have_count(10)
    search = page.get_by_role("searchbox", name="搜索用例草稿")
    search.fill("draft_10")
    search.press("Enter")
    expect(page.locator(".draft-table tbody tr")).to_have_count(1)
    draft_row(page, 10).get_by_role("button", name="删除", exact=True).click()
    expect(page.get_by_text("暂无用例草稿", exact=True)).to_be_visible()
    expect(search).to_have_value("draft_10")
    page.get_by_role("button", name="重置", exact=True).click()
    expect(page.locator(".draft-table tbody tr")).to_have_count(9)


def check_execution_request_budget(page):
    result = page.evaluate("""async () => {
      const { apiClient } = await import('/src/api/client.ts');
      const { runApiCases } = await import('/src/services/api-case.service.ts');
      const original = apiClient.defaults.adapter;
      const calls = [];
      apiClient.defaults.adapter = async config => {
        calls.push({ timeout: config.timeout, data: JSON.parse(config.data) });
        return { data: { code: 0, data: { records: [] } }, status: 200, headers: {}, config };
      };
      try {
        await runApiCases({ case_ids: [1, 1, 2] });
        await runApiCases({ case_ids: Array.from({length: 20}, (_, i) => i + 1), config: { concurrency: 1, timeout: 30, params: {name: 'mock'} } });
        return { calls, globalTimeout: apiClient.defaults.timeout };
      } finally { apiClient.defaults.adapter = original; }
    }""")
    assert result["globalTimeout"] == 15000
    assert result["calls"][0]["data"]["case_ids"] == [1, 2]
    assert result["calls"][0]["data"]["config"] == {"concurrency": 5, "timeout": 15}
    assert result["calls"][0]["timeout"] >= 60000
    assert result["calls"][1]["timeout"] >= 600000
    assert result["calls"][1]["data"]["config"]["params"] == {"name": "mock"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:5182")
    parser.add_argument("--output", default="backend/storage/ui-checks/api-drafts")
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    fixture = DraftFixture()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(viewport={"width": 1440, "height": 960})
        context.route("**/api/v1/**", fixture.intercept)
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("dialog", fixture.dialog)
        open_drafts(page, args.url)
        check_cancel_failure_and_batch_delete(page, fixture)
        check_mixed_status_selection_and_layout(page, fixture, args.url, output)
        check_last_page_and_filters(page, fixture, args.url)
        check_execution_request_budget(page)
        assert not errors, errors
        browser.close()
    print("PASS: confirmed/cancelled/failed draft batch deletion, mixed statuses, pending-only acceptance, last-page fallback, filters, mobile layouts, and execution timeout/config")


if __name__ == "__main__":
    main()
