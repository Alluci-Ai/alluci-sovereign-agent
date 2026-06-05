import pytest
import time
from unittest.mock import patch
from backend.security.circuit_breaker import FinancialCircuitBreaker
from backend.security.exceptions import SecurityException

@pytest.fixture
def circuit_breaker():
    cb = FinancialCircuitBreaker()
    # Reset internal state for isolation
    cb._init()
    return cb

def test_singleton(circuit_breaker):
    cb2 = FinancialCircuitBreaker()
    assert circuit_breaker is cb2

def test_initial_state(circuit_breaker):
    assert circuit_breaker.verus_spent_today == 0.0
    assert circuit_breaker.llm_cost_today == 0.0

def test_record_spend(circuit_breaker):
    circuit_breaker.record_verus_spend(1.5)
    assert circuit_breaker.verus_spent_today == 1.5

    circuit_breaker.record_llm_spend(0.5)
    assert circuit_breaker.llm_cost_today == 0.5

def test_check_verus_spend_ok(circuit_breaker):
    circuit_breaker.check_verus_spend(5.0)  # less than 10.0 limit
    circuit_breaker.record_verus_spend(5.0)
    assert circuit_breaker.verus_spent_today == 5.0

def test_check_verus_spend_exceeded(circuit_breaker):
    with pytest.raises(SecurityException) as excinfo:
        circuit_breaker.check_verus_spend(11.0)
    assert excinfo.value.exception_type == "BUDGET_EXCEEDED"
    assert "budget_type" in excinfo.value.metadata
    assert excinfo.value.metadata["budget_type"] == "VERUS"

def test_check_llm_spend_ok(circuit_breaker):
    circuit_breaker.check_llm_spend(3.0)  # less than 5.0 limit
    circuit_breaker.record_llm_spend(3.0)
    assert circuit_breaker.llm_cost_today == 3.0

def test_check_llm_spend_exceeded(circuit_breaker):
    with pytest.raises(SecurityException) as excinfo:
        circuit_breaker.check_llm_spend(6.0)
    assert excinfo.value.exception_type == "BUDGET_EXCEEDED"
    assert "budget_type" in excinfo.value.metadata
    assert excinfo.value.metadata["budget_type"] == "LLM"

@patch('time.time')
def test_reset_after_24_hours(mock_time, circuit_breaker):
    mock_time.return_value = 1000.0
    circuit_breaker._init()  # last_reset_time = 1000.0
    
    circuit_breaker.record_verus_spend(9.0)
    circuit_breaker.record_llm_spend(4.0)
    
    # 25 hours later
    mock_time.return_value = 1000.0 + 86400 + 3600
    circuit_breaker.check_verus_spend(2.0)  # Should not raise because it resets
    
    assert circuit_breaker.verus_spent_today == 0.0
    assert circuit_breaker.llm_cost_today == 0.0
    assert circuit_breaker.last_reset_time == 1000.0 + 86400 + 3600
