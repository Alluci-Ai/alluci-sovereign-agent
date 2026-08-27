import pytest
pytestmark = pytest.mark.unit

import json
from sqlmodel import Session, select
from backend.models import AgentRecord, AgentSkillBinding
from backend.core.startup_checks import seed_codi_agent

def test_seed_codi_agent(temp_db):
    """Verify that seed_codi_agent correctly initializes Codi in the database."""
    from unittest.mock import patch
    with patch("backend.database.engine", temp_db):
        seed_codi_agent()

        with Session(temp_db) as session:
            codi = session.get(AgentRecord, "codi")
            assert codi is not None
            assert codi.id == "codi"
            assert codi.name == "Codi"
            assert codi.status == "ACTIVE"
            assert "GLM-4-32B" in codi.model
            assert codi.system_prompt is not None
            assert "CODI AUTONOMOUS SOFTWARE ENGINEER" in codi.system_prompt
            
            # Tools verification
            assert codi.tools_manifest is not None
            tools = json.loads(codi.tools_manifest)
            assert tools.get("opencode_ast_diff", {}).get("enabled") is True
            assert tools.get("opencode_lsp_diagnose", {}).get("enabled") is True
            assert tools.get("sovereign_checkpoint_create", {}).get("enabled") is True
            assert tools.get("sovereign_checkpoint_rollback", {}).get("enabled") is True

            # Skills verification
            assert codi.skills_manifest is not None
            skills = json.loads(codi.skills_manifest)
            assert skills.get("codi_01", {}).get("enabled") is True

            # Skill bindings verification
            bindings = session.exec(select(AgentSkillBinding).where(AgentSkillBinding.agent_id == "codi")).all()
            bound_skill_ids = [b.skill_id for b in bindings]
            assert "codi_01" in bound_skill_ids


def test_get_codi_agent_via_api(app_client, auth_headers, temp_db):
    """Verify that Codi is retrieved via /api/v1/agents and /api/v1/agents/codi."""
    from unittest.mock import patch
    with patch("backend.database.engine", temp_db):
        seed_codi_agent()

    with patch("backend.routers.sessions.db_engine", temp_db):
        resp = app_client.get("/api/v1/agents", headers=auth_headers)
        assert resp.status_code == 200
        agents = resp.json().get("agents", [])
        codi_entry = next((a for a in agents if a["id"] == "codi"), None)
        assert codi_entry is not None
        assert codi_entry["name"] == "Codi"
        assert codi_entry["status"] == "ACTIVE"
        assert codi_entry["active_tools"] >= 5

        # Single agent GET
        single_resp = app_client.get("/api/v1/agents/codi", headers=auth_headers)
        assert single_resp.status_code == 200
        agent_data = single_resp.json().get("agent", {})
        assert agent_data["name"] == "Codi"
        assert agent_data["status"] == "ACTIVE"
