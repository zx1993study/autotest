"""Check reusable API detail tabs with mocked APIs; no business data is changed."""

import argparse
import json
import re
from collections import Counter
from copy import deepcopy
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import expect, sync_playwright

class NavigationFixture:
    def __init__(self):
        self.requests = Counter()
        self.writes = []
        self.unexpected = []
        node = {"key": "create", "name": "新增客户", "api_id": 10, "case_id": 101, "auth_id": None,
                "params": {}, "request": {}, "bindings": [], "extracts": [], "routes": [], "next": "auto"}
        self.flow = {"id": 1, "name": "客户生命周期", "project_id": 1, "status": "active",
                     "data": {"version": 1, "nodes": [node], "inputs": {}}}
        self.scenes = []
        self.cases = {
            101: {"id": 101, "name": "新增客户正常用例", "project_id": 1, "source_id": 10, "status": "active",
                  "data": {"params": {"name": "原用例客户"}}},
            102: {"id": 102, "name": "查询客户正常用例", "project_id": 1, "source_id": 11, "status": "active", "data": {}}
        }
        self.flows = {1: self.flow, 2: {**deepcopy(self.flow), "id": 2, "name": "销售订单流程"}}
        self.interfaces = {
            api_id: {"id": api_id, "name": name, "project_id": 1, "status": "active",
                     "data": {"module_id": 21, "module": "客户管理", "method": "GET", "path": path}}
            for api_id, name, path in [(10, "新增客户", "/customers"), (11, "查询客户", "/customers/detail")]
        }

    def intercept(self, route):
        request = route.request
        parsed = urlparse(request.url)
        endpoint = parsed.path.removeprefix("/api/v1")
        self.requests[endpoint] += 1
        if request.method != "GET":
            self.writes.append((request.method, endpoint))
            route.fulfill(status=405, json={"code": 405, "message": "Read-only navigation check"})
            return
        data = None
        if endpoint == "/execution/flows":
            data = self.page(list(self.flows.values()))
        elif endpoint == "/auth/me":
            data = {"id": 1, "username": "ui-check", "display_name": "测试用户", "role": "admin"}
        elif endpoint == "/projects/options":
            data = [{"id": 1, "name": "测试项目", "base_url": "https://example.test", "is_default": True}]
        elif endpoint == "/project-auth/options":
            data = []
        elif endpoint == "/api-testing/interfaces/options":
            data = list(self.interfaces.values())
        elif match := re.fullmatch(r"/execution/flows/(\d+)(/scenarios|/runs)?", endpoint):
            flow_id = int(match[1])
            data = self.flows[flow_id] if not match[2] else ([] if match[2] == "/runs" else self.scenes)
        elif endpoint == "/api-testing/interfaces":
            data = self.page(list(self.interfaces.values()))
        elif match := re.fullmatch(r"/api-testing/interfaces/(\d+)", endpoint):
            data = self.interfaces[int(match[1])]
        elif match := re.fullmatch(r"/api-testing/interfaces/modules/(\d+)", endpoint):
            data = {"id": int(match[1]), "name": "客户管理", "project_id": 1, "data": {}}
        elif endpoint in ("/api-testing/fields", "/api-testing/cases", "/api-testing/case-drafts"):
            data = self.page([])
            if endpoint == "/api-testing/cases":
                source_id = int(parse_qs(parsed.query).get("source_id", [0])[0])
                data = self.page([case for case in self.cases.values() if case["source_id"] == source_id])
        elif match := re.fullmatch(r"/api-testing/cases/(\d+)", endpoint):
            data = self.cases[int(match[1])]
        if data is None:
            self.unexpected.append(endpoint)
        route.fulfill(json={"code": 0, "message": "success", "data": data})

    @staticmethod
    def page(items):
        return {"items": items, "total": len(items), "page": 1, "pageSize": 20}


def navigate(page, path, expected=None):
    result = page.evaluate("""async path => {
        const router = document.getElementById('app').__vue_app__.config.globalProperties.$router;
        const failure = await router.push(path);
        return {path: router.currentRoute.value.fullPath, failure: failure?.message,
            header: document.querySelector('.flow-page-header')?.textContent};
    }""", path)
    assert result["path"] == (expected or path), result


def detail_tab(page, kind):
    return page.locator(f'.page-tab[data-tab-key="/api/{kind}/:detail"]')


def stored_tabs(page):
    return page.evaluate("JSON.parse(sessionStorage.getItem('autotest.session./opened_page_tabs'))")


def check_flows(page, fixture, output):
    expect(page.get_by_text("客户生命周期", exact=True)).to_be_visible()
    page.get_by_role("row").filter(has_text="客户生命周期").get_by_role("button", name="详情", exact=True).click()
    expect(page.get_by_role("heading", name="客户生命周期", exact=True)).to_be_visible()
    page.get_by_role("button", name="新增场景", exact=True).click()
    expect(page.get_by_role("dialog")).to_be_visible()
    navigate(page, "/api/flows/2")
    expect(page.get_by_role("heading", name="销售订单流程", exact=True)).to_be_visible()
    expect(page.get_by_role("dialog")).to_have_count(0)
    expect(detail_tab(page, "flows")).to_have_count(1)
    assert fixture.requests["/execution/flows/2"] == 1
    navigate(page, "/api/flows/1")
    page.get_by_role("button", name="流程模板", exact=True).click()
    request_json = page.get_by_label("参数覆盖 JSON")
    expect(request_json).to_have_value(re.compile("原用例客户"))
    params = json.loads(request_json.input_value())
    params["params"]["name"] = "unsaved customer"
    request_json.fill(json.dumps(params))
    expect(page.get_by_role("button", name="保存模板", exact=True)).to_be_enabled()
    page.once("dialog", lambda dialog: dialog.dismiss())
    navigate(page, "/api/flows/2", expected="/api/flows/1")
    expect(page).to_have_url(re.compile(r"/api/flows/1$"))
    assert fixture.requests["/execution/flows/2"] == 1
    assert next(tab for tab in stored_tabs(page) if tab["key"] == "/api/flows/:detail")["path"] == "/api/flows/1"
    page.once("dialog", lambda dialog: dialog.dismiss())
    page.locator(".flow-back-link").click()
    expect(page).to_have_url(re.compile(r"/api/flows/1$"))
    expect(detail_tab(page, "flows")).to_have_count(1)
    page.once("dialog", lambda dialog: dialog.accept())
    navigate(page, "/api/flows/2")
    expect(page.get_by_role("heading", name="销售订单流程", exact=True)).to_be_visible()
    expect(page.get_by_role("button", name="功能场景", exact=False)).to_have_class("active")
    assert fixture.requests["/execution/flows/2"] == 2
    page.screenshot(path=str(output / "flow-detail-desktop.png"), animations="disabled")
    page.locator(".flow-back-link").click()
    expect(page).to_have_url(re.compile(r"/api/flows$"))
    expect(detail_tab(page, "flows")).to_have_count(0)
    expect(page.locator('.page-tab[data-tab-key="/api/flows"]')).to_have_count(1)
    page.get_by_role("row").filter(has_text="客户生命周期").get_by_role("button", name="详情", exact=True).click()
    expect(page.get_by_role("heading", name="客户生命周期", exact=True)).to_be_visible()
    page.go_back()
    expect(page).to_have_url(re.compile(r"/api/flows$"))
    expect(detail_tab(page, "flows")).to_have_count(0)


def check_interfaces(page, fixture, output):
    navigate(page, "/api/interfaces?project_id=1&module_id=21")
    row = page.get_by_role("row").filter(has_text="新增客户")
    expect(row).to_be_visible()
    row.get_by_role("button", name="详情", exact=True).click()
    expect(page.locator(".detail-breadcrumb strong")).to_have_text("新增客户")
    page.get_by_role("tab", name=re.compile("请求参数")).click()
    page.get_by_role("button", name="新增参数", exact=True).click()
    expect(page.get_by_role("dialog")).to_be_visible()
    navigate(page, "/api/interfaces/11?project_id=1&module_id=21")
    expect(page.locator(".detail-breadcrumb strong")).to_have_text("查询客户")
    expect(page.locator(".api-identity code")).to_have_text("/customers/detail")
    expect(page.get_by_role("dialog")).to_have_count(0)
    expect(page.get_by_role("tab", name=re.compile("正式用例"))).to_have_attribute("aria-selected", "true")
    expect(detail_tab(page, "interfaces")).to_have_count(1)
    assert fixture.requests["/api-testing/interfaces/11"] == 1
    page.screenshot(path=str(output / "api-detail-desktop.png"), animations="disabled")
    page.set_viewport_size({"width": 390, "height": 900})
    expect(detail_tab(page, "interfaces")).to_have_count(1)
    page.screenshot(path=str(output / "api-detail-mobile.png"), animations="disabled")
    page.get_by_role("button", name="返回 API 列表", exact=True).click()
    expect(page).to_have_url(re.compile(r"/api/interfaces\?project_id=1&module_id=21$"))
    expect(detail_tab(page, "interfaces")).to_have_count(0)
    expect(page.locator('.page-tab[data-tab-key="/api/interfaces/:module"]')).to_have_count(1)
    page.set_viewport_size({"width": 1440, "height": 960})


def check_stored_tabs(browser, url, output):
    legacy = [
        {"key": path, "path": path, "title": path, "closable": True}
        for path in ["/api/flows/1", "/api/flows/2", "/api/interfaces/10", "/api/interfaces/11",
                     "/api/interfaces?project_id=1&module_id=21", "/api/interfaces?project_id=1&module_id=22"]
    ]
    context, page, fixture, errors = create_page(browser, legacy)
    page.goto(url + "/api/flows/2")
    expect(page.get_by_role("heading", name="销售订单流程", exact=True)).to_be_visible()
    expect(page.locator(".page-tab")).to_have_count(3)
    expect(detail_tab(page, "flows")).to_have_count(1)
    expect(detail_tab(page, "interfaces")).to_have_count(1)
    assert next(tab for tab in stored_tabs(page) if tab["key"] == "/api/interfaces/:detail")["path"] == "/api/interfaces/11"
    page.locator(".flow-back-link").click()
    expect(page.get_by_text("客户生命周期", exact=True)).to_be_visible()
    expect(page.locator(".page-tab")).to_have_count(3)
    expect(detail_tab(page, "flows")).to_have_count(0)
    page.get_by_role("tab", name="/api/interfaces/11", exact=True).click()
    expect(page.locator(".detail-breadcrumb strong")).to_have_text("查询客户")
    page.get_by_role("button", name="返回 API 列表", exact=True).click()
    expect(page.locator(".page-tab")).to_have_count(2)
    expect(detail_tab(page, "interfaces")).to_have_count(0)
    page.screenshot(path=str(output / "restored-tabs-desktop.png"), animations="disabled")
    assert not errors, errors
    assert not fixture.writes, fixture.writes
    assert not fixture.unexpected, fixture.unexpected
    context.close()


def create_page(browser, tabs=None):
    context = browser.new_context(viewport={"width": 1440, "height": 960})
    context.add_init_script("sessionStorage.setItem('autotest.session./access_token','navigation-ui-check')")
    if tabs:
        context.add_init_script(f"sessionStorage.setItem('autotest.session./opened_page_tabs', {json.dumps(json.dumps(tabs))})")
    fixture = NavigationFixture()
    context.route("**/api/v1/**", fixture.intercept)
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    return context, page, fixture, errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:5173")
    parser.add_argument("--output", default="frontend/node_modules/.cache/ui-checks/api-detail-navigation")
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context, page, fixture, errors = create_page(browser)
        page.goto(args.url + "/api/flows")
        check_flows(page, fixture, output)
        check_interfaces(page, fixture, output)
        assert not errors, errors
        assert not fixture.writes, fixture.writes
        assert not fixture.unexpected, fixture.unexpected
        assert len(context.pages) == 1
        context.close()
        check_stored_tabs(browser, args.url, output)
        browser.close()
    print("PASS: reused API/flow detail tabs, refreshed record state, guarded unsaved edits, reused parent tabs, browser back, and migrated stored tabs")


if __name__ == "__main__":
    main()
