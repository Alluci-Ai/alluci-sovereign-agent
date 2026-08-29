import pytest
pytestmark = pytest.mark.unit

from backend.topology.barcode_clock import TopologicalBarcodeClock, BarcodeFeature


def test_barcode_clock_tick_and_birth():
    clock = TopologicalBarcodeClock(initial_count=0)
    assert clock.clock == 0

    assert clock.tick() == 1
    assert clock.clock == 1

    feature = clock.register_birth(dimension=1, generator_id="loop_node_a")
    assert feature.birth == 1
    assert feature.is_alive is True
    assert feature.dimension == 1
    assert clock.get_persistence("loop_node_a") == 0

    clock.tick()
    clock.tick()
    assert clock.clock == 3
    assert clock.get_persistence("loop_node_a") == 2


def test_barcode_clock_death_and_betti():
    clock = TopologicalBarcodeClock(initial_count=5)
    f0 = clock.register_birth(dimension=0, generator_id="connected_comp_1")
    f1 = clock.register_birth(dimension=1, generator_id="cycle_1")

    betti = clock.get_betti_numbers()
    assert betti[0] >= 1.0
    assert betti[1] == 1.0

    clock.tick()
    dead = clock.register_death("cycle_1")
    assert dead is not None
    assert dead.death == 6
    assert dead.is_alive is False
    assert dead.lifetime(6) == 1

    betti_after = clock.get_betti_numbers()
    assert betti_after[1] == 0.0


def test_barcode_clock_summary_and_pruning():
    clock = TopologicalBarcodeClock(initial_count=0)
    clock._history_limit = 5

    for i in range(10):
        clock.register_birth(dimension=0, generator_id=f"feat_{i}")
        clock.tick()
        clock.register_death(f"feat_{i}")

    summary = clock.get_clock_summary()
    assert summary["clock_N"] == 10
    assert "betti_estimate" in summary
    assert summary["dead_features_count"] <= 6
