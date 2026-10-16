from __future__ import annotations

import json
import threading
from urllib.request import urlopen

from client_config import DEFAULT_PLATFORM_URL, platform_url, save_config


class RemoteRuntime:
    def __init__(self, config, config_path, manager, logger, connection_file) -> None:
        self.config = {"server_url": DEFAULT_PLATFORM_URL, **config}
        self.config_path = config_path
        self.manager, self.logger = manager, logger
        self.connection_file = connection_file
        self.window = None
        self.cancelled = threading.Event()
        self.connection_lock = threading.Lock()
        self.remote_loaded = False

    def start(self):
        if self.config.get("auto_start_agent", True):
            threading.Thread(target=self.manager.start, daemon=True).start()
        self.connect(str(self.config.get("server_url") or ""), save=False)

    def status(self):
        return {"server_url": self.config.get("server_url") or DEFAULT_PLATFORM_URL, "agent": self.manager.status_text()}

    def reload(self):
        if self.window is None or self.cancelled.is_set():
            return
        if self.remote_loaded:
            self.window.evaluate_js("window.location.reload()")
        else:
            self.connect(str(self.config.get("server_url") or ""), save=False)

    def install_reload_shortcuts(self):
        if self.window is None or self.cancelled.is_set():
            return
        try:
            self.window.evaluate_js("""(() => {
                if (window.__autotestReloadKeys) return;
                window.__autotestReloadKeys = true;
                document.addEventListener('keydown', event => {
                    if (event.key === 'F5' || (event.ctrlKey && event.key.toLowerCase() === 'r')) {
                        event.preventDefault(); window.location.reload();
                    }
                });
            })()""")
        except Exception as exc:  # noqa: BLE001 - optional shortcuts must not block remote navigation.
            self.logger.warning("Reload shortcut setup failed: %s", type(exc).__name__)

    def connect(self, url: str, save=True):
        if save and not self._local_page():
            return {"error": "设置只能从本地连接窗口修改"}
        next_config = {**self.config, "server_url": url}
        try:
            address = platform_url(next_config)
            next_config["server_url"] = address
            if save:
                save_config(self.config_path, next_config)
            self.config = next_config
        except ValueError as exc:
            self._error(str(exc))
            return {"error": str(exc)}
        except OSError:
            message = "无法保存连接设置，请检查客户端配置目录权限"
            self._error(message)
            return {"error": message}
        threading.Thread(target=self._connect, args=(address,), daemon=True).start()
        return {"connecting": True}

    def _connect(self, address):
        with self.connection_lock:
            try:
                with urlopen(f"{address}/health", timeout=8) as response:
                    state = json.loads(response.read(64 * 1024))
                    if response.status != 200 or state.get("service") != "Autotest Platform" or state.get("ready") is not True:
                        raise RuntimeError("Platform health check failed")
                if not self.cancelled.is_set():
                    self.remote_loaded = True
                    self.window.load_url(address + "/login?redirect=/reports/statistics")
                    self.logger.info("Remote page navigation requested")
            except Exception as exc:  # noqa: BLE001 - network or WebView failure returns a reconnect state.
                self.logger.warning("Connection failed: %s", type(exc).__name__)
                self._error("平台暂时无法连接，请检查地址、网络或服务器状态后重试")

    def _local_page(self):
        if self.window is None:
            return False
        current = str(self.window.get_current_url() or "")
        return not self.remote_loaded and (not current or current.startswith(("file:", "about:", "data:")))

    def _error(self, message):
        if self.window is not None and self._local_page() and not self.cancelled.is_set():
            self.window.evaluate_js(f"showConnectionError({json.dumps(message)})")

    def open_logs(self):
        if self._local_page():
            self.manager.open_logs()


class DesktopBridge:
    def __init__(self, runtime):
        self._runtime = runtime

    def status(self):
        return self._runtime.status()

    def connect(self, url):
        return self._runtime.connect(url)

    def open_logs(self):
        return self._runtime.open_logs()
