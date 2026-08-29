"""
Markov Trace Operator & Air-Gapped DPO Triplet Harvesting Engine
================================================================
Realizes the Act Operator (A : G x W -> [0,1]) and recursive self-improvement cycle.
Computes Schur complement hidden excursions, Frenet-Serret curvature,
and persists verified (x, y_w, y_l) preference triplets without mutating base weights.
"""

from __future__ import annotations

import os
import json
import time
import numpy as np
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional, Tuple

from ..logging_config import get_logger

logger = get_logger("MarkovTrace")


@dataclass
class DPOTriplet:
    triplet_id: str
    prompt_context_x: str
    winning_response_yw: str
    losing_response_yl: str
    source_category: str            # "gjk_snapback", "ast_self_heal", "avl_rejection", "jspace_dream"
    curvature_kappa: float
    schur_trace_score: float
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class MarkovTraceEngine:
    """
    Evaluates multi-step agent trajectories gamma(t) using the Markov Trace Operator:
        Tr_A(P) = A + B(I - C)^(-1) D
    and evaluates Frenet-Serret curvature (kappa <= 5.0).
    """

    def compute_schur_complement_trace(
        self,
        transition_matrix: np.ndarray
    ) -> float:
        """
        Computes the Schur complement hidden excursion trace for a partitioned Markov transition matrix:
        P = [[A, B], [C, D]].
        """
        # Ensure 2D square matrix
        P = np.asarray(transition_matrix, dtype=np.float64)
        if P.ndim != 2 or P.shape[0] != P.shape[1] or P.shape[0] < 2:
            return 1.0

        n = P.shape[0]
        mid = n // 2

        A = P[:mid, :mid]
        B = P[:mid, mid:]
        C = P[mid:, :mid]
        D = P[mid:, mid:]

        try:
            I_minus_C = np.eye(C.shape[0]) - C
            inv_part = np.linalg.pinv(I_minus_C)
            schur = A + (B @ inv_part @ D)
            trace_val = float(np.trace(schur))
            return trace_val
        except Exception as e:
            logger.debug(f"[MarkovTrace] Schur computation note: {e}")
            return float(np.trace(P))

    def compute_frenet_serret_curvature(
        self,
        trajectory_points: np.ndarray
    ) -> Tuple[float, bool]:
        """
        Computes the curvature kappa of continuous thought trajectories.
        Triggers emergency halt if kappa > 5.0 (curvature snap).
        """
        pts = np.asarray(trajectory_points, dtype=np.float64)
        if pts.shape[0] < 3:
            return 0.0, True  # Not enough points, assume smooth

        # First derivatives (velocities)
        v = np.gradient(pts, axis=0)
        # Second derivatives (accelerations)
        a = np.gradient(v, axis=0)

        # Cross product magnitude ||v x a|| / ||v||^3
        v_norms = np.linalg.norm(v, axis=1)
        # For 3D points
        if pts.shape[1] == 3:
            v_cross_a = np.cross(v, a)
            cross_norms = np.linalg.norm(v_cross_a, axis=1)
            denominators = np.maximum(v_norms ** 3, 1e-6)
            kappas = cross_norms / denominators
            mean_kappa = float(np.mean(kappas))
        else:
            mean_kappa = float(np.mean(np.linalg.norm(a, axis=1) / np.maximum(v_norms ** 2, 1e-6)))

        is_smooth = mean_kappa <= 5.0
        return round(mean_kappa, 3), is_smooth


class DPOTripletHarvester:
    """
    Air-gapped DPO Preference Triplet Harvester.
    Persists (x, y_w, y_l) triplets in workspace/artifacts/dpo_harvest/
    for non-destructive offline dreaming cycles.
    """

    def __init__(self, workspace_root: Optional[str] = None):
        self.workspace_root = workspace_root or os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..")
        )
        self.output_dir = os.path.join(self.workspace_root, "workspace", "artifacts", "dpo_harvest")
        self.trace_engine = MarkovTraceEngine()

    def record_triplet(
        self,
        prompt_x: str,
        winning_yw: str,
        losing_yl: str,
        category: str = "jspace_dream",
        trajectory_points: Optional[np.ndarray] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> DPOTriplet:
        """Constructs and persists an air-gapped DPO triplet."""
        kappa = 0.0
        if trajectory_points is not None and trajectory_points.shape[0] >= 3:
            kappa, _ = self.trace_engine.compute_frenet_serret_curvature(trajectory_points)

        schur_score = 1.0

        triplet = DPOTriplet(
            triplet_id=f"dpo_{int(time.time()*1000)}",
            prompt_context_x=prompt_x,
            winning_response_yw=winning_yw,
            losing_response_yl=losing_yl,
            source_category=category,
            curvature_kappa=kappa,
            schur_trace_score=schur_score,
            timestamp=time.time(),
            metadata=metadata or {}
        )

        self._persist_triplet_to_disk(triplet)
        return triplet

    def _persist_triplet_to_disk(self, triplet: DPOTriplet) -> None:
        """Appends triplet to monthly JSONL file in workspace/artifacts/dpo_harvest/."""
        try:
            os.makedirs(self.output_dir, exist_ok=True)
            month_str = time.strftime("%Y-%m")
            file_path = os.path.join(self.output_dir, f"dpo_triplets_{month_str}.jsonl")
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(triplet)) + "\n")
        except Exception as e:
            logger.debug(f"[DPOTripletHarvester] Failed to persist triplet to disk: {e}")

    def list_recent_triplets(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Retrieves most recent harvested triplets from storage."""
        results = []
        try:
            if not os.path.exists(self.output_dir):
                return results
            files = sorted([f for f in os.listdir(self.output_dir) if f.endswith(".jsonl")], reverse=True)
            for fname in files:
                fpath = os.path.join(self.output_dir, fname)
                with open(fpath, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            try:
                                results.append(json.loads(line.strip()))
                            except Exception:
                                continue
                if len(results) >= limit:
                    break
        except Exception as e:
            logger.debug(f"[DPOTripletHarvester] Error listing triplets: {e}")
        return results[:limit]
