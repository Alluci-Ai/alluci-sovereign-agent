import pytest
import asyncio
from backend.memory.chat_synthesis import ChatSynthesisEngine
from backend.memory.hlsm_manager import HLSMManager
from unittest.mock import MagicMock

@pytest.mark.asyncio
async def test_chat_synthesis_engine_reduction():
    engine = ChatSynthesisEngine()
    messages = [
        {"role": "user", "content": "Let us design a Value Based Pricing strategy for our SaaS product."},
        {"role": "assistant", "content": "Understood. Value-Based Pricing shifts pricing from cost-plus to economic surplus extraction."},
        {"role": "user", "content": "How do we map client ROI?"},
        {"role": "assistant", "content": "We calculate tangible financial savings and charge a fraction of that surplus."}
    ]
    
    result = await engine.synthesize_session("sess_test_123", messages)
    assert result is not None
    assert result["session_key"] == "sess_test_123"
    assert "Summary" in result["summary_content"]
    assert result["turn_count"] == 4
    assert result["source"] == "chat_synthesis"

@pytest.mark.asyncio
async def test_hlsm_manager_chat_synthesis_store():
    db_engine = MagicMock()
    hlsm = HLSMManager(db_engine=db_engine, redis_client=None, kuzu_db_path=None)
    hlsm._l1_sql_insert = MagicMock()
    
    messages = [
        {"role": "user", "content": "Explain Human Centered Design."},
        {"role": "assistant", "content": "HCD is a biological and cognitive feedback integration."}
    ]
    
    entry_id = await hlsm.synthesize_and_store_chat_session("sess_test_456", messages)
    assert entry_id is not None
    assert hlsm._l1_sql_insert.called
