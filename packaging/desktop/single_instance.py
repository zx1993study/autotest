from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import BinaryIO


class InstanceLease:
    """Keep one desktop service alive for each writable data directory."""

    def __init__(self, data_dir: Path) -> None:
        self.path = data_dir / "instance.lock"
        self.handle: BinaryIO | None = None

    def acquire(self) -> bool:
        handle = self.path.open("a+b")
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            handle.close()
            return False
        self.handle = handle
        return True

    def release(self) -> None:
        if self.handle is not None:
            self.handle.close()
            self.handle = None


def focus_existing_window(data_dir: Path, timeout_seconds: float = 5) -> bool:
    if os.name != "nt":
        return False
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            runtime = json.loads((data_dir / "runtime.json").read_text(encoding="utf-8-sig"))
            pid = int(runtime["pid"])
            if _focus_process_window(pid):
                return True
        except (OSError, ValueError, KeyError, TypeError):
            pass
        time.sleep(0.2)
    return False


def _focus_process_window(pid: int) -> bool:
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.IsIconic.argtypes = [wintypes.HWND]
    user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.GetWindowLongW.restype = wintypes.LONG
    user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.SetForegroundWindow.argtypes = [wintypes.HWND]
    found = False

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def visit(hwnd, _):
        nonlocal found
        owner = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        # Windows can initially hide the main form when launched by a hidden helper.
        main_form = user32.IsWindowVisible(hwnd) or user32.GetWindowLongW(hwnd, -16) & 0x00C00000
        if owner.value == pid and main_form:
            user32.ShowWindow(hwnd, 9 if user32.IsIconic(hwnd) else 5)
            user32.SetForegroundWindow(hwnd)
            found = True
            return False
        return True

    user32.EnumWindows.argtypes = [type(visit), wintypes.LPARAM]
    user32.EnumWindows(visit, 0)
    return found
