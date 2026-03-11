import time
from backend.ace.memory_decay import MemoryTopologyDecay

def test_retention_decays():
    md = MemoryTopologyDecay(half_life=1.0)  # 1 second for test speed
    ret = md.calculate_retention(time.time() - 2)  # 2 seconds ago
    assert 0. < ret < 0.5  # Past half-life → less than 50%

def test_should_prune():
    md = MemoryTopologyDecay()
    assert md.should_prune(0.05) == True
    assert md.should_prune(0.5) == False

def test_betti_1_persistence_boost():
    """Memories supporting Betti-1 holes decay slower."""
    md = MemoryTopologyDecay(half_life=1.0)
    past = time.time() - 2  # 2 seconds ago
    
    # Without Betti-1 support
    ret_normal = md.calculate_retention(past, topological_importance=1.0, betti_1_support=0.0)
    
    # With Betti-1 support: should retain more
    ret_betti = md.calculate_retention(past, topological_importance=1.0, betti_1_support=2.0)
    
    assert ret_betti > ret_normal

def test_filter_by_persistence():
    md = MemoryTopologyDecay(half_life=10.0)
    now = time.time()
    
    memories = [
        {"id": 1, "last_accessed": now - 1, "topological_importance": 1.0, "betti_1_support": 0.0},
        {"id": 2, "last_accessed": now - 1, "topological_importance": 1.0, "betti_1_support": 3.0},
        {"id": 3, "last_accessed": now - 100, "topological_importance": 0.1, "betti_1_support": 0.0},
    ]
    
    # With Betti-1 features active
    result = md.filter_by_persistence(memories, current_betti=[1.0, 2.0, 0.0, 0.0])
    
    # Memory 3 should be pruned (old, low importance, no betti support)
    ids = [m["id"] for m in result]
    assert 1 in ids
    assert 2 in ids
