import pytest
import os
from pathlib import Path
from backend.tools.human_resource_onboarding_tool import HumanResourceOnboardingTool
from backend.tool_manager import ToolManager
from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_audit_onboarding_pipeline():
    tool = HumanResourceOnboardingTool(vault_manager=None, exec_approval_mgr=None)
    data = {
        "employees": [
            {"name": "Jane Doe", "role": "Dev", "piia_signed": True, "tax_forms_signed": True, "it_provisioned": True, "onboarding_buddy_assigned": True},
            {"name": "John Smith", "role": "Sales", "piia_signed": False, "tax_forms_signed": True, "it_provisioned": False, "onboarding_buddy_assigned": False}
        ]
    }

    res = tool.audit_onboarding_pipeline(data)
    assert res["status"] == "SUCCESS"
    assert res["total_employees_audited"] == 2
    assert res["compliance_rate_pct"] == 50.0
    assert res["flagged_non_compliant_count"] == 1
    assert res["flagged_compliance_issues"][0]["name"] == "John Smith"


@pytest.mark.asyncio
async def test_generate_onboarding_roadmap():
    tool = HumanResourceOnboardingTool(vault_manager=None, exec_approval_mgr=None)
    emp_input = {
        "name": "Alex Taylor",
        "role": "Product Manager",
        "department": "Product",
        "buddy": "Sarah CPO"
    }

    res = tool.generate_onboarding_roadmap(emp_input)
    assert res["status"] == "SUCCESS"
    rm = res["roadmap"]
    assert rm["employee_name"] == "Alex Taylor"
    assert len(rm["day_30_milestones"]) >= 3
    assert len(rm["day_60_milestones"]) >= 3
    assert len(rm["day_90_milestones"]) >= 3


@pytest.mark.asyncio
async def test_calculate_time_to_productivity():
    tool = HumanResourceOnboardingTool(vault_manager=None, exec_approval_mgr=None)
    metrics = {
        "target_ttp_days": 30.0,
        "actual_ttp_days": 24.0,
        "compliance_score": 100.0,
        "milestone_achievement_pct": 90.0,
        "survey_satisfaction_score": 95.0
    }

    res = tool.calculate_time_to_productivity(metrics)
    assert res["status"] == "SUCCESS"
    assert res["actual_ttp_days"] == 24.0
    assert res["onboarding_efficiency_index"] > 85.0


@pytest.mark.asyncio
async def test_export_onboarding_package(tmp_path):
    tool = HumanResourceOnboardingTool(vault_manager=None, exec_approval_mgr=None)
    tool.output_base_dir = tmp_path / "deliverables"

    payload = {
        "employee_input": {"name": "Jane Doe", "role": "Dev", "department": "Engineering"},
        "pipeline_data": {"employees": [{"name": "Jane Doe", "role": "Dev", "piia_signed": True, "tax_forms_signed": True, "it_provisioned": True, "onboarding_buddy_assigned": True}]}
    }

    res = tool.export_onboarding_package(payload, company_name="OnboardCo")
    assert res["status"] == "SUCCESS"
    assert res["files_generated_count"] >= 5
    assert os.path.exists(res["export_directory"])

    exp_dir = Path(res["export_directory"])
    assert (exp_dir / "Onboarding_Roadmap_Blueprint.json").exists()
    assert (exp_dir / "Employee_Checklist_Ledger.csv").exists()
    assert (exp_dir / "Day_30_60_90_Dashboard.html").exists()
    assert (exp_dir / "Compliance_Verification_Report.md").exists()
    assert (exp_dir / "Onboarding_Manifest.json").exists()


@pytest.mark.asyncio
async def test_hro_01_tool_manifest_discovery():
    mock_vault = AsyncMock()
    mock_vault.retrieve_secret.return_value = {}
    tm = ToolManager(vault=mock_vault)
    tools = await tm.list_tools()
    hro_tool = [t for t in tools if t.get("id") == "hro_tool_01"]
    assert len(hro_tool) > 0
    assert hro_tool[0]["name"] == "Human Resource Onboarding Tool"
