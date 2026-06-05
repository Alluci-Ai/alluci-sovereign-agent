import pytest
import base64
from fastapi import Request
from backend.security.csp import generate_nonce, get_nonce
from unittest.mock import MagicMock

def test_generate_nonce():
    nonce = generate_nonce()
    assert isinstance(nonce, str)
    assert len(nonce) > 0
    # Must be valid base64
    decoded = base64.b64decode(nonce + "==")
    assert len(decoded) == 16

def test_get_nonce_success():
    req = MagicMock(spec=Request)
    req.state = MagicMock()
    req.state.csp_nonce = "abc"
    assert get_nonce(req) == "abc"

def test_get_nonce_missing():
    req = MagicMock(spec=Request)
    req.state = MagicMock(spec=object) # No csp_nonce attr
    assert get_nonce(req) == ""
