import pytest
import asyncio
from unittest.mock import patch
from backend.bridges.notion import NotionBridge
from backend.bridges.slack import SlackBridge
from backend.bridges.signal import SignalBridge
from backend.bridges.gmail import GmailBridge
from backend.bridges.gdrive import GDriveBridge

@pytest.mark.asyncio
async def test_notion_bridge_unconfigured():
    bridge = NotionBridge("notion", vault_root="", vault_manager=None)
    # Provide empty credentials
    success = await bridge.connect({})
    assert success is False
    assert bridge.is_connected is False

@pytest.mark.asyncio
async def test_slack_bridge_unconfigured():
    bridge = SlackBridge("slack", vault_root="", vault_manager=None)
    # Missing tokens
    success = await bridge.connect({"bot_token": "", "app_token": ""})
    assert success is False
    assert bridge.is_connected is False

@pytest.mark.asyncio
@patch("backend.bridges.signal.SignalBridge._start_daemon", return_value=False)
@patch("asyncio.create_task")
async def test_signal_bridge_unconfigured(mock_create_task, mock_start_daemon):
    bridge = SignalBridge("signal", vault_root="", vault_manager=None)
    # Missing CLI path and phone number
    success = await bridge.connect({})
    assert success is False
    assert bridge.is_connected is False

@pytest.mark.asyncio
async def test_gmail_bridge_unconfigured():
    bridge = GmailBridge("gmail", vault_root="", vault_manager=None)
    # Missing access token
    success = await bridge.connect({})
    assert success is False
    assert bridge.is_connected is False

@pytest.mark.asyncio
async def test_gdrive_bridge_unconfigured():
    bridge = GDriveBridge("gdrive", vault_root="", vault_manager=None)
    # Missing access token
    success = await bridge.connect({})
    assert success is False
    assert bridge.is_connected is False
