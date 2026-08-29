"""
Topological Barcode Clock (N) & Persistence Feature Tracker
===========================================================
Realizes the Discrete Clock Count (N) tracking the birth (b) and death (d)
of structural features across cognitive cycles. Increments by exactly N + 1.
"""

from __future__ import annotations

import time
import threading
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Tuple


@dataclass
class BarcodeFeature:
    dimension: int           # 0 for beta_0, 1 for beta_1, 2 for beta_2, etc.
    birth: int               # Discrete clock count N at birth
    generator_id: str        # Unique identifier of generating entity/memory/AST node
    death: Optional[int] = None # Discrete clock count N at death (None if active)
    metadata: Dict[str, Any] = field(default_factory=dict)
    birth_timestamp: float = field(default_factory=time.time)
    death_timestamp: Optional[float] = None

    @property
    def is_alive(self) -> bool:
        return self.death is None

    def lifetime(self, current_clock: int) -> int:
        """Returns the persistence interval (death - birth) or active duration (current - birth)."""
        if self.death is not None:
            return max(0, self.death - self.birth)
        return max(0, current_clock - self.birth)


class TopologicalBarcodeClock:
    """
    Thread-safe Central Discrete Clock Count (N) tracking feature lifespans.
    Acts as the discrete pacing primitive for H-LSM memory decay, 
    proactive cognition, and heartbeat telemetry.
    """

    def __init__(self, initial_count: int = 0):
        self._N: int = max(0, initial_count)
        self._lock = threading.RLock()
        self._features: Dict[str, BarcodeFeature] = {}
        self._history_limit: int = 2000

    @property
    def clock(self) -> int:
        with self._lock:
            return self._N

    def tick(self) -> int:
        """Increments the discrete clock count by exactly N + 1."""
        with self._lock:
            self._N += 1
            return self._N

    def register_birth(
        self,
        dimension: int,
        generator_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> BarcodeFeature:
        """Registers the birth of a structural or topological feature at the current clock tick."""
        with self._lock:
            # If already exists and alive, do not duplicate
            if generator_id in self._features and self._features[generator_id].is_alive:
                return self._features[generator_id]

            feature = BarcodeFeature(
                dimension=dimension,
                birth=self._N,
                generator_id=generator_id,
                death=None,
                metadata=metadata or {},
                birth_timestamp=time.time(),
            )
            self._features[generator_id] = feature
            self._prune_history_if_needed()
            return feature

    def register_death(
        self,
        generator_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[BarcodeFeature]:
        """Registers the death of a structural feature at the current clock tick."""
        with self._lock:
            feature = self._features.get(generator_id)
            if feature and feature.is_alive:
                feature.death = self._N
                feature.death_timestamp = time.time()
                if metadata:
                    feature.metadata.update(metadata)
                return feature
            return feature

    def get_persistence(self, generator_id: str) -> Optional[int]:
        """Returns the persistence interval (clock delta) of a given feature."""
        with self._lock:
            feature = self._features.get(generator_id)
            if feature:
                return feature.lifetime(self._N)
            return None

    def get_active_features(self, dimension: Optional[int] = None) -> List[BarcodeFeature]:
        """Returns all currently active (un-collapsed) topological features."""
        with self._lock:
            return [
                f for f in self._features.values()
                if f.is_alive and (dimension is None or f.dimension == dimension)
            ]

    def get_betti_numbers(self) -> List[float]:
        """
        Computes current active Betti numbers [beta_0, beta_1, beta_2, beta_3]
        based on active barcode counts per dimension.
        """
        with self._lock:
            betti = [0.0, 0.0, 0.0, 0.0]
            for f in self._features.values():
                if f.is_alive and 0 <= f.dimension < 4:
                    betti[f.dimension] += 1.0
            # Ensure base beta_0 is at least 1 (connected manifold)
            betti[0] = max(1.0, betti[0])
            return betti

    def get_clock_summary(self) -> Dict[str, Any]:
        """Returns structured JSON-serializable snapshot of the barcode clock state."""
        with self._lock:
            active = [f for f in self._features.values() if f.is_alive]
            dead = [f for f in self._features.values() if not f.is_alive]
            avg_lifetime = (
                sum(f.lifetime(self._N) for f in dead) / len(dead) if dead else 0.0
            )
            return {
                "clock_N": self._N,
                "active_features_count": len(active),
                "dead_features_count": len(dead),
                "average_dead_persistence": round(avg_lifetime, 2),
                "betti_estimate": self.get_betti_numbers(),
                "recent_active_generators": [f.generator_id for f in active[-10:]],
            }

    def _prune_history_if_needed(self) -> None:
        """Prunes oldest dead features if history exceeds limit."""
        dead_keys = [k for k, f in self._features.items() if not f.is_alive]
        if len(dead_keys) > self._history_limit:
            # Sort by death clock asc
            dead_keys.sort(key=lambda k: self._features[k].death or 0)
            to_remove = dead_keys[: len(dead_keys) - self._history_limit]
            for k in to_remove:
                self._features.pop(k, None)
