import pytest
import os
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

from backend.config import settings
from backend import services

@pytest.fixture
def mock_app():
    return MagicMock()

@pytest.fixture(autouse=True)
def reset_globals():
    # Reset all services before each test
    services.vault = None
    services.router = None
    services.ace = None
    services.orchestrator = None
    services.task_manager = None
    services.skill_manager = None
    services.sovereign_identity = None
    services.local_inference = None
    services.ws_gw = None
    services.usage_tracker = None
    services.cron_engine = None
    services.config_editor = None
    services.exec_approval = None
    services.memory = None
    services.hlsm_manager = None
    services.redis_client = None
    services.scanner = None
    services.device_manager = None
    services.pcl = None
    services.channel_registry.clear()
    yield

@patch("backend.services.redis.from_url")
@patch("fastapi_limiter.FastAPILimiter.init", new_callable=AsyncMock)
@patch("backend.services.create_db_and_tables")
@patch("backend.services.VaultManager")
@patch("backend.services.SovereignIdentity")
@patch("backend.services.UsageTracker")
@patch("backend.services.ModelRouter")
@patch("backend.services.GuardrailScanner")
@patch("backend.services.AffectiveEngine")
@patch("backend.services.SkillManager")
@patch("backend.services.HLSMManager")
@patch("backend.services.JsonRpcGateway")
@patch("backend.services.ExecApprovalManager")
@patch("backend.services.ExecutiveOrchestrator")
@patch("backend.services.TaskManager")
@patch("backend.services.LocalInferenceBridge")
@patch("backend.services.CronEngine")
@patch("backend.services.ConfigEditor")
@patch("backend.services.DeviceManager")
@patch("backend.services.ProactiveCognitionLoop")
@patch("backend.services.updater_instance")
@patch("backend.services._init_channels", new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_init_services_core(mock_channels, mock_updater, mock_pcl, mock_device, mock_config, mock_cron, mock_lib, mock_task, mock_orch, mock_exec, mock_ws, mock_hlsm, mock_skill, mock_ace, mock_scanner, mock_router, mock_usage, mock_sov, mock_vault, mock_db, mock_limiter, mock_redis, mock_app):
    # Make sure mock objects return properly structured async methods where needed
    mock_sov.return_value.load_keys = AsyncMock()
    mock_hlsm.return_value.start_consolidation_loop = AsyncMock()
    mock_cron.return_value.start = AsyncMock()
    mock_pcl.return_value.start = AsyncMock()
    mock_updater.start = AsyncMock()
    mock_orch.return_value.start_background_services = AsyncMock()

    # Execute init_services
    await services.init_services(mock_app)

    # Asserts
    assert services.vault is not None
    assert services.router is not None
    assert services.ace is not None
    assert services.skill_manager is not None
    assert services.hlsm_manager is not None
    assert services.ws_gw is not None
    assert services.pcl is not None

    mock_db.assert_called_once()
    mock_sov.return_value.load_keys.assert_called_once()
    mock_hlsm.return_value.start_consolidation_loop.assert_called_once()
    mock_cron.return_value.start.assert_called_once()
    mock_pcl.return_value.start.assert_called_once()
    mock_channels.assert_called_once()


@pytest.mark.asyncio
async def test_shutdown_services():
    with patch("backend.services.hlsm_manager") as mock_hlsm, \
         patch("backend.services.pcl") as mock_pcl, \
         patch("backend.services.cron_engine") as mock_cron, \
         patch("backend.services.orchestrator") as mock_orch, \
         patch("backend.services.updater") as mock_upd:
         
        mock_hlsm.stop_consolidation_loop = AsyncMock()
        mock_pcl.stop = AsyncMock()
        mock_cron.stop = AsyncMock()
        mock_orch.stop_background_services = AsyncMock()
        mock_upd.stop = AsyncMock()

        class MockAdapter:
            async def disconnect(self): pass
        
        mock_adapter = MockAdapter()
        mock_adapter.disconnect = AsyncMock()
        services.channel_registry["test"] = mock_adapter

        await services.shutdown_services()

        mock_hlsm.stop_consolidation_loop.assert_called_once()
        mock_pcl.stop.assert_called_once()
        mock_cron.stop.assert_called_once()
        mock_orch.stop_background_services.assert_called_once()
        mock_upd.stop.assert_called_once()
        mock_adapter.disconnect.assert_called_once()

@pytest.mark.asyncio
async def test_init_channels():
    # Setup mock vault
    mock_vault = MagicMock()
    mock_vault.retrieve_secret = AsyncMock(return_value={"enabled": True})
    mock_vault.list_connections = AsyncMock(return_value=["acc1"])
    mock_vault.retrieve_connection_secret = AsyncMock(return_value={"key": "val"})
    mock_vault.store_connection_secret = AsyncMock()
    services.vault = mock_vault

    with patch("backend.bridges.telegram.TelegramBridge.connect", new_callable=AsyncMock) as mock_tg_connect:
        mock_tg_connect.return_value = True

        with patch.dict(services.channel_registry, {}):
            await services._init_channels("/tmp/vault")
            assert "telegram" in services.channel_registry
            mock_vault.list_connections.assert_called()

@pytest.mark.asyncio
async def test_init_channels_legacy_fallback():
    mock_vault = MagicMock()
    mock_vault.retrieve_secret = AsyncMock(side_effect=[{"enabled": True}, {"team_id": "legacy_acc"}])
    mock_vault.list_connections = AsyncMock(return_value=[])
    mock_vault.store_connection_secret = AsyncMock()
    services.vault = mock_vault

    with patch("backend.bridges.telegram.TelegramBridge.connect", new_callable=AsyncMock) as mock_tg_connect:
        mock_tg_connect.return_value = True
        with patch.dict(services.channel_registry, {}):
            await services._init_channels("/tmp/vault")
            mock_vault.store_connection_secret.assert_called()
            
@patch("backend.services.redis.from_url")
@patch("backend.services.create_db_and_tables")
@patch("backend.services.ExecutiveOrchestrator")
@patch("backend.services.ProactiveCognitionLoop")
@patch("backend.services.CronEngine")
@patch("backend.services.ModelRouter")
@patch("backend.services.HLSMManager")
@pytest.mark.asyncio
async def test_init_services_redis_error(mock_hlsm, mock_router, mock_cron, mock_pcl, mock_orch, mock_db, mock_redis, mock_app):
    mock_orch.return_value.start_background_services = AsyncMock()
    mock_pcl.return_value.start = AsyncMock()
    mock_cron.return_value.start = AsyncMock()
    mock_hlsm.return_value.start_consolidation_loop = AsyncMock()
    mock_redis.side_effect = Exception("Redis error")
    with patch("backend.config.settings.REDIS_URL", "redis://localhost:6379"):
        await services.init_services(mock_app)
        assert services.redis_client is None

@patch("backend.services.create_db_and_tables")
@patch("backend.services.ExecutiveOrchestrator")
@patch("backend.services.ProactiveCognitionLoop")
@patch("backend.services.CronEngine")
@patch("backend.services.ModelRouter")
@patch("backend.services.HLSMManager")
@pytest.mark.asyncio
async def test_init_services_redis_none_production(mock_hlsm, mock_router, mock_cron, mock_pcl, mock_orch, mock_db, mock_app):
    mock_orch.return_value.start_background_services = AsyncMock()
    mock_pcl.return_value.start = AsyncMock()
    mock_cron.return_value.start = AsyncMock()
    mock_hlsm.return_value.start_consolidation_loop = AsyncMock()
    with patch("backend.config.settings.REDIS_URL", None), \
         patch("backend.config.settings.APP_ENV", "production"), \
         patch("sys.exit") as mock_exit:
        await services.init_services(mock_app)
        mock_exit.assert_called_once_with(1)

@patch("backend.services.create_db_and_tables")
@patch("backend.services.ExecutiveOrchestrator")
@patch("backend.services.ProactiveCognitionLoop")
@patch("backend.services.CronEngine")
@patch("backend.services.ModelRouter")
@patch("backend.services.HLSMManager")
@pytest.mark.asyncio
async def test_init_services_alembic_upgrade(mock_hlsm, mock_router, mock_cron, mock_pcl, mock_orch, mock_db, mock_app):
    mock_orch.return_value.start_background_services = AsyncMock()
    mock_pcl.return_value.start = AsyncMock()
    mock_cron.return_value.start = AsyncMock()
    mock_hlsm.return_value.start_consolidation_loop = AsyncMock()
    with patch("backend.config.settings.APP_ENV", "production"), \
         patch("alembic.command.upgrade") as mock_upgrade, \
         patch("sys.exit"):
        await services.init_services(mock_app)
        mock_upgrade.assert_called()

@pytest.mark.asyncio
async def test_broadcast_bridge_event():
    services.ws_gw = MagicMock()
    services.ws_gw.broadcast_event = AsyncMock()
    
    mock_vault = MagicMock()
    services.vault = mock_vault
    
    with patch.dict(services.channel_registry, {}):
        await services._init_channels("/tmp/vault")
        
        # Test on_event binding
        adapter = services.channel_registry["telegram"]
        await adapter.on_event("test_event", {"data": 123})
        services.ws_gw.broadcast_event.assert_awaited_once_with("test_event", {"data": 123})

@patch("backend.services.create_db_and_tables")
@patch("backend.services.redis.from_url")
@patch("backend.services.ExecutiveOrchestrator")
@patch("backend.services.ProactiveCognitionLoop")
@patch("backend.services.CronEngine")
@patch("backend.services.ModelRouter")
@patch("backend.services.HLSMManager")
@pytest.mark.asyncio
async def test_init_services_redis_error_production(mock_hlsm, mock_router, mock_cron, mock_pcl, mock_orch, mock_redis, mock_db, mock_app):
    mock_orch.return_value.start_background_services = AsyncMock()
    mock_pcl.return_value.start = AsyncMock()
    mock_cron.return_value.start = AsyncMock()
    mock_hlsm.return_value.start_consolidation_loop = AsyncMock()
    mock_redis.side_effect = Exception("Redis error")
    with patch("backend.config.settings.REDIS_URL", "redis://localhost:6379", create=True), \
         patch("backend.config.settings.APP_ENV", "production"), \
         patch("sys.exit") as mock_exit:
        await services.init_services(mock_app)
        mock_exit.assert_called_once_with(1)

@patch("backend.services.create_db_and_tables")
@patch("backend.services.redis.from_url")
@patch("backend.services.ExecutiveOrchestrator")
@patch("backend.services.ProactiveCognitionLoop")
@patch("backend.services.CronEngine")
@patch("backend.services.ModelRouter")
@patch("backend.services.HLSMManager")
@pytest.mark.asyncio
async def test_init_services_redis_success(mock_hlsm, mock_router, mock_cron, mock_pcl, mock_orch, mock_redis, mock_db, mock_app):
    mock_orch.return_value.start_background_services = AsyncMock()
    mock_pcl.return_value.start = AsyncMock()
    mock_cron.return_value.start = AsyncMock()
    mock_hlsm.return_value.start_consolidation_loop = AsyncMock()
    # Tests FastAPILimiter init and verus_auth wire-up
    from fastapi_limiter import FastAPILimiter
    from backend.security.verusid_auth import verus_auth
    
    with patch("backend.config.settings.REDIS_URL", "redis://localhost:6379", create=True), \
         patch("fastapi_limiter.FastAPILimiter.init", new_callable=AsyncMock) as mock_limiter_init, \
         patch("sys.exit"):
        await services.init_services(mock_app)
        mock_limiter_init.assert_called_once_with(mock_redis.return_value)
        assert verus_auth._redis == mock_redis.return_value

@patch("backend.services.create_db_and_tables")
@patch("backend.services.ExecutiveOrchestrator")
@patch("backend.services.ProactiveCognitionLoop")
@patch("backend.services.CronEngine")
@patch("backend.services.ModelRouter")
@patch("backend.services.HLSMManager")
@pytest.mark.asyncio
async def test_init_services_chromadb_success(mock_hlsm, mock_router, mock_cron, mock_pcl, mock_orch, mock_db, mock_app):
    mock_orch.return_value.start_background_services = AsyncMock()
    mock_pcl.return_value.start = AsyncMock()
    mock_cron.return_value.start = AsyncMock()
    mock_hlsm.return_value.start_consolidation_loop = AsyncMock()
    import sys
    # Fake chromadb module
    mock_chromadb = MagicMock()
    mock_client = MagicMock()
    mock_chromadb.PersistentClient.return_value = mock_client
    sys.modules["chromadb"] = mock_chromadb

    with patch("backend.config.settings.LITE_MODE", False), \
         patch("os.makedirs"):
        await services.init_services(mock_app)
        mock_client.get_or_create_collection.assert_called_once_with(
            name="hlsm_semantic",
            metadata={"hnsw:space": "cosine"}
        )

@patch("backend.services.create_db_and_tables")
@patch("backend.services.ExecutiveOrchestrator")
@patch("backend.services.ProactiveCognitionLoop")
@patch("backend.services.CronEngine")
@patch("backend.services.ModelRouter")
@patch("backend.services.HLSMManager")
@pytest.mark.asyncio
async def test_init_services_chromadb_import_error(mock_hlsm, mock_router, mock_cron, mock_pcl, mock_orch, mock_db, mock_app):
    mock_orch.return_value.start_background_services = AsyncMock()
    mock_pcl.return_value.start = AsyncMock()
    mock_cron.return_value.start = AsyncMock()
    mock_hlsm.return_value.start_consolidation_loop = AsyncMock()
    import sys
    # Force ImportError
    sys.modules.pop("chromadb", None)
    with patch("backend.config.settings.LITE_MODE", False):
        await services.init_services(mock_app)
        
@patch("backend.services.create_db_and_tables")
@patch("backend.services.ExecutiveOrchestrator")
@patch("backend.services.ProactiveCognitionLoop")
@patch("backend.services.CronEngine")
@patch("backend.services.ModelRouter")
@patch("backend.services.HLSMManager")
@pytest.mark.asyncio
async def test_init_services_oauth_refresh_loop(mock_hlsm, mock_router, mock_cron, mock_pcl, mock_orch, mock_db, mock_app):
    mock_orch.return_value.start_background_services = AsyncMock()
    mock_pcl.return_value.start = AsyncMock()
    mock_cron.return_value.start = AsyncMock()
    mock_hlsm.return_value.start_consolidation_loop = AsyncMock()
    mock_vault = MagicMock()
    services.vault = mock_vault
    
    mock_adapter = MagicMock()
    mock_adapter.is_connected = True
    mock_adapter._token_refresh_loop = AsyncMock()
    services.channel_registry["slack"] = mock_adapter

    with patch("backend.services.settings") as mock_settings, \
         patch("asyncio.create_task") as mock_create_task:
        
        mock_settings.SLACK_CLIENT_ID = "test_id"
        mock_settings.SLACK_CLIENT_SECRET = "test_secret"
        mock_settings.APP_ENV = "testing"
        mock_settings.REDIS_URL = None
        mock_settings.POLYTOPE_STORAGE_ROOT = "/tmp"
        mock_settings.POLYTOPE_MASTER_KEY = "test_key"
        mock_settings.LITE_MODE = True
        
        await services.init_services(mock_app)
        
        mock_create_task.assert_called()
