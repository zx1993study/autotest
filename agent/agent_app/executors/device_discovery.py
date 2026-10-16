from __future__ import annotations

import ipaddress
import json
import socket
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlsplit
from urllib.request import ProxyHandler, build_opener


class LocalDeviceDiscovery:
    def __init__(self, node_key):
        self.node_key = node_key

    def execute(self, payload):
        known = payload.get("known_devices") or []
        targets = {}
        for device in known:
            data = device.get("data") or {}
            url = str(data.get("wda_url") or data.get("wdaUrl") or "").rstrip("/")
            if url:
                parsed = urlsplit(url)
                if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
                    raise ValueError("WDA 地址无效")
                targets[url] = device
        subnet = payload.get("subnet")
        if not subnet and payload.get("action") != "check":
            addresses = socket.gethostbyname_ex(socket.gethostname())[2]
            subnet = next((f"{ip}/24" for ip in addresses if ipaddress.ip_address(ip).is_private and not ip.startswith(("127.", "169.254."))), None)
        if subnet and payload.get("action") != "check":
            network = ipaddress.ip_network(subnet, strict=False)
            if network.version != 4 or not network.is_private or network.num_addresses > 256:
                raise ValueError("Discovery is limited to one private IPv4 /24 subnet")
            ports = payload.get("ports") or [8100]
            if len(ports) > 4 or any(not 1 <= int(port) <= 65535 for port in ports):
                raise ValueError("Invalid scan ports")
            for host in network.hosts():
                for port in ports:
                    targets.setdefault(f"http://{host}:{int(port)}", {})
        with ThreadPoolExecutor(max_workers=24) as workers:
            items = [item for item in workers.map(self._probe, targets.items()) if item]
        warnings = ["手机需与执行节点处于可互通网络，WDA 已启动且签名有效；当前插件扫描 iOS WDA 设备。"]
        return {"items": items, "summary": {"total": len(items), "online": len(items), "existing": sum(bool(item.get("existing_id")) for item in items), "new": sum(not item.get("existing_id") for item in items)}, "warnings": warnings, "failed_count": 0, "records": []}

    def _probe(self, target):
        url, device = target
        try:
            opener = build_opener(ProxyHandler({}))
            with opener.open(f"{url}/status", timeout=3 if device else .6) as response:
                raw = json.loads(response.read(1024 * 1024))
            value = raw.get("value") or {}
            if not isinstance(value, dict) or not (value.get("build") or value.get("ios") or value.get("os")):
                return None
            if value.get('ready') is False:
                return None
            data = device.get("data") or {}
            os_info = value.get("os") or {}
            reported_udid = str(value.get('udid') or (value.get('ios') or {}).get('udid') or '')
            return {"name": device.get("name") or os_info.get("name") or url, "platform": "iOS", "udid": data.get("udid") or reported_udid or f"wifi-{url.split('//')[-1]}", "reported_udid":reported_udid, "device_name": data.get("device_name") or device.get("name") or "iOS", "platform_version": data.get("platform_version") or os_info.get("version"), "wda_url": url, "wda_status": "ready", "connection_status": "online", "connection_type": "wifi", "source": "agent_wda_wifi", "node_key": self.node_key, "exists": bool(device), "existing_id": device.get("id")}
        except (OSError, ValueError, TypeError, AttributeError):
            return None
