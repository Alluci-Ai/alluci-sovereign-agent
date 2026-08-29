import os
import json
import pytest
import numpy as np
from backend.engine.dpo_harvester import DPOHarvester

pytestmark = pytest.mark.unit


def test_harvest_from_healing():
    """
    Verifies DPO extraction from self-healing resolution strings.
    """
    harvester = DPOHarvester()
    records = [
        {
            "content": "[FAILED: NameError 'x' is not defined] -> [RESOLUTION: initialize x = 0 before loop]",
            "source": "codi_engine"
        },
        {
            "content": "Short",  # Too short, should be filtered
            "source": "test"
        }
    ]

    pairs = harvester.harvest_from_healing(records)
    assert len(pairs) == 1
    assert "initialize x = 0" in pairs[0]["chosen"]
    assert "NameError 'x'" in pairs[0]["rejected"]
    assert pairs[0]["source"] == "self_healing_delta"


def test_harvest_from_quarantine():
    """
    Verifies DPO extraction from quarantined AST anti-patterns.
    """
    harvester = DPOHarvester()
    records = [
        {
            "task_id": "TASK-101",
            "description": "File write operation",
            "reason": "Forbidden path traversal detected",
            "code": "open('../../root/etc', 'w')",
            "repaired_code": "open('./sandbox/file.txt', 'w')"
        }
    ]

    pairs = harvester.harvest_from_quarantine(records)
    assert len(pairs) == 1
    assert pairs[0]["chosen"] == "open('./sandbox/file.txt', 'w')"
    assert pairs[0]["rejected"] == "open('../../root/etc', 'w')"
    assert "TASK-101" in pairs[0]["prompt"]


def test_analytical_dpo_loss():
    """
    Verifies mathematical DPO loss behavior under different log-probability margins.
    """
    harvester = DPOHarvester(beta=0.1)

    # Case 1: Neutral baseline (pi == ref) -> loss = ln(2) ≈ 0.693147
    neutral_loss = harvester.compute_dpo_loss(
        chosen_logp=-1.0,
        rejected_logp=-1.0,
        ref_chosen_logp=-1.0,
        ref_rejected_logp=-1.0
    )
    assert abs(neutral_loss - np.log(2.0)) < 1e-4

    # Case 2: Positive reward margin (policy strongly favors winner) -> loss approaches 0
    winner_loss = harvester.compute_dpo_loss(
        chosen_logp=-0.1,
        rejected_logp=-5.0,
        ref_chosen_logp=-2.0,
        ref_rejected_logp=-2.0,
        beta=1.0
    )
    assert winner_loss < 0.05

    # Case 3: Policy drift (policy favors loser) -> loss grows large
    drift_loss = harvester.compute_dpo_loss(
        chosen_logp=-5.0,
        rejected_logp=-0.1,
        ref_chosen_logp=-2.0,
        ref_rejected_logp=-2.0,
        beta=1.0
    )
    assert drift_loss > 4.5


def test_save_preference_dataset(tmp_path):
    """
    Verifies atomic dataset serialization into valid JSONL format.
    """
    temp_dir = str(tmp_path)
    harvester = DPOHarvester(storage_dir=temp_dir)
    
    sample_pairs = [
        {"prompt": "Task 1", "chosen": "Good code", "rejected": "Bad code"},
        {"prompt": "Task 2", "chosen": "Safe plan", "rejected": "Unsafe plan"}
    ]
    
    out_file = harvester.save_preference_dataset(sample_pairs, "test_dataset")
    assert os.path.exists(out_file)

    with open(out_file, "r", encoding="utf-8") as f:
        lines = [json.loads(line) for line in f]

    assert len(lines) == 2
    assert lines[0]["chosen"] == "Good code"
    assert lines[1]["rejected"] == "Unsafe plan"
