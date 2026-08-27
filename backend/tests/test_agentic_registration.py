import pytest
import asyncio
import httpx
from unittest.mock import AsyncMock, patch, MagicMock

from backend.auth.autonomous_discoverer import AlluciAutonomousDiscoverer
from backend.adapters.agentic_registration import AgenticRegistrationAdapter
from backend.skill_manager import SkillManager
from backend.security.vault import VaultManager

# ==============================================================================
# 1. Discovery Parser & ID-JAG Minting Tests
# ==============================================================================

@pytest.mark.asyncio
@patch("backend.auth.autonomous_discoverer.jwt.encode")
@patch("backend.auth.autonomous_discoverer.httpx.AsyncClient")
@patch("backend.auth.autonomous_discoverer._get_vault")
async def test_agent_verified_handshake(mock_get_vault, mock_client_class, mock_jwt_encode):
    mock_jwt_encode.return_value = "mocked_jwt_token"
    # Mock Vault
    mock_vault = AsyncMock()
    mock_vault.get_web_idp_keypair.return_value = (MagicMock(), MagicMock())
    mock_vault.store_connection_secret = AsyncMock()
    mock_get_vault.return_value = mock_vault
    
    # Mock Memory
    mock_memory = AsyncMock()
    mock_memory.l1_store = AsyncMock()

    # Mock HTTP Client
    mock_client = AsyncMock()
    mock_client_class.return_value.__aenter__.return_value = mock_client
    
    # Mock Hop 1: PRM
    mock_prm_response = MagicMock()
    mock_prm_response.status_code = 200
    mock_prm_response.json.return_value = {
        "agent_auth": {
            "register_uri": "https://test.local/agent/identity",
            "identity_types_supported": ["identity_assertion"]
        }
    }
    
    # Mock POST /agent/identity
    mock_identity_res = MagicMock()
    mock_identity_res.status_code = 200
    mock_identity_res.json.return_value = {
        "identity_assertion": "service_signed_assertion",
        "client_id": "test_client_id"
    }

    # Mock POST /oauth2/token
    mock_token_res = MagicMock()
    mock_token_res.status_code = 200
    mock_token_res.json.return_value = {
        "access_token": "final_access_token"
    }

    mock_client.get.return_value = mock_prm_response
    mock_client.post.side_effect = [mock_identity_res, mock_token_res]

    discoverer = AlluciAutonomousDiscoverer()
    with patch.object(discoverer, '_generate_dpop_proof', return_value="fake_dpop_proof"):
        result = await discoverer.discover_and_register("https://test.local")
    
    assert result is not None
    assert result["flow_type"] == "agent_verified"
    assert result["status"] == "success"
    assert result["access_token"] == "final_access_token"
    mock_vault.get_web_idp_keypair.assert_called_once()

# ==============================================================================
# 2. Async Polling Test (Protecting Event Loop)
# ==============================================================================

@pytest.mark.asyncio
@patch("backend.adapters.agentic_registration.httpx.AsyncClient")
async def test_background_polling(mock_client_class):
    mock_services = MagicMock()
    mock_client = AsyncMock()
    mock_client_class.return_value.__aenter__.return_value = mock_client
    
    # Mock multiple responses: 2 pending, 1 success
    mock_pending = MagicMock()
    mock_pending.status_code = 400
    mock_pending.json.return_value = {"error": "authorization_pending"}
    
    mock_success = MagicMock()
    mock_success.status_code = 200
    mock_success.json.return_value = {"access_token": "polled_access_token"}

    mock_client.post.side_effect = [mock_pending, mock_pending, mock_success]

    adapter = AgenticRegistrationAdapter()
    
    # Instead of full `execute`, we test the polling method directly
    claim_data = {
        "device_code": "dev123",
        "interval": 0, # zero to speed up test
        "token_endpoint": "https://test.local/oauth2/token"
    }
    
    mock_services.vault.store_connection_secret = AsyncMock()
    mock_services.memory = AsyncMock()
    mock_services.memory.l1_store = AsyncMock()
    
    # Run the polling coroutine
    with patch.dict("sys.modules", {"backend.services": mock_services}):
        await adapter._poll_for_token(claim_data, "https://test.local")
    
    # Verify post was called 3 times
    assert mock_client.post.call_count == 3
    # Verify token was stored
    mock_services.vault.store_connection_secret.assert_called_once_with(
        "agent_registration", "https://test.local", {
            "access_token": "polled_access_token",
            "refresh_token": None,
            "expires_in": None,
            "client_id": "https://registry.alluci-ai.internal/profiles/agent-v4"
        }
    )

# ==============================================================================
# 3. Vault Partitioning Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_vault_web_idp_keypair_isolation(tmp_path):
    vault = VaultManager("test_master_key", vault_root=str(tmp_path))
    
    # Generate Verus / Core keypair
    core_priv, core_pub = await vault.get_or_create_jwt_keypair()
    
    # Generate Web IdP keypair
    web_priv, web_pub = await vault.get_web_idp_keypair()
    
    # Verify they are physically different keys and files exist
    assert core_priv is not web_priv
    assert (tmp_path / "jwt_signing.pem").exists()
    assert (tmp_path / "web_idp_signing.pem").exists()

# ==============================================================================
# 4. SkillManager Ingestion Tests
# ==============================================================================

@pytest.mark.asyncio
@patch("backend.skill_manager.os.path.exists")
@patch("backend.skill_manager.open")
async def test_skill_manager_rag_ingestion(mock_open, mock_exists):
    mock_vault = MagicMock(spec=VaultManager)
    # Simulate first run (cache miss)
    mock_vault.retrieve_secret = AsyncMock(return_value={})
    
    # Mock services and hlsm
    mock_services = MagicMock()
    mock_hlsm = MagicMock()
    mock_hlsm.store = AsyncMock()
    mock_services.hlsm_manager = mock_hlsm
    
    # Mock file reading
    mock_exists.return_value = True
    mock_file = MagicMock()
    mock_file.read.return_value = "Mock reference doc content."
    mock_open.return_value.__enter__.return_value = mock_file

    skill_manager = SkillManager(vault=mock_vault)
    
    # Mock registry_list to return a skill with reference_docs
    skill_manager.registry_list = AsyncMock(return_value=[
        {
            "id": "auth_01",
            "reference_docs": ["auth_md_spec.md"]
        }
    ])
    
    # Setup cache retrieval to simulate miss
    skill_manager.get_skill_key = AsyncMock(return_value=None)
    skill_manager.store_skill_key = AsyncMock()

    with patch.dict("sys.modules", {"backend.services": mock_services}):
        merged = await skill_manager.merge_skills_for_runtime(["auth_01"])
    
    assert mock_hlsm.store.call_count == 1
    mock_hlsm.store.assert_called_with(
        content="Mock reference doc content.",
        metadata={"source": "auth_md_spec.md", "skill_id": "auth_01", "type": "reference_doc"}
    )
    skill_manager.store_skill_key.assert_called_once()
