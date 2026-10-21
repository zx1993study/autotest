"""Exercise the template node rail with mock APIs and no live writes."""

import argparse
import asyncio
from pathlib import Path
from urllib.parse import urlparse

from playwright.async_api import async_playwright, expect


class FlowFixture:
    def __init__(self, count=60):
        self.flow = {"id": 1, "name": "Template scrolling", "project_id": 10, "status": "active", "description": "",
                     "data": {"version": 1, "inputs": {"tenant": "demo"}, "nodes": [
                         {"key": f"node_{key}", "name": f"Step {key}", "api_id": 11, "case_id": 101, "auth_id": None,
                          "params": {}, "request": {}, "bindings": [], "extracts": [], "routes": [], "next": "auto"}
                         for key in range(1, count + 1)]}}
        if count >= 30:
            self.flow["data"]["nodes"][29]["name"] = "A long node name with a long API path that must wrap without horizontal page overflow"
        self.saved = []
        self.unexpected = []

    async def intercept(self, route):
        request = route.request
        endpoint = urlparse(request.url).path.removeprefix("/api/v1")
        if request.method == "PUT" and endpoint == "/execution/flows/1":
            payload = request.post_data_json
            self.saved.append(payload)
            self.flow["data"] = {**payload["data"], "version": payload["data"]["version"] + 1}
            data = self.flow
        elif request.method != "GET":
            self.unexpected.append((request.method, endpoint))
            await route.fulfill(status=405, json={"code": 405, "message": "Blocked test write"})
            return
        elif endpoint == "/auth/me":
            data = {"id": 1, "username": "ui-check", "display_name": "UI check", "role": "admin"}
        elif endpoint == "/execution/flows/1":
            data = self.flow
        elif endpoint in ("/execution/flows/1/scenarios", "/execution/flows/1/runs", "/project-auth/options"):
            data = []
        elif endpoint == "/api-testing/interfaces/options":
            data = [{"id": 11, "name": "Example API", "method": "POST", "path": "/example/long-path/for-scroll-layout-test"}]
        elif endpoint == "/api-testing/cases":
            data = {"items": [{"id": 101, "name": "Example case"}], "total": 1, "page": 1, "pageSize": 200}
        elif endpoint == "/api-testing/cases/101":
            data = {"id": 101, "name": "Example case", "data": {"params": {"body": {"name": "example"}}}}
        else:
            self.unexpected.append((request.method, endpoint))
            data = None
        await route.fulfill(json={"code": 0, "message": "success", "data": data})


async def assert_active_visible(page, horizontal=False):
    await page.wait_for_function("""horizontal => {
      const area = document.querySelector('.flow-template-rail');
      const item = area?.querySelector('.flow-rail-item.active');
      if (!area || !item) return false;
      const a = area.getBoundingClientRect(), b = item.getBoundingClientRect();
      return horizontal ? b.left >= a.left - 1 && b.right <= a.right + 1
        : b.top >= a.top - 1 && b.bottom <= a.bottom + 1;
    }""", arg=horizontal)


async def open_template(browser, url, fixture, viewport):
    context = await browser.new_context(viewport=viewport)
    await context.add_init_script("sessionStorage.setItem('autotest.session./access_token','flow-scroll-ui-check')")
    await context.route("**/api/v1/**", fixture.intercept)
    page = await context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    await page.goto(url + "/api/flows/1")
    await page.get_by_role("button", name="流程模板", exact=True).click()
    await expect(page.get_by_label("节点名称", exact=True)).to_be_visible()
    return context, page, errors


async def check_desktop(browser, url, output):
    fixture = FlowFixture()
    context, page, errors = await open_template(browser, url, fixture, {"width": 1440, "height": 900})
    rail = page.get_by_role("region", name="流程节点", exact=True)
    await expect(rail).to_have_attribute("data-orientation", "vertical")
    await page.wait_for_function("""() => {
      const area = document.querySelector('.flow-template-rail');
      return area.scrollHeight > area.clientHeight && area.getBoundingClientRect().bottom <= innerHeight - 15;
    }""")
    initial_y = await page.evaluate("window.scrollY")
    editor_y = (await page.locator(".flow-template-layout > .flow-node-editor").bounding_box())["y"]
    await rail.hover()
    await page.mouse.wheel(0, 900)
    await page.wait_for_function("document.querySelector('.flow-template-rail').scrollTop > 500")
    assert await page.evaluate("window.scrollY") == initial_y
    assert (await page.locator(".flow-template-layout > .flow-node-editor").bounding_box())["y"] == editor_y
    scroll_before = await rail.evaluate("element => element.scrollTop")
    await page.get_by_role("button", name="功能场景", exact=False).click()
    await page.get_by_role("button", name="流程模板", exact=True).click()
    await expect(rail).to_be_visible()
    assert abs(await rail.evaluate("element => element.scrollTop") - scroll_before) < 2
    await rail.evaluate("element => { element.scrollTop = 0 }")
    selected = rail.locator('.flow-node-label[aria-pressed="true"]')
    await selected.focus()
    request_json = page.get_by_role("textbox", name="参数覆盖 JSON", exact=True)
    await request_json.fill('{"body":')
    await expect(page.get_by_role("button", name="保存模板", exact=True)).to_be_disabled()
    await selected.press("End")
    await expect(page.get_by_label("节点名称", exact=True)).to_have_value("Step 60")
    await assert_active_visible(page)
    assert await page.evaluate("window.scrollY") == initial_y
    await selected.press("Home")
    await expect(request_json).to_have_value('{"body":')
    await request_json.fill('{"body":{"name":"updated"}}')
    await page.get_by_role("button", name="新增节点", exact=True).click()
    await expect(page.get_by_label("节点名称", exact=True)).to_have_value("Example API")
    await assert_active_visible(page)
    await rail.locator(".flow-rail-item.active").get_by_role("button", name="上移节点", exact=True).click()
    await expect(rail.locator(".flow-rail-item").nth(59)).to_have_class("flow-rail-item active")
    await assert_active_visible(page)
    page.on("dialog", lambda dialog: dialog.accept())
    await rail.locator(".flow-rail-item.active").get_by_role("button", name="删除节点", exact=True).click()
    await expect(page.get_by_label("节点名称", exact=True)).to_have_value("Step 60")
    await assert_active_visible(page)
    await rail.locator(".flow-rail-item.active").get_by_role("button", name="删除节点", exact=True).click()
    await expect(page.get_by_label("节点名称", exact=True)).to_have_value("Step 59")
    await assert_active_visible(page)
    await page.set_viewport_size({"width": 1280, "height": 650})
    await assert_active_visible(page)
    await page.get_by_text("流程默认输入", exact=True).click()
    await page.wait_for_function("document.querySelector('.flow-template-rail').getBoundingClientRect().bottom <= innerHeight - 15")
    await assert_active_visible(page)
    assert await page.evaluate("window.scrollY") == initial_y
    await page.screenshot(path=str(output / "template-scroll-short.png"), animations="disabled")
    await page.get_by_role("button", name="保存模板", exact=True).click()
    await expect(page.get_by_text("模板已保存", exact=True)).to_be_visible()
    assert len(fixture.saved) == 1 and len(fixture.saved[0]["data"]["nodes"]) == 59
    assert fixture.saved[0]["data"]["nodes"][0]["request"]["body"]["name"] == "updated"
    await page.set_viewport_size({"width": 1440, "height": 900})
    await assert_active_visible(page)
    await page.screenshot(path=str(output / "template-scroll-desktop.png"), animations="disabled")
    assert not errors and not fixture.unexpected, (errors, fixture.unexpected)
    await context.close()


async def check_mobile_and_empty(browser, url, output):
    fixture = FlowFixture(30)
    context, page, errors = await open_template(browser, url, fixture, {"width": 390, "height": 844})
    rail = page.get_by_role("region", name="流程节点", exact=True)
    await expect(rail).to_have_attribute("data-orientation", "horizontal")
    await rail.locator('.flow-node-label[aria-pressed="true"]').press("End")
    await assert_active_visible(page, horizontal=True)
    assert await rail.evaluate("element => element.scrollHeight <= element.clientHeight + 1")
    assert (await rail.locator(".flow-rail-item.active").bounding_box())["height"] < 160
    assert "A long node name" in await rail.locator(".flow-rail-item.active .flow-node-label").get_attribute("title")
    assert await page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
    await page.screenshot(path=str(output / "template-scroll-mobile.png"), animations="disabled")
    assert not errors and not fixture.unexpected, (errors, fixture.unexpected)
    await context.close()
    fixture = FlowFixture(1)
    context, page, errors = await open_template(browser, url, fixture, {"width": 1440, "height": 900})
    page.on("dialog", lambda dialog: dialog.accept())
    await page.get_by_role("button", name="删除节点", exact=True).click()
    await expect(page.get_by_text("暂无流程节点", exact=True)).to_be_visible()
    await page.get_by_role("button", name="新增节点", exact=True).click()
    await expect(page.get_by_label("节点名称", exact=True)).to_have_value("Example API")
    await assert_active_visible(page)
    assert not errors and not fixture.unexpected, (errors, fixture.unexpected)
    await context.close()


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:5173")
    parser.add_argument("--output", default="frontend/node_modules/.cache/ui-checks/flow-template-scroll")
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(ignore_default_args=["--hide-scrollbars"])
        await check_desktop(browser, args.url, output)
        await check_mobile_and_empty(browser, args.url, output)
        await browser.close()
    print("PASS: viewport rail, isolated wheel, tab position, keyboard, add/reorder/delete, drafts, save, resize, mobile, empty state")


if __name__ == "__main__":
    asyncio.run(main())
