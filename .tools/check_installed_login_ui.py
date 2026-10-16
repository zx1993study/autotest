import json
import sys
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
INSTALL = Path('D:/AutotestPlatform')
sys.path.insert(0, str(ROOT / 'backend'))
from app.core.config import settings

config = json.loads((INSTALL / 'config.json').read_text(encoding='utf-8-sig'))
runtime = json.loads((INSTALL / 'runtime.json').read_text(encoding='utf-8-sig'))
username = config.get('default_admin_username') or settings.default_admin_username
password = config.get('default_admin_password') or settings.default_admin_password
with sync_playwright() as playwright:
    browser = playwright.chromium.launch()
    context = browser.new_context(viewport={'width': 1366, 'height': 900})
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    entry = page.goto(runtime['url'].rstrip('/') + '/login')
    assert entry and entry.headers.get('cache-control') == 'no-store, max-age=0'
    page.get_by_placeholder('请输入账号', exact=True).fill(username)
    page.get_by_placeholder('请输入密码', exact=True).fill(password)
    page.get_by_role('checkbox', name='记住密码', exact=True).check()
    with page.expect_response(lambda response: response.url.endswith('/api/v1/auth/login')) as response:
        page.get_by_role('button', name='登录', exact=True).click()
    result = response.value.json()
    assert response.value.status == 200 and result['code'] == 0, result.get('message')
    expect(page).to_have_url(runtime['url'].rstrip('/') + '/reports/statistics')
    assert page.evaluate('Boolean(sessionStorage.getItem("access_token"))')
    assert page.evaluate('Boolean(localStorage.getItem("autotest.login.rememberedPassword"))')
    me = page.evaluate('''async () => {
        const response = await fetch('/api/v1/auth/me', {headers: {Authorization: 'Bearer ' + sessionStorage.getItem('access_token')}});
        const body = await response.json();
        return {status: response.status, code: body.code};
    }''')
    assert me == {'status': 200, 'code': 0}, me
    assert not errors, errors
    print(json.dumps({'url': runtime['url'], 'login_status': response.value.status, 'session_saved': True,
                      'redirect': '/reports/statistics', 'current_user_verified': True,
                      'remember_password_verified': True, 'html_no_store': True}))
    browser.close()
