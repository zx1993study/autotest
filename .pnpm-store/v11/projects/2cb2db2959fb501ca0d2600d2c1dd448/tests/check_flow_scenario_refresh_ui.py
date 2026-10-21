"""Exercise external scenario additions and node labels with mocked APIs only."""

import argparse
import re
from copy import deepcopy
from pathlib import Path
from urllib.parse import urlparse

from check_api_detail_navigation_ui import NavigationFixture
from playwright.sync_api import expect, sync_playwright


class ScenarioFixture(NavigationFixture):
    def __init__(self):
        super().__init__()
        self.scenes = [self.scene(number) for number in range(10)]
        self.saved = []

    @staticmethod
    def scene(number):
        return {"id": 100 + number, "name": f"Scenario {number}", "status": "active", "project_id": 1,
                "data": {"flow_id": 1, "template_version": 1, "inputs": {}, "failure_policy": "stop",
                         "expected_end": "auto", "nodes": {}}}

    def intercept(self, route):
        endpoint = urlparse(route.request.url).path.removeprefix("/api/v1")
        if route.request.method == "PUT" and endpoint.startswith("/execution/flows/1/scenarios/"):
            number = int(endpoint.rsplit("/", 1)[1])
            payload = route.request.post_data_json
            self.saved.append(payload)
            current = next(scene for scene in self.scenes if scene["id"] == number)
            current.update(deepcopy(payload))
            route.fulfill(json={"code": 0, "message": "success", "data": current})
            return
        return super().intercept(route)


def check_refresh(page, fixture):
    expect(page.locator(".flow-table-wrap tbody tr")).to_have_count(10)
    assert fixture.requests["/execution/flows/1/scenarios"] == 1
    fixture.scenes.extend(fixture.scene(number) for number in range(10, 15))
    page.get_by_role("button", name=re.compile("功能场景")).click()
    expect(page.locator(".flow-table-wrap tbody tr")).to_have_count(15)
    assert fixture.requests["/execution/flows/1"] == 1
    fixture.scenes.append(fixture.scene(15))
    page.evaluate("window.dispatchEvent(new Event('focus'))")
    expect(page.get_by_text("Scenario 15", exact=True)).to_be_visible()
    page.get_by_role("button", name="流程模板", exact=True).click()
    page.get_by_label("节点名称", exact=True).fill("Unsubmitted business step")
    count = fixture.requests["/execution/flows/1/scenarios"]
    page.evaluate("window.dispatchEvent(new Event('focus'))")
    page.get_by_role("button", name=re.compile("功能场景")).click()
    assert fixture.requests["/execution/flows/1/scenarios"] == count
    page.get_by_role("button", name="流程模板", exact=True).click()
    expect(page.get_by_label("节点名称", exact=True)).to_have_value("Unsubmitted business step")
    page.get_by_label("节点名称", exact=True).fill("新增客户")
    page.get_by_role("button", name=re.compile("功能场景")).click()
    expect(page.locator(".flow-table-wrap tbody tr")).to_have_count(16)
    fixture.flow["data"]["version"] = 2
    for scene in fixture.scenes:
        scene["data"]["template_version"] = 2
    page.evaluate("window.dispatchEvent(new Event('focus'))")
    expect(page.locator(".flow-page-header")).to_contain_text("模板 v2")
    expect(page.get_by_text("v2 · 待同步", exact=True)).to_have_count(0)


def check_node_labels(page, fixture):
    page.get_by_role("row").filter(has_text="Scenario 15").get_by_role("button", name="配置", exact=True).click()
    dialog = page.get_by_role("dialog", name="功能场景配置")
    dialog.get_by_label("节点名称", exact=True).fill("创建早会-类型：周会")
    expect(dialog.locator(".flow-node-rail")).to_contain_text("创建早会-类型：周会")
    count = fixture.requests["/execution/flows/1/scenarios"]
    page.evaluate("window.dispatchEvent(new Event('focus'))")
    assert fixture.requests["/execution/flows/1/scenarios"] == count
    dialog.get_by_role("button", name="保存场景", exact=True).click()
    expect(dialog).to_have_count(0)
    assert fixture.saved[-1]["data"]["nodes"]["create"]["name"] == "创建早会-类型：周会"
    page.get_by_role("row").filter(has_text="Scenario 15").get_by_role("button", name="配置", exact=True).click()
    expect(dialog.get_by_label("节点名称", exact=True)).to_have_value("创建早会-类型：周会")
    dialog.get_by_label("节点名称", exact=True).fill("")
    dialog.get_by_role("button", name="保存场景", exact=True).click()
    expect(dialog).to_have_count(0)
    assert fixture.saved[-1]["data"]["nodes"]["create"]["name"] is None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:5173")
    args = parser.parse_args()
    output = Path("frontend/node_modules/.cache/ui-checks/flow-scenes")
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(viewport={"width": 1440, "height": 960})
        context.add_init_script("sessionStorage.setItem('autotest.session./access_token','scenario-ui-check')")
        fixture = ScenarioFixture()
        context.route("**/api/v1/**", fixture.intercept)
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(args.url + "/api/flows/1")
        check_refresh(page, fixture)
        check_node_labels(page, fixture)
        page.screenshot(path=str(output / "scenes-desktop.png"), animations="disabled")
        page.set_viewport_size({"width": 390, "height": 900})
        page.get_by_role("row").filter(has_text="Scenario 15").get_by_role("button", name="配置", exact=True).click()
        expect(page.get_by_role("dialog")).to_be_visible()
        page.screenshot(path=str(output / "scene-node-mobile.png"), animations="disabled")
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        assert not fixture.writes and not fixture.unexpected and not errors, (fixture.writes, fixture.unexpected, errors)
        browser.close()
    print("PASS: scenario refresh, dirty draft protection, node naming, mobile layout; mocked writes only")


if __name__ == "__main__":
    main()
