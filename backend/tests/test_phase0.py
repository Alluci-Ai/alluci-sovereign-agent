import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.oauth_config import OAUTH_CONFIGS

client = TestClient(app)

def test_oauth_config_keys():
    # Verify that keys are full-length strings as per P0-003
    assert "slack" in OAUTH_CONFIGS
    assert "gmail" in OAUTH_CONFIGS
    assert "discord" in OAUTH_CONFIGS
    assert "sl" not in OAUTH_CONFIGS
    assert "gm" not in OAUTH_CONFIGS

def test_bridge_endpoints_registered():
    # We can't easily test the full flow without a real token, 
    # but we can check if the routes exist.
    routes = [route.path for route in app.routes]
    assert "/api/channels/{channel_id}/send" in routes
    assert "/api/channels/{channel_id}/upload" in routes
    assert "/api/channels/{channel_id}/health" in routes
    assert "/api/channels/{channel_id}/unread" in routes
    assert "/api/channels/{channel_id}/social" in routes
    assert "/api/channels/{channel_id}/enterprise" in routes

def test_bridge_actualization_mapping(monkeypatch):
    from unittest.mock import MagicMock
    import backend.adapters.bridge_actualization
    
    # Mock VaultManager and handlers to avoid real initialization
    monkeypatch.setattr("backend.adapters.bridge_actualization.VaultManager", MagicMock())
    monkeypatch.setattr("backend.adapters.bridge_actualization.OAuthHandler", MagicMock())
    monkeypatch.setattr("backend.adapters.bridge_actualization.QRSyncHandler", MagicMock())
    monkeypatch.setattr("backend.adapters.bridge_actualization.TunnelHandler", MagicMock())
    
    from backend.adapters.bridge_actualization import BridgeActualizationAdapter
    adapter = BridgeActualizationAdapter()
    assert adapter.bridge_map["gmail"].__name__ == "GmailBridge"
    assert adapter.bridge_map["slack"].__name__ == "SlackBridge"
