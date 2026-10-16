from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent_app.utils.playwright_runtime import chromium_launch_options, resolve_browser_executable


class PlaywrightRuntimeTest(unittest.TestCase):
    def test_source_run_keeps_default_playwright_browser_lookup(self) -> None:
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("agent_app.utils.playwright_runtime._is_frozen", return_value=False),
        ):
            options = chromium_launch_options(headless=False, slow_mo_ms=80)

        self.assertEqual(options["headless"], False)
        self.assertEqual(options["slow_mo"], 80)
        self.assertNotIn("executable_path", options)

    def test_configured_browser_executable_is_used_first(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            browser_path = Path(temp_dir) / "chrome.exe"
            browser_path.write_text("", encoding="utf-8")

            with patch.dict(os.environ, {"AUTOTEST_BROWSER_EXECUTABLE": str(browser_path)}, clear=True):
                resolved = resolve_browser_executable()

        self.assertEqual(resolved, browser_path)

    def test_packaged_run_falls_back_to_browser_on_path(self) -> None:
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("agent_app.utils.playwright_runtime._is_frozen", return_value=True),
            patch("agent_app.utils.playwright_runtime.shutil.which", return_value="C:/Program Files/Google/Chrome/Application/chrome.exe"),
        ):
            options = chromium_launch_options(headless=False, slow_mo_ms=80)

        self.assertEqual(
            Path(str(options["executable_path"])),
            Path("C:/Program Files/Google/Chrome/Application/chrome.exe"),
        )

    def test_packaged_run_can_find_playwright_cache_chromium(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            chrome_path = Path(temp_dir) / "ms-playwright" / "chromium-1223" / "chrome-win64" / "chrome.exe"
            chrome_path.parent.mkdir(parents=True)
            chrome_path.write_text("", encoding="utf-8")

            with (
                patch.dict(os.environ, {"LOCALAPPDATA": temp_dir}, clear=True),
                patch("agent_app.utils.playwright_runtime._is_frozen", return_value=True),
                patch("agent_app.utils.playwright_runtime.shutil.which", return_value=None),
            ):
                resolved = resolve_browser_executable()

        self.assertEqual(resolved, chrome_path)


if __name__ == "__main__":
    unittest.main()
