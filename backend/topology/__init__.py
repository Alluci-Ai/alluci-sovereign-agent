"""
Alluci Sovereign Agent — Topological Manifold & Cognitive Geometry Subsystem
=============================================================================
Exports foundational state spaces (W, X, G, N), J-Space simulation engine,
and topological operators (P, S, D, A).
"""

from .barcode_clock import TopologicalBarcodeClock, BarcodeFeature
from .pmet_filtration import PMETFiltrationEngine, SimplicialComplexSummary
from .j_space_simulator import (
    JSpaceSimulator,
    SimplicialChainOfThought,
    DualTetrahedronSocraticSynthesis,
    SimulationTrace,
)
from .affordance_envelope import ActionAffordanceEnvelope, AffordanceVector
from .markov_trace import MarkovTraceEngine, DPOTripletHarvester, DPOTriplet

__all__ = [
    "TopologicalBarcodeClock",
    "BarcodeFeature",
    "PMETFiltrationEngine",
    "SimplicialComplexSummary",
    "JSpaceSimulator",
    "SimplicialChainOfThought",
    "DualTetrahedronSocraticSynthesis",
    "SimulationTrace",
    "ActionAffordanceEnvelope",
    "AffordanceVector",
    "MarkovTraceEngine",
    "DPOTripletHarvester",
    "DPOTriplet",
]
