"""
Action Affordance Space & Convex Envelope Engine
================================================
Realizes the Decide Operator (D : J x G -> [0,1]) by defining the convex hull
of valid execution vectors, tool invocations, and sub-agent capability envelopes.
"""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Tuple, Any


@dataclass
class AffordanceVector:
    action_type: str              # e.g., "tool_execution", "ast_refactor", "file_write", "os_command"
    target_resource: str          # e.g., "backend/routers/memory.py", "git_commit", "terminal_command"
    risk_weight: float            # [0.0, 1.0]
    requires_hitl: bool           # True if destructive or security-critical
    capability_tag: str           # e.g., "codi_engineering", "rocco_research", "system_admin"
    parameter_payload: Dict[str, Any] = field(default_factory=dict)
    convex_coordinates: np.ndarray = field(default_factory=lambda: np.zeros(3))


class ActionAffordanceEnvelope:
    """
    Action Affordance Envelope (G, G).
    A convex hull boundary defining permitted action vectors given active experience X and simulation J.
    """

    # Base restricted actions that strictly require HITL authorization
    DESTRUCTIVE_ACTIONS: Set[str] = {
        "file_delete", "memory_purge", "drop_table", "force_push",
        "rm_rf", "format_disk", "kill_port_process", "transfer_funds"
    }

    # Sub-agent scoped capability sets
    SUBAGENT_CAPABILITIES: Dict[str, Set[str]] = {
        "codi": {"ast_refactor", "run_test", "lsp_diagnostic", "git_diff", "file_edit", "codebase_search"},
        "rocco": {"web_search", "document_summary", "data_extraction", "read_url", "hlsm_query"},
        "admin": {"system_inspect", "vault_manage", "calibrate_rbm", "service_status"},
    }

    def __init__(self, max_hull_radius: float = 1.0):
        self.max_hull_radius = max_hull_radius

    def build_affordance_vector(
        self,
        action_type: str,
        target_resource: str,
        capability_tag: str = "general",
        parameter_payload: Optional[Dict[str, Any]] = None,
        is_destructive: bool = False
    ) -> AffordanceVector:
        """Constructs an affordance vector with spatial coordinates in the action simplex."""
        params = parameter_payload or {}
        is_hitl = is_destructive or (action_type.lower() in self.DESTRUCTIVE_ACTIONS)

        # Compute risk weight: [0.1 for read, 0.5 for edit, 1.0 for destructive]
        if is_hitl:
            risk = 0.95
        elif "read" in action_type or "search" in action_type or "inspect" in action_type:
            risk = 0.15
        elif "edit" in action_type or "refactor" in action_type:
            risk = 0.45
        else:
            risk = 0.5

        # 3D spatial coordinate representation in action simplex
        coords = np.array([
            risk,
            1.0 if is_hitl else 0.0,
            0.5
        ], dtype=np.float64)

        return AffordanceVector(
            action_type=action_type,
            target_resource=target_resource,
            risk_weight=risk,
            requires_hitl=is_hitl,
            capability_tag=capability_tag,
            parameter_payload=params,
            convex_coordinates=coords,
        )

    def evaluate_affordance(
        self,
        vector: AffordanceVector,
        subagent_id: Optional[str] = None,
        affective_tension_psi: float = 0.0
    ) -> Tuple[bool, str]:
        """
        Validates if the affordance vector lies strictly within the permitted convex hull.
        Checks sub-agent privilege envelope and bio-affective tension thresholds.
        """
        # 1. Sub-agent privilege boundary check
        if subagent_id:
            allowed_caps = self.SUBAGENT_CAPABILITIES.get(subagent_id.lower())
            if allowed_caps and vector.action_type not in allowed_caps and not vector.capability_tag.startswith(subagent_id):
                return False, f"Sub-agent '{subagent_id}' lacks capability envelope for '{vector.action_type}'"

        # 2. Strict HITL Gate for Destructive Actions
        if vector.requires_hitl:
            return False, f"Action '{vector.action_type}' on '{vector.target_resource}' requires explicit HITL Executive authorization"

        # 3. Bio-Affective Tension Gating
        # If agent is under severe affective stress (psi > 0.85), restrict high-risk writes
        if affective_tension_psi > 0.85 and vector.risk_weight > 0.4:
            return False, f"Action suspended: High affective tension (psi={affective_tension_psi:.2f}) exceeds safe write threshold"

        # 4. Convex Radius Check
        norm = float(np.linalg.norm(vector.convex_coordinates))
        if norm > self.max_hull_radius * 1.5:
            return False, f"Action vector radius ({norm:.2f}) exceeds convex envelope ({self.max_hull_radius:.2f})"

        return True, "Affordance verified within safe convex envelope"
