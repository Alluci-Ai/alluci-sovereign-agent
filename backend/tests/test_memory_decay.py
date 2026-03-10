import time
from backend.ace.memory_decay import MemoryTopologyDecay

def test_memory_topology_decay():
    decay = MemoryTopologyDecay(half_life=100.0)
    
    now = time.time()
    
    # Immediate access
    ret1 = decay.calculate_retention(now, topological_importance=1.0)
    assert ret1 > 0.99
    
    # After one half-life
    ret2 = decay.calculate_retention(now - 100.0, topological_importance=1.0)
    assert 0.45 < ret2 < 0.55
    
    # High importance slows decay
    ret3 = decay.calculate_retention(now - 100.0, topological_importance=10.0)
    # lambda_adj = decay_constant / 10.
    # ret = exp(-lambda/10 * 100) = exp(-ln2/10) = 2^(-1/10) = 2^(-0.1) approx 0.93
    assert ret3 > 0.9
