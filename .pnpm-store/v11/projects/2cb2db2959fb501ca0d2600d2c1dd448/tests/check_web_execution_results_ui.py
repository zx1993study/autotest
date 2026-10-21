"""Read-only regression checks for batched Web execution summaries."""

import argparse
import base64
import re
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import Error, expect, sync_playwright


class Fixture:
    def __init__(self):
        self.batches, self.lists, self.details, self.unexpected = [], [], [], []
        self.pending, self.hold, self.fail, self.polls = [], True, False, 0
        self.groups = [self.item(i, f'页面 {i}', route=f'/page/{i}', url=f'https://example.test/{i}')
                       for i in range(100, 123)]
        self.features = [self.item(201, '编辑项目', page_group_id=100, feature_type='edit')]
        self.cases = [self.item(i, f'用例 {i}', input_info={'name': f'输入 {i}'}) for i in range(301, 313)]

    @staticmethod
    def item(number, name, **data):
        return {'id': number, 'name': name, 'project_id': 1, 'source_id': 201, 'status': 'active',
                'data': data, 'feature_count': 1, 'interface_count': 0, 'case_count': 12,
                'updated_at': '2026-10-21T12:00:00'}

    @staticmethod
    def fulfill(route, data):
        route.fulfill(json={'code': 0, 'message': 'success', 'data': data})

    def summary(self, number, scope):
        status = ({100: 'failed', 102: 'partial', 103: 'unverified', 104: 'not_run', 105: 'empty',
                   201: 'failed', 302: 'failed', 303: 'unverified', 304: 'not_run'}).get(number, 'success')
        result = {'id': number, 'status': status, 'total_count': 1, 'success_count': 0, 'failed_count': 0,
                  'not_run_count': 0, 'unverified_count': 0, 'running_count': 0, 'canceled_count': 0,
                  'record_id': 900 + number, 'executed_at': '2026-10-21T12:00:00'}
        if status == 'partial':
            result.update(total_count=2, success_count=1, not_run_count=1)
        elif status == 'empty':
            result.update(total_count=0, record_id=None, executed_at=None)
        else:
            result[status + '_count'] = 1
        if status == 'not_run':
            result.update(record_id=None, executed_at=None)
        if scope != 'case' and status == 'failed':
            result.update(total_count=2, success_count=1, failed_count=1, record_id=1000)
        return result

    def intercept(self, route):
        request = route.request
        parsed = urlparse(request.url)
        path = parsed.path.removeprefix('/api/v1')
        query = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        if path == '/web-testing/execution-summaries' and request.method == 'POST':
            body = request.post_data_json
            self.batches.append(body)
            if self.fail:
                self.fail = False
                route.fulfill(status=503, json={'code': 503, 'message': 'Summary unavailable'})
                return
            data = {'items': [self.summary(i, body['scope']) for i in body['ids']]}
            if self.hold:
                self.pending.append((route, data))
                return
        elif request.method != 'GET':
            self.unexpected.append((request.method, path))
            route.abort()
            return
        elif path == '/auth/me':
            data = {'id': 1, 'username': 'ui-check', 'display_name': '测试用户', 'role': 'admin'}
        elif path == '/projects/options':
            data = [{'id': 1, 'name': '测试项目', 'is_default': True}]
        elif path == '/web-testing/page-groups':
            self.lists.append(query)
            rows = [g for g in self.groups if query.get('keyword', '') in g['name']]
            page, size = int(query.get('page', 1)), int(query.get('pageSize', 20))
            data = {'items': rows[(page-1)*size:page*size], 'total': len(rows), 'page': page, 'pageSize': size}
        elif path == '/web-testing/page-groups/100':
            data = self.groups[0]
        elif path == '/web-testing/page-groups/100/features':
            data = {'items': self.features, 'total': 1, 'page': 1, 'pageSize': 20}
        elif path == '/web-testing/features/201':
            data = {'feature': {**self.features[0], 'data': {**self.features[0]['data'], 'last_agent_task_id': 42}},
                    'page': self.groups[0], 'parameters': [], 'candidate': None, 'screenshots': [],
                    'versions': [], 'cases': self.cases, 'legacy_drafts': [], 'interfaces': [], 'api_candidates': []}
        elif path == '/agent/tasks/42':
            self.polls += 1
            data = {'id': 42, 'name': '历史任务', 'status': 'running' if self.polls == 1 else 'success',
                    'data': {'payload': {'cases': [{'source_id': 201, 'project_id': 1}]}, 'result': {'records': []}}}
        elif match := re.fullmatch(r'/reports/records/(\d+)', path):
            number = int(match[1])
            self.details.append(number)
            data = {'id': number, 'name': '已保存的页面业务结果', 'status': 'failed', 'created_at': '2026-10-21T12:00:00',
                    'data': {'case_type': 'WEB', 'business_result': 'failed', 'assertion_count': 2,
                             'input_snapshot': {'name': '测试', 'password': 'hidden-password'},
                             'assertion_results': [{'type': 'text', 'expected': '已保存', 'actual': '已保存', 'passed': True},
                                                   {'type': 'visible', 'expected': True, 'actual': False, 'passed': False}],
                             'screenshots': [{'screenshot_url': '/api/v1/screenshots/check.png', 'step_name': '保存结果'}]}}
        elif path == '/screenshots/check.png':
            route.fulfill(content_type='image/png', body=base64.b64decode(
                'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aX1cAAAAASUVORK5CYII='))
            return
        else:
            self.unexpected.append(path)
            route.fulfill(status=404, json={'code': 404, 'message': 'Unexpected fixture request'})
            return
        self.fulfill(route, data)

    def release(self):
        self.hold = False
        pending, self.pending = self.pending, []
        for route, data in pending:
            try:
                self.fulfill(route, data)
            except Error:
                pass  # An aborted obsolete batch must not update the current list.


def row(page, name):
    return page.locator('tbody tr').filter(has_text=name).first


def responsive(page, output, name):
    for width in (1440, 390):
        page.set_viewport_size({'width': width, 'height': 960})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), f'{name}: body overflow at {width}'
        table = page.locator('.table-wrap').last
        assert table.evaluate('el => el.clientWidth <= window.innerWidth')
        if width == 1440 and name == 'pages':
            assert page.locator('.address-cell').first.bounding_box()['width'] >= 160
            assert page.locator('.actions-cell button').evaluate_all('items => items.every(el => el.scrollWidth <= el.clientWidth)')
        if width == 1440 and name == 'features':
            assert table.evaluate('el => el.scrollWidth <= el.clientWidth')
        if width == 390:
            result = page.locator('.web-execution-result').first
            result.scroll_into_view_if_needed()
            bounds = result.bounding_box()
            assert bounds and bounds['x'] >= 0 and bounds['x'] + bounds['width'] <= width
        page.screenshot(path=str(output / f'{name}-{width}.png'), animations='disabled')
    page.set_viewport_size({'width': 1440, 'height': 960})


def check(page, fixture, url, output):
    page.goto(url + '/web/pages?project_id=1')
    expect(row(page, '页面 100')).to_be_visible()
    expect(page.locator('.web-execution-result .result-loading')).to_have_count(20)
    expect(page.get_by_role('button', name='下一页', exact=True)).to_be_enabled()
    assert len(fixture.batches) == 1 and len(fixture.batches[0]['ids']) == 20 and not fixture.details
    fixture.release()
    expect(row(page, '页面 100').locator('.result-counts')).to_have_text('成功 1 / 失败 1')
    for number, label in [(101, '成功'), (102, '部分执行'), (103, '未验证'), (104, '未执行'), (105, '无用例')]:
        expect(row(page, f'页面 {number}').locator('.web-execution-result')).to_contain_text(label)
    lists = len(fixture.lists)
    row(page, '页面 100').get_by_role('button', name='查看失败执行结果', exact=True).focus()
    page.keyboard.press('Enter')
    expect(page).to_have_url(url + '/web/pages?project_id=1')
    dialog = page.get_by_role('dialog')
    expect(dialog.locator('[data-outcome="passed"]')).to_have_count(1)
    expect(dialog.locator('[data-outcome="failed"]')).to_have_count(1)
    expect(dialog.locator('.record-screenshots img')).to_have_count(1)
    assert 'hidden-password' not in dialog.inner_text() and fixture.details == [1000]
    expect(dialog.locator('.record-screenshots img')).to_have_js_property('naturalWidth', 1)
    page.screenshot(path=str(output / 'web-result-dialog.png'), animations='disabled')
    page.keyboard.press('Escape')
    assert len(fixture.lists) == lists
    responsive(page, output, 'pages')
    fixture.fail = True
    page.get_by_role('button', name='下一页', exact=True).click()
    expect(row(page, '页面 120').get_by_role('button', name='重试加载执行结果')).to_be_visible()
    lists = len(fixture.lists)
    row(page, '页面 120').get_by_role('button', name='重试加载执行结果').click()
    expect(row(page, '页面 120').locator('.web-execution-result')).to_contain_text('成功')
    assert len(fixture.lists) == lists and fixture.batches[-1]['ids'] == [120, 121, 122]
    fixture.hold = True
    page.get_by_role('button', name='上一页', exact=True).click()
    expect(row(page, '页面 100').locator('.result-loading')).to_be_visible()
    fixture.hold = False
    page.get_by_role('button', name='下一页', exact=True).click()
    expect(row(page, '页面 120').locator('.result-link')).to_have_text('成功')
    fixture.release()
    expect(row(page, '页面 120').locator('.result-link')).to_have_text('成功')
    page.goto(url + '/web/pages/100?project_id=1')
    expect(row(page, '编辑项目').locator('.result-counts')).to_have_text('成功 1 / 失败 1')
    assert fixture.batches[-1] == {'project_id': 1, 'scope': 'feature', 'ids': [201]}
    responsive(page, output, 'features')
    row(page, '编辑项目').get_by_role('button', name='详情', exact=True).click()
    expect(row(page, '用例 302').locator('.result-link')).to_have_text('失败')
    expect(row(page, '用例 303').locator('.result-link')).to_have_text('未验证')
    expect(row(page, '用例 304').locator('.result-label')).to_have_text('未执行')
    before = len(fixture.batches)
    expect(page.locator('.execution-region .section-title')).to_contain_text('业务未验证', timeout=10000)
    assert len(fixture.batches) > before, 'Task completion did not refresh case summaries'
    responsive(page, output, 'cases')
    page.locator('.case-region').get_by_role('button', name='下一页', exact=True).click()
    expect(row(page, '用例 311').locator('.result-link')).to_have_text('成功')
    assert fixture.batches[-1]['ids'] == [311, 312]
    row(page, '用例 311').get_by_role('button', name='查看成功执行结果').click()
    expect(page.locator('.record-title')).to_contain_text('#1211')
    page.keyboard.press('Escape')
    expect(row(page, '用例 311')).to_be_visible()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:5173')
    parser.add_argument('--output', default='frontend/node_modules/.cache/ui-checks/web-execution-results')
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(viewport={'width': 1440, 'height': 960})
        context.add_init_script("sessionStorage.setItem('autotest.session./access_token','web-summary-check')")
        fixture = Fixture()
        context.route('**/api/v1/**', fixture.intercept)
        page = context.new_page()
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        check(page, fixture, args.url, output)
        assert not errors and not fixture.unexpected, (errors, fixture.unexpected)
        context.close()
        browser.close()
    print('PASS: three levels; one visible-ID batch; nonblocking list; retry; stale cancellation; exact record; Web assertions/screenshots; completion refresh; desktop/mobile; no writes')


if __name__ == '__main__':
    main()
