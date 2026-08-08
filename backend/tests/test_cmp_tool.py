import pytest
import os
from pathlib import Path
from backend.tools.compensation_strategy_tool import CompensationStrategyTool
from backend.tool_manager import ToolManager
from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_audit_compensation_bands():
    tool = CompensationStrategyTool(vault_manager=None, exec_approval_mgr=None)
    data = {
        "roles": [
            {"role": "L4 Eng", "department": "Engineering", "current_base": 120000.0, "market_p50": 150000.0, "market_p75": 170000.0},  # -20% drift (flagged)
            {"role": "L5 Eng", "department": "Engineering", "current_base": 185000.0, "market_p50": 185000.0, "market_p75": 210000.0}
        ]
    }

    res = tool.audit_compensation_bands(data)
    assert res["status"] == "SUCCESS"
    assert res["total_roles_audited"] == 2
    assert res["flagged_roles_count"] == 1
    assert res["flagged_roles"][0]["role"] == "L4 Eng"


@pytest.mark.asyncio
async def test_model_equity_incentives():
    tool = CompensationStrategyTool(vault_manager=None, exec_approval_mgr=None)
    grant_data = {
        "total_fully_diluted_shares": 10000000.0,
        "granted_option_shares": 100000.0,
        "strike_price": 1.00,
        "preferred_share_price": 5.00
    }

    res = tool.model_equity_incentives(grant_data)
    assert res["status"] == "SUCCESS"
    assert res["ownership_percentage"] == 1.0
    assert res["gross_grant_value"] == 500000.0
    assert res["total_exercise_cost"] == 100000.0
    assert res["net_economic_value"] == 400000.0
    assert res["annual_vested_value"] == 100000.0
    assert res["vesting_schedule"]["cliff_vested_shares"] == 25000.0


@pytest.mark.asyncio
async def test_calculate_total_rewards_tco():
    tool = CompensationStrategyTool(vault_manager=None, exec_approval_mgr=None)
    payload = {
        "base_salary": 160000.0,
        "target_variable_bonus": 20000.0,
        "annual_benefits_cost": 20000.0,
        "annual_equity_vesting_value": 40000.0,
        "tech_subscriptions_cost": 5000.0
    }

    res = tool.calculate_total_rewards_tco(payload)
    assert res["status"] == "SUCCESS"
    assert res["total_cash_compensation"] == 180000.0
    assert res["total_rewards_tco"] == 245000.0
    assert res["cash_percentage_of_tco"] > 70.0


@pytest.mark.asyncio
async def test_export_compensation_package(tmp_path):
    tool = CompensationStrategyTool(vault_manager=None, exec_approval_mgr=None)
    tool.output_base_dir = tmp_path / "deliverables"

    payload = {
        "benchmark_data": {
            "roles": [{"role": "L4 Eng", "department": "Eng", "current_base": 150000.0, "market_p50": 150000.0}]
        },
        "equity_data": {
            "total_fully_diluted_shares": 10000000.0,
            "granted_option_shares": 50000.0
        },
        "rewards_data": {
            "base_salary": 150000.0
        }
    }

    res = tool.export_compensation_package(payload, company_name="CompCo")
    assert res["status"] == "SUCCESS"
    assert res["files_generated_count"] >= 5
    assert os.path.exists(res["export_directory"])

    exp_dir = Path(res["export_directory"])
    assert (exp_dir / "Compensation_Bands_Registry.csv").exists()
    assert (exp_dir / "Equity_Option_Grant_Model.json").exists()
    assert (exp_dir / "Total_Rewards_TCO_Dashboard.html").exists()
    assert (exp_dir / "Comp_Benchmarking_Report.md").exists()
    assert (exp_dir / "Compensation_Manifest.json").exists()


@pytest.mark.asyncio
async def test_cmp_01_tool_manifest_discovery():
    mock_vault = AsyncMock()
    mock_vault.retrieve_secret.return_value = {}
    tm = ToolManager(vault=mock_vault)
    tools = await tm.list_tools()
    cmp_tool = [t for t in tools if t.get("id") == "cmp_tool_01"]
    assert len(cmp_tool) > 0
    assert cmp_tool[0]["name"] == "Compensation Strategy Tool"
