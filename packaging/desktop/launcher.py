from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path


def main():
    if not getattr(sys, "frozen", False):
        root = Path(__file__).resolve().parents[2]
        sys.path.insert(0, str(root / "agent"))
        sys.path.insert(0, str(root / "packaging" / "desktop"))
    import webview
    from agent_app.tray.process import AgentProcessManager
    from client_config import data_root, read_config
    from remote_runtime import DesktopBridge, RemoteRuntime
    from single_instance import InstanceLease, focus_existing_window
    from webview.menu import Menu, MenuAction

    parser = argparse.ArgumentParser(description="Autotest remote desktop client")
    parser.add_argument("--config")
    parser.add_argument("--check-runtime", action="store_true")
    args = parser.parse_args()
    root = data_root()
    root.mkdir(parents=True, exist_ok=True)
    if args.check_runtime:
        print("Remote desktop runtime OK; no backend or database loaded")
        return
    config_path = Path(args.config) if args.config else root / "client.json"
    (root / "logs").mkdir(exist_ok=True)
    logging.basicConfig(filename=str(root / "logs" / "desktop.log"), level=logging.INFO, format="%(asctime)s %(message)s")
    try:
        config = read_config(config_path)
    except (OSError, ValueError, TypeError):
        config = {}
        logging.getLogger("desktop").warning("Client configuration could not be read; reconnect from the local page")
    (root / "desktop").mkdir(exist_ok=True)
    lease = InstanceLease(root / "desktop")
    if not lease.acquire():
        focus_existing_window(root / "desktop")
        return
    try:
        (root / "desktop" / "runtime.json").write_text(json.dumps({"pid": os.getpid()}), encoding="utf-8")
        manager = AgentProcessManager(Path(config["agent_config"]) if config.get("agent_config") else None)
        connection = Path(__file__).with_name("connection.html")
        runtime = RemoteRuntime(config, config_path, manager, logging.getLogger("desktop"), connection)
        window = webview.create_window("Autotest Platform", html=connection.read_text(encoding="utf-8"), js_api=DesktopBridge(runtime), width=int(config.get("window_width") or 1440), height=int(config.get("window_height") or 900), min_size=(800, 600))
        runtime.window = window
        window.events.loaded += runtime.install_reload_shortcuts
        window.events.closed += lambda: runtime.cancelled.set()
        webview.start(runtime.start, gui="edgechromium", private_mode=False, storage_path=str(root / "webview-remote"), menu=[Menu("视图", [MenuAction("刷新页面", runtime.reload)])])
    finally:
        # Closing the desktop intentionally leaves execution owned by the Agent.
        lease.release()


if __name__ == "__main__":
    main()
