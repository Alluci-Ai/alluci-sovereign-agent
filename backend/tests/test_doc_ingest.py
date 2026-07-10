import pytest
import os
import hashlib
import zlib
from unittest.mock import AsyncMock, patch, MagicMock
from backend.tool_manager import ToolManager
from backend.skill_manager import SkillManager


@pytest.fixture
def temp_vault(tmp_path):
    vault_dir = tmp_path / "alluci_vault"
    vault_dir.mkdir(parents=True, exist_ok=True)
    return str(vault_dir)


@pytest.mark.asyncio
async def test_tool_manager_doc_ingest_success(temp_vault):
    """Verify full happy-path: scan passes → blob stored → barcode in H-LSM → WS events emitted."""
    mock_vault = AsyncMock()
    mock_vault.retrieve_secret.return_value = {}
    mock_hlsm = AsyncMock()

    manager = ToolManager(vault=mock_vault, workspace_tools_dir=temp_vault)
    manager.get_tool_key = AsyncMock(return_value=None)
    manager.store_tool_key = AsyncMock()

    content = "This is a safe markdown reference document."
    doc_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()

    mock_scanner_instance = AsyncMock()
    mock_scanner_instance.scan_input = AsyncMock(return_value=(True, "Safe"))
    MockScannerClass = MagicMock(return_value=mock_scanner_instance)

    mock_ws = AsyncMock()
    mock_ws.broadcast_event = AsyncMock()

    with patch('backend.security.guardrail.GuardrailScanner', MockScannerClass):
        with patch('backend.inference.router.ModelRouter'):
            with patch('backend.services.ws_gw', mock_ws):
                await manager._quarantine_and_ingest(
                    source_path="/fake/path.md",
                    content=content,
                    component_id="tool_123",
                    hlsm=mock_hlsm,
                    is_remote=False
                )

    # Check WebSocket events: "Quarantined / Scanning..." then "Embedded in H-LSM"
    assert mock_ws.broadcast_event.call_count == 2
    mock_ws.broadcast_event.assert_any_call(
        'doc.ingest.status',
        {'source_path': '/fake/path.md', 'status': 'Quarantined / Scanning...', 'component_id': 'tool_123'}
    )
    mock_ws.broadcast_event.assert_any_call(
        'doc.ingest.status',
        {'source_path': '/fake/path.md', 'status': 'Embedded in H-LSM', 'component_id': 'tool_123'}
    )

    # Check Blob Cache
    blob_path = os.path.expanduser(f"~/.polytope/alluci_vault/blobs/{doc_hash}.blob")
    assert os.path.exists(blob_path)
    with open(blob_path, "rb") as f:
        saved_content = zlib.decompress(f.read()).decode('utf-8')
    assert saved_content == content

    # Check H-LSM store was called
    mock_hlsm.store.assert_called_once()

    # Check barcode hash was persisted in vault
    manager.store_tool_key.assert_called_once_with("tool_123", "doc_hash_/fake/path.md", doc_hash)


@pytest.mark.asyncio
async def test_skill_manager_doc_ingest_rupture(temp_vault):
    """Verify that a failed scan emits the Rupture WS event and does NOT touch H-LSM."""
    mock_vault = AsyncMock()
    mock_hlsm = AsyncMock()

    manager = SkillManager(vault=mock_vault)
    manager.get_skill_key = AsyncMock(return_value=None)

    content = "This is a malicious payload that triggers a topological rupture."

    mock_scanner_instance = AsyncMock()
    mock_scanner_instance.scan_input = AsyncMock(return_value=(False, "Malicious content detected"))
    MockScannerClass = MagicMock(return_value=mock_scanner_instance)

    mock_ws = AsyncMock()
    mock_ws.broadcast_event = AsyncMock()

    with patch('backend.security.guardrail.GuardrailScanner', MockScannerClass):
        with patch('backend.inference.router.ModelRouter'):
            with patch('backend.services.ws_gw', mock_ws):
                await manager._quarantine_and_ingest(
                    source_path="https://evil.com/payload.md",
                    content=content,
                    component_id="skill_456",
                    hlsm=mock_hlsm,
                    is_remote=True
                )

    # Check WebSocket events: "Quarantined / Scanning..." then "Error: Topological Rupture Detected"
    assert mock_ws.broadcast_event.call_count == 2
    mock_ws.broadcast_event.assert_any_call(
        'doc.ingest.status',
        {'source_path': 'https://evil.com/payload.md', 'status': 'Quarantined / Scanning...', 'component_id': 'skill_456'}
    )
    mock_ws.broadcast_event.assert_any_call(
        'doc.ingest.status',
        {'source_path': 'https://evil.com/payload.md', 'status': 'Error: Topological Rupture Detected', 'component_id': 'skill_456'}
    )

    # H-LSM should NOT be called on a failed scan
    mock_hlsm.store.assert_not_called()
