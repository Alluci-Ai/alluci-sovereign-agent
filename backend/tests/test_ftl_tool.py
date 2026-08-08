import pytest
import os
from pathlib import Path
from backend.tools.founding_team_leadership_tool import FoundingTeamLeadershipTool
from backend.tool_manager import ToolManager
from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_audit_leadership_architecture():
    tool = FoundingTeamLeadershipTool(vault_manager=None, exec_approval_mgr=None)
    data = {
        "founders": [
            {"name": "Founder A", "title": "CEO", "primary_domain": "Strategy & Vision"},
            {"name": "Founder B", "title": "CTO", "primary_domain": "Technical Architecture"}
        ]
    }

    res = tool.audit_leadership_architecture(data)
    assert res["status"] == "SUCCESS"
    assert res["total_founders"] == 2
    assert res["domain_coverage_score"] == 50.0
    assert "Product Experience" in res["missing_domains"]
    assert "Go-To-Market & Revenue" in res["missing_domains"]


@pytest.mark.asyncio
async def test_model_founder_equity_vesting():
    tool = FoundingTeamLeadershipTool(vault_manager=None, exec_approval_mgr=None)
    grant_data = {
        "total_fully_diluted_shares": 10000000.0,
        "founder_name": "Founder A",
        "granted_shares": 4000000.0,
        "months_elapsed": 12,
        "acceleration_type": "Double-Trigger"
    }

    res = tool.model_founder_equity_vesting(grant_data)
    assert res["status"] == "SUCCESS"
    assert res["ownership_percentage"] == 40.0
    assert res["vested_shares"] == 1000000.0  # 25% cliff at Month 12
    assert res["unvested_shares"] == 3000000.0
    assert res["vested_percentage"] == 25.0
    assert res["acceleration_clause"] == "Double-Trigger"


@pytest.mark.asyncio
async def test_calculate_leadership_capacity_tco():
    tool = FoundingTeamLeadershipTool(vault_manager=None, exec_approval_mgr=None)
    payload = {
        "founder_draws_annual": 240000.0,
        "executive_salaries_annual": 350000.0,
        "board_advisory_fees": 20000.0,
        "advisory_equity_annual_val": 30000.0
    }

    res = tool.calculate_leadership_capacity_tco(payload)
    assert res["status"] == "SUCCESS"
    assert res["total_leadership_tco"] == 640000.0


@pytest.mark.asyncio
async def test_export_leadership_package(tmp_path):
    tool = FoundingTeamLeadershipTool(vault_manager=None, exec_approval_mgr=None)
    tool.output_base_dir = tmp_path / "deliverables"

    payload = {
        "team_data": {
            "founders": [{"name": "Founder A", "title": "CEO", "primary_domain": "Strategy & Vision"}]
        },
        "raci_items": [
            {"function": "Capital Allocation", "responsible": "CEO", "approver": "Board", "consulted": "CFO", "informed": "Team"}
        ],
        "vesting_data": {
            "total_fully_diluted_shares": 10000000.0,
            "founder_name": "Founder A",
            "granted_shares": 4000000.0,
            "months_elapsed": 24
        }
    }

    res = tool.export_leadership_package(payload, company_name="TeamCo")
    assert res["status"] == "SUCCESS"
    assert res["files_generated_count"] >= 5
    assert os.path.exists(res["export_directory"])

    exp_dir = Path(res["export_directory"])
    assert (exp_dir / "Founding_Team_Blueprint.json").exists()
    assert (exp_dir / "Leadership_RACI_Matrix.csv").exists()
    assert (exp_dir / "Founder_Vesting_Dashboard.html").exists()
    assert (exp_dir / "Executive_Hiring_Roadmap.md").exists()
    assert (exp_dir / "Leadership_Manifest.json").exists()


@pytest.mark.asyncio
async def test_ftl_01_tool_manifest_discovery():
    mock_vault = AsyncMock()
    mock_vault.retrieve_secret.return_value = {}
    tm = ToolManager(vault=mock_vault)
    tools = await tm.list_tools()
    ftl_tool = [t for t in tools if t.get("id") == "ftl_tool_01"]
    assert len(ftl_tool) > 0
    assert ftl_tool[0]["name"] == "Founding Team Design & Leadership Architecture Tool"
