import pytest
import os
from pathlib import Path
from backend.tools.use_of_funds_capital_allocation_tool import UseOfFundsCapitalAllocationTool
from backend.tool_manager import ToolManager
from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_audit_capital_allocation():
    tool = UseOfFundsCapitalAllocationTool(vault_manager=None, exec_approval_mgr=None)
    data = {
        "categories": [
            {"name": "R&D", "budgeted": 100000.0, "actual": 125000.0},  # +25% variance (flagged)
            {"name": "GTM", "budgeted": 80000.0, "actual": 82000.0},
            {"name": "Ops", "budgeted": 30000.0, "actual": 30000.0}
        ]
    }

    res = tool.audit_capital_allocation(data)
    assert res["status"] == "SUCCESS"
    assert res["total_budgeted"] == 210000.0
    assert res["total_actual"] == 237000.0
    assert res["flagged_categories_count"] == 1
    assert res["flagged_variances"][0]["category"] == "R&D"


@pytest.mark.asyncio
async def test_calculate_runway_and_burn():
    tool = UseOfFundsCapitalAllocationTool(vault_manager=None, exec_approval_mgr=None)
    metrics = {
        "cash_balance": 2400000.0,
        "gross_monthly_burn": 200000.0,
        "monthly_cash_receipts": 40000.0,
        "milestones_completed": 8.0
    }

    res = tool.calculate_runway_and_burn(metrics)
    assert res["status"] == "SUCCESS"
    assert res["net_monthly_burn"] == 160000.0
    assert res["runway_months"] == 15.0
    assert res["runway_status"] == "Healthy (>= 12 Months)"
    assert res["zero_cash_date"] != ""
    assert res["milestone_runway_efficiency_score"] > 0.0


@pytest.mark.asyncio
async def test_validate_funds_compliance():
    tool = UseOfFundsCapitalAllocationTool(vault_manager=None, exec_approval_mgr=None)
    plan = {"rd_pct": 42.0, "gtm_pct": 33.0}
    covenants = {"target_rd_pct": 40.0, "target_gtm_pct": 35.0, "max_reallocation_cap_pct": 15.0}

    res = tool.validate_funds_compliance(plan, covenants)
    assert res["status"] == "SUCCESS"
    assert res["is_covenant_compliant"] is True
    assert res["covenant_breaches_count"] == 0


@pytest.mark.asyncio
async def test_export_capital_allocation_package(tmp_path):
    tool = UseOfFundsCapitalAllocationTool(vault_manager=None, exec_approval_mgr=None)
    tool.output_base_dir = tmp_path / "deliverables"

    sample_data = {
        "budget": {
            "categories": [{"name": "R&D", "budgeted": 100000.0, "actual": 105000.0}]
        },
        "financial_metrics": {
            "cash_balance": 2000000.0,
            "gross_monthly_burn": 150000.0,
            "monthly_cash_receipts": 50000.0
        },
        "plan": {"rd_pct": 40.0, "gtm_pct": 35.0},
        "covenants": {"target_rd_pct": 40.0, "target_gtm_pct": 35.0}
    }

    res = tool.export_capital_allocation_package(sample_data, company_name="FundCo")
    assert res["status"] == "SUCCESS"
    assert res["files_generated_count"] >= 5
    assert os.path.exists(res["export_directory"])

    exp_dir = Path(res["export_directory"])
    assert (exp_dir / "Use_Of_Funds_Audit_Report.json").exists()
    assert (exp_dir / "Runway_And_Burn_Model.csv").exists()
    assert (exp_dir / "Capital_Allocation_Dashboard.html").exists()
    assert (exp_dir / "Covenant_Compliance_Verification.md").exists()
    assert (exp_dir / "Capital_Allocation_Manifest.json").exists()


@pytest.mark.asyncio
async def test_suf_01_tool_manifest_discovery():
    mock_vault = AsyncMock()
    mock_vault.retrieve_secret.return_value = {}
    tm = ToolManager(vault=mock_vault)
    tools = await tm.list_tools()
    suf_tool = [t for t in tools if t.get("id") == "suf_tool_01"]
    assert len(suf_tool) > 0
    assert suf_tool[0]["name"] == "Use of Funds & Capital Allocation Tool"
