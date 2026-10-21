from urllib.parse import parse_qs, urlsplit

from playwright.async_api import expect

from pages.base_page import BasePage


class ListPage(BasePage):
    async def query(self, inputs):
        if not inputs:
            await self.submit_query({})
            return
        fields = {field["key"]: field for field in self.definition["search_fields"]}
        if len(inputs) != 1:
            raise ValueError("This legacy case adapter supports one source-confirmed text condition")
        key, value = next(iter(inputs.items()))
        field = fields.get(key)
        if not field or field.get("type", "input") != "input":
            raise ValueError("Input must target a source-confirmed text search field")
        steps = self.definition["candidate"]["steps"]
        for original in steps[1:3]:
            step = dict(original)
            if step.get("value") == "{{" + key + "}}":
                step["value"] = value
            await self.engine.execute(step)
        rows = await self.submit_query({field.get("queryKey", key): value})
        if not rows:
            raise AssertionError("No fixture matched; an empty result cannot prove filtering works")
        if any(str(value).casefold() not in str(row.get(field.get("tableKey", key), "")).casefold() for row in rows):
            raise AssertionError("Returned rows do not satisfy the text search condition")
        await self.reset_query(key)

    async def reset_query(self, key):
        endpoint = self.definition["list_api"][0]["url"]
        async with self.page.expect_response(lambda response: self.is_list(response, endpoint)) as pending:
            await self.page.locator('.unified-list__actions button:has-text("重置"):visible').click()
        response = await pending.value
        values = parse_qs(urlsplit(response.url).query)
        if values.get(key, [""])[0]:
            raise AssertionError("Reset left the previous condition in the request")
        await self.validate_list_response(response)

    def is_list(self, response, endpoint):
        return (response.request.method == "GET"
                and urlsplit(response.url).path == "/dev-api/" + endpoint.lstrip("/"))

    async def submit_query(self, inputs):
        endpoint = self.definition["list_api"][0]["url"]
        async with self.page.expect_response(lambda response: self.is_list(response, endpoint)) as pending:
            await self.page.locator('.unified-list__actions button:has-text("查询"):visible').click()
        response = await pending.value
        values = parse_qs(urlsplit(response.url).query)
        if any(values.get(key, [None])[0] != str(value) for key, value in inputs.items()):
            raise AssertionError("The UI did not send the expected query parameters")
        return await self.validate_list_response(response)

    async def validate_list_response(self, response):
        if response.status != 200:
            raise AssertionError(f"List query HTTP status {response.status}")
        body = await response.json()
        if not isinstance(body, dict) or body.get("code") != 200 or not isinstance(body.get("rows"), list):
            raise AssertionError("List query did not return code=200 and rows[]")
        await expect(self.page.locator(".app-main .el-table:visible")).to_be_visible()
        await expect(self.page.locator(".app-main .el-loading-mask:visible")).to_have_count(0)
        return body["rows"]


async def execute(config, feature, case=None, inputs=None):
    if feature.get("status") != "source_ready" or (case and case.get("status") != "source_ready"):
        raise ValueError("Definition is blocked; consult generation-report.md")
    definition = {**feature, **(case or {})}
    async with ListPage(config, definition) as page:
        await page.open()
        if feature["feature_type"] == "query":
            await page.query(inputs if inputs is not None else (case or {}).get("input_info", {}))
        await expect(page.page.locator(".app-main .el-loading-mask:visible")).to_have_count(0)
        await page.settle_business_requests()
        await page.assert_clean_network()
    return {"status": "passed", "scope": "query_filter" if case else "page_list_smoke",
            "case_id": (case or {}).get("case_id"), "feature_id": feature["feature_id"],
            "business_writes": 0, "ai_calls": 0}
