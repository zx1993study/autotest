from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent_app.config import default_config_path, load_config


class AgentConfigTest(unittest.TestCase):
    def test_frozen_runtime_prefers_installed_config_next_to_executable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            install_dir = Path(temp_dir)
            installed_config = install_dir / "config.json"
            installed_config.write_text("{}", encoding="utf-8")

            with (
                patch.dict(os.environ, {"AUTOTEST_AGENT_CONFIG": "", "LOCALAPPDATA": str(install_dir / "user")}, clear=False),
                patch("agent_app.config._is_frozen", return_value=True),
                patch.object(sys, "executable", str(install_dir / "AutotestAgent.exe")),
            ):
                config_path = default_config_path()

        self.assertEqual(config_path, installed_config)

    def test_agent_prefers_legacy_agent_token_when_it_is_node_token(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "server_url": "http://example.test/api/v1",
                        "agent_token": "agt_old_invalid",
                        "token": "agt_new_current",
                        "node_key": "local-win-01",
                    }
                ),
                encoding="utf-8",
            )

            config = load_config(str(config_path))

        self.assertEqual(config.token, "agt_new_current")

    def test_user_jwt_token_does_not_override_agent_token(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "server_url": "http://example.test/api/v1",
                        "agent_token": "agt_current",
                        "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.payload.signature",
                        "node_key": "local-win-01",
                    }
                ),
                encoding="utf-8",
            )

            config = load_config(str(config_path))

        self.assertEqual(config.token, "agt_current")

    def test_removed_schema_capability_is_not_advertised(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "server_url": "http://example.test/api/v1",
                        "agent_token": "agt_current",
                        "node_key": "local-win-01",
                        "capabilities": ["case_execution", "api_schema_test"],
                    }
                ),
                encoding="utf-8",
            )

            config = load_config(str(config_path))

        self.assertNotIn("api_schema_test", config.capabilities)
        self.assertIn("stagehand", config.capabilities)


if __name__ == "__main__":
    unittest.main()
