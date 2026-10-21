import json
import os
import time
from pathlib import Path
from urllib.parse import urlsplit

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_catalog():
    data = json.loads((ROOT / "catalog.json").read_text(encoding="utf-8"))
    selected = set(filter(None, os.getenv("FW_CASE_IDS", "").split(",")))
    cases = [case for case in data["cases"] if case["automation"] == "scripted" and "h5" in case["platforms"]]
    if selected:
        known = {case["id"] for case in cases}
        if selected - known:
            raise pytest.UsageError("Unknown or non-scripted FW_CASE_IDS")
        cases = [case for case in cases if case["id"] in selected]
    return cases


def route_params(case):
    if not case["requires_fixture"]:
        return {}
    filename = os.getenv("FW_FIXTURES")
    if not filename:
        pytest.skip("Requires isolated batch fixtures; not executed")
    data = json.loads(Path(filename).read_text(encoding="utf-8-sig"))
    entry = data.get("pages", {}).get(case["route"], {})
    valid = data.get("approved_for_test") is True and entry.get("approved_for_test") is True
    valid = valid and data.get("batch_id") and entry.get("batch_id") == data["batch_id"]
    if not valid or not entry.get("params") or any(value == "" for value in entry["params"].values()):
        pytest.skip("Missing approved current-batch route parameters; not executed")
    return entry["params"]


class ReadOnlyGuard:
    def __init__(self):
        self.failures = []
        self.pending = set()
        self.changed = time.monotonic()

    def route(self, route):
        request = route.request
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            self.failures.append(f"Blocked write: {request.method} {urlsplit(request.url).path}")
            route.abort("blockedbyclient")
        else:
            route.continue_()

    def started(self, request):
        if request.resource_type in {"xhr", "fetch"}:
            self.pending.add(request)
            self.changed = time.monotonic()

    def completed(self, request):
        if request in self.pending:
            self.pending.discard(request)
            self.changed = time.monotonic()

    def failed(self, request):
        self.completed(request)
        if request.resource_type in {"xhr", "fetch"}:
            self.failures.append(f"Request failed: {request.method} {urlsplit(request.url).path}")

    def response(self, response):
        if response.request.resource_type not in {"xhr", "fetch"}:
            return
        path = urlsplit(response.url).path
        if response.status >= 400:
            self.failures.append(f"HTTP {response.status}: {path}")
        try:
            data = response.json()
            if isinstance(data, dict) and (data.get("success") is False or data.get("code", 200) not in {200, "200"}):
                self.failures.append(f"Business rejection: {path}")
        except (ValueError, TypeError):
            pass

    def settle(self, page):
        deadline = time.monotonic() + 10
        while (self.pending or time.monotonic() - self.changed < 0.5) and time.monotonic() < deadline:
            page.wait_for_timeout(100)
        assert not self.pending, "Read requests did not settle within 10 seconds"
        assert not self.failures, "\n".join(self.failures)


@pytest.fixture(scope="session")
def browser():
    if not os.getenv("FW_H5_BASE_URL"):
        pytest.skip("Set FW_H5_BASE_URL to FieldNovaMini H5 test deployment; not executed")
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        instance = playwright.chromium.launch(headless=os.getenv("FW_HEADED") != "1")
        yield instance
        instance.close()


@pytest.fixture
def guarded_page(browser, request):
    case = request.node.callspec.params["case"]
    state = os.getenv("FW_AUTH_STATE") if case["requires_auth"] else None
    if case["requires_auth"] and (not state or not Path(state).is_file()):
        pytest.skip("Requires locally saved browser login state; not executed")
    params = route_params(case)
    guard = ReadOnlyGuard()
    context = browser.new_context(storage_state=state, service_workers="block", viewport={"width": 390, "height": 844})
    context.route("**/*", guard.route)
    page = context.new_page()
    page.set_default_timeout(10000)
    page.on("request", guard.started)
    page.on("requestfinished", guard.completed)
    page.on("requestfailed", guard.failed)
    page.on("response", guard.response)
    try:
        yield page, params, guard
    finally:
        context.close()
