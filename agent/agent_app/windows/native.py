"""Task-owned Win32 windows; never locate a browser by its title."""
from __future__ import annotations

import ctypes
import os
import queue
import threading
from ctypes import wintypes as wt
from pathlib import Path


class PROCESSENTRY32(ctypes.Structure):
    _fields_ = [("size", wt.DWORD), ("usage", wt.DWORD), ("pid", wt.DWORD), ("heap", ctypes.c_size_t),
                ("module", wt.DWORD), ("threads", wt.DWORD), ("parent", wt.DWORD), ("priority", wt.LONG),
                ("flags", wt.DWORD), ("exe", wt.WCHAR * 260)]


class FLASHWINFO(ctypes.Structure):
    _fields_ = [("size", wt.UINT), ("hwnd", wt.HWND), ("flags", wt.DWORD), ("count", wt.UINT), ("timeout", wt.DWORD)]


class Win32:
    def __init__(self):
        self.user = ctypes.WinDLL("user32", use_last_error=True)
        self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        definitions = {
            self.kernel: {
                "CreateToolhelp32Snapshot": ([wt.DWORD, wt.DWORD], wt.HANDLE),
                "Process32FirstW": ([wt.HANDLE, ctypes.POINTER(PROCESSENTRY32)], wt.BOOL),
                "Process32NextW": ([wt.HANDLE, ctypes.POINTER(PROCESSENTRY32)], wt.BOOL),
                "OpenProcess": ([wt.DWORD, wt.BOOL, wt.DWORD], wt.HANDLE),
                "QueryFullProcessImageNameW": ([wt.HANDLE, wt.DWORD, wt.LPWSTR, ctypes.POINTER(wt.DWORD)], wt.BOOL),
                "GetProcessTimes": ([wt.HANDLE, *[ctypes.POINTER(wt.FILETIME)] * 4], wt.BOOL),
                "CloseHandle": ([wt.HANDLE], wt.BOOL),
            },
            self.user: {
                "EnumWindows": ([ctypes.c_void_p, wt.LPARAM], wt.BOOL),
                "GetWindowThreadProcessId": ([wt.HWND, ctypes.POINTER(wt.DWORD)], wt.DWORD),
                "GetClassNameW": ([wt.HWND, wt.LPWSTR, ctypes.c_int], ctypes.c_int),
                "IsWindow": ([wt.HWND], wt.BOOL), "IsWindowVisible": ([wt.HWND], wt.BOOL),
                "IsIconic": ([wt.HWND], wt.BOOL), "GetForegroundWindow": ([], wt.HWND),
                "GetWindow": ([wt.HWND, wt.UINT], wt.HWND),
                "GetWindowRect": ([wt.HWND, ctypes.POINTER(wt.RECT)], wt.BOOL),
                "SetForegroundWindow": ([wt.HWND], wt.BOOL), "BringWindowToTop": ([wt.HWND], wt.BOOL),
                "ShowWindow": ([wt.HWND, ctypes.c_int], wt.BOOL),
                "FlashWindowEx": ([ctypes.POINTER(FLASHWINFO)], wt.BOOL),
                "CreateWindowExW": ([wt.DWORD, wt.LPCWSTR, wt.LPCWSTR, wt.DWORD, *[ctypes.c_int] * 4,
                                     wt.HWND, wt.HMENU, wt.HINSTANCE, ctypes.c_void_p], wt.HWND),
                "DestroyWindow": ([wt.HWND], wt.BOOL), "SetWindowTextW": ([wt.HWND, wt.LPCWSTR], wt.BOOL),
                "SetWindowPos": ([wt.HWND, wt.HWND, *[ctypes.c_int] * 4, wt.UINT], wt.BOOL),
                "SendMessageW": ([wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM], wt.LPARAM),
                "PeekMessageW": ([ctypes.POINTER(wt.MSG), wt.HWND, wt.UINT, wt.UINT, wt.UINT], wt.BOOL),
                "TranslateMessage": ([ctypes.POINTER(wt.MSG)], wt.BOOL),
                "DispatchMessageW": ([ctypes.POINTER(wt.MSG)], wt.LPARAM),
            },
        }
        for library, functions in definitions.items():
            for name, (args, result) in functions.items():
                function = getattr(library, name)
                function.argtypes, function.restype = args, result

    def windows(self):
        result = []

        @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
        def visit(hwnd, _):
            name, pid = ctypes.create_unicode_buffer(128), wt.DWORD()
            self.user.GetClassNameW(hwnd, name, len(name))
            if name.value == "Chrome_WidgetWin_1":
                self.user.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                result.append((hwnd, pid.value))
            return True

        self.user.EnumWindows(visit, 0)
        return result

    def descendants(self):
        parents = {}
        snapshot = self.kernel.CreateToolhelp32Snapshot(2, 0)
        if snapshot == ctypes.c_void_p(-1).value:
            return set()
        try:
            entry = PROCESSENTRY32(size=ctypes.sizeof(PROCESSENTRY32))
            more = self.kernel.Process32FirstW(snapshot, ctypes.byref(entry))
            while more:
                parents[entry.pid] = entry.parent
                more = self.kernel.Process32NextW(snapshot, ctypes.byref(entry))
        finally:
            self.kernel.CloseHandle(snapshot)
        owned = {os.getpid()}
        for _ in range(32):
            expanded = owned | {pid for pid, parent in parents.items() if parent in owned}
            if expanded == owned:
                break
            owned = expanded
        return owned

    def fingerprint(self, pid):
        handle = self.kernel.OpenProcess(0x1000, False, pid)
        if not handle:
            return None
        try:
            name, size = ctypes.create_unicode_buffer(32768), wt.DWORD(32768)
            times = [wt.FILETIME() for _ in range(4)]
            if not self.kernel.QueryFullProcessImageNameW(handle, 0, name, ctypes.byref(size)):
                return None
            if not self.kernel.GetProcessTimes(handle, *[ctypes.byref(t) for t in times]):
                return None
            return (times[0].dwHighDateTime << 32 | times[0].dwLowDateTime, name.value)
        finally:
            self.kernel.CloseHandle(handle)


class NativeBrowserWindow:
    def __init__(self, label):
        self.label = label
        self.phase = "starting"
        self.api = Win32() if os.name == "nt" else None
        self.before = set(self.api.windows()) if self.api else set()
        self.binding = None
        self.strip = None
        self.status, self.browser_name = "opening", ""
        self.ready = threading.Event()
        self.stopped = threading.Event()
        self.actions = queue.Queue()
        self.thread = None

    def start(self):
        if not self.api:
            self.status = "unavailable"
            self.ready.set()
            return
        self.thread = threading.Thread(target=self._run, name="browser-window", daemon=True)
        self.thread.start()

    def _find(self):
        owned = self.api.descendants()
        candidates = [(h, p) for h, p in self.api.windows() if (h, p) not in self.before and p in owned
                      and self.api.user.IsWindowVisible(h) and not self.api.user.GetWindow(h, 4)]
        candidates = [(h, p, f) for h, p in candidates if (f := self.api.fingerprint(p))
                      and Path(f[1]).name.lower() in {"chrome.exe", "msedge.exe"}]
        # Multiple new windows are ambiguous: do not guess or touch a personal browser.
        if len(candidates) == 1:
            self.binding = candidates[0]
            path = self.binding[2][1].lower()
            self.browser_name = "Microsoft Edge" if path.endswith("msedge.exe") else "Chromium" if "ms-playwright" in path else "Google Chrome"
            self.status = "open"
            self.ready.set()

    def valid(self):
        if not self.binding or not self.api:
            return False
        hwnd, pid, identity = self.binding
        actual = wt.DWORD()
        self.api.user.GetWindowThreadProcessId(hwnd, ctypes.byref(actual))
        return bool(self.api.user.IsWindow(hwnd) and actual.value == pid and self.api.fingerprint(pid) == identity)

    def focus(self):
        if not self.thread or self.stopped.is_set():
            return "failed"
        result = queue.Queue(maxsize=1)
        self.actions.put(result)
        try:
            return result.get(timeout=4)
        except queue.Empty:
            return "failed"

    def _focus(self):
        if not self.valid():
            return "failed"
        hwnd = self.binding[0]
        if self.api.user.IsIconic(hwnd):
            self.api.user.ShowWindow(hwnd, 9)
        self.api.user.BringWindowToTop(hwnd)
        self.api.user.SetForegroundWindow(hwnd)
        if self.api.user.GetForegroundWindow() == hwnd:
            return "active"
        self.api.user.FlashWindowEx(ctypes.byref(FLASHWINFO(ctypes.sizeof(FLASHWINFO), hwnd, 3, 3, 0)))
        return "blocked"

    def _update_strip(self):
        hwnd = self.binding[0]
        if not self.strip:
            # Owned, non-activating tool window. Deliberately no WS_EX_TOPMOST.
            self.strip = self.api.user.CreateWindowExW(0x08000080, "STATIC", self.label, 0x80800201,
                                                       0, 0, 600, 28, hwnd, None, None, None)
        if not self.strip:
            return
        phases = {"starting": "\u542f\u52a8\u4e2d", "waiting_login": "\u7b49\u5f85\u767b\u5f55", "analyzing": "AI \u5206\u6790\u4e2d",
                  "running": "\u6267\u884c\u4e2d", "finished": "\u5df2\u7ed3\u675f"}
        self.api.user.SetWindowTextW(self.strip, f"{self.label} | {phases.get(self.phase, self.phase)}")
        rect = wt.RECT()
        self.api.user.GetWindowRect(hwnd, ctypes.byref(rect))
        if self.api.user.IsIconic(hwnd) or not self.api.user.IsWindowVisible(hwnd):
            self.api.user.ShowWindow(self.strip, 0)
            return
        width = max(120, min(760, rect.right - rect.left - 110))
        self.api.user.SetWindowPos(self.strip, None, max(0, rect.left + 80), max(0, rect.top - 28), width, 28, 0x0054)

    def _run(self):
        import time

        deadline = time.monotonic() + 6
        try:
            while not self.stopped.wait(.15):
                if not self.binding:
                    self._find()
                    if not self.binding:
                        if time.monotonic() >= deadline:
                            self.status = "unavailable"
                            return
                        continue
                if not self.valid():
                    self.status = "closed"
                    return
                self._update_strip()
                while not self.actions.empty():
                    self.actions.get_nowait().put(self._focus())
                message = wt.MSG()
                while self.api.user.PeekMessageW(ctypes.byref(message), None, 0, 0, 1):
                    self.api.user.TranslateMessage(ctypes.byref(message))
                    self.api.user.DispatchMessageW(ctypes.byref(message))
        except Exception:  # noqa: BLE001 - native controls are optional and must not fail business execution.
            self.status = "unavailable"
        finally:
            if self.strip:
                self.api.user.DestroyWindow(self.strip)
                self.strip = None
            self.ready.set()

    def close(self):
        self.stopped.set()
        if self.thread:
            self.thread.join(timeout=2)
        self.status = "closed"
