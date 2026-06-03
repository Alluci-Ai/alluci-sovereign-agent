import logging
import time
from typing import Dict
from ..logging_config import get_logger

logger = get_logger("CircuitBreaker")

from .exceptions import SecurityException

class FinancialCircuitBreaker:
    _instance = None
    
    # Defaults
    MAX_VERUS_SPEND_PER_DAY = 10.0 # 10 VRSCTEST
    MAX_LLM_API_COST_PER_DAY = 5.0 # $5.00 USD
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FinancialCircuitBreaker, cls).__new__(cls)
            cls._instance._init()
        return cls._instance
        
    def _init(self):
        self.verus_spent_today = 0.0
        self.llm_cost_today = 0.0
        self.last_reset_time = time.time()
        
    def _check_reset(self):
        # Reset at 24 hours
        if time.time() - self.last_reset_time > 86400:
            self.verus_spent_today = 0.0
            self.llm_cost_today = 0.0
            self.last_reset_time = time.time()
            
    def check_verus_spend(self, amount: float):
        self._check_reset()
        if self.verus_spent_today + amount > self.MAX_VERUS_SPEND_PER_DAY:
            logger.error(f"[SECURITY] CIRCUIT BREAKER TRIPPED: Max Verus spend exceeded ({self.verus_spent_today + amount} > {self.MAX_VERUS_SPEND_PER_DAY}). Agent paused.")
            raise SecurityException(
                "Daily Verus spending limit exceeded.",
                exception_type="BUDGET_EXCEEDED",
                metadata={"budget_type": "VERUS", "amount": amount, "limit": self.MAX_VERUS_SPEND_PER_DAY}
            )
            
    def record_verus_spend(self, amount: float):
        self.verus_spent_today += amount
        
    def check_llm_spend(self, estimated_cost: float):
        self._check_reset()
        if self.llm_cost_today + estimated_cost > self.MAX_LLM_API_COST_PER_DAY:
            logger.error(f"[SECURITY] CIRCUIT BREAKER TRIPPED: Max LLM API cost exceeded (${self.llm_cost_today + estimated_cost} > ${self.MAX_LLM_API_COST_PER_DAY}). Agent paused.")
            raise SecurityException(
                "Daily LLM API spending limit exceeded.",
                exception_type="BUDGET_EXCEEDED",
                metadata={"budget_type": "LLM", "amount": estimated_cost, "limit": self.MAX_LLM_API_COST_PER_DAY}
            )
            
    def record_llm_spend(self, cost: float):
        self.llm_cost_today += cost

circuit_breaker = FinancialCircuitBreaker()
