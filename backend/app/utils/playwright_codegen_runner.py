from __future__ import annotations

import subprocess
import sys
import time
import importlib.util
import json
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4
from typing import Any

from app.utils.cookie_utils import normalize_playwright_cookies


BROWSER_PROCESS_NAMES = {
    "chrome.exe",
    "chromium.exe",
    "msedge.exe",
    "firefox.exe",
    "webkit.exe",
}
CODEGEN_DIR = Path(
    os.getenv("AUTOTEST_CODEGEN_DIR")
    or (Path(tempfile.gettempdir()) / "autotest-codegen")
)
LOG_DIR = Path(
    os.getenv("AUTOTEST_LOG_DIR")
    or (Path(__file__).resolve().parents[3] / "logs")
)
CODEGEN_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class CodegenSession:
    id: str
    url: str
    script_path: Path
    process: subprocess.Popen
    created_at: float
    state_path: Path | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    seen_browser_process: bool = False
    ended_by_browser_close: bool = False
    stopped_by_request: bool = False


class PlaywrightCodegenRunner:
    _sessions: dict[str, CodegenSession] = {}

    def start(
        self,
        url: str,
        cookies: list[dict[str, Any]] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not url:
            raise ValueError("页面地址为空，无法启动 codegen")
        if importlib.util.find_spec("playwright") is None:
            raise RuntimeError("后端未安装 playwright，请先安装依赖并执行 playwright install")
        session_id = uuid4().hex
        script_path = CODEGEN_DIR / f"codegen_{session_id}.py"
        state_path = self._storage_state_path(session_id, cookies or [], url)
        command = [
            sys.executable,
            "-m",
            "playwright",
            "codegen",
            "--target",
            "python",
            "--output",
            str(script_path),
        ]
        if state_path:
            command.extend(["--load-storage", str(state_path)])
        command.append(url)
        try:
            with (
                (LOG_DIR / "playwright-codegen.out.log").open("ab") as stdout_log,
                (LOG_DIR / "playwright-codegen.err.log").open("ab") as stderr_log,
            ):
                process = subprocess.Popen(
                    command,
                    cwd=str(CODEGEN_DIR),
                    stdout=stdout_log,
                    stderr=stderr_log,
                    creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
                )
        except FileNotFoundError as exc:
            raise RuntimeError("无法启动 Python 运行环境") from exc

        self._sessions[session_id] = CodegenSession(
            id=session_id,
            url=url,
            script_path=script_path,
            process=process,
            created_at=time.time(),
            state_path=state_path,
            metadata=dict(metadata or {}),
        )
        return {
            "session_id": session_id,
            "status": "running",
            "script_path": str(script_path),
            "metadata": dict(metadata or {}),
        }

    def _storage_state_path(self, session_id: str, cookies: list[dict[str, Any]], url: str) -> Path | None:
        normalized_cookies = normalize_playwright_cookies(cookies, url)
        if not normalized_cookies:
            return None
        state_path = CODEGEN_DIR / f"storage_state_{session_id}.json"
        state_path.write_text(
            json.dumps({"cookies": normalized_cookies, "origins": []}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return state_path

    def status(self, session_id: str) -> dict[str, Any]:
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError("codegen 会话不存在")

        return_code = session.process.poll()
        script_exists = session.script_path.exists()
        script_text = session.script_path.read_text(encoding="utf-8", errors="ignore") if script_exists else ""
        browser_running = False
        if return_code is None:
            browser_running = bool(self._has_browser_descendant(session.process.pid))
            if browser_running:
                session.seen_browser_process = True
            elif session.seen_browser_process and script_text.strip():
                session.ended_by_browser_close = True
                self._terminate_process_tree(session.process)
                return_code = session.process.poll()

        status = (
            "finished"
            if session.ended_by_browser_close or session.stopped_by_request or return_code is not None
            else "running"
        )
        if return_code not in (None, 0):
            status = "finished" if session.ended_by_browser_close or session.stopped_by_request else "failed"

        return {
            "session_id": session_id,
            "status": status,
            "return_code": return_code,
            "script_path": str(session.script_path),
            "script_exists": script_exists,
            "script_text": script_text,
            "browser_running": browser_running,
            "ended_by_browser_close": session.ended_by_browser_close,
            "stopped_by_request": session.stopped_by_request,
            "metadata": dict(session.metadata),
        }

    def stop(self, session_id: str) -> dict[str, Any]:
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError("codegen 会话不存在")
        if session.process.poll() is None:
            session.stopped_by_request = True
            self._terminate_process_tree(session.process)
        return self.status(session_id)

    def _has_browser_descendant(self, root_pid: int) -> bool:
        if not sys.platform.startswith("win"):
            return False
        processes = self._windows_process_snapshot()
        children_by_parent: dict[int, list[dict[str, Any]]] = {}
        for process in processes:
            children_by_parent.setdefault(int(process["parent_pid"]), []).append(process)

        stack = list(children_by_parent.get(root_pid, []))
        while stack:
            process = stack.pop()
            if str(process["name"]).lower() in BROWSER_PROCESS_NAMES:
                return True
            stack.extend(children_by_parent.get(int(process["pid"]), []))
        return False

    def _windows_process_snapshot(self) -> list[dict[str, Any]]:
        import ctypes
        from ctypes import wintypes

        class PROCESSENTRY32W(ctypes.Structure):
            _fields_ = [
                ("dwSize", wintypes.DWORD),
                ("cntUsage", wintypes.DWORD),
                ("th32ProcessID", wintypes.DWORD),
                ("th32DefaultHeapID", ctypes.c_size_t),
                ("th32ModuleID", wintypes.DWORD),
                ("cntThreads", wintypes.DWORD),
                ("th32ParentProcessID", wintypes.DWORD),
                ("pcPriClassBase", wintypes.LONG),
                ("dwFlags", wintypes.DWORD),
                ("szExeFile", wintypes.WCHAR * 260),
            ]

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        snapshot = kernel32.CreateToolhelp32Snapshot(0x00000002, 0)
        if snapshot == ctypes.c_void_p(-1).value:
            return []

        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
        processes: list[dict[str, Any]] = []
        try:
            has_entry = kernel32.Process32FirstW(snapshot, ctypes.byref(entry))
            while has_entry:
                processes.append(
                    {
                        "pid": int(entry.th32ProcessID),
                        "parent_pid": int(entry.th32ParentProcessID),
                        "name": str(entry.szExeFile),
                    }
                )
                has_entry = kernel32.Process32NextW(snapshot, ctypes.byref(entry))
        finally:
            kernel32.CloseHandle(snapshot)
        return processes

    def _terminate_process_tree(self, process: subprocess.Popen) -> None:
        if process.poll() is not None:
            return
        try:
            if sys.platform.startswith("win"):
                with (
                    (LOG_DIR / "taskkill.out.log").open("ab") as stdout_log,
                    (LOG_DIR / "taskkill.err.log").open("ab") as stderr_log,
                ):
                    subprocess.run(
                        ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                        stdout=stdout_log,
                        stderr=stderr_log,
                        check=False,
                    )
            else:
                process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    return
        except Exception:
            return
