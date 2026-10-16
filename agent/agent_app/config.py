from __future__ import annotations

import json
import os
import platform
import socket
import sys
from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_CONFIG_PATH = Path.home() / ".autotest-agent" / "config.json"
AGENT_TOKEN_PREFIX = "agt_"


@dataclass(frozen=True)
class AgentConfig:
    """Runtime configuration for the local execution Agent."""

    server_url: str
    token: str
    node_key: str
    node_name: str
    version: str = "0.1.0"
    poll_interval_sec: int = 3
    heartbeat_interval_sec: int = 15
    artifacts_dir: Path = field(default_factory=lambda: Path.cwd() / "agent_artifacts")
    capabilities: tuple[str, ...] = ("case_execution",)
    plugins: tuple[str, ...] = ("mobile", "web", "ai_web")

    @property
    def system_info(self) -> dict[str, str]:
        """Return stable host metadata for node registration and heartbeat."""

        return {
            "hostname": socket.gethostname(),
            "platform": platform.platform(),
            "python": platform.python_version(),
        }


def load_config(config_path: str | None = None) -> AgentConfig:
    """Load Agent configuration from JSON and environment variables.

    Environment variables intentionally override the config file so packaged
    deployments can inject secrets without rewriting files.
    """

    raw = _load_json_config(config_path)
    server_url = _read_value(raw, "server_url", "AUTOTEST_SERVER_URL").rstrip("/")
    token = _read_agent_token(raw)
    node_key = _read_value(raw, "node_key", "AUTOTEST_AGENT_NODE_KEY")
    node_name = _read_value(raw, "node_name", "AUTOTEST_AGENT_NODE_NAME") or node_key
    if not server_url:
        raise ValueError("请配置 AUTOTEST_SERVER_URL 或 config.json server_url")
    if not token:
        raise ValueError("请配置 AUTOTEST_AGENT_TOKEN 或 config.json agent_token")
    if not node_key:
        raise ValueError("请配置 AUTOTEST_AGENT_NODE_KEY 或 config.json node_key")
    artifacts_dir = Path(
        os.path.expandvars(
            _read_value(raw, "artifacts_dir", "AUTOTEST_AGENT_ARTIFACTS_DIR") or "agent_artifacts"
        )
    ).expanduser()
    from agent_app.runtime.capabilities import available_capabilities

    plugins = tuple(str(item) for item in raw.get("plugins", ["mobile", "web", "ai_web"]))
    capabilities = available_capabilities(plugins)
    return AgentConfig(
        server_url=server_url,
        token=token,
        node_key=node_key,
        node_name=node_name,
        version=str(raw.get("version") or os.getenv("AUTOTEST_AGENT_VERSION") or "0.1.0"),
        poll_interval_sec=int(
            raw.get("poll_interval_sec") or os.getenv("AUTOTEST_AGENT_POLL_INTERVAL") or 3
        ),
        heartbeat_interval_sec=int(
            raw.get("heartbeat_interval_sec") or os.getenv("AUTOTEST_AGENT_HEARTBEAT_INTERVAL") or 15
        ),
        artifacts_dir=artifacts_dir,
        capabilities=capabilities,
        plugins=plugins,
    )


def default_config_path() -> Path:
    """Return the config file path that matches the current runtime.

    Packaged Windows installs keep ``config.json`` next to the executables
    under ``%LOCALAPPDATA%\\AutotestAgent``. Source runs keep the historical
    user-home path, so developers can run the Agent without installing it.
    """

    env_path = os.getenv("AUTOTEST_AGENT_CONFIG")
    if env_path:
        return Path(os.path.expandvars(env_path)).expanduser()

    if _is_frozen():
        user_config = Path(os.getenv("LOCALAPPDATA") or Path.home()) / "AutotestAgent" / "config.json"
        if user_config.exists() or not Path(sys.executable).stem.startswith("AutotestAgent"):
            return user_config
        installed_path = Path(sys.executable).resolve().parent / "config.json"
        if installed_path.exists():
            return installed_path

    return DEFAULT_CONFIG_PATH


def _load_json_config(config_path: str | None) -> dict[str, object]:
    path = Path(config_path).expanduser() if config_path else default_config_path()
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8-sig") as file:
        value = json.load(file)
    return value if isinstance(value, dict) else {}


def _read_value(raw: dict[str, object], key: str, env_key: str) -> str:
    value = os.getenv(env_key)
    if value is not None:
        return value.strip()
    raw_value = raw.get(key)
    return str(raw_value or "").strip()


def _read_agent_token(raw: dict[str, object]) -> str:
    """Read the node-scoped Agent token while tolerating legacy config files.

    Older local packages and a few manual setups used ``token`` for the Agent
    credential. User JWTs may also be stored under ``token``, so we only let
    that legacy field override ``agent_token`` when it has the Agent token
    prefix issued by the platform.
    """

    env_token = os.getenv("AUTOTEST_AGENT_TOKEN")
    if env_token is not None:
        return env_token.strip()

    agent_token = str(raw.get("agent_token") or "").strip()
    legacy_token = str(raw.get("token") or "").strip()
    if legacy_token.startswith(AGENT_TOKEN_PREFIX):
        return legacy_token
    return agent_token or legacy_token


def _is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))
