import pytest
from unittest.mock import patch
from backend.security.dpk import DiscreteProjectionKernel, PolytopeState, TearingException

@pytest.mark.asyncio
@patch("backend.security.dpk.CalibrationManager")
async def test_dpk_authorize_dynamic_ffi(MockCM):
    mock_cm = MockCM.return_value
    mock_cm.get_dynamic_threshold.return_value = 0.5
    
    dpk = DiscreteProjectionKernel()
    
    # Mock native library since .so might not be compiled
    from unittest.mock import MagicMock
    dpk.native_lib = MagicMock()
    dpk.native_instance = MagicMock()
    
    call_count = [0]
    # First call returns True (stable), second returns False (tearing)
    def mock_auth(kernel, state, thresh, out_shift):
        thresh_val = getattr(thresh, "value", thresh)
        if pytest.approx(thresh_val) == 0.5:
            # We'll use a hack to set out_shift value
            if out_shift:
                out_shift._obj.value = 8.0 # Simulate the shift
        call_count[0] += 1
        # return True for first state, False for tearing state
        return call_count[0] == 1
        
    dpk.native_lib.dpk_authorize_dynamic.side_effect = mock_auth

    
    # Initial state to setup the 'prev_state'
    state_init = PolytopeState(
        signature_hash=123,
        vertices_V=8,
        edges_E=12,
        faces_F=6,
        betti=[1.0, 0.0, 0.0, 0.0],
        affective_tension_psi=0.5,
        origin="test_origin", 
        is_tool_action=False,
        hardware_status=2,
        coherence=1.0
    )
    stable_init = dpk.validate_manifold_integrity(state_init)
    assert stable_init is True
    
    # State with massive topology shift
    state_tear = PolytopeState(
        signature_hash=123,
        vertices_V=8,
        edges_E=12,
        faces_F=6,
        betti=[9.0, 0.0, 0.0, 0.0], # Shift = 8.0, Threshold = 0.5 * 10.0 = 5.0
        affective_tension_psi=0.5,
        origin="test_origin", 
        is_tool_action=False,
        hardware_status=2,
        coherence=1.0
    )
    
    # Assert that it catches the tearing shift via dynamic_threshold and raises
    with pytest.raises(TearingException) as exc:
        dpk.validate_manifold_integrity(state_tear)
        
    assert exc.value.topology_shift == 8.0
    assert exc.value.dynamic_threshold == 5.0
    assert exc.value.origin == "test_origin"
    
    # Verify that CalibrationManager was queried correctly
    mock_cm.get_dynamic_threshold.assert_called_with(origin="test_origin", is_tool=False)
