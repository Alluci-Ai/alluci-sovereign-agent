import pytest
pytestmark = pytest.mark.unit

import json
from backend.ws_gateway import _rpc_error
from backend.config import settings

def test_rpc_error_includes_data_when_debug(monkeypatch):
    monkeypatch.setattr(settings, "DEBUG", True)
    err_json = _rpc_error(1, -32603, "Internal error", data={"detail": "x"})
    parsed = json.loads(err_json)
    assert "error" in parsed
    assert "data" in parsed["error"]
    assert parsed["error"]["data"] == {"detail": "x"}

def test_rpc_error_omits_data_when_debug_off(monkeypatch):
    monkeypatch.setattr(settings, "DEBUG", False)
    err_json = _rpc_error(1, -32603, "Internal error", data={"detail": "x"})
    parsed = json.loads(err_json)
    assert "error" in parsed
    assert "data" not in parsed["error"]
