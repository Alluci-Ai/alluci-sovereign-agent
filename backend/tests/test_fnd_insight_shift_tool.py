import pytest
import os
from pathlib import Path
from backend.tools.founder_insight_market_shift_tool import FounderInsightMarketShiftTool
from backend.tool_manager import ToolManager
from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_extract_market_shifts():
    tool = FounderInsightMarketShiftTool(vault_manager=None, exec_approval_mgr=None)
    sample_inputs = [
        {"title": "Agentic AI Infrastructure Surge", "vector": "technology", "permanence": "structural", "impact_summary": "High demand for autonomous local execution"},
        {"title": "Data Sovereignty Regulation", "vector": "regulatory", "permanence": "structural", "impact_summary": "Mandatory local compute for sensitive data"},
        {"title": "Temporary Hype Cycle", "vector": "market", "permanence": "trend", "impact_summary": "Short-term consumer interest"}
    ]

    res = tool.extract_market_shifts(sample_inputs)
    assert res["status"] == "SUCCESS"
    assert res["total_forces_analyzed"] == 3
    assert res["structural_shifts_count"] == 2
    assert res["temporary_trends_count"] == 1


@pytest.mark.asyncio
async def test_score_decision_confidence():
    tool = FounderInsightMarketShiftTool(vault_manager=None, exec_approval_mgr=None)
    claims = [
        {"claim": "Patented topology engine", "level": 5},
        {"claim": "ARR grew 250%", "level": 4},
        {"claim": "Gartner market report", "level": 4},
        {"claim": "Customer survey", "level": 3}
    ]

    res = tool.score_decision_confidence("Focus on sovereign enterprise AI positioning", claims)
    assert res["status"] == "SUCCESS"
    assert res["confidence_level"] in ["Very High Confidence", "High Confidence"]
    assert res["confidence_score"] >= 0.8


@pytest.mark.asyncio
async def test_evaluate_signals_and_risks():
    tool = FounderInsightMarketShiftTool(vault_manager=None, exec_approval_mgr=None)
    signals = [
        {"type": "market", "description": "Competitor launched cloud-only model", "severity": "medium"},
        {"type": "regulatory", "description": "Strict on-prem data requirements passed", "severity": "high"}
    ]

    res = tool.evaluate_signals_and_risks({}, signals)
    assert res["status"] == "SUCCESS"
    assert res["signals_monitored_count"] == 2
    assert res["high_severity_risks_count"] == 1


@pytest.mark.asyncio
async def test_export_insight_assets(tmp_path):
    tool = FounderInsightMarketShiftTool(vault_manager=None, exec_approval_mgr=None)
    tool.output_base_dir = tmp_path / "deliverables"

    sample_insight_payload = {
        "earned_insight": "Founders require persistent, self-healing strategic operating narratives.",
        "market_thesis": "Sovereign local AI agents outperform cloud API wrappers on privacy and latency.",
        "category_definition": "Autonomous Strategic Intelligence Systems",
        "why_now": "Local hardware (M-series / Metal) is now fast enough for local multi-agent loops.",
        "confidence_level": "High Confidence",
        "confidence_score": 0.88
    }

    res = tool.export_insight_assets(sample_insight_payload, company_name="InsightCo")
    assert res["status"] == "SUCCESS"
    assert res["files_generated_count"] >= 6
    assert os.path.exists(res["export_directory"])

    exp_dir = Path(res["export_directory"])
    assert (exp_dir / "Strategic_Intelligence_Package.json").exists()
    assert (exp_dir / "Opportunity_Architecture.md").exists()
    assert (exp_dir / "Category_Thesis.md").exists()
    assert (exp_dir / "Market_Shift_Analysis.json").exists()
    assert (exp_dir / "Signals_And_Risks_Report.md").exists()
    assert (exp_dir / "Decision_Confidence_Matrix.json").exists()


@pytest.mark.asyncio
async def test_fnd_02_tool_manifest_discovery():
    mock_vault = AsyncMock()
    mock_vault.retrieve_secret.return_value = {}
    tm = ToolManager(vault=mock_vault)
    tools = await tm.list_tools()
    fnd_tool_02 = [t for t in tools if t.get("id") == "fnd_tool_02"]
    assert len(fnd_tool_02) > 0
    assert fnd_tool_02[0]["name"] == "Founder Insight & Market Shift Tool"
