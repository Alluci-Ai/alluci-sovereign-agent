import pytest
pytestmark = pytest.mark.unit

import os
from unittest.mock import patch
from backend.security.oauth_config import get_provider_config, get_client_credentials

def test_get_provider_config():
    cfg = get_provider_config("slack")
    assert cfg is not None
    assert cfg["client_id_env"] == "SLACK_CLIENT_ID"
    
    # Test alias
    x_cfg = get_provider_config("x")
    twitter_cfg = get_provider_config("twitter")
    assert x_cfg == twitter_cfg
    assert x_cfg is not None
    
    # Test missing
    missing_cfg = get_provider_config("unknown")
    assert missing_cfg is None

@patch.dict(os.environ, {"SLACK_CLIENT_ID": "id123", "SLACK_CLIENT_SECRET": "secret123"})
def test_get_client_credentials():
    client_id, client_secret = get_client_credentials("slack")
    assert client_id == "id123"
    assert client_secret == "secret123"

def test_get_client_credentials_missing_provider():
    client_id, client_secret = get_client_credentials("unknown")
    assert client_id is None
    assert client_secret is None

@patch.dict(os.environ, {}, clear=True)
def test_get_client_credentials_missing_env():
    client_id, client_secret = get_client_credentials("slack")
    assert client_id is None
    assert client_secret is None
