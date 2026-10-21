"""Exercise report record filters with mocked, read-only APIs."""

import argparse
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import expect, sync_playwright

STATUSES = ("queued", "running", "success", "failed", "blocked", "interrupted")


class RecordFixture:
    def __init__(self):
        self.queries = []
        self.writes = []
        self.unexpected = []
        self.rows = [
            {"id": number, "name": f"Run {status}", "project_id": 10, "status": status,
             "data": {"case_id": number, "case_type": "API", "duration_ms": 100}}
            for number, status in enumerate(STATUSES, start=1)
        ]
        self.rows += [{**self.rows[3], "id": 10 + number, "name": f"Run failed {number}"} for number in range(25)]
        self.rows.append({**self.rows[3], "id": 100, "name": "Other project failure", "project_id": 20})

    def intercept(self, route):
        request = route.request
        parsed = urlparse(request.url)
        endpoint = parsed.path.removeprefix("/api/v1")
        if request.method != "GET":
            self.writes.append((request.method, endpoint))
            route.fulfill(status=405, json={"code": 405, "message": "Read-only UI check"})
            return
        if endpoint == "/auth/me":
            data = {"id": 1, "username": "ui-check", "display_name": "测试用户", "role": "admin"}
        elif endpoint == "/projects/options":
            data = [{"id": 10, "name": "Project A", "is_default": True}, {"id": 20, "name": "Project B"}]
        elif endpoint == "/reports/records":
            query = {key: values[0] for key, values in parse_qs(parsed.query).items()}
            self.queries.append(query)
            rows = [row for row in self.rows
                    if (not query.get("status") or row["status"] == query["status"])
                    and (not query.get("project_id") or row["project_id"] == int(query["project_id"]))
                    and query.get("keyword", "").lower() in row["name"].lower()]
            page, size = int(query.get("page", 1)), int(query.get("pageSize", 20))
            data = {"items": rows[(page - 1) * size:page * size], "total": len(rows), "page": page, "pageSize": size}
        else:
            self.unexpected.append(endpoint)
            data = None
        route.fulfill(json={"code": 0, "message": "success", "data": data})


def change_filter(browser_page, fixture, selector, selected_value, **expected):
    count = len(fixture.queries)
    with browser_page.expect_response("**/api/v1/reports/records?*"):
        selector.select_option(selected_value)
    expect(browser_page.locator(".table-wrap")).to_have_attribute("aria-busy", "false")
    assert len(fixture.queries) == count + 1, fixture.queries[count:]
    assert all(fixture.queries[-1].get(key) == str(value) for key, value in expected.items()), fixture.queries[-1]


def check_filters(page, fixture, output):
    status = page.get_by_role("combobox", name="按执行状态筛选", exact=True)
    project = page.get_by_role("combobox", name="按项目筛选", exact=True)
    keyword = page.get_by_placeholder("搜索名称/说明")
    expect(status).to_have_value("")
    assert len(fixture.queries) == 1 and fixture.queries[0]["project_id"] == "10"
    assert "status" not in fixture.queries[0]
    assert status.locator("option").count() == len(STATUSES) + 1
    for value in STATUSES:
        change_filter(page, fixture, status, value, status=value, project_id=10, page=1)
        rows = page.locator("tbody tr").filter(has=page.locator('input[type="checkbox"]'))
        expect(rows).to_have_count(20 if value == "failed" else 1)
    change_filter(page, fixture, status, "failed", status="failed", page=1)
    page.get_by_role("button", name="下一页", exact=True).click()
    expect(page.locator("tbody tr").filter(has_text="Run failed")).to_have_count(6)
    assert fixture.queries[-1]["status"] == "failed" and fixture.queries[-1]["page"] == "2"
    change_filter(page, fixture, status, "success", status="success", page=1)
    expect(page.get_by_role("cell", name="Run success", exact=True)).to_be_visible()
    keyword.fill("not-existing")
    page.get_by_role("button", name="查询", exact=True).click()
    expect(page.get_by_role("cell", name="暂无数据", exact=True)).to_be_visible()
    assert fixture.queries[-1]["keyword"] == "not-existing" and fixture.queries[-1]["status"] == "success"
    keyword.fill("Run failed")
    change_filter(page, fixture, status, "failed", status="failed", keyword="Run failed", page=1)
    expect(page.get_by_role("cell", name="Run failed", exact=True)).to_be_visible()
    change_filter(page, fixture, status, "", keyword="Run failed", project_id=10, page=1)
    assert "status" not in fixture.queries[-1]
    keyword.fill("")
    change_filter(page, fixture, status, "failed", status="failed", page=1)
    change_filter(page, fixture, project, "20", status="failed", project_id=20, page=1)
    expect(page.get_by_role("cell", name="Other project failure", exact=True)).to_be_visible()
    change_filter(page, fixture, project, "0", status="failed", page=1)
    assert "project_id" not in fixture.queries[-1]
    status_bounds, project_bounds = status.bounding_box(), project.bounding_box()
    assert status_bounds and project_bounds and status_bounds["width"] <= 180
    assert abs(status_bounds["y"] - project_bounds["y"]) <= 1, (status_bounds, project_bounds)
    page.screenshot(path=str(output / "record-status-desktop.png"), animations="disabled")
    page.set_viewport_size({"width": 390, "height": 900})
    expect(status).to_be_visible()
    bounds = status.bounding_box()
    assert bounds and bounds["x"] >= 0 and bounds["x"] + bounds["width"] <= 390, bounds
    page.screenshot(path=str(output / "record-status-mobile.png"), animations="disabled")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:5173")
    parser.add_argument("--output", default="frontend/node_modules/.cache/ui-checks/record-filters")
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(viewport={"width": 1440, "height": 960})
        context.add_init_script("sessionStorage.setItem('autotest.session./access_token','record-filters-ui-check')")
        fixture = RecordFixture()
        context.route("**/api/v1/**", fixture.intercept)
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(args.url + "/reports/records")
        expect(page.get_by_role("cell", name="Run success", exact=True)).to_be_visible()
        check_filters(page, fixture, output)
        assert not errors and not fixture.writes and not fixture.unexpected, (errors, fixture.writes, fixture.unexpected)
        context.close()
        browser.close()
    print("PASS: all record statuses, project/keyword combinations, pagination reset, clear filter, empty state and mobile layout")


if __name__ == "__main__":
    main()
