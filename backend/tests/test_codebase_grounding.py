import pytest
pytestmark = pytest.mark.unit

import os
from unittest.mock import AsyncMock, patch, MagicMock
from backend.engine.codebase_grounding import LocalCodebaseInspector, GitManifoldInspector, GitHubRepositoryInspector


def test_local_codebase_tree():
    inspector = LocalCodebaseInspector()
    tree = inspector.get_workspace_tree(max_depth=2, max_files=50)
    assert isinstance(tree, dict)
    assert tree["type"] == "directory"
    assert "children" in tree
    assert len(tree["children"]) > 0


def test_local_codebase_file_catalog():
    inspector = LocalCodebaseInspector()
    catalog = inspector.get_file_catalog(limit=25)
    assert isinstance(catalog, list)
    assert len(catalog) > 0
    assert "path" in catalog[0]
    assert "language" in catalog[0]
    assert "lines_count" in catalog[0]


def test_local_codebase_parse_ast_symbols():
    inspector = LocalCodebaseInspector()
    symbols = inspector.parse_ast_symbols(target_files=["backend/models.py"], max_files=5)
    assert isinstance(symbols, dict)
    assert "files" in symbols
    assert "backend/models.py" in symbols["files"]
    classes = symbols["files"]["backend/models.py"]["classes"]
    class_names = [c["name"] for c in classes]
    assert "HLSMEpisodicEntry" in class_names


def test_read_file_snippet():
    inspector = LocalCodebaseInspector()
    snippet = inspector.read_file_snippet("ARCHITECTURE.md", start_line=1, end_line=10)
    assert snippet["path"] == "ARCHITECTURE.md"
    assert snippet["start_line"] == 1
    assert snippet["end_line"] == 10
    assert "Alluci Sovereign Agent Architecture" in snippet["content"]


def test_read_file_snippet_path_traversal_blocked():
    inspector = LocalCodebaseInspector()
    with pytest.raises(ValueError):
        inspector.read_file_snippet("../../etc/passwd")


def test_get_architecture_summary():
    inspector = LocalCodebaseInspector()
    arch = inspector.get_architecture_summary()
    assert "title" in arch
    assert len(arch["pillars"]) == 5
    assert "domains" in arch
    assert len(arch["domains"]) == 6


def test_get_system_capabilities():
    inspector = LocalCodebaseInspector()
    caps = inspector.get_system_capabilities()
    assert isinstance(caps, dict)
    assert len(caps) == 6
    assert "core_compute_and_inference" in caps
    assert "topological_and_mathematical_physics" in caps
    assert "autonomous_subagent_constellation" in caps
    assert "memory_and_knowledge_fabric" in caps
    assert "zero_trust_security_and_identity" in caps
    assert "omnichannel_bridges_and_ui" in caps
    for domain in caps.values():
        assert "name" in domain
        assert "description" in domain
        assert "modules" in domain


@pytest.mark.asyncio
async def test_git_manifold_inspector():
    git_inspector = GitManifoldInspector()
    status = await git_inspector.get_git_status()
    assert isinstance(status, dict)
    assert "is_git_repo" in status
    assert status["is_git_repo"] is True
    assert "branch" in status

    commits = await git_inspector.get_recent_commits(limit=3)
    assert isinstance(commits, list)
    if len(commits) > 0:
        assert "commit_hash" in commits[0]
        assert "message" in commits[0]

    remotes = await git_inspector.get_remotes()
    assert isinstance(remotes, dict)
    assert "remotes" in remotes


@pytest.mark.asyncio
async def test_github_repository_inspector():
    mock_vault = MagicMock()
    mock_vault.retrieve_secret = AsyncMock(return_value={"token": "test_token", "repository": "Alluci-Ai/alluci-sovereign-agent"})
    inspector = GitHubRepositoryInspector(vault=mock_vault)

    with patch("httpx.AsyncClient.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "full_name": "Alluci-Ai/alluci-sovereign-agent",
            "description": "Enterprise Sovereign Agent",
            "default_branch": "main",
            "stargazers_count": 42,
            "forks_count": 7,
            "open_issues_count": 0,
            "visibility": "private",
            "updated_at": "2026-08-29T12:00:00Z"
        }
        mock_get.return_value = mock_resp

        overview = await inspector.get_repo_overview()
        assert overview["status"] == "connected"
        assert overview["repository"] == "Alluci-Ai/alluci-sovereign-agent"
        assert overview["stars"] == 42
