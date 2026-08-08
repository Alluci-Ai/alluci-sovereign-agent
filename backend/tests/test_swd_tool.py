import pytest
import os
from pathlib import Path
from backend.tools.strategic_workforce_design_tool import StrategicWorkforceDesignTool
from backend.tool_manager import ToolManager
from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_map_business_capabilities():
    tool = StrategicWorkforceDesignTool(vault_manager=None, exec_approval_mgr=None)
    tasks = [
        {"title": "Quarterly Budget Planning", "domain": "Strategic Leadership", "is_repetitive": False, "requires_judgment": True},
        {"title": "Contract Document Triage", "domain": "Operations & Support", "is_repetitive": True, "requires_judgment": False},
        {"title": "AI Model Fine-Tuning", "domain": "Engineering & R&D", "is_repetitive": False, "requires_judgment": True}
    ]

    res = tool.map_business_capabilities(tasks)
    assert res["status"] == "SUCCESS"
    assert res["total_tasks_mapped"] == 3
    assert res["repetitive_tasks_count"] == 1
    assert res["judgment_intensive_count"] == 2
    assert "Engineering & R&D" in res["capability_nodes"]


@pytest.mark.asyncio
async def test_analyze_resource_optimization():
    tool = StrategicWorkforceDesignTool(vault_manager=None, exec_approval_mgr=None)
    capabilities = [
        {"name": "Corporate Strategy", "high_human_judgment": True, "high_repetition": False, "ai_suitable": False},
        {"name": "Invoice Data Extraction", "high_human_judgment": False, "high_repetition": True, "ai_suitable": True},
        {"name": "Code Review & Refactoring", "high_human_judgment": True, "high_repetition": True, "ai_suitable": True}
    ]

    res = tool.analyze_resource_optimization(capabilities)
    assert res["status"] == "SUCCESS"
    assert res["total_capabilities_analyzed"] == 3
    assert res["execution_model_distribution"]["Human Employee"] == 1
    assert res["execution_model_distribution"]["Workflow Automation"] == 1
    assert res["execution_model_distribution"]["Hybrid (Human + AI)"] == 1


@pytest.mark.asyncio
async def test_calculate_ai_token_tco():
    tool = StrategicWorkforceDesignTool(vault_manager=None, exec_approval_mgr=None)
    model_data = {
        "human_headcount": 5,
        "avg_human_salary": 120000.0,
        "benefits_ratio": 0.25,
        "ai_agents_count": 10,
        "monthly_tokens_millions": 50.0,
        "token_price_per_million": 3.0,
        "monthly_ai_subscriptions": 500.0
    }

    res = tool.calculate_ai_token_tco(model_data)
    assert res["status"] == "SUCCESS"
    assert res["human_annual_tco"] == 750000.0
    assert res["monthly_token_cost"] == 150.0
    assert res["ai_annual_tco"] == (150.0 + 500.0) * 12.0
    assert res["total_combined_tco"] > 750000.0
    assert res["estimated_annual_tco_savings"] > 0.0


@pytest.mark.asyncio
async def test_export_workforce_package(tmp_path):
    tool = StrategicWorkforceDesignTool(vault_manager=None, exec_approval_mgr=None)
    tool.output_base_dir = tmp_path / "deliverables"

    sample_data = {
        "tasks": [
            {"title": "Core System Dev", "domain": "Engineering & R&D", "is_repetitive": False, "requires_judgment": True}
        ],
        "capabilities": [
            {"name": "Core System Dev", "high_human_judgment": True, "high_repetition": False, "ai_suitable": False}
        ],
        "economics": {
            "human_headcount": 4,
            "avg_human_salary": 110000.0
        }
    }

    res = tool.export_workforce_package(sample_data, company_name="TalentCo")
    assert res["status"] == "SUCCESS"
    assert res["files_generated_count"] >= 5
    assert os.path.exists(res["export_directory"])

    exp_dir = Path(res["export_directory"])
    assert (exp_dir / "Workforce_Blueprint.json").exists()
    assert (exp_dir / "Resource_Optimization_Matrix.csv").exists()
    assert (exp_dir / "Human_AI_Collaboration_Model.md").exists()
    assert (exp_dir / "Token_And_Labor_TCO_Report.json").exists()
    assert (exp_dir / "Workforce_Manifest.json").exists()


@pytest.mark.asyncio
async def test_swd_01_tool_manifest_discovery():
    mock_vault = AsyncMock()
    mock_vault.retrieve_secret.return_value = {}
    tm = ToolManager(vault=mock_vault)
    tools = await tm.list_tools()
    swd_tool = [t for t in tools if t.get("id") == "swd_tool_01"]
    assert len(swd_tool) > 0
    assert swd_tool[0]["name"] == "Strategic Workforce Design & Resource Optimization Tool"
