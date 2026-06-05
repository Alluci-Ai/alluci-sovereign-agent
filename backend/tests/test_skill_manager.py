import pytest
import os
import json
import yaml  # type: ignore
from unittest.mock import patch, MagicMock, AsyncMock
from backend.skill_manager import SkillManager
from backend.security.vault import VaultManager

@pytest.fixture
def mock_vault():
    vault = MagicMock(spec=VaultManager)
    # Store secrets in a local dictionary for testing
    vault.storage = {}
    
    async def store_secret(k, v):
        vault.storage[k] = v
        
    async def retrieve_secret(k):
        return vault.storage.get(k, {})
        
    vault.store_secret = AsyncMock(side_effect=store_secret)
    vault.retrieve_secret = AsyncMock(side_effect=retrieve_secret)
    return vault

@pytest.fixture
def temp_skills_dir(tmp_path):
    d = tmp_path / "skills"
    d.mkdir()
    return str(d)

@pytest.fixture
def skill_manager(mock_vault, temp_skills_dir):
    return SkillManager(vault=mock_vault, skills_dir=temp_skills_dir)

class TestSkillManager:
    @pytest.mark.asyncio
    async def test_list_skills(self, skill_manager, temp_skills_dir, mock_vault):
        # 1. Disk skills
        skill_manifest = {"id": "disk_skill", "name": "Test Disk"}
        with open(os.path.join(temp_skills_dir, "test.yaml"), "w") as f:
            yaml.dump(skill_manifest, f)
            
        # 2. Vault skills
        await mock_vault.store_secret(skill_manager.registry_id, {
            "skills": [{"id": "vault_skill", "name": "Test Vault"}]
        })
        
        skills = await skill_manager.list_skills()
        assert len(skills) == 2
        ids = [s["id"] for s in skills]
        assert "disk_skill" in ids
        assert "vault_skill" in ids

    @pytest.mark.asyncio
    async def test_import_and_promote(self, skill_manager, mock_vault):
        package = {"id": "test1", "name": "MySkill"}
        
        # Mock ModelRouter inside import_package
        with patch("backend.inference.router.ModelRouter") as MockRouter:
            mock_router = MockRouter.return_value
            # Return valid JSON wrapped in markdown
            mock_router.get_response = AsyncMock(return_value='```json\n{"risk_score": 10, "notes": ["Looks good"]}\n```')
            
            res = await skill_manager.import_package(package)
            
            assert res["status"] == "queued"
            assert res["risk_score"] == 40  # 10 + 30 (unsigned penalty)
            
        # Check queue
        queue = await skill_manager.get_review_queue()
        assert len(queue) == 1
        assert queue[0]["id"] == "test1"
        assert "import_timestamp" in queue[0]
        
        # Promote
        promoted = await skill_manager.promote_from_queue("test1")
        assert promoted is True
        
        # Check active registry
        active = await skill_manager.registry_list()
        assert len(active) == 1
        assert active[0]["id"] == "test1"
        assert active[0]["verified"] is True
        
        # Queue should be empty
        queue = await skill_manager.get_review_queue()
        assert len(queue) == 0

    @pytest.mark.asyncio
    async def test_save_get_delete_skill(self, skill_manager):
        skill = {"id": "s1", "name": "Skill 1"}
        
        # Save
        await skill_manager.save_skill(skill)
        s = await skill_manager.get_skill("s1")
        assert s is not None
        assert s["name"] == "Skill 1"
        assert s["verified"] is True
        
        # Update
        s["name"] = "Skill 1 Updated"
        await skill_manager.save_skill(s)
        s_updated = await skill_manager.get_skill("s1")
        assert s_updated["name"] == "Skill 1 Updated"
        
        # Delete
        res = await skill_manager.delete_skill("s1")
        assert res is True
        assert await skill_manager.get_skill("s1") is None
        
        # Delete nonexistent
        res = await skill_manager.delete_skill("s1")
        assert res is False

    @pytest.mark.asyncio
    async def test_merge_skills_for_runtime(self, skill_manager):
        skill1 = {
            "id": "s1",
            "knowledge": ["k1"],
            "personalityMapping": {"toneShift": 0.5, "creativityShift": 0.1}
        }
        skill2 = {
            "id": "s2",
            "knowledge": ["k2"],
            "personalityMapping": {"toneShift": -0.2, "assertivenessShift": 0.3}
        }
        await skill_manager.save_skill(skill1)
        await skill_manager.save_skill(skill2)
        
        merged = await skill_manager.merge_skills_for_runtime(["s1", "s2"])
        assert "k1" in merged["knowledge"]
        assert "k2" in merged["knowledge"]
        assert merged["vectors"]["toneShift"] == 0.3
        assert merged["vectors"]["creativityShift"] == 0.1
        assert merged["vectors"]["assertivenessShift"] == 0.3

    @pytest.mark.asyncio
    async def test_get_skill_status(self, skill_manager):
        # 1. Not found
        res = await skill_manager.get_skill_status("missing")
        assert res["status"] == "error"
        
        # 2. Healthy
        await skill_manager.save_skill({"id": "healthy_skill"})
        res = await skill_manager.get_skill_status("healthy_skill")
        assert res["status"] == "HEALTHY"
        
        # 3. Missing dependencies
        await skill_manager.save_skill({"id": "dep_skill", "dependencies": ["missing_dep"]})
        res = await skill_manager.get_skill_status("dep_skill")
        assert res["status"] == "DEPENDENCY_MISSING"
        assert "missing_dep" in res["dependencies"]["missing"]
        
        # 4. Unhealthy (has error)
        await skill_manager.save_skill({"id": "err_skill", "error": "Crash!"})
        res = await skill_manager.get_skill_status("err_skill")
        assert res["status"] == "UNHEALTHY"

    @pytest.mark.asyncio
    async def test_store_and_get_skill_key(self, skill_manager):
        await skill_manager.store_skill_key("s1", "api_key", "123")
        val = await skill_manager.get_skill_key("s1", "api_key")
        assert val == "123"
        val2 = await skill_manager.get_skill_key("s1", "missing")
        assert val2 is None

    @pytest.mark.asyncio
    async def test_install_remote_package_success(self, skill_manager):
        package = {"id": "remote1", "name": "Remote", "version": "1.0"}
        
        class MockResponse:
            content = json.dumps(package).encode()
            def raise_for_status(self): pass
            
        class AsyncContextManager:
            async def __aenter__(self):
                mock_client = MagicMock()
                mock_client.get = AsyncMock(return_value=MockResponse())
                return mock_client
            async def __aexit__(self, exc_type, exc, tb): pass

        with patch("httpx.AsyncClient", return_value=AsyncContextManager()):
            with patch("backend.inference.router.ModelRouter") as MockRouter:
                mock_router = MockRouter.return_value
                mock_router.get_response = AsyncMock(return_value='{"risk_score": 0}')
                
                res = await skill_manager.install_remote_package("http://example.com/skill.json")
                assert "error" not in res
                assert res["status"] == "QUEUED_FOR_REVIEW"
                assert res["id"] == "remote1"

    @pytest.mark.asyncio
    async def test_install_remote_package_http_error(self, skill_manager):
        import httpx
        class MockRequest: pass
        class MockResponse:
            status_code = 404
            
        class AsyncContextManager:
            async def __aenter__(self):
                mock_client = MagicMock()
                mock_client.get = AsyncMock(side_effect=httpx.HTTPStatusError("404", request=MockRequest(), response=MockResponse()))
                return mock_client
            async def __aexit__(self, exc_type, exc, tb): pass

        with patch("httpx.AsyncClient", return_value=AsyncContextManager()):
            res = await skill_manager.install_remote_package("http://example.com")
            assert "error" in res
            assert "404" in res["error"]
