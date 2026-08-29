import pytest
pytestmark = pytest.mark.unit

from unittest.mock import AsyncMock, MagicMock
from backend.memory.codebase_indexer import CodebaseMemoryIndexer


@pytest.mark.asyncio
async def test_codebase_indexer_sync():
    mock_hlsm = MagicMock()
    mock_hlsm.l1_store = AsyncMock(return_value="mem_test_id_123")

    indexer = CodebaseMemoryIndexer()
    result = await indexer.sync_codebase_memory(mock_hlsm)

    assert result["status"] == "success"
    assert result["indexed_entries"] > 0
    assert mock_hlsm.l1_store.called
    assert mock_hlsm.l1_store.call_count >= 3


@pytest.mark.asyncio
async def test_codebase_indexer_skipped_when_none():
    indexer = CodebaseMemoryIndexer()
    result = await indexer.sync_codebase_memory(None)
    assert result["status"] == "skipped"
