import pytest
from backend.security.dpk import DiscreteProjectionKernel, PolytopeState

@pytest.mark.asyncio
async def test_tearing_threshold_tool_vs_skill():
    dpk = DiscreteProjectionKernel()
    
    state_skill = PolytopeState(
        signature_hash=123,
        vertices_V=8,
        edges_E=12,
        faces_F=6,
        betti=[1.0, 0.0, 0.0, 0.0],
        affective_tension_psi=0.5,
        origin="test", 
        is_tool_action=False
    )
    stable_skill = dpk.validate_manifold_integrity(state_skill)
    
    state_tool = PolytopeState(
        signature_hash=123,
        vertices_V=8,
        edges_E=12,
        faces_F=6,
        betti=[1.0, 0.0, 0.0, 0.0],
        affective_tension_psi=0.5,
        origin="test", 
        is_tool_action=True
    )
    stable_tool = dpk.validate_manifold_integrity(state_tool)
    
    assert stable_skill is True
    assert stable_tool is True
