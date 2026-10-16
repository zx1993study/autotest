"""Read device/app identities without guessing IDs or switching arbitrary apps."""
import ipaddress
from copy import deepcopy
from urllib.parse import urlsplit
from xml.etree import ElementTree

from agent_app.executors.device_discovery import LocalDeviceDiscovery


class AppConnectionError(ValueError):
    pass


def resolve_device(device, node_key):
    data = device.get('data') or {}
    url = str(data.get('wda_url') or data.get('wdaUrl') or '').rstrip('/')
    if not url and data.get('wda_host'):
        url = f"http://{data['wda_host']}:{data.get('wda_port') or 8100}"
    scanner = LocalDeviceDiscovery(node_key)
    known = {**device, 'data':{**data, 'wda_url':url}}
    items = scanner.execute({'action':'check', 'known_devices':[known]})['items'] if url else []
    udid = str(data.get('udid') or '')
    if items and items[0].get('reported_udid') and udid and items[0]['reported_udid'] != udid:
        raise AppConnectionError('设备池地址对应另一台手机，请扫描并确认设备；未操作该手机。')
    if not items:
        scan = {'action':'scan', 'known_devices':[]}
        if url:
            parsed = urlsplit(url)
            try:
                ip = ipaddress.ip_address(parsed.hostname)
                if ip.version != 4 or not ip.is_private or ip.is_loopback:
                    raise ValueError()
                scan.update(subnet=f'{ip}/24', ports=[parsed.port or 8100])
            except ValueError:
                raise AppConnectionError('设备池 WDA 地址无法连接，请检查 WDA 并在设备池刷新连接。') from None
        found = scanner.execute(scan)['items']
        items = [item for item in found if udid and not udid.startswith('wifi-') and item.get('reported_udid') == udid]
        if len(items) != 1:
            raise AppConnectionError('设备池 WDA 地址无法连接，重新扫描未找到可确认属于该设备的地址。请检查同一网络、WDA 签名与运行状态，并在设备池确认扫描结果。')
    resolved = deepcopy(device)
    resolved['data'] = {**data, 'wda_url':items[0]['wda_url']}
    return resolved, items[0]


def foreground_identity(session):
    current = session.app_current()
    bundle_id = str(current.get('bundleId') or '')
    if not bundle_id:
        raise AppConnectionError('WDA 未返回前台应用标识，请在手机打开目标应用后重新连接。')
    name = str(current.get('name') or '')
    if not name and bundle_id != 'com.apple.springboard':
        xml = session.source()
        if len(xml) > 2_000_000 or '<!DOCTYPE' in xml.upper() or '<!ENTITY' in xml.upper():
            raise AppConnectionError('应用元素树无效，不能确认应用身份。')
        root = ElementTree.fromstring(xml)
        app = next((n for n in root.iter() if (n.attrib.get('type') or n.tag) == 'XCUIElementTypeApplication'), None)
        name = (app.attrib.get('name') or app.attrib.get('label') or '') if app is not None else ''
    if session.app_current().get('bundleId') != bundle_id:
        raise AppConnectionError('读取应用信息时前台应用已切换，未绑定；请重新检测。')
    return {'bundle_id':bundle_id, 'app_name':name[:240]}
