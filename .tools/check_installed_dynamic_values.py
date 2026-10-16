import hashlib
import json
import re
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
INSTALL = Path('D:/AutotestPlatform')
sys.path.insert(0, str(ROOT / 'backend'))
from app.core.config import settings
from PyInstaller.archive.readers import ZlibArchiveReader

archive = ZlibArchiveReader(str(ROOT / 'packaging/standalone/build/AutotestPlatform/PYZ-00.pyz'))
for module in ('web_automation.dynamic_values', 'app.api.v1.dynamic_values', 'app.scheduler.jobs.api_case_executor'):
    assert module in archive.toc, module

executable = ROOT / 'packaging/standalone/dist/AutotestPlatform/AutotestPlatform.exe'
assert hashlib.sha256(executable.read_bytes()).digest() == hashlib.sha256((INSTALL / 'app/AutotestPlatform.exe').read_bytes()).digest()

source = ROOT / 'frontend/dist'
installed = INSTALL / 'app/_internal/frontend/dist'
files = [file for file in source.rglob('*') if file.is_file()]
for file in files:
    target = installed / file.relative_to(source)
    assert target.is_file(), str(target)
    assert hashlib.sha256(file.read_bytes()).digest() == hashlib.sha256(target.read_bytes()).digest(), str(target)

config = json.loads((INSTALL / 'config.json').read_text(encoding='utf-8-sig'))
runtime = None
for _ in range(60):
    try:
        runtime = json.loads((INSTALL / 'runtime.json').read_text(encoding='utf-8-sig'))
        with urlopen(runtime['url'], timeout=2) as response:
            assert response.status == 200
        break
    except Exception:
        time.sleep(1)
else:
    raise RuntimeError('Installed application did not become ready')


def post(endpoint, payload, token=None):
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    request = Request(runtime['url'].rstrip('/') + '/api/v1' + endpoint,
                      data=json.dumps(payload).encode('utf-8'), headers=headers, method='POST')
    with urlopen(request, timeout=20) as response:
        result = json.loads(response.read())
    assert result['code'] == 0, result.get('message')
    return result['data']


login = post('/auth/login', {'username': config.get('default_admin_username') or settings.default_admin_username,
                             'password': config.get('default_admin_password') or settings.default_admin_password})
token = login['access_token']
template = {'name': 'customer_{{timestamp_ms}}', 'phone': '{{contact_phone}}', 'confirm_phone': '{{contact_phone}}'}
result = post('/testing/dynamic-values/preview', {'value': template, 'variables': {'contact_phone': {'generator': 'phone', 'prefix': '139'}}}, token)
resolved = result['resolved']
assert re.fullmatch(r'customer_\d{13}', resolved['name'])
assert re.fullmatch(r'139\d{8}', resolved['phone'])
assert resolved['phone'] == resolved['confirm_phone']
assert result['dynamic_values']['values']['contact_phone'] == resolved['phone']
print(json.dumps({'installed_url': runtime['url'], 'frontend_files_verified': len(files), 'bundled_runtime_verified': True,
                  'installed_executable_verified': True, 'timestamp_preview': True, 'phone_preview': True, 'same_value_reuse': True}, ensure_ascii=False))
