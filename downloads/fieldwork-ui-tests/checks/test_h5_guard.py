import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

MODULE = Path(__file__).resolve().parents[1] / "h5" / "conftest.py"
SPEC = importlib.util.spec_from_file_location("fieldwork_h5_configuration", MODULE)
configuration = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(configuration)


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_h5_blocks_writes(method):
    guard = configuration.ReadOnlyGuard()
    route = Mock(request=SimpleNamespace(method=method, url="https://example.invalid/order?token=private"))
    guard.route(route)
    route.abort.assert_called_once_with("blockedbyclient")
    route.continue_.assert_not_called()
    assert len(guard.failures) == 1
    assert "private" not in guard.failures[0]


def test_h5_forwards_read():
    guard = configuration.ReadOnlyGuard()
    route = Mock(request=SimpleNamespace(method="GET", url="https://example.invalid/list"))
    guard.route(route)
    route.continue_.assert_called_once()
    assert not guard.failures


def test_h5_does_not_pass_business_failure_with_http_200():
    guard = configuration.ReadOnlyGuard()
    response = Mock(status=200, url="https://example.invalid/list", request=SimpleNamespace(resource_type="xhr"))
    response.json.return_value = {"code": 500, "success": False}
    guard.response(response)
    assert guard.failures == ["Business rejection: /list"]
