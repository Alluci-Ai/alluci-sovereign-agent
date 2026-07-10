import pytest
import os
import json
from unittest.mock import AsyncMock
from backend.tool_manager import ToolManager

@pytest.fixture
def temp_tool_vault(tmp_path):
    tools_dir = tmp_path / "alluci_vault" / "tools"
    tools_dir.mkdir(parents=True, exist_ok=True)
    return str(tmp_path / "alluci_vault")

@pytest.mark.asyncio
async def test_tool_manager_list_tools(temp_tool_vault):
    mock_vault = AsyncMock()
    mock_vault.retrieve_secret.return_value = {}
    
    manager = ToolManager(vault=mock_vault, workspace_tools_dir=temp_tool_vault)
    tool_data = {
        "id": "mock_tool",
        "name": "Mock Tool",
        "category": "TOOL",
        "parameters": {"test": "val"},
        "capabilities": ["do_something"]
    }
    
    mock_vault.store_secret.return_value = True
    mock_vault.retrieve_secret.return_value = {"tools": [tool_data]}
    
    await manager.save_tool(tool_data)
    
    tools = await manager.list_tools()
    assert len(tools) == 1
    assert tools[0]["id"] == "mock_tool"

@pytest.mark.asyncio
async def test_tool_manager_delete_tool(temp_tool_vault):
    mock_vault = AsyncMock()
    tool_data = {"id": "mock_tool_2", "name": "Mock Tool 2", "category": "TOOL"}
    
    # setup state
    mock_vault.retrieve_secret.side_effect = [
        {}, # initially empty on save
        {"tools": [tool_data]}, # retrieve for delete
        {"tools": []} # list after delete
    ]
    
    manager = ToolManager(vault=mock_vault, workspace_tools_dir=temp_tool_vault)
    
    await manager.save_tool(tool_data)
    
    deleted = await manager.delete_tool("mock_tool_2")
    assert deleted is True
    
    tools = await manager.list_tools()
    assert len(tools) == 0

@pytest.mark.asyncio
async def test_tool_manager_blob_cache_storage(temp_tool_vault):
    from unittest.mock import patch, MagicMock
    import hashlib
    import zlib
    mock_vault = AsyncMock()
    manager = ToolManager(vault=mock_vault, workspace_tools_dir=temp_tool_vault)
    manager.get_tool_key = AsyncMock(return_value=None)
    manager.store_tool_key = AsyncMock()
    mock_hlsm = AsyncMock()

    content = "Test content for blob storage."
    doc_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()

    mock_scanner_instance = AsyncMock()
    mock_scanner_instance.scan_input = AsyncMock(return_value=(True, "Safe"))
    MockScannerClass = MagicMock(return_value=mock_scanner_instance)

    with patch('backend.security.guardrail.GuardrailScanner', MockScannerClass):
        with patch('backend.inference.router.ModelRouter'):
            with patch('backend.services.ws_gw', AsyncMock()):
                await manager._quarantine_and_ingest(
                    source_path="/test/path.md",
                    content=content,
                    component_id="tool_cache",
                    hlsm=mock_hlsm,
                    is_remote=False
                )

    blob_path = os.path.expanduser(f"~/.polytope/alluci_vault/blobs/{doc_hash}.blob")
    assert os.path.exists(blob_path)
    with open(blob_path, "rb") as f:
        saved_content = zlib.decompress(f.read()).decode('utf-8')
    assert saved_content == content
    manager.store_tool_key.assert_called_once_with("tool_cache", f"doc_hash_/test/path.md", doc_hash)

