"""Resolve native app identity before allowing feature operations."""
import re
import unicodedata
from copy import deepcopy
from urllib.parse import urlsplit

from app.core.exceptions import BusinessRuleError
from app.services.app_exploration_service import now, patch_live
from app.services.app_exploration_control_service import ask
from app.services.resource_service import ResourceService


def app_name_matches(actual, expected):
    def normalize(value):
        return ''.join(unicodedata.normalize('NFKC', str(value)).split()).casefold()
    return bool(actual) and normalize(actual) == normalize(expected)


def valid_application(bundle_id):
    return bool(re.fullmatch(r'[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)+', bundle_id)) and \
        bundle_id != 'com.apple.springboard' and not bundle_id.lower().endswith('.xctrunner')


class AppExplorationConnectionService:
    def __init__(self, repository):
        self.repository = repository

    def report(self, task, payload):
        live = deepcopy(task['data']['live'])
        if live['phase'] != 'connecting':
            duplicate = payload.status == 'connected' and (live.get('connection') or {}).get('wda_url') == payload.wda_url.rstrip('/')
            return {'accepted':duplicate, 'bundle_id':task['data']['payload']['bundle_id']}
        if payload.status == 'connected':
            return self.connected(task, live, payload)
        if not live.get('connection'):
            raise BusinessRuleError('请先确认设备连接，再识别应用')
        if task['data']['payload']['bundle_id']:
            raise BusinessRuleError('应用已绑定，不能在运行中改为其他应用')
        if payload.status == 'identified':
            if not valid_application(payload.bundle_id):
                raise BusinessRuleError('不能将手机桌面或 WDA Runner 绑定为目标应用')
            candidate = {'bundle_id':payload.bundle_id, 'app_name':payload.app_name,
                         'observed_at':now(), 'device_id':task['data']['payload']['device']['id']}
            confirmed = live.pop('confirmed_app', None)
            live['app_candidate'] = candidate
            if confirmed and confirmed.get('bundle_id') == payload.bundle_id:
                return self.bind(task, live, 'user_confirmed')
            if app_name_matches(payload.app_name, task['data']['payload']['entry_name']):
                return self.bind(task, live, 'foreground_name')
            ask(live, '已读取前台应用的真实 Bundle ID，请确认手机已打开所选应用后绑定。', 'waiting_app_confirmation')
        else:
            live.pop('app_candidate', None)
            ask(live, '未能唯一定位目标应用。请在手机打开所选应用，然后点击“重新检测应用”。', 'waiting_app')
        patch_live(self.repository, task, live)
        return {'accepted':True, 'bundle_id':''}

    def connected(self, task, live, payload):
        url = payload.wda_url.rstrip('/')
        parsed = urlsplit(url)
        if parsed.scheme not in {'http','https'} or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise BusinessRuleError('设备连接地址无效')
        raw = deepcopy(task['data']['payload'])
        device = ResourceService('app_devices', self.repository).get(raw['device']['id'])
        dd = device.get('data') or {}
        old_url = str(dd.get('wda_url') or dd.get('wdaUrl') or '').rstrip('/')
        legacy_url = f"http://{dd.get('wda_host')}:{dd.get('wda_port') or 8100}" if dd.get('wda_host') else ''
        if url not in {old_url, legacy_url} and (not dd.get('udid') or payload.reported_udid != dd['udid'] or str(dd['udid']).startswith('wifi-')):
            raise BusinessRuleError('无法确认新地址属于所选设备，请在设备池扫描并确认')
        if device.get('status') != 'active' or dd.get('node_key') not in {None, '', task['data']['claimed_by']}:
            raise BusinessRuleError('设备已停用或改绑其他节点')
        live['connection'] = {'wda_url':url, 'status':'online', 'checked_at':now()}
        live['phase'] = 'observing' if raw['bundle_id'] else 'connecting'
        live['events'] = (live['events'] + [{'label':'已连接设备池 WDA', 'status':'success', 'time':now()}])[-100:]
        raw['device'] = {**device, 'data':{**dd, 'wda_url':url}}
        self.persist(task, live, raw, {'table':'app_devices', 'id':device['id'], 'project_id':device.get('project_id'),
            'expected_data':{k:dd.get(k) for k in ('wda_url','wdaUrl','wda_host','wda_port','udid','node_key')},
            'patch':{'wda_url':url, 'wda_status':'online', 'connection_status':'online', 'last_check_at':now()}})
        return {'accepted':True, 'bundle_id':raw['bundle_id']}

    def bind(self, task, live, source):
        candidate = live.get('app_candidate') or {}
        bundle_id = candidate.get('bundle_id', '')
        if not valid_application(bundle_id):
            raise BusinessRuleError('尚未读取有效的目标应用 Bundle ID')
        raw = deepcopy(task['data']['payload'])
        entries = ResourceService('app_entries', self.repository)
        entry = entries.get(raw['entry_id'])
        ed = entry.get('data') or {}
        existing = ed.get('bundle_id') or ed.get('bundleId')
        if entry['status'] != 'active' or entry.get('project_id') != raw['project_id'] or entry['name'] != raw['entry_name'] or (existing and existing != bundle_id):
            raise BusinessRuleError('应用入口已变化，不会覆盖已有 Bundle ID；请重新开始')
        raw['bundle_id'] = bundle_id
        live.update(phase='observing', discovering_app=False, app_candidate=None, nonce=None)
        live['events'] = (live['events'] + [{'label':'已识别应用并保存 Bundle ID', 'status':'success', 'time':now()}])[-100:]
        self.persist(task, live, raw, {'table':'app_entries', 'id':entry['id'], 'name':entry['name'], 'project_id':entry['project_id'],
            'expected_data':{k:ed.get(k) for k in ('bundle_id','bundleId')},
            'patch':{'bundle_id':bundle_id, 'bundle_discovery':{**candidate, 'source':source, 'task_id':task['id']}}})
        return {'accepted':True, 'bundle_id':bundle_id}

    def persist(self, task, live, raw, resource):
        updated = self.repository.resolve_app_connection(task['id'], task['data']['claimed_by'], {
            'patch':{'live':live, 'payload':raw}, 'expected':{'live':task['data']['live'], 'payload':task['data']['payload']},
            'resource':resource})
        if not updated:
            raise BusinessRuleError('连接、应用或任务状态已变化，请重新检测；未覆盖配置')
