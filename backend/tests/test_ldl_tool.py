import pytest
import os
from pathlib import Path
from backend.tools.legal_document_lifecycle_tool import LegalDocumentLifecycleTool
from backend.tool_manager import ToolManager
from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_audit_legal_compliance():
    tool = LegalDocumentLifecycleTool(vault_manager=None, exec_approval_mgr=None)
    sample_repository = {
        "corporate_governance": ["Certificate of Incorporation", "Bylaws", "Board Resolutions"],
        "equity_&_cap_table": ["Cap Table Ledger", "Founder Vesting Agreements"],
        "intellectual_property": ["Employee PIIA Agreements", "Contractor IP Assignments"],
        "commercial_contracts": ["Mutual NDAs", "Master Services Agreements"],
        "hr_&_team": ["Executive Offer Letters"],
        "regulatory_&_compliance": ["Privacy Policy", "SOC2 Certification"]
    }

    res = tool.audit_legal_compliance(sample_repository)
    assert res["status"] == "SUCCESS"
    assert res["compliance_index_pct"] > 50.0
    assert "Intellectual Property" in res["category_audit"]


@pytest.mark.asyncio
async def test_generate_legal_templates():
    tool = LegalDocumentLifecycleTool(vault_manager=None, exec_approval_mgr=None)
    details = {
        "company_name": "Acme Corp",
        "counterparty_name": "Tech Corp",
        "effective_date": "2026-08-08"
    }

    res = tool.generate_legal_templates("Mutual NDA", details)
    assert res["status"] == "SUCCESS"
    assert "Acme Corp" in res["draft_markdown"]
    assert "Tech Corp" in res["draft_markdown"]
    assert "NON-DISCLOSURE" in res["draft_markdown"]


@pytest.mark.asyncio
async def test_verify_signature_status():
    tool = LegalDocumentLifecycleTool(vault_manager=None, exec_approval_mgr=None)
    contracts = [
        {"title": "Mutual NDA", "status": "Executed", "signers": ["Alice", "Bob"]},
        {"title": "IP Assignment", "status": "Executed", "signers": ["Alice"]},
        {"title": "Vendor Contract", "status": "Out for Signature", "signers": ["Charlie"]}
    ]

    res = tool.verify_signature_status(contracts)
    assert res["status"] == "SUCCESS"
    assert res["total_contracts_audited"] == 3
    assert res["status_counts"]["Executed"] == 2
    assert res["status_counts"]["Out for Signature"] == 1


@pytest.mark.asyncio
async def test_export_legal_repository(tmp_path):
    tool = LegalDocumentLifecycleTool(vault_manager=None, exec_approval_mgr=None)
    tool.output_base_dir = tmp_path / "deliverables"

    sample_data = {
        "repository": {
            "corporate_governance": ["Certificate of Incorporation"],
            "intellectual_property": ["Employee PIIA Agreements"]
        },
        "contracts": [
            {"title": "Mutual NDA - Partner Co", "status": "Executed", "owner": "Legal Counsel"}
        ]
    }

    res = tool.export_legal_repository(sample_data, company_name="LegalCo")
    assert res["status"] == "SUCCESS"
    assert res["files_generated_count"] >= 5
    assert os.path.exists(res["export_directory"])

    exp_dir = Path(res["export_directory"])
    assert (exp_dir / "Legal_Audit_Report.json").exists()
    assert (exp_dir / "Contract_Register.csv").exists()
    assert (exp_dir / "IP_And_Cap_Table_Summary.md").exists()
    assert (exp_dir / "Corporate_Governance_Log.json").exists()
    assert (exp_dir / "Legal_Repository_Manifest.json").exists()


@pytest.mark.asyncio
async def test_ldl_01_tool_manifest_discovery():
    mock_vault = AsyncMock()
    mock_vault.retrieve_secret.return_value = {}
    tm = ToolManager(vault=mock_vault)
    tools = await tm.list_tools()
    ldl_tool = [t for t in tools if t.get("id") == "ldl_tool_01"]
    assert len(ldl_tool) > 0
    assert ldl_tool[0]["name"] == "Legal Document Lifecycle Orchestrator Tool"
