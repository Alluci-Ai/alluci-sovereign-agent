import pytest
import os
from pathlib import Path
from backend.tools.organizational_knowledge_document_tool import OrganizationalKnowledgeDocumentTool
from backend.tool_manager import ToolManager
from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_audit_knowledge_repository():
    tool = OrganizationalKnowledgeDocumentTool(vault_manager=None, exec_approval_mgr=None)
    data = {
        "layers": [
            {"layer": "Strategic Memory", "document_count": 10, "has_owner": True, "indexed": True, "stale_count": 0},
            {"layer": "Legal Memory", "document_count": 5, "has_owner": True, "indexed": True, "stale_count": 0}
        ]
    }

    res = tool.audit_knowledge_repository(data)
    assert res["status"] == "SUCCESS"
    assert res["total_documents_audited"] == 15
    assert res["stale_documents_count"] == 0
    assert res["knowledge_health_index"] == 100.0


@pytest.mark.asyncio
async def test_index_document_metadata():
    tool = OrganizationalKnowledgeDocumentTool(vault_manager=None, exec_approval_mgr=None)
    doc_input = {
        "category": "LEGAL",
        "doc_type": "PIIA",
        "owner": "John Doe",
        "version": "1.0",
        "extension": "pdf",
        "confidentiality": "Strictly Confidential"
    }

    res = tool.index_document_metadata(doc_input)
    assert res["status"] == "SUCCESS"
    meta = res["metadata"]
    assert meta["standardized_filename"].startswith("LEGAL_PIIA_JohnDoe_")
    assert meta["standardized_filename"].endswith("_v1.0.pdf")
    assert meta["confidentiality_level"] == "Strictly Confidential"


@pytest.mark.asyncio
async def test_query_organizational_memory():
    tool = OrganizationalKnowledgeDocumentTool(vault_manager=None, exec_approval_mgr=None)

    res = tool.query_organizational_memory("capital runway burn rate")
    assert res["status"] == "SUCCESS"
    assert res["results_count"] > 0
    assert "Financial & Capital Memory" in [node["layer"] for node in res["matching_nodes"]]


@pytest.mark.asyncio
async def test_export_knowledge_package(tmp_path):
    tool = OrganizationalKnowledgeDocumentTool(vault_manager=None, exec_approval_mgr=None)
    tool.output_base_dir = tmp_path / "deliverables"

    payload = {
        "audit_data": {
            "layers": [
                {"layer": "Strategic Memory", "document_count": 5, "stale_count": 0}
            ]
        },
        "documents": [
            {"category": "STRATEGY", "doc_type": "OperatingPlan", "owner": "CEO", "version": "1.0"}
        ]
    }

    res = tool.export_knowledge_package(payload, company_name="KnowledgeCo")
    assert res["status"] == "SUCCESS"
    assert res["files_generated_count"] >= 5
    assert os.path.exists(res["export_directory"])

    exp_dir = Path(res["export_directory"])
    assert (exp_dir / "Knowledge_Graph_Index.json").exists()
    assert (exp_dir / "Document_Taxonomy_Registry.csv").exists()
    assert (exp_dir / "Organizational_Memory_Architecture.md").exists()
    assert (exp_dir / "Metadata_Verification_Report.json").exists()
    assert (exp_dir / "Knowledge_Management_Manifest.json").exists()


@pytest.mark.asyncio
async def test_okd_01_tool_manifest_discovery():
    mock_vault = AsyncMock()
    mock_vault.retrieve_secret.return_value = {}
    tm = ToolManager(vault=mock_vault)
    tools = await tm.list_tools()
    okd_tool = [t for t in tools if t.get("id") == "okd_tool_01"]
    assert len(okd_tool) > 0
    assert okd_tool[0]["name"] == "Organizational Knowledge & Document Management Tool"
