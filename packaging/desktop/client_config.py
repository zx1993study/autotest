from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

DEFAULT_PLATFORM_URL = "https://dev-cn-01.yios.cn/autotest"


def data_root() -> Path:
    base = Path(os.getenv("LOCALAPPDATA") or Path.home())
    return base / "AutotestPlatform"


def read_config(path: Path) -> dict:
    if not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise TypeError("Client configuration must be a JSON object")
    return value


def platform_url(config: dict) -> str:
    url = str(config.get("server_url") or DEFAULT_PLATFORM_URL).strip()
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("请输入有效的 HTTPS 平台地址或登录页链接，不要包含账号密码")
    _ = parsed.port
    path = parsed.path.rstrip("/")
    if path.endswith("/login"):
        path = path[:-6]
    elif parsed.query or parsed.fragment:
        raise ValueError("查询参数只能包含在登录页链接中")
    if parsed.scheme == "http" and parsed.hostname not in {"localhost", "127.0.0.1", "::1"} and not config.get("allow_insecure_http"):
        raise ValueError("远程平台需要 HTTPS；内网调试请显式启用 allow_insecure_http")
    return urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))


def save_config(path: Path, config: dict) -> None:
    # Desktop files must never become a second database or secret configuration.
    allowed = {"server_url", "agent_config", "auto_start_agent", "window_width", "window_height", "allow_insecure_http"}
    value = {key: item for key, item in config.items() if key in allowed}
    value["server_url"] = platform_url(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)
