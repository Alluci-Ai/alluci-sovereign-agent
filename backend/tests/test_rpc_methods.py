import pytest
pytestmark = pytest.mark.unit

from backend.ws_gateway import _rpc_success, _rpc_error
from backend.config import settings

import json

def test_rpc_success():
    result = _rpc_success(1, {"ok": True})
    payload = json.loads(result)
    assert payload["id"] == 1
    assert payload["result"] == {"ok": True}

def test_rpc_error_respects_debug(monkeypatch):
    monkeypatch.setattr(settings, "DEBUG", False)
    err = _rpc_error(2, -32602, "Invalid", {"info": "secret"})
    payload = json.loads(err)
    assert "data" not in payload["error"]
    monkeypatch.setattr(settings, "DEBUG", True)
    err_dbg = _rpc_error(3, -32602, "Invalid", {"info": "secret"})
    payload_dbg = json.loads(err_dbg)
    assert payload_dbg["error"]["data"] == {"info": "secret"}
