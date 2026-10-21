"""Check singleton page tabs against mocked APIs without changing business data."""

import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlparse

from check_api_detail_navigation_ui import NavigationFixture, navigate, stored_tabs
from playwright.sync_api import expect, sync_playwright


class PageFixture(NavigationFixture):
    def intercept(self, route):
        endpoint = urlparse(route.request.url).path.removeprefix("/api/v1")
        if route.request.method != "GET":
            return super().intercept(route)
        data = self.page_data(endpoint)
        if data is None:
            return super().intercept(route)
        self.requests[endpoint] += 1
        route.fulfill(json={"code": 0, "message": "success", "data": data})

    def page_data(self, endpoint):
        if endpoint in ("/app-testing/devices/options", "/system/model-configs/options"):
            return []
        if endpoint in ("/agent/nodes", "/api-testing/interfaces/modules", "/web-testing/features/options"):
            return self.page([])
        if match := re.fullmatch(r"/api-testing/interfaces/modules/(\d+)", endpoint):
            return {"id": int(match[1]), "name": f"Module {match[1]}", "project_id": 1, "data": {}}
        if match := re.fullmatch(r"/web-testing/page-groups/(\d+)(/features)?", endpoint):
            page_id = int(match[1])
            return self.page([]) if match[2] else self.web_page(page_id)
        if match := re.fullmatch(r"/web-testing/features/(\d+)", endpoint):
            feature_id = int(match[1])
            return {"feature": {"id": feature_id, "name": f"Web feature {feature_id}",
                                "project_id": 1, "status": "active", "data": {"feature_type": "add"}},
                    "page": self.web_page(10 if feature_id == 101 else 20), "parameters": [],
                    "candidate": None, "screenshots": [], "versions": [], "cases": [],
                    "interfaces": [], "legacy_drafts": []}
        if match := re.fullmatch(r"/app-testing/features/(\d+)(/scenarios)?", endpoint):
            feature_id = int(match[1])
            return self.page([]) if match[2] else {"id": feature_id, "name": f"App feature {feature_id}",
                                                  "project_id": 1, "status": "active", "data": {}}
        if endpoint == "/app-testing/features":
            return self.page([])
        if match := re.fullmatch(r"/app-testing/scenarios/(\d+)(/runs)?", endpoint):
            scenario_id = int(match[1])
            return self.page([]) if match[2] else {"id": scenario_id, "name": f"App scenario {scenario_id}",
                                                   "project_id": 1, "status": "active", "data": {}}
        if match := re.fullmatch(r"/execution/plans/(\d+)/detail", endpoint):
            plan_id = int(match[1])
            return {"plan": {"id": plan_id, "name": f"Plan {plan_id}", "project_id": 1,
                             "api_count": 0, "web_feature_count": 0, "api_ids": [], "web_feature_ids": [],
                             "test_rounds": 1, "status": "active"},
                    "summary": {"case_count": 0, "run_count": 0}, "groups": [], "runs": []}
        if endpoint == "/execution/plans":
            return self.page([])
        return None

    @staticmethod
    def web_page(page_id):
        return {"id": page_id, "name": f"Web page {page_id}", "project_id": 1,
                "status": "active", "data": {"route": f"/customers/{page_id}"}}


def tab(page, key):
    return page.locator(f'.page-tab[data-tab-key="{key}"]')


def create_page(browser, viewport=None, legacy=None):
    context = browser.new_context(viewport=viewport or {"width": 1440, "height": 960})
    context.add_init_script("sessionStorage.setItem('autotest.session./access_token','page-tabs-ui-check')")
    if legacy:
        context.add_init_script(
            f"sessionStorage.setItem('autotest.session./opened_page_tabs', {json.dumps(json.dumps(legacy))})"
        )
    fixture = PageFixture()
    context.route("**/api/v1/**", fixture.intercept)
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    return context, page, fixture, errors


def check_details(page, fixture, output):
    pairs = [
        ("/web/pages/10", "/web/pages/20", "Web page 20", "/web/pages/:detail"),
        ("/web/pages/10/features/101", "/web/pages/20/features/202", "Web feature 202", "/web/features/:detail"),
        ("/app/features/10", "/app/features/20", "App feature 20", "/app/features/:detail"),
        ("/app/features/10/scenarios/101", "/app/features/20/scenarios/202", "App scenario 202",
         "/app/features/:detail/scenarios/:detail"),
        ("/execution/plans/10", "/execution/plans/20", "Plan 20", "/execution/plans/:detail")
    ]
    for first, second, title, key in pairs:
        navigate(page, first)
        expect(tab(page, key)).to_have_count(1)
        index = next(i for i, item in enumerate(stored_tabs(page)) if item["key"] == key)
        count = page.locator(".page-tab").count()
        if key == "/app/features/:detail":
            page.get_by_role("button", name="开始操作生成脚本", exact=True).click()
            expect(page.get_by_role("dialog")).to_be_visible()
        navigate(page, second)
        expect(page.get_by_role("heading", name=title, exact=True)).to_be_visible()
        expect(tab(page, key)).to_have_count(1)
        expect(page.locator(".page-tab")).to_have_count(count)
        expect(page.get_by_role("dialog")).to_have_count(0)
        expect(page.locator(".form-error:visible, [role=alert]:visible")).to_have_count(0)
        assert stored_tabs(page)[index]["path"] == second
        if key == "/execution/plans/:detail":
            assert fixture.requests["/execution/plans/20/detail"] == 1
        elif key == "/app/features/:detail":
            assert fixture.requests["/app-testing/features/20"] == 1
        elif key.endswith("scenarios/:detail"):
            assert fixture.requests["/app-testing/scenarios/202"] == 1
    page.screenshot(path=str(output / "plan-singleton-desktop.png"), animations="disabled")
    page.get_by_role("button", name="返回", exact=True).click()
    expect(page).to_have_url(re.compile(r"/execution/plans$"))
    expect(tab(page, "/execution/plans/:detail")).to_have_count(0)
    expect(tab(page, "/execution/plans")).to_have_count(1)


def check_module_lists(page):
    navigate(page, "/api/interfaces?project_id=1&module_id=21")
    expect(page.get_by_role("navigation", name="API 模块层级").locator("strong")).to_have_text("Module 21")
    count = page.locator(".page-tab").count()
    navigate(page, "/api/interfaces?project_id=1&module_id=22")
    expect(page.get_by_role("navigation", name="API 模块层级").locator("strong")).to_have_text("Module 22")
    expect(tab(page, "/api/interfaces/:module")).to_have_count(1)
    expect(page.locator(".page-tab")).to_have_count(count)
    assert next(item for item in stored_tabs(page) if item["key"] == "/api/interfaces/:module")["path"].endswith("module_id=22")


def check_web_alias_and_back(page, output):
    navigate(page, "/web/features/101")
    expect(page.get_by_role("heading", name="Web feature 101", exact=True)).to_be_visible()
    navigate(page, "/web/pages/20/features/202")
    expect(page.get_by_role("heading", name="Web feature 202", exact=True)).to_be_visible()
    expect(tab(page, "/web/features/:detail")).to_have_count(1)
    page.get_by_role("button", name="返回页面功能", exact=True).click()
    expect(page).to_have_url(re.compile(r"/web/pages/20$"))
    expect(tab(page, "/web/features/:detail")).to_have_count(0)
    expect(tab(page, "/web/pages/:detail")).to_have_count(1)
    navigate(page, "/web/pages/10")
    navigate(page, "/web/pages/20")
    page.go_back()
    expect(page.get_by_role("heading", name="Web page 10", exact=True)).to_be_visible()
    expect(tab(page, "/web/pages/:detail")).to_have_count(1)
    assert next(item for item in stored_tabs(page) if item["key"] == "/web/pages/:detail")["path"] == "/web/pages/10"
    page.go_forward()
    expect(page.get_by_role("heading", name="Web page 20", exact=True)).to_be_visible()
    page.set_viewport_size({"width": 390, "height": 900})
    expect(tab(page, "/web/pages/:detail")).to_be_visible()
    page.locator(".page-tabs-menu summary").click()
    panel = page.locator(".page-tabs-menu-panel")
    expect(panel).to_be_visible()
    bounds = panel.bounding_box()
    assert bounds and bounds["x"] >= 0 and bounds["x"] + bounds["width"] <= 390, bounds
    page.screenshot(path=str(output / "singleton-tabs-mobile.png"), animations="disabled")
    page.get_by_role("button", name="关闭其他", exact=True).click()
    expect(page.locator(".page-tab")).to_have_count(1)
    page.reload()
    expect(page.get_by_role("heading", name="Web page 20", exact=True)).to_be_visible()
    expect(page.locator(".page-tab")).to_have_count(1)


def check_stored_migration(browser, url):
    paths = ["/web/pages/10", "/web/pages/20", "/web/features/101", "/web/pages/20/features/202",
             "/app/features/10", "/app/features/20", "/app/features/10/scenarios/101",
             "/app/features/20/scenarios/202", "/execution/plans/10", "/execution/plans/20",
             "/api/interfaces?module_id=21&project_id=1", "/api/interfaces?module_id=22&project_id=2",
             "/system/users?keyword=old", "/system/users?keyword=new", "/web/cases"]
    legacy = [{"key": path, "path": path, "title": path, "closable": True} for path in paths]
    context, page, fixture, errors = create_page(browser, legacy=legacy)
    page.goto(url + "/web/pages/20")
    expect(page.get_by_role("heading", name="Web page 20", exact=True)).to_be_visible()
    expect(page.locator(".page-tab")).to_have_count(7)
    values = stored_tabs(page)
    assert [item["path"] for item in values] == paths[1:12:2] + [paths[13]]
    assert len({item["key"] for item in values}) == 7
    assert not errors and not fixture.writes and not fixture.unexpected, (errors, fixture.writes, fixture.unexpected)
    context.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:5173")
    parser.add_argument("--output", default="frontend/node_modules/.cache/ui-checks/page-tabs")
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        harness = browser.new_page()
        harness.goto(args.url + "/tests/page-tabs.html")
        harness.wait_for_function("typeof window.runPageTabChecks === 'function'")
        result = harness.evaluate("window.runPageTabChecks()")
        assert result["passed"] and result["routes"] >= 30, result
        harness.close()
        context, page, fixture, errors = create_page(browser)
        page.goto(args.url + "/web/pages/10")
        expect(page.get_by_role("heading", name="Web page 10", exact=True)).to_be_visible()
        check_details(page, fixture, output)
        check_module_lists(page)
        check_web_alias_and_back(page, output)
        assert not errors and not fixture.writes and not fixture.unexpected, (errors, fixture.writes, fixture.unexpected)
        assert len(context.pages) == 1
        context.close()
        check_stored_migration(browser, args.url)
        browser.close()
    print(f"PASS: {result['routes']} page routes, 4 store check groups, Web/App/plan detail refresh, aliases, back/forward, mobile, reload and stored-tab migration")


if __name__ == "__main__":
    main()
