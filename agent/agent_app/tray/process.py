from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import webbrowser
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

from agent_app.config import default_config_path, load_config
from agent_app.runtime.local_state import read_state

WINDOWS_CREATE_NO_WINDOW = 0x08000000


class AgentProcessManager:
    """Manage the background Agent process launched by the tray program.

    The tray is intentionally only a lifecycle wrapper. Task polling, browser
    execution and result reporting stay inside ``agent_app.main`` so packaged
    and command-line runs use the same execution path.
    """

    def __init__(
        self,
        config_path: Path | None = None,
        log_dir: Path | None = None,
    ) -> None:
        self.config_path = Path(config_path).expanduser() if config_path else default_config_path()
        self.log_dir = Path(log_dir or _default_log_dir())
        self.process: subprocess.Popen[bytes] | None = None
        self.last_error = ""
        self._log_handle: object | None = None

    def start(self) -> bool:
        """Start the Agent if it is not already running."""

        if self.is_running():
            return True
        if not self.config_path.exists():
            self.last_error = "尚未配置 Agent，请在平台生成节点 Token 并配置本机"
            return False
        from agent_app.runtime.stop_request import clear

        self.last_error = ""
        self.log_dir.mkdir(parents=True, exist_ok=True)
        try:
            clear(load_config(str(self.config_path)))
            self._close_log_handle()
            self._log_handle = self._open_log_file()
            self.process = subprocess.Popen(
                self._command(),
                cwd=str(Path(sys.executable).resolve().parent if _is_frozen() else Path(__file__).resolve().parents[2]),
                stdin=subprocess.DEVNULL,
                stdout=self._log_handle,
                stderr=subprocess.STDOUT,
                creationflags=WINDOWS_CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            return True
        except (OSError, ValueError) as exc:
            self.last_error = f"Agent 启动失败：{exc}"
            self.process = None
            self._close_log_handle()
            return False

    def stop(self, timeout_sec: int = 10) -> None:
        """Stop the Agent process owned by this tray instance."""

        if read_state(self.config_path).get("status") in {"busy", "uploading"}:
            self.last_error = "任务执行或结果上传中，暂时不能停止 Agent"
            return
        if self.is_running():
            from agent_app.runtime.stop_request import request

            request(load_config(str(self.config_path)))
            deadline = time.monotonic() + timeout_sec
            while self.is_running() and time.monotonic() < deadline:
                time.sleep(.2)
            if self.is_running():
                self.last_error = "已请求安全停止，等待当前网络请求结束"
                return
        self.process = None
        self._close_log_handle()

    def restart(self) -> bool:
        """Restart the Agent and return whether it started successfully."""

        self.stop()
        if self.is_running():
            return False
        return self.start()

    def is_running(self) -> bool:
        """Return whether the owned Agent process is alive."""

        return (self.process is not None and self.process.poll() is None) or bool(read_state(self.config_path))

    def status_text(self) -> str:
        """Return a short status string suitable for tray menu text."""

        state = read_state(self.config_path)
        if state:
            return {"connecting": "连接中", "busy": "执行中", "uploading": "结果上传中", "online": "运行中"}.get(state.get("status"), "运行中")
        if self.is_running():
            return "运行中"
        if self.process is not None:
            return f"已退出({self.process.poll()})，请查看日志"
        if self.last_error:
            return self.last_error
        return "未运行"

    def open_config(self) -> None:
        """Open the config file or its parent directory with the OS shell."""

        target = self.config_path if self.config_path.exists() else self.config_path.parent
        _open_path(target)

    def open_logs(self) -> None:
        """Open the local logs directory with the OS shell."""

        self.log_dir.mkdir(parents=True, exist_ok=True)
        _open_path(self.log_dir)

    def open_platform(self) -> None:
        self._open_platform_page("")

    def open_devices(self) -> None:
        self._open_platform_page("app/devices")

    def current_browser(self):
        from agent_app.windows.local_control import read_window

        try:
            return read_window(load_config(str(self.config_path)))
        except (OSError, ValueError):
            return {}

    def can_show_browser(self):
        current = self.current_browser()
        state = read_state(self.config_path)
        return current.get("task_id") == state.get("current_task_id") and (current.get("window") or {}).get("status") == "open"

    def show_browser(self):
        from agent_app.windows.local_control import request_local_show

        if not self.can_show_browser():
            raise ValueError("\u6ca1\u6709\u8fd0\u884c\u4e2d\u7684\u4efb\u52a1\u6d4f\u89c8\u5668")
        request_local_show(load_config(str(self.config_path)))

    def _open_platform_page(self, page: str) -> None:
        config = json.loads(self.config_path.read_text(encoding="utf-8-sig"))
        url = str(config.get("server_url") or "").rstrip("/")
        if url.endswith("/api/v1"):
            url = url[:-7]
        parsed = urlsplit(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username:
            raise ValueError("请先配置有效的平台地址")
        webbrowser.open(f"{url}/{page}")

    def _command(self) -> list[str]:
        if _is_frozen():
            candidates = [Path(sys.executable).with_name("AutotestAgent.exe"), Path(os.getenv("LOCALAPPDATA") or Path.home()) / "AutotestAgent" / "AutotestAgent.exe", Path(sys.executable).resolve().parents[1] / "agent" / "AutotestAgent.exe", Path(sys.executable).resolve().parents[1] / "AutotestAgent" / "AutotestAgent.exe"]
            runner = next((path for path in candidates if path.exists()), None)
            if runner is None:
                raise FileNotFoundError("请先安装本地 Agent")
            return [str(runner), "--config", str(self.config_path)]
        return [sys.executable, "-m", "agent_app.main", "--config", str(self.config_path)]

    def _open_log_file(self) -> object:
        filename = datetime.now().strftime("agent-%Y%m%d.log")
        return (self.log_dir / filename).open("ab")

    def _close_log_handle(self) -> None:
        handle = self._log_handle
        self._log_handle = None
        if handle is not None:
            close = getattr(handle, "close", None)
            if callable(close):
                close()


def _default_log_dir() -> Path:
    base_dir = os.getenv("LOCALAPPDATA")
    if base_dir:
        return Path(base_dir) / "AutotestAgent" / "logs"
    return Path.home() / ".autotest-agent" / "logs"


def _is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def _open_path(path: Path) -> None:
    if os.name == "nt":
        os.startfile(str(path))  # type: ignore[attr-defined]
        return
    subprocess.Popen(["xdg-open", str(path)])
