import pytest
import numpy as np
pytestmark = pytest.mark.unit

from backend.topology.pmet_filtration import PMETFiltrationEngine, SimplicialComplexSummary


def test_pmet_filtration_empty_and_single():
    engine = PMETFiltrationEngine()
    empty_summary = engine.build_vietoris_rips_complex(np.empty((0, 3)))
    assert empty_summary.vertices_count == 0
    assert empty_summary.is_nilpotent is True

    single_summary = engine.build_vietoris_rips_complex(np.array([[1.0, 2.0, 3.0]]))
    assert single_summary.vertices_count == 1
    assert single_summary.betti_numbers[0] == 1.0
    assert single_summary.euler_characteristic == 1


def test_pmet_filtration_triangle_and_nilpotence():
    engine = PMETFiltrationEngine(default_epsilon=1.5)
    # Equilateral triangle in 2D
    triangle_pts = np.array([
        [0.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
        [0.5, 0.866, 0.0]
    ])
    summary = engine.build_vietoris_rips_complex(triangle_pts, epsilon=1.1)
    assert summary.vertices_count == 3
    assert summary.edges_count == 3
    assert summary.faces_count == 1
    assert summary.euler_characteristic == 3 - 3 + 1  # 1
    assert summary.is_nilpotent is True


def test_pmet_filter_ast_graph():
    engine = PMETFiltrationEngine()
    nodes = ["backend/app.py", "backend/services.py", "backend/routers/memory.py"]
    edges = [
        ("backend/app.py", "backend/services.py"),
        ("backend/services.py", "backend/routers/memory.py"),
        ("backend/routers/memory.py", "backend/services.py")  # Circular dependency
    ]

    summary = engine.filter_ast_graph(nodes=nodes, edges=edges, epsilon=2.0)
    assert summary.vertices_count == 3
    assert summary.is_nilpotent is True
    assert isinstance(summary.has_circular_dependencies, bool)
