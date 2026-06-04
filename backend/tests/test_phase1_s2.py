import pytest
import os
import yaml  # type: ignore
from cryptography.fernet import Fernet
from backend.memory.manager import MemoryManager
from backend.skill_manager import SkillManager
from backend.adapters.registry import AdapterRegistry
from backend.adapters.shell import ShellAdapter
from backend.adapters.web import WebAdapter

@pytest.fixture
def temp_dir(tmp_path):
    d = tmp_path / "polytope"
    d.mkdir()
    return str(d)

@pytest.mark.asyncio
async def test_memory_manager(temp_dir):
    mem_dir = os.path.join(temp_dir, "memory")
    manager = MemoryManager(persist_directory=mem_dir)
    
    # Store
    mid = await manager.store("The secret code is 1234", {"type": "test"})
    assert mid is not None
    
    # Search
    results = await manager.search("secret code")
    assert len(results) > 0
    assert "1234" in results[0]["content"]

@pytest.mark.asyncio
async def test_skill_manager_disk(temp_dir):
    skills_dir = os.path.join(temp_dir, "skills")
    os.makedirs(skills_dir)
    
    # Create a dummy skill YAML
    skill_manifest = {
        "id": "test_skill",
        "name": "Test Disk Skill",
        "version": "1.0.0",
        "description": "Testing disk loading"
    }
    with open(os.path.join(skills_dir, "test.yaml"), "w") as f:
        yaml.dump(skill_manifest, f)
        
    class MockVault:
        async def retrieve_secret(self, key): return {}
        
    manager = SkillManager(MockVault(), skills_dir=skills_dir)  # type: ignore
    skills = await manager.list_skills()
    
    assert any(s["id"] == "test_skill" for s in skills)
    assert any(s.get("source") == "disk" for s in skills)

@pytest.mark.asyncio
async def test_goals_and_sop(temp_db):
    # Goals — use temp_db engine for isolation
    from backend.goals.engine import GoalsEngine
    engine = GoalsEngine(engine=temp_db)
    gid = await engine.create_goal("Test Goal", "Verify goals")
    goal = await engine.get_goal(gid)
    assert goal is not None
    assert goal.status == "active"
    
    # SOPs — also DB-backed, inject temp_db
    from backend.sop.engine import SOPEngine
    sop = SOPEngine(engine=temp_db)
    sop_id = await sop.register_sop("test_sop", "Test SOP", [{"action": "shell", "args": {"command": "ls"}}])
    result = sop.get_sop(sop_id)
    assert result is not None

@pytest.mark.asyncio
async def test_adapters_registry(monkeypatch, tmp_path):
    # Vault root isolation
    vroot = tmp_path / "vault"
    vroot.mkdir()
    
    # BridgeActualizationAdapter -> VaultManager -> Fernet requires 32-byte b64 key
    valid_key = Fernet.generate_key().decode()
    monkeypatch.setattr("backend.config.settings.POLYTOPE_MASTER_KEY", valid_key)
    
    registry = AdapterRegistry(vault_root=str(vroot))
    assert registry.get("shell") is not None
    assert registry.get("web_search") is not None
    
    # Test shell execution (safe check)
    shell = registry.get("shell")
    res = await shell.execute({"command": "echo 'hello'"})  # type: ignore
    assert "hello" in res.strip()
