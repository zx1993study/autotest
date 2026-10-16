import json
import tempfile
import unittest
import sys
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "packaging" / "desktop"))
sys.path.insert(0, str(ROOT / "agent"))

from client_config import DEFAULT_PLATFORM_URL, platform_url, save_config
from remote_runtime import RemoteRuntime, DesktopBridge


class RemoteDesktopTest(unittest.TestCase):
    def test_reload_preserves_current_page_without_reconnecting_or_touching_agent(self):
        runtime = RemoteRuntime({}, Path('unused'), Mock(), Mock(), Path('unused'))
        runtime.window = Mock()
        runtime.remote_loaded = True
        runtime.reload()
        runtime.window.evaluate_js.assert_called_once_with('window.location.reload()')
        runtime.manager.start.assert_not_called()
        runtime.window.load_url.assert_not_called()

    def test_reload_shortcuts_are_installed_on_loaded_documents(self):
        runtime = RemoteRuntime({}, Path('unused'), Mock(), Mock(), Path('unused'))
        runtime.window = Mock()
        runtime.install_reload_shortcuts()
        script = runtime.window.evaluate_js.call_args.args[0]
        self.assertIn("event.key === 'F5'", script)
        self.assertIn('event.ctrlKey', script)
        runtime.cancelled.set()
        runtime.install_reload_shortcuts()
        self.assertEqual(runtime.window.evaluate_js.call_count, 1)

    def test_default_remote_platform_and_login_url(self):
        self.assertEqual(platform_url({}), DEFAULT_PLATFORM_URL)
        self.assertEqual(platform_url({"server_url": ""}), DEFAULT_PLATFORM_URL)
        for link in (
            DEFAULT_PLATFORM_URL + "/login?redirect=/reports/statistics",
            DEFAULT_PLATFORM_URL + "/login/",
            DEFAULT_PLATFORM_URL + "/login#fragment",
        ):
            with self.subTest(link=link):
                self.assertEqual(platform_url({"server_url": link}), DEFAULT_PLATFORM_URL)
        self.assertEqual(platform_url({"server_url": "https://platform.test/login?redirect=/app/devices"}), "https://platform.test")

    def test_login_link_does_not_allow_credentials_or_insecure_remote_url(self):
        for link in (
            "https://admin:secret@platform.test/login?redirect=/",
            "http://platform.test/login?redirect=/",
            "https://platform.test:invalid/login",
            "https://platform.test/autotest?token=secret",
        ):
            with self.subTest(link=link), self.assertRaises(ValueError):
                platform_url({"server_url": link})

    def test_configuration_persists_only_platform_root_from_login_link(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "client.json"
            save_config(target, {"server_url": DEFAULT_PLATFORM_URL + "/login?redirect=/reports/statistics"})
            self.assertEqual(json.loads(target.read_text()), {"server_url": DEFAULT_PLATFORM_URL})

    def test_ready_platform_opens_login_directly(self):
        runtime = RemoteRuntime({}, Path("unused"), Mock(), Mock(), Path("unused"))
        runtime.window = Mock()
        response = Mock(status=200)
        response.read.return_value = json.dumps({"service": "Autotest Platform", "ready": True}).encode()
        with patch("remote_runtime.urlopen") as opener:
            opener.return_value.__enter__.return_value = response
            runtime._connect(DEFAULT_PLATFORM_URL)
        opener.assert_called_once_with(DEFAULT_PLATFORM_URL + "/health", timeout=8)
        runtime.window.load_url.assert_called_once_with(DEFAULT_PLATFORM_URL + "/login?redirect=/reports/statistics")

    def test_start_uses_default_without_requiring_configuration(self):
        runtime = RemoteRuntime({"auto_start_agent": False}, Path("unused"), Mock(), Mock(), Path("unused"))
        with patch.object(runtime, "connect") as connect:
            runtime.start()
        connect.assert_called_once_with(DEFAULT_PLATFORM_URL, save=False)

    def test_desktop_does_not_store_backend_secrets(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "client.json"
            save_config(target, {"server_url": "https://platform.example.com", "database_url": "secret", "auth_secret_key": "secret"})
            self.assertEqual(json.loads(target.read_text()), {"server_url": "https://platform.example.com"})

    def test_remote_platform_requires_https(self):
        with self.assertRaises(ValueError):
            platform_url({"server_url": "http://platform.example.com"})
        self.assertEqual(platform_url({"server_url": "http://127.0.0.1:8765"}), "http://127.0.0.1:8765")

    def test_remote_page_cannot_change_local_settings(self):
        runtime = RemoteRuntime({}, Path("unused"), Mock(), Mock(), Path("unused"))
        runtime.window = Mock()
        runtime.window.get_current_url.return_value = "https://untrusted.example.com"
        self.assertIn("error", DesktopBridge(runtime).connect("https://other.example.com"))
        self.assertFalse(hasattr(DesktopBridge(runtime), "manager"))

    def test_inline_connection_page_is_local_only_before_remote_navigation(self):
        runtime = RemoteRuntime({}, Path("unused"), Mock(), Mock(), Path("unused"))
        runtime.window = Mock()
        runtime.window.get_current_url.return_value = None
        self.assertTrue(runtime._local_page())
        runtime.remote_loaded = True
        self.assertFalse(runtime._local_page())

    def test_health_check_cannot_mistake_a_frontend_html_page_for_a_ready_platform(self):
        runtime = RemoteRuntime({}, Path("unused"), Mock(), Mock(), Path("unused"))
        runtime.window = Mock()
        runtime.window.get_current_url.return_value = None
        response = Mock(status=200)
        response.read.return_value = b"<html>fallback</html>"
        with patch("remote_runtime.urlopen") as opener:
            opener.return_value.__enter__.return_value = response
            runtime._connect("https://platform.test")
        runtime.window.load_url.assert_not_called()
        runtime.window.evaluate_js.assert_called_once()


if __name__ == "__main__":
    unittest.main()
