import pytest
import asyncio
import os
from unittest.mock import MagicMock
from cryptography.fernet import Fernet
from backend.orchestrator import ExecutiveOrchestrator
from backend.config import settings
from backend.security.vault import VaultManager

@pytest.mark.asyncio
async def test_full_phase1_flow(monkeypatch, tmp_path):
    # 1. Isolation
    vroot = str(tmp_path / "vault")
    os.makedirs(vroot)
    
    valid_key = Fernet.generate_key().decode()
    monkeypatch.setattr("backend.config.settings.POLYTOPE_MASTER_KEY", valid_key)
    
    vault = VaultManager(valid_key, vault_root=vroot)

    # 2. Setup Mock Router & Components
    router = MagicMock()
    # Mock planning response
    router.get_response.return_value = '{"steps": [{"id": "s1", "description": "echo test", "tool": "shell", "args": {"command": "echo hello"}, "dependencies": []}]}'
    
    vault = MagicMock()
    # The original vault (VaultManager instance) is used, not a MagicMock.
    # vault = MagicMock()
    # vault.retrieve_secret.return_value = {"skills": []}
    
    ace = MagicMock()
    ace.get_affective_state.return_value = MagicMock(tension=100.0)
    ace.btm.psi_from_state.return_value = 0.1
    
    # 2. Initialize Orchestrator
    # We need to mock PPN as it involves torch/models
    orchestrator = ExecutiveOrchestrator(router, vault, ace, settings, vault_root=vroot)
    orchestrator.ppn = MagicMock()
    # PPN Return: G, D, B, Points, Phi, Budget, Coherence, Shift
    import torch
    orchestrator.ppn.return_value = (MagicMock(), MagicMock(), torch.tensor([1,1,1]), MagicMock(), 0.1, 0.1, 0.9, 0.0)
    orchestrator.ppn.extract_simplex_counts.return_value = (10, 20, 10)
    
    # 3. Execute Objective
    result = await orchestrator.execute_objective("Test full flow", autonomy="autonomous")
    
    # 4. Verify
    assert orchestrator.ppn.called
