from __future__ import annotations

import logging
import threading
from collections.abc import Callable

from agent_app.tray.process import AgentProcessManager

try:
    import pystray
    from PIL import Image, ImageDraw
except ModuleNotFoundError as exc:  # pragma: no cover - exercised on machines without tray deps.
    raise RuntimeError("请先安装托盘依赖：pip install -r agent/requirements-core.txt") from exc


class AgentTrayApp:
    """Windows tray controller for the local Autotest Agent."""

    def __init__(self, manager: AgentProcessManager | None = None) -> None:
        self.manager = manager or AgentProcessManager()
        self.watcher_stop = threading.Event()
        self.icon = pystray.Icon(
            "AutotestAgent",
            _build_icon(),
            "Autotest Agent",
            menu=self._menu(),
        )

    def run(self) -> None:
        """Run the tray app and start the Agent after the icon is ready."""

        self.icon.run(setup=self._setup)

    def _setup(self, icon: pystray.Icon) -> None:
        logging.getLogger(__name__).info("Tray icon ready")
        icon.visible = True
        if self.manager.start():
            logging.getLogger(__name__).info("Agent worker start requested")
            _notify(icon, "Autotest Agent", "本地执行节点已启动")
        else:
            logging.getLogger(__name__).warning("Agent worker not started: %s", self.manager.last_error)
            _notify(icon, "Autotest Agent", self.manager.status_text())
        icon.update_menu()
        if hasattr(self, "watcher_stop"):
            threading.Thread(target=self._watch_browser, daemon=True, name="tray-browser-status").start()

    def _menu(self) -> pystray.Menu:
        return pystray.Menu(
            pystray.MenuItem("打开平台", self._wrap(self.manager.open_platform), default=True),
            pystray.MenuItem("设备管理", self._wrap(self.manager.open_devices)),
            pystray.MenuItem("显示当前任务浏览器", self._wrap(self.manager.show_browser), enabled=lambda _: self.manager.can_show_browser()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(lambda _: f"状态：{self.manager.status_text()}", None, enabled=False),
            pystray.MenuItem("启动 Agent", self._wrap(self._start), enabled=lambda _: not self.manager.is_running()),
            pystray.MenuItem("停止 Agent", self._wrap(self._stop), enabled=lambda _: self.manager.is_running()),
            pystray.MenuItem("重启 Agent", self._wrap(self._restart)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("打开配置", self._wrap(self.manager.open_config)),
            pystray.MenuItem("打开日志", self._wrap(self.manager.open_logs)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("退出", self._exit),
        )

    def _start(self) -> None:
        if self.manager.start():
            _notify(self.icon, "Autotest Agent", "本地执行节点已启动")
        else:
            _notify(self.icon, "Autotest Agent", self.manager.status_text())

    def _stop(self) -> None:
        self.manager.stop()
        message = self.manager.last_error if self.manager.is_running() else "本地执行节点已停止"
        _notify(self.icon, "Autotest Agent", message or "已请求停止本地执行节点")

    def _restart(self) -> None:
        if self.manager.restart():
            _notify(self.icon, "Autotest Agent", "本地执行节点已重启")
        else:
            _notify(self.icon, "Autotest Agent", self.manager.status_text())

    def _exit(self, icon: pystray.Icon, _: pystray.MenuItem) -> None:
        self.manager.stop()
        if self.manager.is_running():
            _notify(icon, "Autotest Agent", self.manager.last_error or "Agent 仍在运行")
            return
        self.watcher_stop.set()
        icon.stop()

    def _watch_browser(self):
        last = None
        while not self.watcher_stop.wait(1):
            current = self.manager.current_browser()
            window = current.get("window") or {}
            marker = (window.get("window_id"), window.get("phase"), window.get("focus"), window.get("command_id"), window.get("status"))
            if marker == last:
                continue
            last = marker
            self.icon.update_menu()
            if window.get("status") == "open" and window.get("focus") == "blocked":
                _notify(self.icon, "任务浏览器", f"{window.get('label', '')}：系统未允许窗口自动激活")

    def _wrap(self, action: Callable[[], None]) -> Callable[[pystray.Icon, pystray.MenuItem], None]:
        def handler(icon: pystray.Icon, _: pystray.MenuItem) -> None:
            try:
                action()
            except Exception as exc:  # noqa: BLE001 - tray actions report failures without ending the controller.
                _notify(icon, "Autotest Agent", str(exc))
            icon.update_menu()

        return handler


def main() -> None:
    """Start the Windows tray app."""

    import os
    from pathlib import Path

    from agent_app.utils.file_lease import FileLease

    root = Path(os.getenv("LOCALAPPDATA") or Path.home()) / "AutotestAgent"
    lease = FileLease(root / "tray.lock")
    if not lease.acquire():
        return
    try:
        AgentTrayApp().run()
    finally:
        lease.release()


def _build_icon() -> Image.Image:
    image = Image.new("RGBA", (64, 64), (37, 99, 235, 255))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((8, 8, 56, 56), radius=10, fill=(255, 255, 255, 255))
    draw.rectangle((18, 31, 46, 37), fill=(37, 99, 235, 255))
    draw.polygon([(31, 18), (47, 32), (31, 46)], fill=(37, 99, 235, 255))
    return image


def _notify(icon: pystray.Icon, title: str, message: str) -> None:
    notify = getattr(icon, "notify", None)
    if callable(notify):
        notify(message, title)


if __name__ == "__main__":
    main()
