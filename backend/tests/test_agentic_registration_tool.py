import pytest
import os
from pathlib import Path
from backend.tools.agentic_registration_tool import AgenticRegistrationTool
from backend.tool_manager import ToolManager
from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_discover_agent_auth_metadata():
    tool = AgenticRegistrationTool(vault_manager=None, exec_approval_mgr=None)
    res = await tool.discover_agent_auth_metadata("example.com")
    assert res["status"] == "SUCCESS"
    assert "agent_auth" in res
    assert "identity_endpoint" in res["agent_auth"]


@pytest.mark.asyncio
async def test_register_agent_identity():
    tool = AgenticRegistrationTool(vault_manager=None, exec_approval_mgr=None)
    payload = {
        "type": "identity_assertion",
        "assertion_type": "urn:ietf:params:oauth:token-type:id-jag",
        "assertion": "eyJhbGciOiJSUzI1NiJ9.simulated_jwt",
        "scopes": ["api.read", "api.write"]
    }

    res = await tool.register_agent_identity("example.com", payload)
    assert res["status"] == "SUCCESS"
    assert res["registration_type"] == "identity_assertion"
    assert "registration_id" in res["response"]


@pytest.mark.asyncio
async def test_exchange_token_jwt_bearer():
    tool = AgenticRegistrationTool(vault_manager=None, exec_approval_mgr=None)
    token_endpoint = "https://auth.example.com/oauth2/token"
    assertion = "eyJhbGciOiJSUzI1NiJ9.simulated_jwt"

    res = await tool.exchange_token_jwt_bearer(token_endpoint, assertion, target_domain="example.com")
    assert res["status"] == "SUCCESS"
    assert "access_token" in res["token_response"]


@pytest.mark.asyncio
async def test_export_registration_package(tmp_path):
    tool = AgenticRegistrationTool(vault_manager=None, exec_approval_mgr=None)
    tool.output_base_dir = tmp_path / "deliverables"

    payload = {
        "target_domain": "workos.com",
        "type": "identity_assertion",
        "registration_id": "reg_12345"
    }

    res = tool.export_registration_package(payload, company_name="AuthCo")
    assert res["status"] == "SUCCESS"
    assert res["files_generated_count"] >= 5
    assert os.path.exists(res["export_directory"])

    exp_dir = Path(res["export_directory"])
    assert (exp_dir / "Agentic_Registration_Blueprint.json").exists()
    assert (exp_dir / "Registration_Audit_Ledger.csv").exists()
    assert (exp_dir / "Agent_Auth_Dashboard.html").exists()
    assert (exp_dir / "Protocol_Compliance_Report.md").exists()
    assert (exp_dir / "Registration_Manifest.json").exists()


@pytest.mark.asyncio
async def test_agentic_registration_tool_manifest_discovery():
    mock_vault = AsyncMock()
    mock_vault.retrieve_secret.return_value = {}
    tm = ToolManager(vault=mock_vault)
    tools = await tm.list_tools()
    reg_tool = [t for t in tools if t.get("id") == "agentic_registration_tool_01"]
    assert len(reg_tool) > 0
    assert reg_tool[0]["name"] == "Agentic Registration Engine Tool"
