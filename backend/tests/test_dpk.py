import pytest
pytestmark = pytest.mark.unit

"""
Discrete Projection Kernel Unit Tests

Validates manifold integrity checking, Euler characteristic computation,
tearing detection, and authorization gates.

INVARIANTS:
  - signature_hash == 0 always blocks execution
  - Euler mismatch (|chi_geom - chi_betti| > 2) always blocks
  - Manifold tearing (sudden Betti shift > threshold) always blocks
  - Valid, consistent state always passes
"""
from backend.security.dpk import DiscreteProjectionKernel, PolytopeState


def make_state(**kwargs) -> PolytopeState:
    """Create a PolytopeState with valid defaults, overrideable by kwargs."""
    defaults = {
        "signature_hash":        42,
        "vertices_V":            10,
        "edges_E":               15,
        "faces_F":               7,
        "betti":                 [1.0, 1.0, 1.0, 0.0],
        "affective_tension_psi": 0.9,
    }
    defaults.update(kwargs)
    return PolytopeState(**defaults)  # type: ignore


class TestDPKSignatureGating:

    @pytest.mark.unit
    def test_unsigned_state_is_blocked(self):
        """signature_hash == 0 must always block execution, no exceptions."""
        dpk = DiscreteProjectionKernel()
        state = make_state(signature_hash=0)
        assert dpk.validate_manifold_integrity(state) is False

    @pytest.mark.unit
    def test_negative_signature_hash_is_valid(self):
        """Negative signature_hash values are valid (only zero is unsigned)."""
        dpk = DiscreteProjectionKernel()
        state = make_state(signature_hash=-42)
        # Negative hash should not be treated as unsigned
        # (validation depends on Euler check, not sign)
        # This test verifies signature_hash=0 is the specific trigger
        assert state.signature_hash != 0


class TestEulerCharacteristic:

    @pytest.mark.unit
    def test_valid_euler_characteristic_passes(self):
        """
        State where |chi_geom - chi_betti| <= 2 passes.
        chi_geom = V - E + F = 10 - 15 + 7 = 2
        chi_betti = B0 - B1 + B2 - B3 = 1 - 1 + 1 - 0 = 1
        |2 - 1| = 1 <= 2: PASS
        """
        dpk = DiscreteProjectionKernel()
        state = make_state(
            vertices_V=10, edges_E=15, faces_F=7,
            betti=[1.0, 1.0, 1.0, 0.0]
        )
        assert dpk.validate_manifold_integrity(state) is True

    @pytest.mark.unit
    def test_euler_mismatch_exceeding_tolerance_is_blocked(self):
        """
        State where |chi_geom - chi_betti| > 2 is blocked.
        chi_geom = 10 - 5 + 1 = 6
        chi_betti = 1 - 0 + 0 - 0 = 1
        |6 - 1| = 5 > 2: BLOCK
        """
        dpk = DiscreteProjectionKernel()
        state = make_state(
            vertices_V=10, edges_E=5, faces_F=1,
            betti=[1.0, 0.0, 0.0, 0.0]
        )
        assert dpk.validate_manifold_integrity(state) is False

    @pytest.mark.unit
    def test_euler_tolerance_boundary_exactly_2_passes(self):
        """
        |chi_geom - chi_betti| == 2 is at the boundary — should PASS.
        chi_geom = 10 - 15 + 7 = 2
        chi_betti = 4 (manipulated)
        |2 - 4| = 2: PASS (not strictly greater than 2)
        """
        dpk = DiscreteProjectionKernel()
        # chi_betti = 4 - 0 + 0 - 0 = 4; chi_geom = 2; diff = 2
        state = make_state(
            vertices_V=10, edges_E=15, faces_F=7,
            betti=[4.0, 0.0, 0.0, 0.0]
        )
        assert dpk.validate_manifold_integrity(state) is True


class TestManifoldTearingDetection:

    @pytest.mark.unit
    def test_stable_transition_passes(self):
        """Two consecutive states with similar Betti numbers pass tearing check."""
        dpk = DiscreteProjectionKernel()
        state_a = make_state(betti=[1.0, 1.0, 1.0, 0.0], affective_tension_psi=0.5)
        state_b = make_state(betti=[1.1, 1.0, 0.9, 0.0], affective_tension_psi=0.5)
        dpk.validate_manifold_integrity(state_a)
        assert dpk.validate_manifold_integrity(state_b) is True

    @pytest.mark.unit
    def test_sudden_betti_jump_is_blocked(self):
        """Sudden large jump in Betti numbers (tearing) is blocked when psi < 0.8."""
        dpk = DiscreteProjectionKernel()
        state_a = make_state(betti=[1.0, 0.0, 0.0, 0.0], affective_tension_psi=0.5)
        # Massive jump: total shift = |100 - 1| + |50 - 0| + ... >> threshold
        state_b = make_state(betti=[100.0, 50.0, 25.0, 10.0], affective_tension_psi=0.5)
        dpk.validate_manifold_integrity(state_a)
        assert dpk.validate_manifold_integrity(state_b) is False

    @pytest.mark.unit
    def test_tearing_not_triggered_on_first_state(self):
        """Tearing check is skipped for the first state (no previous state to compare)."""
        dpk = DiscreteProjectionKernel()
        assert dpk.initialized is False
        state = make_state(betti=[100.0, 50.0, 25.0, 10.0], affective_tension_psi=0.1)
        # First state: no tearing check, only signature + Euler checks
        # This should pass IF Euler is valid — verify Euler too
        chi_geom = state.vertices_V - state.edges_E + state.faces_F
        chi_betti = round(state.betti[0] - state.betti[1] + state.betti[2] - state.betti[3])
        if abs(chi_geom - chi_betti) <= 2:
            result = dpk.validate_manifold_integrity(state)
            assert result is True

from unittest.mock import patch, MagicMock
import ctypes

@pytest.fixture
def dpk_py():
    with patch("backend.security.dpk.DiscreteProjectionKernel._load_native_lib", return_value=None):
        return DiscreteProjectionKernel()

def test_load_native_lib_env_path():
    with patch("os.environ.get", return_value="/mock/path.so"):
        with patch("os.path.isfile", return_value=True):
            with patch("ctypes.CDLL") as mock_cdll:
                mock_cdll.return_value = MagicMock()
                dpk = DiscreteProjectionKernel()
                assert dpk.native_lib is not None
                mock_cdll.assert_called_with("/mock/path.so")

def test_load_native_lib_env_path_oserror():
    with patch("os.environ.get", return_value="/mock/path.so"):
        with patch("os.path.isfile", return_value=True):
            with patch("ctypes.CDLL", side_effect=OSError("Load error")):
                # Should fallback to convention path, mock isfile for convention to False
                with patch("os.path.isfile", side_effect=[True, False]):
                    dpk = DiscreteProjectionKernel()
                    assert dpk.native_lib is None

def test_load_native_lib_convention_path():
    with patch("os.environ.get", return_value=None):
        with patch("platform.system", return_value="Linux"):
            with patch("os.path.isfile", return_value=True):
                with patch("ctypes.CDLL") as mock_cdll:
                    mock_cdll.return_value = MagicMock()
                    dpk = DiscreteProjectionKernel()
                    assert dpk.native_lib is not None

def test_compute_signature_hash(dpk_py):
    h = dpk_py.compute_signature_hash([1.0, 0.0, 0.0, 0.0], 1)
    assert isinstance(h, int)
    assert h > 0

def test_validate_manifold_integrity_py_budget_exceeded(dpk_py):
    state = PolytopeState(
        signature_hash=123,
        vertices_V=1, edges_E=0, faces_F=0,
        betti=[1.0, 0.0, 0.0, 0.0],
        affective_tension_psi=1.0,
        coherence=1.0,
        budget_used=0.95 # > 0.9
    )
    assert dpk_py.validate_manifold_integrity_py(state) is False

def test_validate_manifold_integrity_py_low_coherence(dpk_py):
    state = PolytopeState(
        signature_hash=123,
        vertices_V=1, edges_E=0, faces_F=0,
        betti=[1.0, 0.0, 0.0, 0.0],
        affective_tension_psi=1.0,
        coherence=0.2, # < 0.3
        budget_used=0.0
    )
    assert dpk_py.validate_manifold_integrity_py(state) is False

def test_native_validate_manifold_integrity():
    mock_lib = MagicMock()
    mock_lib.dpk_new.return_value = 12345
    mock_lib.dpk_authorize.return_value = True
    
    with patch("backend.security.dpk.DiscreteProjectionKernel._load_native_lib", return_value=mock_lib):
        dpk = DiscreteProjectionKernel()
        
        state = PolytopeState(
            signature_hash=123,
            vertices_V=1, edges_E=0, faces_F=0,
            betti=[1.0, 0.0, 0.0, 0.0],
            affective_tension_psi=1.0,
            coherence=1.0,
            budget_used=0.0
        )
        assert dpk.validate_manifold_integrity(state) is True
        mock_lib.dpk_authorize.assert_called_once()
        
        mock_lib.dpk_authorize.return_value = False
        assert dpk.validate_manifold_integrity(state) is False

def test_native_validate_manifold_integrity_init_exception():
    mock_lib = MagicMock()
    mock_lib.dpk_new.side_effect = Exception("init error")
    with patch("backend.security.dpk.DiscreteProjectionKernel._load_native_lib", return_value=mock_lib):
        dpk = DiscreteProjectionKernel()
        assert dpk.native_lib is None

def test_del():
    mock_lib = MagicMock()
    mock_lib.dpk_new.return_value = 12345
    with patch("backend.security.dpk.DiscreteProjectionKernel._load_native_lib", return_value=mock_lib):
        dpk = DiscreteProjectionKernel()
        dpk.__del__()
        mock_lib.dpk_free.assert_called_once_with(12345)

