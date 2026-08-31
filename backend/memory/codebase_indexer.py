"""
H-LSM Codebase & Architecture Memory Indexer
============================================
Ingests codebase AST symbols, architecture guides, and git manifolds into
H-LSM L1 Episodic and L2 Semantic memory tiers.
"""

from __future__ import annotations

import time
import json
from typing import Dict, List, Any, Optional
from sqlmodel import Session, select, col

from ..logging_config import get_logger
from ..models import HLSMEpisodicEntry
from ..engine.codebase_grounding import LocalCodebaseInspector, GitManifoldInspector

logger = get_logger("CodebaseIndexer")


class CodebaseMemoryIndexer:
    """
    Ingests authoritative codebase structure and architecture documents into H-LSM memory.
    Ensures that topological memory recall grounds LLM generations in real codebase truth.
    """

    def __init__(self, project_root: Optional[str] = None):
        self.inspector = LocalCodebaseInspector(project_root)
        self.git_inspector = GitManifoldInspector(project_root)

    async def sync_codebase_memory(self, hlsm_manager: Any) -> Dict[str, Any]:
        """
        Synchronizes codebase architecture blueprints, FastAPI routes, SQLModel schemas,
        and git manifold state into H-LSM L1/L2 memory.
        """
        if not hlsm_manager:
            return {"status": "skipped", "reason": "H-LSM manager not initialized"}

        indexed_count = 0
        now = time.time()

        try:
            # 1. Ingest Architecture Pillars & Guides
            arch_summary = self.inspector.get_architecture_summary()
            arch_content = (
                f"[CODEBASE ARCHITECTURE BLUEPRINT]\n"
                f"Title: {arch_summary['title']}\n"
                f"Pillars:\n" + "\n".join(f"- {p}" for p in arch_summary["pillars"]) + "\n"
                f"Hardware Profiling: {arch_summary['hardware_profiling']}\n"
            )

            entry_id = await hlsm_manager.l1_store(
                content=arch_content,
                source="codebase_architecture",
                session_key="system_architecture",
                objective="System Architecture Grounding",
                psi=0.0,
                valence=1.0,
                topological_importance=2.5,
                extra_metadata={"type": "architecture_blueprint", "domain": "architecture"}
            )
            indexed_count += 1

            # 2. Ingest AST Symbols (Routers, Schemas, Core Services)
            ast_data = self.inspector.parse_ast_symbols(max_files=35)
            for rel_path, f_symbols in ast_data.get("files", {}).items():
                classes = f_symbols.get("classes", [])
                routes = f_symbols.get("routes", [])

                if not classes and not routes:
                    continue

                symbol_parts = [f"[CODEBASE AST SYMBOL: {rel_path}]"]
                if classes:
                    symbol_parts.append("Classes:")
                    for c in classes:
                        methods_str = ", ".join(m["name"] for m in c.get("methods", [])[:6])
                        doc = f" - {c['docstring']}" if c.get("docstring") else ""
                        symbol_parts.append(f"  - class {c['name']}({', '.join(c.get('bases', []))}): methods=[{methods_str}]{doc}")

                if routes:
                    symbol_parts.append("API Routes:")
                    for r in routes:
                        symbol_parts.append(f"  - {r['http_method']} {r['path']} -> {r['endpoint']}() [line {r['line']}]")

                content_block = "\n".join(symbol_parts)
                await hlsm_manager.l1_store(
                    content=content_block,
                    source="codebase_symbol",
                    session_key="system_codebase",
                    objective=f"Symbol Index: {rel_path}",
                    psi=0.0,
                    valence=0.8,
                    topological_importance=1.8,
                    extra_metadata={"file": rel_path, "type": "ast_symbol", "domain": "codebase"}
                )
                indexed_count += 1

            # 3. Ingest Installed Skills (core_skills/*.json)
            skills = self.inspector.get_installed_skills_inventory()
            for s in skills:
                skill_content = (
                    f"[AUTHENTIC SKILL MANIFEST: {s['name']}]\n"
                    f"Identifier: {s['id']}\n"
                    f"Path: {s['path']}\n"
                    f"Description: {s['description']}\n"
                )
                await hlsm_manager.l1_store(
                    content=skill_content,
                    source="skill_manifest",
                    session_key="system_skills",
                    objective=f"Skill Manifest: {s['id']}",
                    psi=0.0,
                    valence=1.0,
                    topological_importance=2.2,
                    extra_metadata={"skill_id": s["id"], "type": "skill_manifest", "domain": "skills"}
                )
                indexed_count += 1

            # 4. Ingest Installed Tools (backend/tools/*.py)
            tools = self.inspector.get_installed_tools_inventory()
            for t in tools:
                tool_content = (
                    f"[AUTHENTIC TOOL MANIFEST: {t['name']}]\n"
                    f"Identifier: {t['id']}\n"
                    f"Path: {t['path']}\n"
                    f"Description: {t['description']}\n"
                )
                await hlsm_manager.l1_store(
                    content=tool_content,
                    source="tool_manifest",
                    session_key="system_tools",
                    objective=f"Tool Manifest: {t['id']}",
                    psi=0.0,
                    valence=1.0,
                    topological_importance=2.2,
                    extra_metadata={"tool_id": t["id"], "type": "tool_manifest", "domain": "tools"}
                )
                indexed_count += 1

            # 5. Ingest Local Git Manifold State
            git_status = await self.git_inspector.get_git_status()
            recent_commits = await self.git_inspector.get_recent_commits(limit=5)

            commit_summaries = []
            for c in recent_commits:
                commit_summaries.append(f"- {c['short_hash']} by {c['author']} ({c['date'][:10]}): {c['message']}")

            git_content = (
                f"[GIT MANIFOLD CONTEXT]\n"
                f"Active Branch: {git_status.get('branch', 'unknown')}\n"
                f"Working Tree Clean: {git_status.get('is_clean', True)}\n"
                f"Recent Commits:\n" + ("\n".join(commit_summaries) if commit_summaries else "- None recorded")
            )

            await hlsm_manager.l1_store(
                content=git_content,
                source="git_manifold",
                session_key="system_git",
                objective="Git Manifold State",
                psi=0.0,
                valence=0.7,
                topological_importance=1.5,
                extra_metadata={"type": "git_manifold", "domain": "git"}
            )
            indexed_count += 1

            logger.info(f"[CodebaseIndexer] Successfully synchronized {indexed_count} codebase, skill, tool & architecture memory blocks into H-LSM.")
            return {
                "status": "success",
                "indexed_entries": indexed_count,
                "timestamp": datetime_iso(now)
            }

        except Exception as e:
            logger.error(f"[CodebaseIndexer] Codebase memory sync failed: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}


def datetime_iso(ts: float) -> str:
    from datetime import datetime, timezone
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
