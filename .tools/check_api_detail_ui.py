import argparse
import json
import re
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import expect, sync_playwright
from web_automation.dynamic_values import prepare_dynamic_execution


OUTPUT = Path(__file__).resolve().parents[1] / 'backend/storage/ui-checks'
OUTPUT.mkdir(parents=True, exist_ok=True)
interface = {
    'id': 42, 'name': '新增客户', 'project_id': 10, 'status': 'active',
    'data': {'method': 'POST', 'path': '/customers', 'module': '客户管理', 'content_type': 'application/json'},
}
fields = [
    {'id': index, 'name': f'parameter_{index}', 'project_id': 10, 'status': 'active',
     'data': {'interface_id': 42, 'location': 'body', 'field_type': 'string', 'example': f'value_{index}'}}
    for index in range(1, 41)
]
fields[0]['data'].update({'field_type': 'boolean', 'example': 'false'})
fields[1]['name'] = 'businessRegistrationNumberWithVeryLongFieldNameThatMustWrapWithoutMovingTheNextColumn'
drafts = []
cases = []
saved_payloads = []
run_payloads = []
auth_requests = []
auth_options = [{'id': 77, 'name': '客户项目 Token'}, {'id': 78, 'name': '备用 Token'}]
auth_failure = False
snapshot = {'id': 8, 'data': {'openapi_version': '3.1.0', 'operation_count': 1, 'schema_hash': 'testhash'}}


def intercept(route):
    request = route.request
    parsed = urlparse(request.url)
    endpoint = parsed.path.removeprefix('/api/v1')
    query = parse_qs(parsed.query)
    data = {'items': [], 'total': 0, 'page': 1, 'pageSize': 20}
    if endpoint == '/auth/me':
        data = {'id': 1, 'username': 'admin', 'display_name': '管理员', 'role': 'admin'}
    elif endpoint == '/project-auth/options':
        auth_requests.append(query)
        assert query.get('project_id') == ['10'], query
        assert query.get('login_case_type') == ['API'], query
        if auth_failure:
            route.fulfill(status=500, json={'code': 500, 'message': '认证选项加载失败'})
            return
        data = auth_options
    elif endpoint == '/testing/dynamic-values/preview':
        payload = request.post_data_json
        resolved, _, dynamic = prepare_dynamic_execution({'data': {'value': payload['value'], 'variables': payload.get('variables', {})}}, {})
        data = {'resolved': resolved['data']['value'], 'dynamic_values': dynamic.snapshot()}
    elif endpoint == '/projects/options':
        data = [{'id': 10, 'name': '测试项目', 'base_url': 'https://example.test'}]
    elif endpoint == '/api-testing/interfaces/42':
        data = interface
    elif endpoint == '/api-testing/interfaces/schema-snapshots/latest':
        data = snapshot
    elif endpoint == '/api-testing/fields':
        data = {'items': fields, 'total': len(fields), 'page': 1, 'pageSize': 200}
    elif endpoint == '/api-testing/case-drafts/openapi/preview':
        data = {'snapshot': snapshot, 'total': 1, 'truncated': False, 'summary': {'new': 1, 'update': 0, 'unchanged': 0},
                'items': [{'fingerprint': 'preview1', 'generation_key': 'normal', 'source_id': 42,
                           'source_name': interface['name'], 'name': '新增客户正常场景', 'category': 'normal',
                           'strategy': 'normal', 'method': 'POST', 'path': '/customers',
                           'assertions': [{'type': 'status', 'expected': 200}], 'action': 'new'}]}
    elif endpoint == '/api-testing/case-drafts/openapi/generate':
        drafts.append({'id': 51, 'name': '新增客户正常场景', 'project_id': 10, 'source_id': 42, 'status': 'draft',
                       'updated_at': '2026-10-09T12:00:00', 'data': {'priority': 'P2', 'category': 'normal'}})
        data = {'created_count': 1, 'updated_count': 0, 'skipped_count': 0, 'draft_ids': [51]}
    elif endpoint == '/api-testing/case-drafts':
        assert query['source_id'] == ['42']
        rows = [row for row in drafts if not query.get('status') or row['status'] == query['status'][0]]
        data = {'items': rows, 'total': len(rows), 'page': 1, 'pageSize': 10}
    elif endpoint == '/api-testing/cases' and request.method == 'POST':
        payload = request.post_data_json
        saved_payloads.append(payload)
        data = {**payload, 'id': 61 + len(cases), 'updated_at': '2026-10-09T12:00:00'}
        cases.append(data)
    elif endpoint == '/api-testing/cases/61' and request.method == 'PUT':
        payload = request.post_data_json
        saved_payloads.append(payload)
        data = {**payload, 'id': 61, 'updated_at': '2026-10-09T12:00:00'}
        cases[0] = data
    elif endpoint == '/api-testing/cases/run':
        payload = request.post_data_json
        assert payload['case_ids'] == [61], payload
        run_payloads.append({'request': payload, 'saved_auth_id': cases[0]['data']['auth_id']})
        data = {'submitted_count': 1}
    elif endpoint == '/api-testing/cases':
        assert query['source_id'] == ['42']
        data = {'items': cases, 'total': len(cases), 'page': 1, 'pageSize': 10}
    route.fulfill(json={'code': 0, 'message': 'success', 'data': data})


def assert_compact_columns(page):
    for selector, name_index, minimum, maximum in (
        ('.parameter-table', 0, 180, 260),
        ('.case-table', 1, 220, 360),
    ):
        table = page.locator(selector)
        columns = table.locator('thead th').evaluate_all(
            'elements => elements.map(element => ({width: element.getBoundingClientRect().width, '
            'x: element.getBoundingClientRect().x, height: element.getBoundingClientRect().height}))'
        )
        name_column = columns[name_index]
        assert minimum - 1 <= name_column['width'] <= maximum + 1, (selector, columns)
        next_column = columns[name_index + 1]
        assert abs(next_column['x'] - name_column['x'] - name_column['width']) < 2
        assert columns[-1]['width'] >= (110 if name_index == 0 else 236) - 1, columns
        assert columns[-1]['height'] <= 46, columns
        assert table.locator('tbody td .compact-actions').evaluate_all('''elements => elements.every(element => {
            const cell = element.parentElement.getBoundingClientRect();
            const buttons = [...element.querySelectorAll('button')];
            return buttons.every(button => {
                const rect = button.getBoundingClientRect();
                return rect.x >= cell.x && rect.right <= cell.right;
            });
        })'''), selector
        assert table.locator('tbody tr').evaluate_all('''(rows, nameIndex) => rows.every(row => {
            const cell = row.children[nameIndex];
            const text = cell?.querySelector('strong');
            if (!text) return true;
            const rect = text.getBoundingClientRect();
            const bounds = cell.getBoundingClientRect();
            return text.scrollWidth <= text.clientWidth + 1 && rect.right <= bounds.right;
        })''', name_index), selector
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')


parser = argparse.ArgumentParser()
parser.add_argument('--url', default='http://127.0.0.1:5181')
args = parser.parse_args()

with sync_playwright() as playwright:
    browser = playwright.chromium.launch()
    context = browser.new_context(viewport={'width': 1440, 'height': 960})
    context.add_init_script("sessionStorage.setItem('access_token', 'ui-test');")
    context.route('**/api/v1/**', intercept)
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    entry = page.goto(args.url.rstrip('/') + '/api/interfaces/42?project_id=10')
    assert entry and entry.status == 200, 'API detail deep link did not serve the frontend entry'
    expect(page.locator('.parameter-table tbody tr')).to_have_count(40)
    height = page.get_by_label('请求参数列表高度', exact=True)
    expect(height).to_have_value('auto')
    for width, viewport_height in ((2560, 1369), (1920, 1080), (1401, 960), (1440, 960)):
        page.set_viewport_size({'width': width, 'height': viewport_height})
        expect(page.locator('.detail-grid')).to_have_css('height', re.compile(r'^\d+px$'))
        page.wait_for_function('Math.abs(document.querySelector(".detail-grid").getBoundingClientRect().bottom - (window.innerHeight - 28)) < 3')
        left = page.locator('.parameter-panel').bounding_box()
        right = page.locator('.case-panel').bounding_box()
        assert abs(left['height'] - right['height']) < 2, (left, right)
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), width
        if width == 2560:
            assert page.locator('.parameter-table-wrap').bounding_box()['height'] > 900
        page.screenshot(path=str(OUTPUT / f'api-detail-auto-{width}.png'), full_page=True)
    height.select_option('custom')
    custom = page.get_by_label('自定义请求参数列表高度', exact=True)
    custom.fill('560')
    custom.press('Tab')
    expect(page.locator('.parameter-table-wrap')).to_have_css('height', '560px')
    page.reload()
    expect(page.get_by_label('自定义请求参数列表高度', exact=True)).to_have_value('560')
    page.locator('.parameter-table-wrap').evaluate('(element) => { element.scrollTop = 300; }')
    positions = page.locator('.parameter-table-wrap').evaluate('element => ({ outer: element.getBoundingClientRect().top, head: element.querySelector("th").getBoundingClientRect().top })')
    assert abs(positions['head'] - positions['outer']) < 3, positions
    page.get_by_label('重置请求参数列表高度').click()
    expect(height).to_have_value('auto')

    page.get_by_role('button', name='生成用例草稿', exact=True).click()
    page.get_by_role('button', name='预览用例', exact=True).click()
    page.get_by_role('button', name='生成选中草稿 (1)', exact=True).click()
    expect(page.locator('.draft-table tbody tr')).to_have_count(1)
    expect(page.locator('.draft-table')).to_contain_text('新增客户正常场景')
    page.screenshot(path=str(OUTPUT / 'api-detail-desktop.png'), full_page=True)

    page.get_by_role('tab', name='正式用例').click()
    page.get_by_role('button', name='新增用例', exact=True).click()
    dialog = page.get_by_role('dialog', name='新增正式用例')
    expect(dialog).to_be_visible()
    expect(dialog.get_by_label('认证方式', exact=True)).to_have_value('inherit')
    expect(dialog.locator('.inherited-auth')).to_contain_text('未配置')
    dialog.get_by_label('认证方式', exact=True).select_option('token')
    expect(dialog.get_by_label('Token / 鉴权信息', exact=True).get_by_role('option', name='客户项目 Token')).to_have_count(1)
    dialog.get_by_label('Token / 鉴权信息', exact=True).select_option('77')
    dialog.get_by_label('用例名称').fill('手工新增客户场景')
    dialog.get_by_label('请求参数 JSON', exact=True).fill('[]')
    dialog.get_by_role('button', name='保存用例', exact=True).click()
    expect(dialog.get_by_role('alert')).to_contain_text('必须是 JSON 对象')
    assert not saved_payloads
    dialog.get_by_label('请求参数 JSON', exact=True).fill(json.dumps({'name': 'UI Customer', 'phone': '', 'enabled': False}))
    selector = dialog.get_by_label('请求参数动态字段', exact=True)
    selector.select_option('["name"]')
    mode = dialog.get_by_label('请求参数字段值生成方式', exact=True)
    mode.select_option('timestamp_ms')
    expect(dialog.get_by_label('请求参数字段值', exact=True)).to_have_value('UI Customer_{{timestamp_ms}}')
    dialog.get_by_label('请求参数字段值时间戳分隔符', exact=True).fill('-')
    dialog.get_by_label('请求参数字段值预览动态值', exact=True).click()
    expect(dialog.get_by_label('请求参数字段值动态值预览', exact=True)).to_have_text(re.compile(r'^UI Customer-\d{13}$'))
    mode.select_option('custom')
    expect(mode).to_have_value('custom')
    selector.select_option('["phone"]')
    mode.select_option('phone')
    dialog.get_by_label('请求参数字段值手机号号段', exact=True).fill('139')
    expect(dialog.get_by_label('请求参数字段值', exact=True)).to_have_value('{{random_phone:139}}')
    dialog.get_by_label('请求参数字段值预览动态值', exact=True).click()
    expect(dialog.get_by_label('请求参数字段值动态值预览', exact=True)).to_have_text(re.compile(r'^139\d{8}$'))
    page.screenshot(path=str(OUTPUT / 'dynamic-api-form-desktop.png'))
    page.set_viewport_size({'width': 390, 'height': 844})
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    dialog.get_by_label('请求参数字段值生成方式', exact=True).scroll_into_view_if_needed()
    page.screenshot(path=str(OUTPUT / 'dynamic-api-form-mobile.png'))
    page.set_viewport_size({'width': 1440, 'height': 960})
    dialog.get_by_role('button', name='保存用例', exact=True).click()
    expect(dialog).not_to_be_visible()
    expect(page.locator('.case-table')).to_contain_text('手工新增客户场景')
    assert saved_payloads[0]['source_id'] == 42
    assert saved_payloads[0]['project_id'] == 10
    assert saved_payloads[0]['data']['params']['enabled'] is False
    assert saved_payloads[0]['data']['params']['name'] == 'UI Customer-{{timestamp_ms}}'
    assert saved_payloads[0]['data']['params']['phone'] == '{{random_phone:139}}'
    assert saved_payloads[0]['assertions'] == [{'type': 'status', 'expected': 200}]
    assert saved_payloads[0]['data']['auth_id'] == 77
    assert saved_payloads[0]['data']['skip_auth'] is False
    assert auth_requests
    page.locator('.case-table').get_by_role('button', name='执行', exact=True).click()
    expect(page.locator('.case-panel')).to_contain_text('已提交 1 条正式用例执行')
    assert run_payloads[-1]['saved_auth_id'] == 77

    page.locator('.case-table').get_by_role('button', name='编辑', exact=True).click()
    editor = page.get_by_role('dialog', name='编辑正式用例')
    expect(editor.get_by_label('认证方式', exact=True)).to_have_value('token')
    expect(editor.get_by_label('Token / 鉴权信息', exact=True)).to_have_value('77')
    editor.get_by_label('认证方式', exact=True).select_option('none')
    editor.get_by_role('button', name='保存用例', exact=True).click()
    expect(editor).not_to_be_visible()
    assert saved_payloads[-1]['data']['auth_id'] is None
    assert saved_payloads[-1]['data']['skip_auth'] is True

    page.locator('.case-table').get_by_role('button', name='编辑', exact=True).click()
    expect(editor.get_by_label('认证方式', exact=True)).to_have_value('none')
    editor.get_by_label('认证方式', exact=True).select_option('inherit')
    editor.get_by_role('button', name='保存用例', exact=True).click()
    expect(editor).not_to_be_visible()
    assert saved_payloads[-1]['data']['auth_id'] is None
    assert saved_payloads[-1]['data']['skip_auth'] is False

    cases[0]['data']['auth_id'] = 999
    page.get_by_label('刷新正式用例', exact=True).click()
    expect(page.locator('.case-table')).to_contain_text('手工新增客户场景')
    page.locator('.case-table').get_by_role('button', name='编辑', exact=True).click()
    expect(editor.get_by_label('Token / 鉴权信息', exact=True)).to_have_value('999')
    editor.get_by_role('button', name='保存用例', exact=True).click()
    expect(editor.get_by_role('alert')).to_contain_text('请选择有效的项目 Token')
    editor.get_by_role('button', name='取消', exact=True).click()

    auth_failure = True
    page.get_by_role('button', name='新增用例', exact=True).click()
    expect(dialog.get_by_role('alert')).to_contain_text('认证选项加载失败')
    auth_failure = False
    dialog.get_by_role('button', name='重试', exact=True).click()
    expect(dialog.get_by_role('alert')).to_have_count(0)
    dialog.get_by_role('button', name='取消', exact=True).click()

    for width in (1024, 390):
        page.set_viewport_size({'width': width, 'height': 844})
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), width
        page.get_by_role('button', name='新增用例', exact=True).click()
        expect(dialog).to_be_visible()
        dialog.get_by_label('认证方式', exact=True).select_option('token')
        dialog.get_by_label('Token / 鉴权信息', exact=True).select_option('77')
        rect = dialog.bounding_box()
        assert rect['x'] >= 0 and rect['x'] + rect['width'] <= width + 1, rect
        heading = dialog.get_by_role('heading', name='新增正式用例')
        heading.scroll_into_view_if_needed()
        if width == 390:
            assert heading.evaluate('element => { const r = element.getBoundingClientRect(); return element.contains(document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2)); }')
        page.screenshot(path=str(OUTPUT / f'api-case-form-{width}.png'))
        dialog.get_by_role('button', name='取消', exact=True).click()
        page.screenshot(path=str(OUTPUT / f'api-detail-{width}.png'), full_page=True)
    page.set_viewport_size({'width': 1920, 'height': 1080})
    cases[0]['data'].update({'auth_id': 77, 'generated_plan_id': 15, 'openapi_generation': {'fingerprint': 'original-fingerprint'}})
    page.get_by_label('刷新正式用例', exact=True).click()
    original_row = page.locator('.case-table tbody tr').filter(has_text='手工新增客户场景')
    before = json.dumps(cases[0], sort_keys=True)
    saved_count = len(saved_payloads)
    original_row.get_by_role('button', name='复制', exact=True).click()
    copy_dialog = page.get_by_role('dialog', name='复制正式用例')
    expect(copy_dialog).to_be_visible()
    expect(copy_dialog.get_by_label('用例名称')).to_have_value('手工新增客户场景 - 副本')
    expect(copy_dialog.get_by_label('Token / 鉴权信息', exact=True)).to_have_value('77')
    copy_dialog.get_by_label('用例名称').fill('取消的副本')
    copy_dialog.get_by_role('button', name='取消', exact=True).click()
    assert len(saved_payloads) == saved_count
    assert json.dumps(cases[0], sort_keys=True) == before

    original_row.get_by_role('button', name='复制', exact=True).click()
    expect(copy_dialog.get_by_label('用例名称')).to_have_value('手工新增客户场景 - 副本')
    copy_dialog.get_by_label('用例名称').fill('编辑后独立保存的副本')
    copy_dialog.get_by_label('优先级', exact=True).select_option('P1')
    copied_params = json.loads(copy_dialog.get_by_label('请求参数 JSON', exact=True).input_value())
    copied_params['name'] = 'Copied Customer-{{timestamp_ms}}'
    copy_dialog.get_by_label('请求参数 JSON', exact=True).fill(json.dumps(copied_params))
    page.screenshot(path=str(OUTPUT / 'api-case-copy-desktop.png'))
    page.set_viewport_size({'width': 390, 'height': 844})
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    copy_dialog.get_by_role('heading', name='复制正式用例').scroll_into_view_if_needed()
    page.screenshot(path=str(OUTPUT / 'api-case-copy-mobile.png'))
    copy_dialog.get_by_role('button', name='保存为新用例', exact=True).click()
    expect(copy_dialog).not_to_be_visible()
    expect(page.locator('.case-table')).to_contain_text('编辑后独立保存的副本')
    assert len(cases) == 2
    assert cases[1]['id'] != cases[0]['id']
    assert json.dumps(cases[0], sort_keys=True) == before
    copied = saved_payloads[-1]
    assert copied['name'] == '编辑后独立保存的副本'
    assert copied['data']['params']['name'] == 'Copied Customer-{{timestamp_ms}}'
    assert copied['data']['params']['phone'] == '{{random_phone:139}}'
    assert copied['data']['auth_id'] == 77 and copied['data']['priority'] == 'P1'
    assert copied['assertions'] == cases[0]['assertions']
    assert 'generated_plan_id' not in copied['data'] and 'openapi_generation' not in copied['data']
    assert 'id' not in copied and 'execution_records' not in copied and 'updated_at' not in copied

    cases[0]['name'] = '新增客户正常场景_' + 'VeryLongUnbrokenCustomerName' * 5
    drafts[0]['name'] = '[类型错误] POST /business/customer - ' + 'directCustomerType' * 6
    drafts[0]['description'] = 'Schema 自动生成；策略：type；字段：directCustomerType'
    page.get_by_label('刷新正式用例', exact=True).click()
    expect(page.locator('.case-table tbody tr')).to_have_count(2)
    expect(page.locator('.case-table')).to_contain_text(cases[0]['name'])
    page.get_by_role('tab', name='用例草稿').click()
    page.get_by_label('刷新用例草稿', exact=True).click()
    expect(page.locator('.draft-table')).to_contain_text(drafts[0]['name'])
    for width, viewport_height in ((2560, 1369), (1920, 1080), (1440, 960), (1024, 844), (390, 844)):
        page.set_viewport_size({'width': width, 'height': viewport_height})
        page.get_by_role('tab', name='正式用例').click()
        assert_compact_columns(page)
        page.screenshot(path=str(OUTPUT / f'api-detail-compact-cases-{width}.png'), full_page=True)
        page.get_by_role('tab', name='用例草稿').click()
        expect(page.locator('.draft-table tbody tr')).to_have_count(1)
        assert_compact_columns(page)
        expect(page.locator('.draft-table tbody td:nth-child(2) small')).to_have_attribute('title', drafts[0]['description'])
        page.screenshot(path=str(OUTPUT / f'api-detail-compact-drafts-{width}.png'), full_page=True)
    assert not errors, errors
    browser.close()
print('PASS: adaptive layout, compact bounded columns, long-name wrapping, complete row actions, authentication, draft refresh, dynamic values, independent editable copy/save/cancel, desktop/mobile layout')
