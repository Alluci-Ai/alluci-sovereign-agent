import pytest
import os
from pathlib import Path
from backend.tools.ownership_capital_strategy_tool import OwnershipCapitalStrategyTool
from backend.tool_manager import ToolManager
from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_audit_cap_table_ledger():
    tool = OwnershipCapitalStrategyTool(vault_manager=None, exec_approval_mgr=None)
    sample_cap = {
        "common_shares": 8000000,
        "preferred_shares": 1000000,
        "issued_options": 500000,
        "unallocated_options": 500000,
        "founder_shares": 7000000,
        "safe_count": 2
    }

    res = tool.audit_cap_table_ledger(sample_cap)
    assert res["status"] == "SUCCESS"
    assert res["fully_diluted_shares"] == 10000000
    assert res["founder_ownership_pct"] == 70.0
    assert res["option_pool_pct"] == 10.0


@pytest.mark.asyncio
async def test_model_dilution_scenarios():
    tool = OwnershipCapitalStrategyTool(vault_manager=None, exec_approval_mgr=None)
    cap = {"fully_diluted_shares": 10000000, "founder_shares": 7000000}
    financing = {
        "pre_money_valuation": 15000000,
        "investment_amount": 5000000
    }

    res = tool.model_dilution_scenarios(cap, financing)
    assert res["status"] == "SUCCESS"
    assert res["post_money_valuation"] == 20000000
    assert res["share_price"] == 1.5
    assert res["new_investor_shares"] == 3333333
    assert res["founder_post_round_pct"] < 70.0


@pytest.mark.asyncio
async def test_calculate_waterfall_payouts():
    tool = OwnershipCapitalStrategyTool(vault_manager=None, exec_approval_mgr=None)
    cap = {
        "common_shares": 8000000,
        "preferred_shares": 2000000,
        "preferred_investment": 2000000,
        "founder_shares": 7000000
    }

    res = tool.calculate_waterfall_payouts(cap, 50000000.0)
    assert res["status"] == "SUCCESS"
    assert res["exit_valuation"] == 50000000.0
    assert "converts to Common" in res["waterfall_decision"]
    assert res["preferred_investor_payout"] == 10000000.0
    assert res["common_shareholders_payout"] == 40000000.0
    assert res["founder_payout"] == 35000000.0


@pytest.mark.asyncio
async def test_export_capital_strategy_package(tmp_path):
    tool = OwnershipCapitalStrategyTool(vault_manager=None, exec_approval_mgr=None)
    tool.output_base_dir = tmp_path / "deliverables"

    sample_data = {
        "cap_table": {
            "common_shares": 8000000,
            "preferred_shares": 1000000,
            "issued_options": 500000,
            "unallocated_options": 500000,
            "founder_shares": 7000000
        },
        "financing_round": {
            "pre_money_valuation": 15000000,
            "investment_amount": 5000000
        }
    }

    res = tool.export_capital_strategy_package(sample_data, company_name="EquityCo")
    assert res["status"] == "SUCCESS"
    assert res["files_generated_count"] >= 5
    assert os.path.exists(res["export_directory"])

    exp_dir = Path(res["export_directory"])
    assert (exp_dir / "Cap_Table_Ledger.json").exists()
    assert (exp_dir / "Pro_Forma_Dilution_Model.csv").exists()
    assert (exp_dir / "Liquidation_Waterfall_Analysis.md").exists()
    assert (exp_dir / "Capital_Strategy_Brief.json").exists()
    assert (exp_dir / "Ownership_Manifest.json").exists()


@pytest.mark.asyncio
async def test_ocs_01_tool_manifest_discovery():
    mock_vault = AsyncMock()
    mock_vault.retrieve_secret.return_value = {}
    tm = ToolManager(vault=mock_vault)
    tools = await tm.list_tools()
    ocs_tool = [t for t in tools if t.get("id") == "ocs_tool_01"]
    assert len(ocs_tool) > 0
    assert ocs_tool[0]["name"] == "Ownership Intelligence & Capital Strategy Tool"
