import json
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent


def pytest_addoption(parser):
    parser.addoption("--base-url", default="https://test.waiqin.yios.cn")
    parser.addoption("--storage-state", default=os.getenv("FIELDWORK_WEB_STORAGE_STATE"))
    parser.addoption("--headed", action="store_true")
    parser.addoption("--browser-executable", default=os.getenv("FIELDWORK_WEB_BROWSER"))
    parser.addoption("--feature-smoke", action="store_true")
    parser.addoption("--inputs-file", default=str(ROOT / "inputs.json"))


@pytest.fixture
def web_config(request):
    state = request.config.getoption("--storage-state")
    token = os.getenv("FIELDWORK_WEB_TOKEN")
    if not state and not token:
        pytest.skip("No browser login state; use capture_auth.py or an approved runtime token")
    return {"base_url": request.config.getoption("--base-url"), "storage_state": state,
            "runtime_token": token, "headed": request.config.getoption("--headed"),
            "browser_executable": request.config.getoption("--browser-executable")}


def load_catalog():
    return json.loads((ROOT / "catalog.json").read_text(encoding="utf-8"))
