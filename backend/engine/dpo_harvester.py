import json
import os
import numpy as np
from typing import List, Dict, Any, Optional
from ..logging_config import get_logger

logger = get_logger("DPOHarvester")


class DPOHarvester:
    """
    [ Direct Preference Optimization (DPO) Harvester & Loss Engine ]
    Source: AAP §DREAM — Teacher-Student Manifold Adapter Distillation

    Structures teacher-student preference triplets (x, y_w, y_l) from self-healing deltas,
    quarantined code anti-patterns, and topological verification failures without
    mutating immutable base foundation model weights.
    """

    def __init__(self, beta: float = 0.1, storage_dir: str = "./models/dpo"):
        self.beta = beta
        self.storage_dir = storage_dir
        os.makedirs(self.storage_dir, exist_ok=True)

    def harvest_from_healing(self, healing_records: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """
        Extracts (x, y_w, y_l) preference triplets from self-healing event logs.
        y_w = healed/corrected resolution, y_l = initial failed plan/error.
        """
        pairs: List[Dict[str, str]] = []
        for record in healing_records:
            content = record.get("content", "")
            source = record.get("source", "self_healing")
            if not content or len(content) < 30:
                continue

            # Parse standard self-healing deltas (e.g. "[FAILED: ...] -> [HEALED: ...]")
            if "->" in content or "RESOLUTION:" in content or "FIX:" in content:
                parts = content.split("->", 1) if "->" in content else content.split("RESOLUTION:", 1)
                if len(parts) == 2:
                    prompt = f"Resolve error during task execution ({source})"
                    rejected = parts[0].strip()
                    chosen = parts[1].strip()
                    if len(chosen) > 10 and len(rejected) > 10:
                        pairs.append({
                            "prompt": prompt,
                            "chosen": chosen,
                            "rejected": rejected,
                            "source": "self_healing_delta"
                        })
            else:
                # Default structured triplet from healing entry
                pairs.append({
                    "prompt": f"Self-healing execution resolution for: {content[:100]}",
                    "chosen": content,
                    "rejected": f"Error or unhandled exception during: {content[:100]}",
                    "source": "self_healing_implicit"
                })

        logger.info(f"[DPO Harvester] Harvested {len(pairs)} preference pairs from self-healing logs.")
        return pairs

    def harvest_from_quarantine(self, quarantine_records: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """
        Extracts (x, y_w, y_l) preference triplets from quarantined AST / runtime anti-patterns.
        y_w = sanitized / compliant solution, y_l = reverted quarantined code.
        """
        pairs: List[Dict[str, str]] = []
        for q in quarantine_records:
            task_id = q.get("task_id", "unknown_task")
            desc = q.get("description", "AST/Runtime Code Execution")
            reason = q.get("reason", "Violated topological boundary or test failure")
            bad_code = q.get("code", q.get("content", ""))
            repaired_code = q.get("repaired_code", q.get("clean_solution", ""))

            prompt = f"Implement secure and verified solution for task: {desc} ({task_id})"
            rejected = bad_code if bad_code else f"Failed execution pattern rejected due to: {reason}"
            chosen = repaired_code if repaired_code else f"Correct verified implementation adhering to zero-trust invariants without: {reason}"

            pairs.append({
                "prompt": prompt,
                "chosen": chosen,
                "rejected": rejected,
                "source": "quarantine_anti_pattern"
            })

        logger.info(f"[DPO Harvester] Harvested {len(pairs)} preference pairs from quarantined anti-patterns.")
        return pairs

    def compute_dpo_loss(
        self,
        chosen_logp: float,
        rejected_logp: float,
        ref_chosen_logp: float,
        ref_rejected_logp: float,
        beta: Optional[float] = None
    ) -> float:
        """
        Computes analytical DPO Loss:
          L_DPO = -ln(σ(β * [(log π_θ(y_w|x) - log π_ref(y_w|x)) - (log π_θ(y_l|x) - log π_ref(y_l|x))]))
                = ln(1 + exp(-margin))
        """
        effective_beta = beta if beta is not None else self.beta
        
        # Policy log-ratio deltas
        pi_logratios = chosen_logp - rejected_logp
        ref_logratios = ref_chosen_logp - ref_rejected_logp
        
        margin = effective_beta * (pi_logratios - ref_logratios)
        
        # Numerically stable softplus: ln(1 + exp(-margin)) = logaddexp(0, -margin)
        loss = float(np.logaddexp(0.0, -margin))
        return round(loss, 6)

    def save_preference_dataset(self, pairs: List[Dict[str, str]], filename: str) -> str:
        """
        Persists preference pairs to JSONL format in storage directory.
        """
        if not filename.endswith(".jsonl"):
            filename = f"{filename}.jsonl"
        out_path = os.path.join(self.storage_dir, filename)
        
        with open(out_path, "w", encoding="utf-8") as f:
            for pair in pairs:
                f.write(json.dumps(pair, ensure_ascii=False) + "\n")

        logger.info(f"[DPO Harvester] Persisted {len(pairs)} DPO pairs to: {out_path}")
        return out_path
