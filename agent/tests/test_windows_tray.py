import sys
import unittest
from unittest.mock import Mock


@unittest.skipUnless(sys.platform == "win32", "Windows tray behavior")
class WindowsTrayTest(unittest.TestCase):
    def test_custom_setup_explicitly_makes_the_icon_visible(self):
        from agent_app.tray.windows_tray import AgentTrayApp

        app = AgentTrayApp.__new__(AgentTrayApp)
        app.manager = Mock()
        app.manager.start.return_value = True
        icon = Mock()
        icon.visible = False
        app._setup(icon)
        self.assertTrue(icon.visible)
        icon.update_menu.assert_called_once()

    def test_busy_stop_is_not_reported_as_stopped(self):
        from agent_app.tray.windows_tray import AgentTrayApp

        app = AgentTrayApp.__new__(AgentTrayApp)
        app.manager = Mock()
        app.manager.is_running.return_value = True
        app.manager.last_error = "busy"
        app.icon = Mock()
        app._stop()
        app.icon.notify.assert_called_once_with("busy", "Autotest Agent")
