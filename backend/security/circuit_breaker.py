import time
from typing import Dict
from ..logging_config import get_logger

logger = get_logger("CircuitBreaker")

from .exceptions import SecurityException

class ProviderCircuitBreaker:
    """Per‑provider token quota circuit breaker.

    Tracks token usage per provider in a rolling time window (default 60 seconds).
    When a provider exceeds its token quota, a ``SecurityException`` with
    ``PROVIDER_QUOTA_EXCEEDED`` is raised.
    """
    _instance = None
    DEFAULT_MAX_TOKENS_PER_MINUTE = 100_000  # configurable default quota

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ProviderCircuitBreaker, cls).__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        # Mapping: provider -> {"tokens": int, "window_start": float}
        self.provider_usage: Dict[str, Dict[str, float]] = {}
        self.window_seconds = 60  # one‑minute sliding window

    def _reset_window_if_needed(self, provider: str):
        info = self.provider_usage.get(provider)
        if not info:
            return
        now = time.time()
        if now - info["window_start"] > self.window_seconds:
            info["tokens"] = 0
            info["window_start"] = now

    def check_quota(self, provider: str, tokens: int = 0):
        """Validate that ``provider`` can consume ``tokens`` without exceeding quota.
        Raises ``SecurityException`` if the quota would be exceeded.
        """
        self._reset_window_if_needed(provider)
        usage = self.provider_usage.setdefault(
            provider, {"tokens": 0, "window_start": time.time()}
        )
        if usage["tokens"] + tokens > self.DEFAULT_MAX_TOKENS_PER_MINUTE:
            raise SecurityException(
                f"Provider {provider} token quota exceeded.",
                exception_type="PROVIDER_QUOTA_EXCEEDED",
                metadata={"provider": provider, "requested": tokens, "used": usage["tokens"]}
            )
        return True

    def record_usage(self, provider: str, tokens: int = 0):
        """Record that ``provider`` has consumed ``tokens``.
        Should be called after a successful request.
        """
        self._reset_window_if_needed(provider)
        usage = self.provider_usage.setdefault(
            provider, {"tokens": 0, "window_start": time.time()}
        )
        usage["tokens"] += tokens
        return True

class FinancialCircuitBreaker:
    _instance = None
    
    # Defaults
    MAX_VERUS_SPEND_PER_DAY = 10.0 # 10 VRSCTEST
    MAX_LLM_API_COST_PER_DAY = 25.0 # $25.00 USD
    
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
        
    def check_llm_spend(self, estimated_cost: float, provider: str = ""):
        self._check_reset()
        if estimated_cost <= 0.0 or (provider and provider.lower() in ["local", "lce", "mlx"]):
            return
        if self.llm_cost_today + estimated_cost > self.MAX_LLM_API_COST_PER_DAY:
            logger.error(f"[SECURITY] CIRCUIT BREAKER TRIPPED: Max LLM API cost exceeded (${self.llm_cost_today + estimated_cost} > ${self.MAX_LLM_API_COST_PER_DAY}). Agent paused.")
            raise SecurityException(
                "Daily LLM API spending limit exceeded.",
                exception_type="BUDGET_EXCEEDED",
                metadata={"budget_type": "LLM", "amount": estimated_cost, "limit": self.MAX_LLM_API_COST_PER_DAY}
            )
            
    def record_llm_spend(self, cost: float, provider: str = ""):
        if cost <= 0.0 or (provider and provider.lower() in ["local", "lce", "mlx"]):
            return
        self.llm_cost_today += cost

    def reset_llm_spend(self):
        self.llm_cost_today = 0.0

class VerusCircuitBreaker:
    """Circuit breaker for Verus RPC calls to prevent blocking and allow graceful degradation."""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(VerusCircuitBreaker, cls).__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        self.failure_count = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF-OPEN
        self.last_failure_time = 0.0
        self.open_duration = 300  # 5 minutes

    def record_failure(self):
        self.failure_count += 1
        if self.state == "CLOSED" and self.failure_count >= 3:
            self.state = "OPEN"
            self.last_failure_time = time.time()
            logger.error("[SECURITY] Verus Circuit Breaker OPENED. Network calls degraded.")
        elif self.state == "HALF-OPEN":
            # If we fail while testing recovery, immediately open again
            self.state = "OPEN"
            self.last_failure_time = time.time()
            self.failure_count = 3

    def record_success(self):
        self.failure_count = 0
        if self.state != "CLOSED":
            self.state = "CLOSED"
            logger.info("[SECURITY] Verus Circuit Breaker CLOSED. Network calls restored.")

    def is_open(self) -> bool:
        if self.state == "CLOSED":
            return False
        
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.open_duration:
                self.state = "HALF-OPEN"
                return False  # Allow one request through to test
            return True
            
        if self.state == "HALF-OPEN":
            return False

        return False

circuit_breaker = FinancialCircuitBreaker()
verus_circuit_breaker = VerusCircuitBreaker()
