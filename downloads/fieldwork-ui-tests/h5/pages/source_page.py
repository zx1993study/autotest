import re
from urllib.parse import urlencode

from playwright.sync_api import expect


class SourcePage:
    def __init__(self, page, base_url):
        self.page = page
        self.base_url = base_url.rstrip("/")

    def open(self, route, params):
        query = "?" + urlencode(params) if params else ""
        self.page.goto(f"{self.base_url}/#/{route}{query}", wait_until="domcontentloaded")
        self.assert_route(route)

    def assert_route(self, route):
        expected = re.escape(f"{self.base_url}/#/{route}") + r"(?:\?.*)?$"
        expect(self.page).to_have_url(re.compile("^" + expected))

    def element(self, selector, editable=False):
        target = self.page.locator(selector)
        expect(target).to_have_count(1)
        if editable:
            tag = target.evaluate("element => element.tagName.toLowerCase()")
            if tag not in {"input", "textarea"}:
                target = target.locator("input, textarea")
                expect(target).to_have_count(1)
        return target

    def execute(self, operation):
        action = operation["action"]
        if action == "toast":
            expect(self.page.get_by_text(operation["text"], exact=True)).to_be_visible()
            return
        target = self.element(operation["selector"], editable=action in {"input", "password_mode"})
        if action == "visible":
            expect(target).to_be_visible()
        elif action == "input":
            target.fill(operation["value"])
        elif action == "click":
            target.click()
        elif action == "disabled":
            expect(target).to_be_disabled()
        elif action == "password_mode":
            expect(target).to_have_attribute("type", "password" if operation["masked"] else "text")
        else:
            raise ValueError(f"Unsupported operation: {action}")
