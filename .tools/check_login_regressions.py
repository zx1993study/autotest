import argparse
import json
import sys
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
INSTALL = Path('D:/AutotestPlatform')
sys.path.insert(0, str(ROOT / 'backend'))
from app.core.config import settings

parser = argparse.ArgumentParser()
parser.add_argument('--url')
parser.add_argument('--backend-url')
parser.add_argument('--mock-api', action='store_true')
parser.add_argument('--expect-bug', action='store_true')
args = parser.parse_args()
config = json.loads((INSTALL / 'config.json').read_text(encoding='utf-8-sig'))
runtime = json.loads((INSTALL / 'runtime.json').read_text(encoding='utf-8-sig'))
backend_url = (args.backend_url or runtime['url']).rstrip('/')
url = (args.url or backend_url).rstrip('/')
username = config.get('default_admin_username') or settings.default_admin_username
password = config.get('default_admin_password') or settings.default_admin_password
if args.mock_api:
    username, password = 'admin', 'fixture-valid-password'


with sync_playwright() as playwright:
    browser = playwright.chromium.launch()
    scenarios = ['remember_write_denied', 'session_write_denied', 'stale_chunk']
    if not args.expect_bug:
        scenarios += ['remember_read_denied', 'wrong_password', 'external_redirect']
    for scenario in scenarios:
        context = browser.new_context()
        if scenario == 'remember_write_denied':
            context.add_init_script('''const original = Storage.prototype.setItem;
                Storage.prototype.setItem = function(key, value) {
                    if (this === window.localStorage) throw new DOMException('Storage unavailable', 'QuotaExceededError');
                    return original.call(this, key, value);
                };''')
        elif scenario == 'session_write_denied':
            context.add_init_script('''const original = Storage.prototype.setItem;
                Storage.prototype.setItem = function(key, value) {
                    if (this === window.sessionStorage) throw new DOMException('Storage unavailable', 'QuotaExceededError');
                    return original.call(this, key, value);
                };''')
        elif scenario == 'remember_read_denied':
            context.add_init_script('''Object.defineProperty(window, 'localStorage', {
                get() { throw new DOMException('Storage unavailable', 'SecurityError'); }
            });''')
        if args.mock_api:
            def mock_api(route):
                endpoint = route.request.url.split('/api/v1', 1)[1].split('?')[0]
                user = {'id': 1, 'username': 'admin', 'display_name': '管理员', 'roles': ['admin'], 'permissions': ['*']}
                if endpoint == '/auth/bootstrap':
                    data = {'default_username': 'admin', 'password_policy': ''}
                elif endpoint == '/auth/login':
                    if route.request.post_data_json['password'] != password:
                        route.fulfill(status=400, json={'code': 400, 'message': '账号或密码错误', 'data': None})
                        return
                    data = {'access_token': 'ui-test-token', 'expires_in': 3600, 'user': user}
                elif route.request.headers.get('authorization') != 'Bearer ui-test-token':
                    route.fulfill(status=401, json={'code': 401, 'message': '请先登录', 'data': None})
                    return
                elif endpoint == '/auth/me':
                    data = user
                elif endpoint == '/projects/options':
                    data = []
                elif endpoint == '/auth/logout':
                    data = {'logged_out': True}
                else:
                    data = {'summary': {key: 0 for key in ['case_total', 'active_case_total', 'execution_total', 'success_count', 'abnormal_count', 'queued_count', 'running_count', 'pass_rate', 'avg_duration_ms']},
                            'case_groups': [], 'status_distribution': [], 'case_type_distribution': [], 'trend': [], 'recent_records': []}
                route.fulfill(json={'code': 0, 'message': 'success', 'data': data})
            context.route('**/api/v1/**', mock_api)
        elif args.url:
            def proxy(route):
                suffix = route.request.url.split('/api/v1', 1)[1]
                try:
                    response = route.fetch(url=backend_url + '/api/v1' + suffix)
                    route.fulfill(response=response)
                except Exception:
                    route.abort()
            context.route('**/api/v1/**', proxy)
        page = context.new_page()
        requests = []
        page.on('request', lambda request: requests.append(request.url.split('?')[0]))
        failures = []
        page.on('pageerror', lambda error: failures.append(str(error)))
        chunk_blocked = []
        if scenario == 'stale_chunk':
            def block_once(route):
                if not chunk_blocked and 'ReportStatisticsPage-' in route.request.url and route.request.url.endswith('.js'):
                    chunk_blocked.append(route.request.url)
                    route.fulfill(status=404, body='Not Found', headers={'Cache-Control': 'no-store'})
                else:
                    route.continue_()
            context.route('**/assets/*.js', block_once)
        page.goto(url + ('/login?redirect=//example.invalid/' if scenario == 'external_redirect' else '/login'))
        page.get_by_placeholder('请输入账号', exact=True).fill(username)
        page.get_by_placeholder('请输入密码', exact=True).fill('deliberately-invalid-ui-test-password' if scenario == 'wrong_password' else password)
        page.get_by_label('记住密码', exact=True).check()
        if scenario == 'session_write_denied' and not args.expect_bug:
            with page.expect_response(lambda response: '/api/v1/projects/options' in response.url) as protected_response:
                with page.expect_response(lambda response: '/api/v1/auth/login' in response.url) as login_response:
                    page.get_by_role('button', name='登录', exact=True).click()
        else:
            try:
                with page.expect_response(lambda response: '/api/v1/auth/login' in response.url, timeout=10000) as login_response:
                    page.get_by_role('button', name='登录', exact=True).click()
            except Exception:
                print(json.dumps({'scenario': scenario, 'page_errors': failures,
                                  'error_text': page.locator('.login-error').all_text_contents(),
                                  'api_paths': [path for path in requests if '/api/v1/' in path]}, ensure_ascii=False))
                raise
        result = login_response.value.json()
        if scenario == 'wrong_password':
            expect(page.locator('.login-error')).to_have_text('账号或密码错误')
            assert result['code'] != 0
        elif args.expect_bug:
            assert result['code'] == 0
            expect(page.locator('.login-error')).to_have_text('登录失败，请稍后重试')
        else:
            assert result['code'] == 0
            page.wait_for_url('**/reports/statistics*')
            expect(page.get_by_role('button', name='退出登录', exact=True)).to_be_visible()
            me = page.evaluate('''async () => {
                const response = await fetch('/api/v1/auth/me', {headers: {Authorization: 'Bearer ' + sessionStorage.getItem('access_token')}});
                return response.status;
            }''') if scenario != 'session_write_denied' else None
            if me is not None:
                assert me == 200
            if scenario == 'session_write_denied':
                assert protected_response.value.status == 200
                assert protected_response.value.request.headers.get('authorization', '').startswith('Bearer ')
                page.get_by_role('button', name='退出登录', exact=True).click()
                page.wait_for_url('**/login')
                assert not page.evaluate('Boolean(sessionStorage.getItem("access_token"))')
        if scenario == 'stale_chunk':
            assert chunk_blocked
        print(json.dumps({'scenario': scenario, 'login_http_status': login_response.value.status,
                          'result': 'reproduced' if args.expect_bug else 'passed'}))
        context.unroute_all(behavior='ignoreErrors')
        context.close()
    browser.close()
