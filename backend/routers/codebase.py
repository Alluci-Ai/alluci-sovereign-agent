"""
Sovereign Codebase & Architecture REST API Router
=================================================
Exposes endpoints for local workspace tree inspection, AST symbol parsing,
git manifold state, and Vault-authenticated GitHub synchronization.
"""

from __future__ import annotations

import os
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Query, Request
from ..security.auth import verify_authenticated
from ..logging_config import get_logger
from .. import services
from ..engine.codebase_grounding import LocalCodebaseInspector, GitManifoldInspector, GitHubRepositoryInspector
from ..memory.codebase_indexer import CodebaseMemoryIndexer

from fastapi_csrf_protect import CsrfProtect

logger = get_logger("CodebaseRouter")

router = APIRouter(prefix="/codebase", tags=["Sovereign Codebase & Architecture"])


@router.get("/tree", dependencies=[Depends(verify_authenticated)])
async def get_workspace_tree(max_depth: int = Query(4, ge=1, le=8)) -> Dict[str, Any]:
    """Returns the workspace directory tree excluding build artifacts and dependencies."""
    inspector = LocalCodebaseInspector()
    return inspector.get_workspace_tree(max_depth=max_depth)


@router.get("/catalog", dependencies=[Depends(verify_authenticated)])
async def get_file_catalog(limit: int = Query(150, ge=1, le=500)) -> List[Dict[str, Any]]:
    """Returns recognized source files in the workspace with metadata."""
    inspector = LocalCodebaseInspector()
    return inspector.get_file_catalog(limit=limit)


@router.get("/symbols", dependencies=[Depends(verify_authenticated)])
async def get_ast_symbols(files: Optional[List[str]] = Query(None), max_files: int = Query(40, ge=1, le=100)) -> Dict[str, Any]:
    """Parses AST symbols (classes, functions, routes, interfaces) from workspace files."""
    inspector = LocalCodebaseInspector()
    return inspector.parse_ast_symbols(target_files=files, max_files=max_files)


@router.get("/snippet", dependencies=[Depends(verify_authenticated)])
async def read_file_snippet(path: str = Query(...), start: int = Query(1, ge=1), end: Optional[int] = Query(None, ge=1)) -> Dict[str, Any]:
    """Safely reads a slice of a source code file."""
    inspector = LocalCodebaseInspector()
    try:
        return inspector.read_file_snippet(rel_path=path, start_line=start, end_line=end)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except FileNotFoundError as fnf:
        raise HTTPException(status_code=404, detail=str(fnf))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read snippet: {str(e)}")


@router.get("/architecture", dependencies=[Depends(verify_authenticated)])
async def get_architecture_summary() -> Dict[str, Any]:
    """Returns structured architectural blueprints and core sovereign pillars."""
    inspector = LocalCodebaseInspector()
    return inspector.get_architecture_summary()


@router.get("/git", dependencies=[Depends(verify_authenticated)])
async def get_git_status() -> Dict[str, Any]:
    """Returns local git branch, uncommitted diffs, and recent commit log."""
    git_inspector = GitManifoldInspector()
    status = await git_inspector.get_git_status()
    commits = await git_inspector.get_recent_commits(limit=10)
    remotes = await git_inspector.get_remotes()
    return {
        "status": status,
        "recent_commits": commits,
        "remotes": remotes.get("remotes", {})
    }


@router.get("/github", dependencies=[Depends(verify_authenticated)])
async def get_github_overview() -> Dict[str, Any]:
    """Returns remote GitHub repository overview, pull requests, and issues (Vault-authenticated)."""
    github_inspector = GitHubRepositoryInspector(vault=services.vault)
    overview = await github_inspector.get_repo_overview()
    prs = await github_inspector.get_pull_requests(state="all", limit=5)
    issues = await github_inspector.get_issues(state="all", limit=5)
    return {
        "overview": overview,
        "pull_requests": prs,
        "issues": issues
    }


@router.post("/index", dependencies=[Depends(verify_authenticated)])
async def index_codebase(request: Request, csrf_protect: CsrfProtect = Depends()) -> Dict[str, Any]:
    """Synchronizes codebase AST symbols and architecture into H-LSM L1/L2 memory."""
    await csrf_protect.validate_csrf(request)
    if not services.hlsm_manager:
        raise HTTPException(status_code=503, detail="H-LSM memory manager not ready")
    indexer = CodebaseMemoryIndexer()
    return await indexer.sync_codebase_memory(services.hlsm_manager)
