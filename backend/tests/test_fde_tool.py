import pytest
import os
from pathlib import Path
from backend.tools.founder_education_decision_tool import FounderEducationDecisionTool
from backend.tool_manager import ToolManager
from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_synthesize_learning_modules():
    tool = FounderEducationDecisionTool(vault_manager=None, exec_approval_mgr=None)
    topic = {"domain": "Capital Allocation & Burn Rate", "stage": "Series A"}

    res = tool.synthesize_learning_modules(topic)
    assert res["status"] == "SUCCESS"
    assert res["domain"] == "Capital Allocation & Burn Rate"
    assert len(res["module"]["mental_models"]) >= 4


@pytest.mark.asyncio
async def test_evaluate_decision_confidence():
    tool = FounderEducationDecisionTool(vault_manager=None, exec_approval_mgr=None)
    scenario = {
        "evidence_score": 90.0,
        "alignment_score": 85.0,
        "risk_mitigation_score": 80.0,
        "scenario_agreement_score": 80.0
    }

    res = tool.evaluate_decision_confidence(scenario)
    assert res["status"] == "SUCCESS"
    assert res["decision_confidence_score"] >= 80.0
    assert res["confidence_level"].startswith("High Confidence")


@pytest.mark.asyncio
async def test_log_decision_journal_entry():
    tool = FounderEducationDecisionTool(vault_manager=None, exec_approval_mgr=None)
    journal_data = {
        "decision_title": "Launch AI Agent Service",
        "rationale": "High customer demand and positive ROI model",
        "alternatives_considered": ["Hire 10 Consultants", "Do Nothing"],
        "expected_outcome": "$500k ARR in 2 quarters",
        "review_after_days": 90
    }

    res = tool.log_decision_journal_entry(journal_data)
    assert res["status"] == "SUCCESS"
    entry = res["journal_entry"]
    assert entry["decision_title"] == "Launch AI Agent Service"
    assert entry["entry_id"].startswith("DEC_")
    assert entry["review_date"] != ""


@pytest.mark.asyncio
async def test_export_education_package(tmp_path):
    tool = FounderEducationDecisionTool(vault_manager=None, exec_approval_mgr=None)
    tool.output_base_dir = tmp_path / "deliverables"

    payload = {
        "topic_scope": {"domain": "Strategy Execution", "stage": "Seed"},
        "confidence_data": {"evidence_score": 85.0},
        "journal_data": {"decision_title": "Seed Round Hiring Plan"}
    }

    res = tool.export_education_package(payload, company_name="EduCo")
    assert res["status"] == "SUCCESS"
    assert res["files_generated_count"] >= 5
    assert os.path.exists(res["export_directory"])

    exp_dir = Path(res["export_directory"])
    assert (exp_dir / "Founder_Executive_Curriculum.json").exists()
    assert (exp_dir / "Decision_Journal_Ledger.csv").exists()
    assert (exp_dir / "Mental_Models_Dashboard.html").exists()
    assert (exp_dir / "Decision_Confidence_Report.md").exists()
    assert (exp_dir / "Education_Manifest.json").exists()


@pytest.mark.asyncio
async def test_fde_01_tool_manifest_discovery():
    mock_vault = AsyncMock()
    mock_vault.retrieve_secret.return_value = {}
    tm = ToolManager(vault=mock_vault)
    tools = await tm.list_tools()
    fde_tool = [t for t in tools if t.get("id") == "fde_tool_01"]
    assert len(fde_tool) > 0
    assert fde_tool[0]["name"] == "Founder Education & Decision Intelligence Tool"
