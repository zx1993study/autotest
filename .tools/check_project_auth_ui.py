import argparse
import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import expect, sync_playwright

parser = argparse.ArgumentParser()
parser.add_argument('--url', default='http://127.0.0.1:5181')
args = parser.parse_args()
output = Path(__file__).resolve().parents[1] / 'backend/storage/ui-checks'
output.mkdir(parents=True, exist_ok=True)
projects = [{'id': 10, 'name': '测试项目', 'base_url': 'https://example.test', 'is_default': True},
            {'id': 20, 'name': '第二项目', 'base_url': 'https://second.example.test'}]
apis = [{'id': 42, 'project_id': 10, 'name': '账号登录', 'method': 'POST', 'path': '/login'},
        {'id': 43, 'project_id': 10, 'name': '客户登录', 'method': 'POST', 'path': '/customer/login'},
        {'id': 44, 'project_id': 10, 'name': '空接口', 'method': 'POST', 'path': '/empty'},
        {'id': 46, 'project_id': 10, 'name': '分页登录', 'method': 'POST', 'path': '/many'},
        {'id': 142, 'project_id': 20, 'name': '第二项目登录', 'method': 'POST', 'path': '/login'}]
api_cases = [{'id': 61, 'name': '账号密码登录', 'project_id': 10, 'source_id': 42, 'status': 'active', 'data': {}},
             {'id': 62, 'name': '验证码登录', 'project_id': 10, 'source_id': 42, 'status': 'active', 'data': {}},
             {'id': 63, 'name': '客户登录成功', 'project_id': 10, 'source_id': 43, 'status': 'active', 'data': {}},
             {'id': 64, 'name': '停用的登录用例', 'project_id': 10, 'source_id': 42, 'status': 'disabled', 'data': {}},
             {'id': 201, 'name': '第二项目用例', 'project_id': 20, 'source_id': 142, 'status': 'active', 'data': {}}]
api_cases.extend({'id': 5000 + index, 'name': f'分页用例 {index}', 'project_id': 10, 'source_id': 46, 'status': 'active', 'data': {}}
                 for index in range(1, 202))
web_cases = [{'id': 71, 'name': '网页登录', 'project_id': 10, 'status': 'active', 'data': {}},
             {'id': 72, 'name': '网页备用登录', 'project_id': 10, 'status': 'active', 'data': {}}]
auths = [{'id': 101, 'name': '原API鉴权', 'project_id': 10, 'status': 'active',
          'data': {'auth_type': 'bearer', 'login_case_type': 'API', 'login_case_id': 61, 'token_file': 'test-auth.json', 'header_name': 'Authorization', 'refresh_strategy': 'manual'}},
         {'id': 102, 'name': '原Web鉴权', 'project_id': 10, 'status': 'active',
          'data': {'auth_type': 'cookie', 'login_case_type': 'WEB', 'login_case_id': 71, 'refresh_strategy': 'manual'}},
         {'id': 103, 'name': '失效用例鉴权', 'project_id': 10, 'status': 'active',
          'data': {'auth_type': 'bearer', 'login_case_type': 'API', 'login_case_id': 999, 'refresh_strategy': 'manual'}}]
saved = []
queries = []
fail_source = None
delay_source = None
pending = []
project_saves = []


def response(data):
    return {'code': 0, 'message': 'success', 'data': data}


def intercept(route):
    request = route.request
    parsed = urlparse(request.url)
    endpoint = parsed.path.removeprefix('/api/v1')
    query = parse_qs(parsed.query)
    data = {'items': [], 'total': 0, 'page': 1, 'pageSize': 20}
    if endpoint == '/auth/me':
        data = {'id': 1, 'username': 'admin', 'display_name': '管理员', 'role': 'admin'}
    elif endpoint == '/projects/options':
        data = projects
    elif endpoint == '/projects' and request.method == 'POST':
        project_saves.append(request.post_data_json)
        data = {**request.post_data_json, 'id': 30}
    elif endpoint == '/api-testing/interfaces/options':
        data = [item for item in apis if item['project_id'] == int(query['project_id'][0])]
    elif endpoint in ('/api-testing/cases', '/web-testing/cases'):
        queries.append((endpoint, query))
        assert query['status'] == ['active'], query
        source = int(query.get('source_id', ['0'])[0])
        if source == delay_source:
            pending.append(route)
            return
        if source == fail_source:
            route.fulfill(status=500, json={'code': 500, 'message': '登录用例加载失败'})
            return
        rows = api_cases if endpoint.startswith('/api-') else web_cases
        rows = [item for item in rows if item['project_id'] == int(query['project_id'][0]) and item['status'] == 'active'
                and (not source or item.get('source_id') == source)]
        page, size = int(query['page'][0]), int(query['pageSize'][0])
        data = {'items': rows[(page - 1) * size:page * size], 'total': len(rows), 'page': page, 'pageSize': size}
    elif endpoint.startswith('/api-testing/cases/'):
        item_id = int(endpoint.rsplit('/', 1)[1])
        data = next((item for item in api_cases if item['id'] == item_id), None)
        if data is None:
            route.fulfill(status=404, json={'code': 404, 'message': '资源不存在'})
            return
    elif endpoint == '/project-auth' and request.method == 'POST':
        payload = request.post_data_json
        saved.append(('POST', payload))
        data = {**payload, 'id': 110 + len(saved)}
        auths.append(data)
    elif endpoint.startswith('/project-auth/') and request.method == 'PUT':
        item_id = int(endpoint.rsplit('/', 1)[1])
        payload = request.post_data_json
        saved.append(('PUT', payload))
        data = {**payload, 'id': item_id}
        index = next(index for index, item in enumerate(auths) if item['id'] == item_id)
        auths[index] = data
    elif endpoint == '/project-auth':
        rows = [item for item in auths if not query.get('project_id') or item['project_id'] == int(query['project_id'][0])]
        data = {'items': rows, 'total': len(rows), 'page': 1, 'pageSize': 20}
    route.fulfill(json=response(data))


with sync_playwright() as playwright:
    browser = playwright.chromium.launch()
    context = browser.new_context(viewport={'width': 1440, 'height': 960})
    context.add_init_script("sessionStorage.setItem('access_token', 'ui-test');")
    context.route('**/api/v1/**', intercept)
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(args.url.rstrip('/') + '/projects/auth')
    expect(page.locator('tbody')).to_contain_text('原API鉴权')

    def dialog():
        return page.get_by_role('dialog').filter(has=page.get_by_role('heading', name='新增项目鉴权'))

    def editor():
        return page.get_by_role('dialog').filter(has=page.get_by_role('heading', name='编辑项目鉴权'))

    def field(modal, text, tag='input'):
        return modal.locator('.field').filter(has=page.locator('span', has_text=text)).locator(tag)

    def open_new():
        page.get_by_role('button', name='新增', exact=True).click()
        modal = dialog()
        expect(modal.get_by_label('登录 API', exact=True)).to_be_enabled()
        return modal

    modal = open_new()
    expect(field(modal, '登录用例类型', 'select')).to_have_value('API')
    field(modal, '鉴权名称').fill('新API鉴权')
    modal.get_by_label('登录 API', exact=True).select_option('42')
    expect(modal.get_by_label('登录用例', exact=True)).to_be_enabled()
    expect(modal.get_by_label('登录用例', exact=True).locator('option')).to_have_count(3)
    expect(modal.get_by_role('button', name='保存', exact=True)).to_be_disabled()
    modal.get_by_label('登录用例', exact=True).select_option('61')
    modal.get_by_role('button', name='保存', exact=True).click()
    expect(modal).not_to_be_visible()
    assert saved[-1][1]['data']['login_case_id'] == 61
    assert saved[-1][1]['data']['login_case_type'] == 'API'
    assert 'login_api_id' not in saved[-1][1]['data']

    page.locator('tbody tr').filter(has_text='原API鉴权').get_by_role('button', name='编辑', exact=True).click()
    modal = editor()
    expect(modal.get_by_label('登录 API', exact=True)).to_have_value('42')
    expect(modal.get_by_label('登录用例', exact=True)).to_have_value('61')
    expect(modal.get_by_role('button', name='保存', exact=True)).to_be_enabled()
    modal.get_by_label('登录 API', exact=True).select_option('43')
    expect(modal.get_by_label('登录用例', exact=True)).to_have_value('')
    expect(modal.get_by_label('登录用例', exact=True)).to_be_enabled()
    expect(modal.get_by_label('登录用例', exact=True).locator('option')).to_have_count(2)
    modal.get_by_label('登录用例', exact=True).select_option('63')
    modal.get_by_role('button', name='保存', exact=True).click()
    expect(modal).not_to_be_visible()
    assert saved[-1][1]['data']['login_case_id'] == 63
    assert saved[-1][1]['data']['token_file'] == 'test-auth.json'

    page.locator('tbody tr').filter(has_text='原API鉴权').get_by_role('button', name='编辑', exact=True).click()
    modal = editor()
    expect(modal.get_by_label('登录 API', exact=True)).to_have_value('43')
    modal.locator('select').first.select_option('20')
    expect(modal.get_by_label('登录 API', exact=True)).to_have_value('')
    expect(modal.get_by_label('登录用例', exact=True)).to_have_value('')
    expect(modal.get_by_label('登录 API', exact=True)).to_be_enabled()
    expect(modal.get_by_label('登录 API', exact=True).locator('option')).to_have_count(2)
    modal.get_by_label('登录 API', exact=True).select_option('142')
    modal.get_by_label('登录用例', exact=True).select_option('201')
    modal.get_by_role('button', name='保存', exact=True).click()
    expect(modal).not_to_be_visible()
    assert saved[-1][1]['project_id'] == 20 and saved[-1][1]['data']['login_case_id'] == 201

    page.locator('tbody tr').filter(has_text='原Web鉴权').get_by_role('button', name='编辑', exact=True).click()
    modal = editor()
    expect(modal.get_by_label('登录 API', exact=True)).to_have_count(0)
    expect(modal.get_by_label('登录用例', exact=True)).to_have_value('71')
    modal.get_by_label('登录用例', exact=True).select_option('72')
    modal.get_by_role('button', name='保存', exact=True).click()
    expect(modal).not_to_be_visible()
    assert saved[-1][1]['data']['login_case_type'] == 'WEB' and saved[-1][1]['data']['login_case_id'] == 72

    modal = open_new()
    modal.get_by_label('登录 API', exact=True).select_option('42')
    modal.get_by_label('登录用例', exact=True).select_option('61')
    field(modal, '登录用例类型', 'select').select_option('WEB')
    expect(modal.get_by_label('登录 API', exact=True)).to_have_count(0)
    expect(modal.get_by_label('登录用例', exact=True)).to_have_value('')
    expect(modal.get_by_label('登录用例', exact=True)).to_be_enabled()
    modal.get_by_label('登录用例', exact=True).select_option('71')
    field(modal, '登录用例类型', 'select').select_option('API')
    expect(modal.get_by_label('登录 API', exact=True)).to_have_value('')
    expect(modal.get_by_label('登录用例', exact=True)).to_have_value('')
    modal.get_by_label('登录 API', exact=True).select_option('46')
    expect(modal.get_by_label('登录用例', exact=True).locator('option')).to_have_count(202)
    modal.get_by_label('登录用例', exact=True).select_option('5201')
    field(modal, '鉴权名称').fill('分页API鉴权')
    page.screenshot(path=str(output / 'project-auth-picker-desktop.png'))
    modal.get_by_role('button', name='保存', exact=True).click()
    expect(modal).not_to_be_visible()
    assert saved[-1][1]['data']['login_case_id'] == 5201
    assert any(query.get('source_id') == ['46'] and query.get('page') == ['2'] for _, query in queries)

    page.locator('tbody tr').filter(has_text='失效用例鉴权').get_by_role('button', name='编辑', exact=True).click()
    modal = editor()
    expect(modal.get_by_role('alert')).to_contain_text('资源不存在')
    expect(modal.get_by_role('button', name='保存', exact=True)).to_be_disabled()
    modal.get_by_label('登录 API', exact=True).select_option('42')
    modal.get_by_label('登录用例', exact=True).select_option('62')
    expect(modal.get_by_role('button', name='保存', exact=True)).to_be_enabled()
    modal.get_by_role('button', name='取消', exact=True).click()
    assert auths[2]['data']['login_case_id'] == 999

    modal = open_new()
    fail_source = 43
    modal.get_by_label('登录 API', exact=True).select_option('43')
    expect(modal.get_by_role('alert')).to_contain_text('登录用例加载失败')
    fail_source = None
    modal.get_by_role('button', name='重试', exact=True).click()
    expect(modal.get_by_label('登录 API', exact=True)).to_have_value('43')
    modal.get_by_label('登录用例', exact=True).select_option('63')
    expect(modal.get_by_role('alert')).to_have_count(0)
    modal.get_by_role('button', name='取消', exact=True).click()

    modal = open_new()
    delay_source = 43
    modal.get_by_label('登录 API', exact=True).select_option('43')
    expect(modal.get_by_role('button', name='保存', exact=True)).to_be_disabled()
    modal.locator('select').first.select_option('20')
    expect(modal.get_by_label('登录 API', exact=True)).to_be_enabled()
    assert pending
    pending.pop().fulfill(json=response({'items': [api_cases[2]], 'total': 1, 'page': 1, 'pageSize': 200}))
    delay_source = None
    expect(modal.get_by_label('登录 API', exact=True)).to_have_value('')
    expect(modal.get_by_label('登录用例', exact=True)).to_have_value('')
    modal.get_by_label('登录 API', exact=True).select_option('142')
    expect(modal.get_by_label('登录用例', exact=True).locator('option')).to_have_count(2)
    modal.get_by_role('button', name='取消', exact=True).click()

    page.set_viewport_size({'width': 390, 'height': 844})
    modal = open_new()
    modal.get_by_label('登录 API', exact=True).select_option('42')
    modal.get_by_label('登录用例', exact=True).select_option('61')
    modal.get_by_label('登录 API', exact=True).scroll_into_view_if_needed()
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    page.screenshot(path=str(output / 'project-auth-picker-mobile.png'))
    modal.get_by_role('button', name='取消', exact=True).click()

    page.goto(args.url.rstrip('/') + '/projects/info')
    page.get_by_role('button', name='新增', exact=True).click()
    fallback = page.get_by_role('dialog').filter(has=page.get_by_role('heading', name='新增项目信息'))
    field(fallback, '项目名称').fill('通用表单回归')
    field(fallback, '项目地址').fill('https://example.test')
    expect(fallback.get_by_role('button', name='保存', exact=True)).to_be_enabled()
    fallback.get_by_role('button', name='保存', exact=True).click()
    expect(fallback).not_to_be_visible()
    assert project_saves[-1]['name'] == '通用表单回归'
    assert not errors, errors
    browser.close()
print('PASS: API-to-case cascade, legacy edit restoration, project/type resets, active-case filtering, pagination, retry, stale-response protection, Web compatibility, mobile layout and default form fallback')
