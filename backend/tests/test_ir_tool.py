import pytest
import os
from pathlib import Path
from backend.tools.investment_readiness_tool import InvestmentReadinessTool
from backend.tool_manager import ToolManager
from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_assess_readiness_gaps():
    tool = InvestmentReadinessTool(vault_manager=None, exec_approval_mgr=None)
    sample_inventory = {
        "strategy": ["Executive Summary", "Business Model", "Vision & Mission", "Market Analysis", "Strategic Roadmap"],
        "finance": ["Financial Statements", "Financial Model"],
        "legal": ["Ownership & Equity", "Corporate Governance", "Formation Documents"],
        "product": ["Product Overview", "Technical Architecture"],
        "commercial": ["Customer Validation"],
        "operations": ["Org Structure", "Leadership Bios"]
    }

    res = tool.assess_readiness_gaps(sample_inventory)
    assert res["status"] == "SUCCESS"
    assert res["readiness_score_pct"] > 40.0
    assert "Finance" in res["domain_breakdown"]
    assert len(res["domain_breakdown"]["Finance"]["missing_deliverables"]) == 3


@pytest.mark.asyncio
async def test_audit_data_room_structure():
    tool = InvestmentReadinessTool(vault_manager=None, exec_approval_mgr=None)
    sample_structure = {
        "folders": [
            "00_START_HERE",
            "01_CORPORATE_GOVERNANCE",
            "02_STRATEGY_AND_MARKET",
            "03_FINANCIAL_INFORMATION",
            "04_PRODUCT_AND_TECHNOLOGY",
            "05_COMMERCIAL_AND_CUSTOMERS",
            "06_TEAM_AND_OPERATIONS",
            "07_APPENDIX_AND_SUPPORTING_EVIDENCE"
        ]
    }

    res = tool.audit_data_room_structure(sample_structure)
    assert res["status"] == "SUCCESS"
    assert res["valid_folders_count"] == 8
    assert res["missing_folders_count"] == 0


@pytest.mark.asyncio
async def test_generate_investor_guide():
    tool = InvestmentReadinessTool(vault_manager=None, exec_approval_mgr=None)
    res = tool.generate_investor_guide("DiligenceCo", {})
    assert res["status"] == "SUCCESS"
    assert "DiligenceCo" in res["investor_guide_markdown"]
    assert "00_START_HERE" in res["investor_guide_markdown"]


@pytest.mark.asyncio
async def test_export_diligence_package(tmp_path):
    tool = InvestmentReadinessTool(vault_manager=None, exec_approval_mgr=None)
    tool.output_base_dir = tmp_path / "deliverables"

    sample_data = {
        "inventory": {
            "strategy": ["Executive Summary", "Business Model"],
            "finance": ["Financial Model"]
        },
        "structure": {
            "folders": ["00_START_HERE", "01_CORPORATE_GOVERNANCE"]
        }
    }

    res = tool.export_diligence_package(sample_data, company_name="DiligenceCo")
    assert res["status"] == "SUCCESS"
    assert res["files_generated_count"] >= 6
    assert os.path.exists(res["export_directory"])

    exp_dir = Path(res["export_directory"])
    assert (exp_dir / "Investor_Guide.md").exists()
    assert (exp_dir / "Investment_Readiness_Assessment.json").exists()
    assert (exp_dir / "Data_Room_Taxonomy.json").exists()
    assert (exp_dir / "Due_Diligence_Readiness_Checklist.md").exists()
    assert (exp_dir / "DocSend_Space_Spec.json").exists()
    assert (exp_dir / "Investor_Data_Room_Manifest.json").exists()


@pytest.mark.asyncio
async def test_ir_01_tool_manifest_discovery():
    mock_vault = AsyncMock()
    mock_vault.retrieve_secret.return_value = {}
    tm = ToolManager(vault=mock_vault)
    tools = await tm.list_tools()
    ir_tool = [t for t in tools if t.get("id") == "ir_tool_01"]
    assert len(ir_tool) > 0
    assert ir_tool[0]["name"] == "Investment Readiness Orchestrator Tool"
