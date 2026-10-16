import json
import re
from copy import deepcopy
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import expect, sync_playwright
from web_automation.dynamic_values import prepare_dynamic_execution

OUTPUT = Path(__file__).resolve().parents[1] / 'backend/storage/ui-checks'
scenario = {'id': 2, 'name': '新增客户', 'project_id': 10, 'status': 'active', 'data': {
    'feature_id': 1, 'device_id': 3, 'variables': {},
    'input_info': {'name': {'label': '客户名称', 'value': '测试客户'}, 'phone': {'label': '手机号', 'value': ''}},
    'operation_steps': [{'name': '输入名称', 'action': 'input', 'input_key': 'name'}]}}
web_case = {'id': 4, 'name': 'Web 新增客户', 'project_id': 10, 'status': 'active', 'data': {'case_type': 'WEB', 'variables': {}},
            'steps': [{'name': '客户', 'action': 'fill', 'locator': '#name', 'value': '测试客户'}], 'assertions': []}
saved = []
executed = []
runs = []


def intercept(route):
    endpoint = urlparse(route.request.url).path.removeprefix('/api/v1')
    method = route.request.method
    data = {'items': [], 'total': 0, 'page': 1, 'pageSize': 20}
    if endpoint == '/auth/me':
        data = {'id': 1, 'username': 'admin', 'display_name': '管理员', 'role': 'admin'}
    elif endpoint == '/projects/options':
        data = [{'id': 10, 'name': '测试项目', 'is_default': True, 'data': {'is_default': True}}]
    elif endpoint == '/app-testing/devices/options':
        data = [{'id': 3, 'name': 'iPhone'}]
    elif endpoint == '/testing/dynamic-values/preview':
        payload = route.request.post_data_json
        case, _, context = prepare_dynamic_execution({'data': {'value': payload['value'], 'variables': payload.get('variables', {})}}, {})
        data = {'resolved': case['data']['value'], 'dynamic_values': context.snapshot()}
    elif endpoint == '/app-testing/scenarios/2':
        if method == 'PUT':
            payload = route.request.post_data_json
            saved.append(deepcopy(payload))
            scenario['data'].update(payload)
        data = scenario
    elif endpoint == '/app-testing/scenarios/2/run':
        payload = route.request.post_data_json
        executed.append(deepcopy(payload))
        case, _, context = prepare_dynamic_execution({'data': {'input_info': payload['input_info'], 'variables': payload['variables']}}, {})
        run = {'id': len(runs) + 1, 'name': '执行记录', 'status': 'success', 'data': {'dynamic_values': context.snapshot(), 'input_snapshot': case['data']['input_info']}}
        runs.insert(0, run)
        data = {'run': run, 'execution_record': {}}
    elif endpoint == '/app-testing/scenarios/2/runs':
        data = {'items': runs, 'total': len(runs), 'page': 1, 'pageSize': 20}
    elif endpoint == '/web-testing/cases':
        data = {'items': [web_case], 'total': 1, 'page': 1, 'pageSize': 20}
    elif endpoint == '/web-testing/cases/4' and method == 'PUT':
        payload = route.request.post_data_json
        saved.append(deepcopy(payload))
        web_case.update(payload)
        data = web_case
    route.fulfill(json={'code': 0, 'message': 'success', 'data': data})


with sync_playwright() as playwright:
    browser = playwright.chromium.launch()
    context = browser.new_context(viewport={'width': 1440, 'height': 960})
    context.add_init_script("sessionStorage.setItem('access_token', 'ui-test');")
    context.route('**/api/v1/**', intercept)
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto('http://127.0.0.1:5173/app/features/1/scenarios/2')
    page.get_by_label('客户名称生成方式', exact=True).select_option('timestamp_ms')
    expect(page.get_by_label('客户名称', exact=True)).to_have_value('测试客户_{{timestamp_ms}}')
    page.get_by_label('手机号生成方式', exact=True).select_option('phone')
    page.get_by_label('手机号预览动态值', exact=True).click()
    expect(page.get_by_label('手机号动态值预览', exact=True)).to_have_text(re.compile(r'^138\d{8}$'))
    page.get_by_text('命名变量', exact=True).click()
    page.get_by_label('变量定义 JSON', exact=True).fill(json.dumps({'contact_phone': {'generator': 'phone', 'prefix': '139'}}))
    page.get_by_label('手机号', exact=True).fill('{{contact_phone}}')
    page.get_by_role('button', name='保存输入信息', exact=True).click()
    expect(page.get_by_text('输入信息已保存', exact=True)).to_be_visible()
    assert saved[-1]['input_info']['phone']['value'] == '{{contact_phone}}'
    assert saved[-1]['variables']['contact_phone']['prefix'] == '139'
    page.get_by_role('button', name='执行场景', exact=True).click()
    page.get_by_text('本次动态输入值', exact=True).click()
    expect(page.locator('.dynamic-value-evidence')).to_contain_text('contact_phone')
    assert executed[-1]['input_info']['phone'] == '{{contact_phone}}'
    assert re.fullmatch(r'139\d{8}', runs[0]['data']['input_snapshot']['phone'])
    page.screenshot(path=str(OUTPUT / 'dynamic-app-desktop.png'), full_page=True)
    page.set_viewport_size({'width': 390, 'height': 844})
    page.evaluate('window.scrollTo(0, 0)')
    page.wait_for_function('document.querySelector(".sidebar").getBoundingClientRect().right <= 0')
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    page.screenshot(path=str(OUTPUT / 'dynamic-app-mobile.png'), full_page=True)
    page.set_viewport_size({'width': 1440, 'height': 960})
    page.goto('http://127.0.0.1:5173/web/cases')
    page.get_by_role('button', name='编辑', exact=True).click()
    dialog = page.get_by_role('dialog')
    expect(dialog.get_by_label('执行步骤 JSON', exact=True)).to_be_visible()
    selector = dialog.get_by_label('执行步骤 JSON动态字段', exact=True)
    selector.select_option('[0,"value"]')
    dialog.get_by_label('执行步骤 JSON字段值生成方式', exact=True).select_option('timestamp_ms')
    expect(dialog.get_by_label('执行步骤 JSON字段值', exact=True)).to_have_value('测试客户_{{timestamp_ms}}')
    dialog.get_by_role('button', name='保存', exact=True).click()
    expect(dialog).not_to_be_visible()
    assert saved[-1]['steps'][0]['value'] == '测试客户_{{timestamp_ms}}'
    assert not errors, errors
    browser.close()
print('PASS: App named variables, template save, simulated execution/evidence, Web step editor, desktop/mobile layouts')
