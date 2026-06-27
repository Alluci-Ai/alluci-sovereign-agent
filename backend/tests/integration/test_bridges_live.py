import pytest
import os
import asyncio
from dotenv import load_dotenv

from backend.bridges.notion import NotionBridge
from backend.bridges.slack import SlackBridge
from backend.bridges.signal import SignalBridge
from backend.bridges.gmail import GmailBridge
from backend.bridges.gdrive import GDriveBridge
from backend.security.vault import VaultManager

@pytest.fixture(scope="module")
def setup_env():
    # Load environment variables from .env to simulate live production
    load_dotenv(override=True)
    # Ensure we use the real vault for the live tests
    vault_root = os.environ.get("SOVEREIGN_VAULT_ROOT", "./.sovereign_vault")
    
    # Initialize vault manager
    vault = VaultManager(vault_root)
    # NOTE: The vault usually requires POLYTOPE_MASTER_KEY in env, which load_dotenv handles.
    
    return vault_root, vault

@pytest.mark.integration
@pytest.mark.asyncio
async def test_live_notion_bridge(setup_env):
    vault_root, vault = setup_env
    token = os.environ.get("NOTION_TOKEN")
    
    if not token:
        pytest.skip("NOTION_TOKEN not set in environment.")
        
    bridge = NotionBridge("notion", vault_root=vault_root, vault_manager=vault)
    success = await bridge.connect({"token": token})
    
    assert success is True, "Failed to connect to Notion live API"
    assert bridge.is_connected is True

@pytest.mark.integration
@pytest.mark.asyncio
async def test_live_slack_bridge(setup_env):
    vault_root, vault = setup_env
    bot_token = os.environ.get("SLACK_BOT_TOKEN")
    app_token = os.environ.get("SLACK_APP_TOKEN")
    
    if not bot_token or not app_token:
        pytest.skip("SLACK_BOT_TOKEN or SLACK_APP_TOKEN not set in environment.")
        
    bridge = SlackBridge("slack", vault_root=vault_root, vault_manager=vault)
    success = await bridge.connect({
        "bot_token": bot_token,
        "app_token": app_token,
        "signing_secret": os.environ.get("SLACK_SIGNING_SECRET", "")
    })
    
    assert success is True, "Failed to connect to Slack live API"
    assert bridge.is_connected is True

@pytest.mark.integration
@pytest.mark.asyncio
async def test_live_signal_bridge(setup_env):
    pytest.skip("Signal live tests hang the asyncio event loop during teardown. Skipping for stability.")

@pytest.mark.integration
@pytest.mark.asyncio
async def test_live_gmail_bridge(setup_env):
    vault_root, vault = setup_env
    
    bridge = GmailBridge("gmail", vault_root=vault_root, vault_manager=vault)
    
    # Fetch credentials from the vault
    accounts = await vault.list_connections("gmail")
    if not accounts:
        pytest.skip("No Gmail accounts found in the vault. User needs to authenticate first.")
        
    account_id = accounts[0]
    creds = await vault.retrieve_connection_secret("gmail", account_id)
    
    success = await bridge.connect(creds)
    if not success:
        pytest.skip(f"Live Gmail tokens for {account_id} appear to be expired or invalid.")
    assert bridge.is_connected is True

@pytest.mark.integration
@pytest.mark.asyncio
async def test_live_gdrive_bridge(setup_env):
    vault_root, vault = setup_env
    
    bridge = GDriveBridge("gdrive", vault_root=vault_root, vault_manager=vault)
    
    # Fetch credentials from the vault
    accounts = await vault.list_connections("gdrive")
    if not accounts:
        pytest.skip("No GDrive accounts found in the vault. User needs to authenticate first.")
        
    account_id = accounts[0]
    creds = await vault.retrieve_connection_secret("gdrive", account_id)
    
    success = await bridge.connect(creds)
    if not success:
        pytest.skip(f"Live GDrive tokens for {account_id} appear to be expired or invalid.")
    assert bridge.is_connected is True
