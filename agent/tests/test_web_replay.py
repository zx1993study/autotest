import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock

from agent_app.executors.web_replay_executor import LocalWebReplayExecutor
from web_automation.engines.playwright import PlaywrightEngine


class ReplayTests(unittest.IsolatedAsyncioTestCase):
    async def test_unique_locator_does_not_click_first_of_many(self):
        locator = Mock(count=AsyncMock(return_value=2), click=AsyncMock())
        locator.first.wait_for = AsyncMock()
        page = Mock(get_by_label=Mock(return_value=locator))
        engine = PlaywrightEngine(page)
        with self.assertRaisesRegex(ValueError, 'exactly one'):
            await engine.execute({'action': 'click', 'locator_type': 'label', 'locator': 'Name', 'require_unique': True})
        locator.click.assert_not_called()

    async def test_assertion_fails_on_wrong_text(self):
        locator = Mock(inner_text=AsyncMock(return_value='Wrong'))
        locator.wait_for = AsyncMock()
        page = Mock()
        engine = PlaywrightEngine(page)
        engine.locator = Mock(return_value=locator)
        with self.assertRaises(AssertionError):
            await engine.execute({'action': 'assert', 'expected': 'Success'})

    async def test_waiting_login_cancel_prevents_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Mock(artifacts_dir=Path(tmp), node_key='synthetic')
            executor = LocalWebReplayExecutor(config, Mock())
            executor._state = AsyncMock(side_effect=[{}, {'cancel_requested': True}])
            with self.assertRaisesRegex(RuntimeError, '取消'):
                await executor._login(1, 'lease')
