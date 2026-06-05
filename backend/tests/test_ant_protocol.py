import pytest
from unittest.mock import AsyncMock
from backend.network.ant_protocol import AntNetworkProtocol

@pytest.fixture
def ant_protocol():
    return AntNetworkProtocol()

@pytest.mark.asyncio
async def test_broadcast_and_sync_pheromone(ant_protocol):
    res = await ant_protocol.broadcast_pheromone("agent_1", "barcode_123", 0.5)
    assert res is True
    
    pheromones = await ant_protocol.sync_pheromones()
    assert "agent_1" in pheromones
    assert pheromones["agent_1"]["betti_signature"] == "barcode_123"
    assert pheromones["agent_1"]["affective_tension"] == 0.5
    assert pheromones["agent_1"]["protocol"] == "Alluci_Ant_v1"

@pytest.mark.asyncio
async def test_broadcast_with_verus_client():
    mock_client = AsyncMock()
    protocol = AntNetworkProtocol(verus_client=mock_client)
    
    res = await protocol.broadcast_pheromone("agent_2", "barcode_456", 0.8)
    assert res is True
    # mock_client.send_message is currently commented out in the implementation,
    # but we test that providing verus_client doesn't break.
    pheromones = await protocol.sync_pheromones()
    assert "agent_2" in pheromones
