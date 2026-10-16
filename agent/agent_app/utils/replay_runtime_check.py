"""Isolated localhost smoke check for the packaged replay and video runtime."""
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from agent_app.executors.web_replay_executor import LocalWebReplayExecutor
from agent_app.utils.playwright_runtime import chromium_launch_options


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(b"<html><body><p>Ready</p></body></html>")

    def log_message(self, *args):
        pass


def check():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with tempfile.TemporaryDirectory() as tmp:
            executor = LocalWebReplayExecutor(SimpleNamespace(artifacts_dir=Path(tmp), node_key="fixture"), None)
            executor._state = AsyncMock(return_value={})
            payload = {"project_id": 1, "generation_task_id": 1, "target_url": f"http://127.0.0.1:{server.server_port}", "wait_for_login": False,
                       "candidate": {"name": "Runtime check", "steps": [{"action": "assert", "locator_type": "text", "locator": "Ready", "expected": "Ready"}]}}
            with patch("agent_app.executors.web_replay_executor.chromium_launch_options", return_value=chromium_launch_options(headless=True, slow_mo_ms=0)):
                result = executor.execute(1, "fixture", payload)
            if result["failed_count"] or not Path(result["records"][0]["data"]["video_local_path"]).is_file():
                raise RuntimeError("Replay runtime smoke check failed")
            print("Web replay, strict assertions, screenshots and WebM recording: OK")
    finally:
        server.shutdown()
        server.server_close()
