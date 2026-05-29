import pytest
from backend.harmonic_enhancer import LatticeAnalyzer, TopologyMapper, AttentionSignal

def test_lattice_analyzer_periodic():
    analyzer = LatticeAnalyzer()
    
    # 1. High periodicity (cosine wave with cycle length 2)
    series_looping = [1.0, -1.0, 1.0, -1.0, 1.0, -1.0, 1.0, -1.0]
    desc = analyzer.analyze(series_looping)
    assert desc.periodicity_strength > 0.5
    assert desc.cycle_length == 2
    assert desc.is_looping is True

    # 2. Random/flat series (no loops)
    series_flat = [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1]
    desc2 = analyzer.analyze(series_flat)
    assert desc2.periodicity_strength == 0.0
    assert desc2.is_looping is False


def test_topology_mapper_centroid():
    with TopologyMapper() as mapper:
        # Pushing a set of neutral/stress signals
        mapper.update(AttentionSignal(valence=0.5, arousal=0.5, focus=0.5))
        mapper.update(AttentionSignal(valence=0.4, arousal=0.6, focus=0.5))
        
        centroid, stress = mapper.update(AttentionSignal(valence=0.3, arousal=0.7, focus=0.5))
        
        # Centroid should be mean
        assert 0.3 <= centroid[0] <= 0.5
        assert 0.5 <= centroid[1] <= 0.7
        assert stress is False
        
        # Push extreme stress basin values (Valence < 0.3, Arousal > 0.7)
        for _ in range(10):
            centroid, stress = mapper.update(AttentionSignal(valence=0.1, arousal=0.9, focus=0.5))
            
        assert centroid[0] < 0.3
        assert centroid[1] > 0.7
        assert stress is True
