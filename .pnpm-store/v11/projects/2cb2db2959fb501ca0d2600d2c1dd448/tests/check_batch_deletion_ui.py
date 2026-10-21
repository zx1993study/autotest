"""Verify deletion UX with intercepted APIs; never mutate a live database."""

import argparse
import asyncio
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from playwright.async_api import async_playwright, expect


class DeletionFixture:
    def __init__(self, endpoint):
        self.endpoint = endpoint
        self.rows = [{"id": key, "name": f"Item {key}", "project_id": 10, "status": "success", "data": {},
                      "api_count": 1, "web_feature_count": 0, "created_at": "2026-01-01T00:00:00"}
                     for key in range(1, 22)]
        self.queries = []
        self.deletions = []
        self.pending = None
        self.unexpected = []

    async def intercept(self, route):
        request = route.request
        parsed = urlparse(request.url)
        endpoint = parsed.path.removeprefix("/api/v1")
        if request.method == "POST" and endpoint == self.endpoint + "/batch-delete":
            self.deletions.append(request.post_data_json["ids"])
            self.pending = route
            return
        if request.method == "DELETE" and endpoint.startswith(self.endpoint + "/"):
            self.deletions.append([int(endpoint.rsplit("/", 1)[1])])
            self.pending = route
            return
        if request.method != "GET":
            self.unexpected.append((request.method, endpoint))
            await route.fulfill(status=405, json={"code": 405, "message": "Blocked UI check write"})
            return
        if endpoint == "/auth/me":
            data = {"id": 1, "username": "ui-check", "display_name": "UI check", "role": "admin"}
        elif endpoint == "/projects/options":
            data = [{"id": 10, "name": "Test project", "is_default": True}]
        elif endpoint == self.endpoint:
            query = {key: values[0] for key, values in parse_qs(parsed.query).items()}
            self.queries.append(query)
            page, size = int(query.get("page", 1)), int(query.get("pageSize", 20))
            data = {"items": self.rows[(page - 1) * size:page * size], "total": len(self.rows), "page": page, "pageSize": size}
        else:
            self.unexpected.append((request.method, endpoint))
            data = None
        await route.fulfill(json={"code": 0, "message": "success", "data": data})

    async def finish(self, fail=False):
        assert self.pending
        route, self.pending = self.pending, None
        if fail:
            await route.fulfill(status=409, json={"code": 409, "message": "Deletion is blocked"})
            return
        ids = set(self.deletions[-1])
        count = sum(row["id"] in ids for row in self.rows)
        self.rows = [row for row in self.rows if row["id"] not in ids]
        await route.fulfill(json={"code": 0, "message": "success", "data": {"deleted_count": count}})


async def check_page(browser, url, path, endpoint, output):
    context = await browser.new_context(viewport={"width": 1440, "height": 960})
    await context.add_init_script("sessionStorage.setItem('autotest.session./access_token','batch-deletion-ui-check')")
    fixture = DeletionFixture(endpoint)
    await context.route("**/api/v1/**", fixture.intercept)
    page = await context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    await page.goto(url + path)
    await expect(page.get_by_role("cell", name="Item 1", exact=True)).to_be_visible()
    await page.get_by_role("button", name="下一页", exact=True).click()
    await expect(page.get_by_role("cell", name="Item 21", exact=True)).to_be_visible()
    await page.locator('thead input[type="checkbox"]').check()
    batch_button = page.get_by_role("button", name="批量删除", exact=True)
    page.once("dialog", lambda dialog: dialog.dismiss())
    await batch_button.click()
    assert not fixture.deletions
    page.on("dialog", lambda dialog: dialog.accept())
    await batch_button.click()
    busy_button = page.get_by_role("button", name="删除中...", exact=True)
    await expect(busy_button).to_be_disabled()
    for _ in range(3):
        await busy_button.dispatch_event("click")
    assert fixture.deletions == [[21]], fixture.deletions
    await expect(page.locator(".table-wrap")).to_have_attribute("aria-busy", "true")
    await page.screenshot(path=str(output / f"{path.strip('/').replace('/', '-')}-busy.png"), animations="disabled")
    await fixture.finish()
    await expect(page.get_by_role("cell", name="Item 1", exact=True)).to_be_visible()
    assert fixture.queries[-1]["page"] == "1", fixture.queries
    await page.locator('tbody input[type="checkbox"]').first.check()
    await batch_button.click()
    await expect(busy_button).to_be_disabled()
    await fixture.finish(fail=True)
    await expect(page.get_by_text("Deletion is blocked", exact=True).last).to_be_visible()
    await expect(page.locator('tbody input[type="checkbox"]').first).to_be_checked()
    await expect(batch_button).to_be_enabled()
    await batch_button.click()
    await expect(busy_button).to_be_disabled()
    await fixture.finish()
    await expect(page.get_by_role("cell", name="Item 2", exact=True)).to_be_visible()
    await page.locator("tbody tr").first.get_by_role("button", name="删除", exact=True).click()
    await expect(busy_button).to_be_disabled()
    await fixture.finish()
    await expect(page.get_by_role("cell", name="Item 3", exact=True)).to_be_visible()
    assert fixture.deletions == [[21], [1], [1], [2]], fixture.deletions
    await page.screenshot(path=str(output / f"{path.strip('/').replace('/', '-')}-desktop.png"), animations="disabled")
    await page.set_viewport_size({"width": 390, "height": 900})
    await expect(batch_button).to_be_visible()
    bounds = await batch_button.bounding_box()
    assert bounds and 0 <= bounds["x"] and bounds["x"] + bounds["width"] <= 390, bounds
    await page.screenshot(path=str(output / f"{path.strip('/').replace('/', '-')}-mobile.png"), animations="disabled")
    assert not errors and not fixture.unexpected, (errors, fixture.unexpected)
    await context.close()


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:5173")
    parser.add_argument("--output", default="frontend/node_modules/.cache/ui-checks/batch-deletion")
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        for path, endpoint in (("/reports/records", "/reports/records"), ("/execution/plans", "/execution/plans")):
            await check_page(browser, args.url, path, endpoint, output)
        await browser.close()
    print("PASS: cancellation, one request, busy guard, rollback UX, retry, last-page fallback, single deletion, desktop/mobile")


if __name__ == "__main__":
    asyncio.run(main())
