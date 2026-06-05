import pytest
from unittest.mock import AsyncMock, patch
from backend.subagents.boot_template import AlluciSubagentRuntime, test_boot_sequence

@pytest.mark.asyncio
async def test_subagent_runtime_bind_success():
    with patch("backend.subagents.boot_template.AlluciAutonomousDiscoverer") as mock_discoverer_cls:
        mock_discoverer = mock_discoverer_cls.return_value
        mock_discoverer.discover_and_register = AsyncMock(return_value={"api_key": "test_key", "status": "ok"})
        
        runtime = AlluciSubagentRuntime("TestAgent-01", "test_manifest.json")
        await runtime.bind_to_target_resource("http://test.url")
        
        assert "http://test.url" in runtime.active_credentials
        assert runtime.active_credentials["http://test.url"] == "test_key"
        mock_discoverer.discover_and_register.assert_awaited_once_with("http://test.url")

@pytest.mark.asyncio
async def test_subagent_runtime_bind_failure():
    with patch("backend.subagents.boot_template.AlluciAutonomousDiscoverer") as mock_discoverer_cls:
        mock_discoverer = mock_discoverer_cls.return_value
        mock_discoverer.discover_and_register = AsyncMock(return_value=None)
        
        runtime = AlluciSubagentRuntime("TestAgent-02", "test_manifest.json")
        await runtime.bind_to_target_resource("http://fail.url")
        
        assert "http://fail.url" not in runtime.active_credentials

@pytest.mark.asyncio
async def test_boot_sequence_func():
    with patch("backend.subagents.boot_template.AlluciSubagentRuntime") as mock_runtime_cls:
        mock_runtime = mock_runtime_cls.return_value
        mock_runtime.bind_to_target_resource = AsyncMock()
        
        await test_boot_sequence()
        
        mock_runtime_cls.assert_called_once_with(subagent_id="ScraperAgent-09", secure_manifest="./backend/config/skill_manifest.json")
        mock_runtime.bind_to_target_resource.assert_awaited_once_with("http://localhost:8000")
