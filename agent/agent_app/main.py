from __future__ import annotations

import argparse
import logging
import sys
import time

from agent_app.config import load_config
from agent_app.runtime.lifecycle import build_poller


def main() -> None:
    """Start the local Autotest Agent process."""

    if "--tray" in sys.argv:
        _run_tray()
        return
    parser = argparse.ArgumentParser(description="Autotest local execution Agent")
    parser.add_argument("--config", help="Path to Agent config.json")
    parser.add_argument("--once", action="store_true", help="Claim and run at most one task")
    parser.add_argument("--check-runtime", action="store_true")
    parser.add_argument("--check-web-replay", action="store_true")
    parser.add_argument("--check-browser-window", action="store_true")
    parser.add_argument("--check-vision-target", action="store_true")
    args = parser.parse_args()
    if args.check_vision_target:
        from agent_app.utils.vision_target_check import check

        check()
        return
    if args.check_browser_window:
        from agent_app.utils.browser_window_check import check

        check()
        return
    if args.check_web_replay:
        from agent_app.utils.replay_runtime_check import check

        check()
        return
    if args.check_runtime:
        if sys.platform == "win32":
            from agent_app.tray import windows_tray  # noqa: F401 - verify frozen tray dependencies, without opening a window.
        from agent_app.runtime.capabilities import available_capabilities

        print(available_capabilities(("mobile", "web", "ai_web")))
        return

    config = load_config(args.config)
    from agent_app.runtime.local_state import runtime_path, write_state
    from agent_app.runtime.stop_request import clear, requested
    from agent_app.utils.file_lease import FileLease

    with FileLease(runtime_path(config.node_key).with_suffix(".lock")):
        clear(config)
        while not requested(config):
            write_state(config, "connecting")
            try:
                poller = build_poller(config)
                if args.once:
                    poller.run_once()
                    return
                poller.run_forever()
                return
            except Exception as exc:
                if args.once:
                    raise
                logging.getLogger(__name__).warning("Registration failed: %s", type(exc).__name__)
                time.sleep(10)


def _run_tray():
    import os
    from pathlib import Path

    logs = Path(os.getenv("LOCALAPPDATA") or Path.home()) / "AutotestAgent" / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=str(logs / "tray.log"), level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", force=True)
    logging.getLogger(__name__).info("Tray controller starting")
    try:
        if sys.platform == "win32" and getattr(sys, "frozen", False):
            import ctypes

            ctypes.windll.kernel32.FreeConsole()
        from agent_app.tray.windows_tray import main as tray_main

        tray_main()
    except Exception:
        logging.getLogger(__name__).exception("Agent tray startup failed")
        raise


if __name__ == "__main__":
    main()

