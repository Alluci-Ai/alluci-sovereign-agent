"""
Synchronous performance benchmarks for critical code paths.
These run as part of the normal pytest suite with a timeout guard.
"""
import time
import pytest
from backend.security.guardrail import GuardrailScanner
from backend.security.dpk import DiscreteProjectionKernel, PolytopeState


class TestGuardrailPerformance:

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_guardrail_scan_completes_in_1ms(self):
        """Guardrail scan must complete in under 1ms (inline on every request)."""
        from unittest.mock import MagicMock
        scanner = GuardrailScanner(router=MagicMock())
        input_text = "Summarize the quarterly earnings for Acme Corp fiscal year 2024."

        start = time.perf_counter()
        for _ in range(1000):
            await scanner.scan_input(input_text)
        elapsed_per_call = (time.perf_counter() - start) / 1000 * 1000  # ms per call

        assert elapsed_per_call < 1.0, \
            f"Guardrail scan too slow: {elapsed_per_call:.3f}ms per call (max 1ms)"

    @pytest.mark.performance
    def test_dpk_validation_completes_under_half_ms(self):
        """DPK manifold integrity check must complete in under 0.5ms (sync hot path)."""
        dpk = DiscreteProjectionKernel()
        state = PolytopeState(
            signature_hash=42,
            vertices_V=10, edges_E=15, faces_F=7,
            betti=[1.0, 1.0, 1.0, 0.0],
            affective_tension_psi=0.9
        )

        start = time.perf_counter()
        for _ in range(10_000):
            dpk.validate_manifold_integrity(state)
        elapsed_per_call = (time.perf_counter() - start) / 10_000 * 1000

        assert elapsed_per_call < 0.5, \
            f"DPK validation too slow: {elapsed_per_call:.4f}ms per call (max 0.5ms)"
