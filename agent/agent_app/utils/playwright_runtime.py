from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


def chromium_launch_options(headless: bool, slow_mo_ms: int) -> dict[str, object]:
    """Build Chromium launch options that also work from PyInstaller builds.

    PyInstaller one-file apps extract Playwright into a temporary directory
    without the managed browser binaries. In that mode Playwright's default
    browser lookup points at a non-existent ``_MEI.../.local-browsers`` path.
    Passing a real browser executable keeps local headed execution independent
    from the package extraction directory.
    """

    options: dict[str, object] = {"headless": headless, "slow_mo": slow_mo_ms}
    executable = resolve_browser_executable()
    if executable:
        options["executable_path"] = str(executable)
    return options


def prepare_recording_runtime() -> None:
    if _is_frozen():
        import playwright

        root = Path(playwright.__file__).parent / "driver/package/.local-browsers"
        os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(root))


def resolve_browser_executable() -> Path | None:
    """Return a local Chromium-compatible executable for packaged Agents."""

    configured = _existing_path(
        os.getenv("AUTOTEST_BROWSER_EXECUTABLE")
        or os.getenv("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH")
    )
    if configured:
        return configured

    # Source runs should keep Playwright's normal managed-browser behavior so
    # developers notice missing browser installs during local development.
    if not _is_frozen():
        return None

    for command in ("chrome", "chrome.exe", "msedge", "msedge.exe"):
        path = _which_path(command)
        if path:
            return path

    for path in _common_browser_paths():
        if path.exists():
            return path

    return _latest_playwright_chromium()


def _common_browser_paths() -> list[Path]:
    candidates: list[Path] = []
    for base_env in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
        base = os.getenv(base_env)
        if not base:
            continue
        root = Path(base)
        candidates.extend(
            [
                root / "Google" / "Chrome" / "Application" / "chrome.exe",
                root / "Microsoft" / "Edge" / "Application" / "msedge.exe",
            ]
        )
    return candidates


def _latest_playwright_chromium() -> Path | None:
    local_app_data = os.getenv("LOCALAPPDATA")
    if not local_app_data:
        return None
    root = Path(local_app_data) / "ms-playwright"
    if not root.exists():
        return None
    candidates = sorted(
        root.glob("chromium-*/chrome-win*/chrome.exe"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def _existing_path(value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(os.path.expandvars(value)).expanduser()
    return path if path.exists() else None


def _which_path(command: str) -> Path | None:
    value = shutil.which(command)
    return Path(value) if value else None


def _is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))
