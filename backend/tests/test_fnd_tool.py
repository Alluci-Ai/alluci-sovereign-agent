import pytest
import os
import shutil
from pathlib import Path
from backend.tools.founder_narrative_tool import FounderNarrativeTool
from backend.tool_manager import ToolManager


@pytest.mark.asyncio
async def test_founder_narrative_tool_deliverable_export(tmp_path):
    tool = FounderNarrativeTool(vault_manager=None, exec_approval_mgr=None)
    tool.output_base_dir = tmp_path / "deliverables"

    sample_narrative = {
        "founder_story": "Founded after experiencing enterprise data bottlenecks firsthand.",
        "why_now": "Convergence of AI agent architectures and real-time streaming data.",
        "problem": "Legacy narrative tools are fragmented and disconnected from core execution.",
        "solution": "Alluci Sovereign Agent operating narrative engine.",
        "market_thesis": "Category creation for AI strategic intelligence.",
        "vision": "Autonomous strategic operating narratives for all enterprises.",
        "category": "Strategic Operating Narratives"
    }

    result = tool.export_deliverables(sample_narrative, company_name="TestCo")
    assert result["status"] == "SUCCESS"
    assert result["files_generated_count"] >= 6
    assert os.path.exists(result["export_directory"])

    # Check key deliverable files exist
    exp_dir = Path(result["export_directory"])
    assert (exp_dir / "Investor_Pitch_Deck_Spec.json").exists()
    assert (exp_dir / "Executive_Summary.md").exists()
    assert (exp_dir / "Founder_Discovery_Report.json").exists()
    assert (exp_dir / "Website_Messaging.html").exists()
    assert (exp_dir / "Investor_One_Pager.md").exists()
    assert (exp_dir / "Data_Room_Investor_FAQ.md").exists()


@pytest.mark.asyncio
async def test_evidence_auditor():
    tool = FounderNarrativeTool(vault_manager=None, exec_approval_mgr=None)
    sample_claims = [
        {"statement": "Product has patent protection", "evidence_type": "patent", "proof": "US Patent 12345"},
        {"statement": "ARR grew 300% YoY", "evidence_type": "revenue", "proof": "Stripe metrics"},
        {"statement": "Gartner market report supports timing", "evidence_type": "industry_report", "proof": "2026 AI Report"},
        {"statement": "5 customer pilots completed", "evidence_type": "customer_interview", "proof": "Pilot notes"},
        {"statement": "Market will shift radically", "evidence_type": "founder_belief", "proof": "Founder intuition"}
    ]

    res = tool.audit_evidence(sample_claims)
    assert res["status"] == "SUCCESS"
    assert res["total_claims_audited"] == 5
    assert res["level_counts"][5] == 1
    assert res["level_counts"][4] == 1
    assert res["level_counts"][3] == 1
    assert res["level_counts"][2] == 1
    assert res["level_counts"][1] == 1
    assert res["overall_evidence_confidence_score"] > 0.6


@pytest.mark.asyncio
async def test_transcript_parsing(tmp_path):
    tool = FounderNarrativeTool(vault_manager=None, exec_approval_mgr=None)
    transcript_file = tmp_path / "interview_transcript.txt"
    transcript_file.write_text("Interviewer: Tell us about the origin. Founder: We realized traditional workflows break.")

    res = await tool.transcribe_interview(str(transcript_file))
    assert res["status"] == "SUCCESS"
    assert res["source"] == "text_file"
    assert res["word_count"] > 5


@pytest.mark.asyncio
async def test_tool_manifest_discovery():
    from unittest.mock import AsyncMock
    mock_vault = AsyncMock()
    mock_vault.retrieve_secret.return_value = {}
    tm = ToolManager(vault=mock_vault)
    tools = await tm.list_tools()
    fnd_tool = [t for t in tools if t.get("id") == "fnd_tool_01"]
    assert len(fnd_tool) > 0
    assert fnd_tool[0]["name"] == "Founder Narrative Orchestrator Tool"
