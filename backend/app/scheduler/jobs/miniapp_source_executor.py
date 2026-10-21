import re
import time
from urllib.parse import urlsplit

from app.schemas.miniapp_source import SourceCase


def execute_source_case(case, platform, base_url):
    started = time.monotonic()
    definition = SourceCase.model_validate(case["data"]["definition"])
    result = {"case_id": case["id"], "source_case_id": definition.id, "name": case["name"],
              "definition": definition.model_dump(), "status": "blocked", "executed": False,
              "assertions": [], "source_revision": case["data"]["source_revision"]}
    reason = _blocked_reason(definition, platform, base_url)
    if reason:
        result["reason"] = reason
    else:
        try:
            _run_h5(definition, base_url)
            result.update(status="success", executed=True, assertions=[{"type": "source_operations", "passed": True}])
        except AssertionError as error:
            result.update(status="failed", executed=True, reason=str(error))
        except Exception as error:  # noqa: BLE001 - never persist browser errors containing request values.
            result.update(status="failed", executed=True, reason=f"H5执行异常：{type(error).__name__}")
    result["duration_ms"] = round((time.monotonic() - started) * 1000)
    return result


def _blocked_reason(case, platform, base_url):
    if platform not in case.platforms:
        return "用例不支持所选平台"
    if platform == "mp-weixin":
        return "当前服务未连接 uni-automator 微信开发者工具执行节点；原生小程序未执行"
    if not base_url:
        return "项目未配置 miniapp_h5_url；未执行 UI 测试"
    if not isinstance(base_url, str):
        return "miniapp_h5_url 配置无效"
    try:
        url = urlsplit(base_url)
        host = url.hostname
    except ValueError:
        return "miniapp_h5_url 配置无效"
    if url.scheme not in {"http", "https"} or not host or url.username or url.password or url.query or url.fragment:
        return "miniapp_h5_url 配置无效"
    if case.automation != "scripted":
        return "业务/人工步骤尚未转换为可回放 UI 操作；API 关联结果不能替代 UI 结果"
    if case.requires_fixture:
        return "缺少当前批次归属已验证的路由数据"
    if case.requires_auth:
        return "H5 执行尚未配置专用浏览器登录态；不会复用管理端或 API Token"
    if case.risk != "read":
        return "仅允许无业务写入的源码 UI 操作"
    return None


class ReadOnlyNetwork:
    def __init__(self):
        self.failures = set()
        self.pending = set()

    def route(self, route):
        if route.request.method not in {"GET", "HEAD", "OPTIONS"}:
            self.failures.add("页面尝试写入，已拦截")
            route.abort("blockedbyclient")
        else:
            route.continue_()

    def response(self, response):
        if response.request.resource_type not in {"xhr", "fetch", "document"}:
            return
        if response.status >= 400:
            self.failures.add(f"页面请求 HTTP {response.status}")
        if response.request.resource_type == "document":
            return
        try:
            data = response.json()
            if isinstance(data, dict) and (data.get("success") is False or data.get("code", 200) not in (200, "200")):
                self.failures.add("页面接口返回业务失败")
        except (ValueError, TypeError):
            pass

    def started(self, request):
        if request.resource_type in {"xhr", "fetch"}:
            self.pending.add(request)

    def finished(self, request):
        self.pending.discard(request)

    def failed(self, request):
        self.finished(request)
        if request.resource_type in {"xhr", "fetch", "document"}:
            self.failures.add("页面网络请求失败")

    def settle(self, page):
        page.wait_for_timeout(500)
        deadline = time.monotonic() + 10
        while self.pending and time.monotonic() < deadline:
            page.wait_for_timeout(100)
        assert not self.pending, "页面请求超时未结束"
        assert not self.failures, "；".join(sorted(self.failures))


def _run_h5(case, base_url):
    from playwright.sync_api import expect, sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            context = browser.new_context(service_workers="block", viewport={"width": 390, "height": 844})
            guard = ReadOnlyNetwork()
            context.route("**/*", guard.route)
            context.route_web_socket("**/*", lambda route: route.close())
            page = context.new_page()
            page.set_default_timeout(10000)
            for event, handler in (("request", guard.started), ("requestfinished", guard.finished),
                                   ("requestfailed", guard.failed), ("response", guard.response)):
                page.on(event, handler)
            target = f"{base_url.rstrip('/')}/#/{case.route}"
            page.goto(target, wait_until="domcontentloaded", timeout=20000)
            expect(page).to_have_url(re.compile("^" + re.escape(target) + r"(?:\?.*)?$"))
            for operation in case.operations:
                try:
                    _operation(page, operation)
                except AssertionError:
                    raise AssertionError(f"源码操作断言未满足：{operation.action} {operation.selector or 'toast'}") from None
            guard.settle(page)
            expect(page).to_have_url(re.compile("^" + re.escape(target) + r"(?:\?.*)?$"))
        finally:
            browser.close()


def _operation(page, operation):
    from playwright.sync_api import expect

    if operation.action == "toast":
        expect(page.get_by_text(operation.text, exact=True)).to_be_visible()
        return
    target = page.locator(operation.selector)
    expect(target).to_have_count(1)
    if operation.action in {"input", "password_mode"} and target.evaluate("el => el.tagName.toLowerCase()") not in {"input", "textarea"}:
        target = target.locator("input, textarea")
        expect(target).to_have_count(1)
    if operation.action == "visible":
        expect(target).to_be_visible()
    elif operation.action == "input":
        target.fill(operation.value)
    elif operation.action == "click":
        target.click()
    elif operation.action == "disabled":
        expect(target).to_be_disabled()
    elif operation.action == "password_mode":
        expect(target).to_have_attribute("type", "password" if operation.masked else "text")
