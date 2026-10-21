import asyncio
import copy
import json
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import pytest
from pages.base_page import BasePage
from pages.list_page import ListPage, execute

HTML = '''<div class="app-main"><div class="unified-list__actions">
<button onclick="fetch('/dev-api/items/list').then(r=>r.json())">查询</button>
</div><div class="el-table"><span>Items</span><div class="el-table__body-wrapper">WH001</div></div></div>'''


@contextmanager
def server(html=HTML, code=200):
    writes = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            body = (json.dumps({"code": code, "rows": [{"warehouseCode": "WH001"}]}).encode()
                    if self.path.startswith("/dev-api/") else html.encode())
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8" if self.path.startswith("/dev-api/") else "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            writes.append(self.path)
            self.send_response(200)
            self.end_headers()

        def log_message(self, *_):
            pass

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_port}", writes
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join()


@pytest.fixture
def definition():
    return {"status": "source_ready", "feature_id": 1, "feature_type": "query", "route": "/items",
            "list_api": [{"url": "/items/list"}], "candidate": {"steps": [
                {"name": "List", "action": "assert", "locator_type": "css", "locator": ".el-table", "expected": "Items", "require_unique": True}]}}


def test_readonly_browser_checks_list_response(definition):
    with server() as (origin, writes):
        result = asyncio.run(execute({"base_url": origin}, definition))
    assert result["status"] == "passed" and result["ai_calls"] == 0
    assert writes == []


def test_http_200_business_failure_is_not_a_pass(definition):
    with server(code=500) as (origin, writes), pytest.raises(AssertionError, match="code=200"):
        asyncio.run(execute({"base_url": origin}, definition))
    assert writes == []


def test_post_is_blocked_before_reaching_server(definition):
    async def probe(origin):
        async with BasePage({"base_url": origin}, definition) as page:
            await page.open()
            await page.page.evaluate("fetch('/dev-api/write',{method:'POST'}).catch(()=>null)")
            with pytest.raises(AssertionError, match="write"):
                await page.assert_clean_network()
    with server() as (origin, writes):
        asyncio.run(probe(origin))
    assert writes == []


def test_blocked_definition_does_not_start_browser(definition):
    blocked = copy.deepcopy(definition)
    blocked["status"] = "blocked"
    with pytest.raises(ValueError, match="blocked"):
        asyncio.run(execute({}, blocked))


@pytest.mark.parametrize("rows", [[], [{"warehouseCode": "OTHER"}]])
def test_empty_or_unfiltered_rows_do_not_count_as_query_pass(rows):
    class Adapter:
        def __init__(self):
            self.definition = {"search_fields": [{"key": "warehouseCode", "label": "Code"}],
                               "candidate": {"steps": [{}, {}, {}]}}
            self.engine = self

        async def execute(self, _):
            pass

        async def submit_query(self, _):
            return rows

    with pytest.raises(AssertionError):
        asyncio.run(ListPage.query(Adapter(), {"warehouseCode": "WH001"}))
