"""A deterministic, strictly read-only browser context. No AI calls or retries."""

import asyncio
from urllib.parse import urlsplit

from playwright.async_api import async_playwright
from web_automation.engines.playwright import PlaywrightEngine


class BasePage:
    def __init__(self, config, definition):
        self.config = config
        self.definition = definition
        self.denied_writes = []
        self.request_failures = []
        self.responses = []
        self.pending_requests = set()

    async def __aenter__(self):
        self.pw = await async_playwright().start()
        options = {"headless": not self.config.get("headed", False)}
        if self.config.get("browser_executable"):
            options["executable_path"] = self.config["browser_executable"]
        self.browser = None
        try:
            self.browser = await self.pw.chromium.launch(**options)
            context_options = {"service_workers": "block"}
            if self.config.get("storage_state"):
                context_options["storage_state"] = self.config["storage_state"]
            self.context = await self.browser.new_context(**context_options)
            if self.config.get("runtime_token"):
                origin = self.config["base_url"].rstrip("/")
                await self.context.add_cookies([{"name": "Admin-Token", "value": self.config["runtime_token"],
                                                "url": origin, "sameSite": "Lax"}])
            await self.context.route("**/*", self.guard_request)
            await self.context.route_web_socket("**/*", lambda socket: socket.close())
            self.page = await self.context.new_page()
            self.page.set_default_timeout(10000)
            self.page.on("response", lambda response: self.responses.append(response))
            self.page.on("request", self.record_request)
            self.page.on("requestfinished", lambda request: self.pending_requests.discard(request))
            self.page.on("requestfailed", self.record_failure)
            self.engine = PlaywrightEngine(self.page, default_timeout=10000)
            return self
        except BaseException:
            if self.browser:
                await self.browser.close()
            await self.pw.stop()
            raise

    async def guard_request(self, route):
        request = route.request
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            self.denied_writes.append({"method": request.method, "path": urlsplit(request.url).path})
            await route.abort()
            return
        await route.continue_()

    def record_failure(self, request):
        self.pending_requests.discard(request)
        if "/dev-api/" in urlsplit(request.url).path:
            self.request_failures.append({"method": request.method, "path": urlsplit(request.url).path})

    def record_request(self, request):
        if "/dev-api/" in urlsplit(request.url).path:
            self.pending_requests.add(request)

    async def settle_business_requests(self):
        async with asyncio.timeout(15):
            while self.pending_requests:
                await asyncio.sleep(0.05)

    async def open(self):
        target = self.config["base_url"].rstrip("/") + self.definition["route"]
        navigation = await self.page.goto(target, wait_until="domcontentloaded", timeout=45000)
        if navigation and navigation.status >= 400:
            raise AssertionError(f"Page navigation returned HTTP {navigation.status}")
        await self.engine.execute(self.definition["candidate"]["steps"][0])
        expected = urlsplit(target)
        actual = urlsplit(self.page.url)
        if actual.netloc != expected.netloc or actual.path.rstrip("/") != expected.path.rstrip("/"):
            raise AssertionError("Target route changed; login, permission or deployment mismatch")

    async def assert_clean_network(self):
        if self.denied_writes:
            raise AssertionError("Read-only page attempted a write; request blocked")
        if self.request_failures:
            raise AssertionError("One or more business API requests failed to complete")
        for response in self.responses:
            if "/dev-api/" not in urlsplit(response.url).path:
                continue
            if response.status >= 400:
                raise AssertionError(f"Business HTTP failure at {urlsplit(response.url).path}")
            if "json" not in response.headers.get("content-type", ""):
                continue
            try:
                body = await response.json()
            except Exception as exc:
                raise AssertionError("Business response is not valid JSON") from exc
            if isinstance(body, dict) and body.get("code", 200) not in (0, 200):
                raise AssertionError(f"Business code rejected at {urlsplit(response.url).path}")

    async def __aexit__(self, *_):
        try:
            await self.context.close()
        finally:
            try:
                await self.browser.close()
            finally:
                await self.pw.stop()
