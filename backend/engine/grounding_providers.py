"""
Modular Grounding Providers & Reference Context Orchestrator
============================================================
Replaces monolithic context dumping with single-responsibility, orthogonal grounding providers.
Ensures the Alluci Sovereign Agent receives strictly scoped reference context relevant to the user prompt intent.
"""

from __future__ import annotations

import os
import re
import ast
import glob
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple

from ..logging_config import get_logger
from .intent_decomposer import IntentDecomposer, IntentType, ParsedGoalTuple
from .codebase_grounding import LocalCodebaseInspector, GitManifoldInspector

logger = get_logger("Engine.GroundingProviders")


class GroundingResult:
    """Encapsulates output from a grounding provider with an optional specialized directive."""
    def __init__(self, content: str, specialized_directive: Optional[str] = None):
        self.content = content.strip()
        self.specialized_directive = specialized_directive


class BaseGroundingProvider(ABC):
    """Abstract base class for modular grounding providers."""

    @abstractmethod
    async def can_handle(self, prompt: str, parsed_intent: ParsedGoalTuple) -> bool:
        """Determines whether this provider is relevant to the user's prompt and intent."""
        pass

    @abstractmethod
    async def provide_grounding(self, prompt: str, parsed_intent: ParsedGoalTuple) -> Optional[GroundingResult]:
        """Extracts and formats grounded context for LLM reference."""
        pass


class SkillsAndToolsManifestProvider(BaseGroundingProvider):
    """
    Grounds inquiries regarding Skills, Tools, Frameworks, and Capabilities directly from disk.
    Strictly isolated: does NOT pollute context with broader architectural essays or physics equations.
    """

    def __init__(self, inspector: Optional[LocalCodebaseInspector] = None):
        self.inspector = inspector or LocalCodebaseInspector()

    async def can_handle(self, prompt: str, parsed_intent: ParsedGoalTuple) -> bool:
        body_lower = prompt.lower()
        triggers = [
            "skill", "skills", "tool", "tools", "framework", "frameworks",
            "what can you do", "what are your capabilities", "list your capabilities",
            "available capabilities", "manifest", "manifests", "installed capabilities"
        ]
        return any(re.search(rf"\b{re.escape(t)}\b", body_lower) for t in triggers)

    async def provide_grounding(self, prompt: str, parsed_intent: ParsedGoalTuple) -> Optional[GroundingResult]:
        skills = self.inspector.get_installed_skills_inventory()
        tools = self.inspector.get_installed_tools_inventory()

        lines = [
            f"[AUTHENTIC DISK MANIFEST: {len(skills)} SPECIALIZED SKILLS & FRAMEWORKS]",
            "The following skills and frameworks are installed with complete operational workflows in `core_skills/`:"
        ]
        for s in skills:
            lines.append(f"- **{s['name']}** (`{s['id']}`): {s['description']} [Path: `{s['path']}`]")

        lines.append(f"\n[AUTHENTIC DISK MANIFEST: {len(tools)} CAPABILITY TOOLS]")
        lines.append("The following tools are implemented in `backend/tools/`:")
        for t in tools:
            lines.append(f"- **{t['name']}** (`{t['id']}`): {t['description']} [Path: `{t['path']}`]")

        content = "\n".join(lines)
        directive = (
            f"INSTRUCTION: The user is asking to list, explain, or inspect your installed Skills and Tools. "
            f"Directly enumerate and explain all {len(skills)} skills and all {len(tools)} capability tools provided in the Authentic Disk Manifests above. "
            f"Provide a complete, comprehensive inventory covering each installed item in full. Do not omit any items or summarize as a partial selection. "
            f"Do not drift into unrelated architectural or mathematical essays."
        )
        return GroundingResult(content=content, specialized_directive=directive)


class ArchitectureGroundingProvider(BaseGroundingProvider):
    """
    Grounds inquiries specifically asking about System Architecture, 6 Functional Domains,
    Topological Physics, MLX compute engine, AVL Gate, DPK, and memory layers.
    """

    def __init__(self, inspector: Optional[LocalCodebaseInspector] = None):
        self.inspector = inspector or LocalCodebaseInspector()
        self.project_root = self.inspector.project_root
        self.subsystem_map = {
            "dpk": "backend/security/dpk.py",
            "discrete projection kernel": "backend/security/dpk.py",
            "ppn": "backend/security/dpk.py",
            "polytope projection network": "backend/security/dpk.py",
            "pmet": "backend/topology/pmet_filtration.py",
            "vietoris-rips": "backend/topology/pmet_filtration.py",
            "j-space": "backend/topology/j_space_simulator.py",
            "barcode_clock": "backend/topology/barcode_clock.py",
            "barcode clock": "backend/topology/barcode_clock.py",
            "markov_trace": "backend/topology/markov_trace.py",
            "spe": "backend/tools/strategic_planning_execution_tool.py",
            "swd": "backend/tools/strategic_workforce_design_tool.py",
            "suf": "backend/tools/use_of_funds_tool.py",
            "ownership": "backend/tools/ownership_capital_strategy_tool.py",
            "cap table": "backend/tools/ownership_capital_strategy_tool.py",
            "founding team": "backend/tools/founding_team_leadership_tool.py",
            "signal": "backend/bridges/signal_cli.py",
            "bridge": "backend/bridges/manager.py",
            "vault": "backend/security/vault.py",
            "hlsm": "backend/memory/hlsm_manager.py",
            "kuzudb": "backend/memory/hlsm_manager.py",
            "ace": "backend/ace/engine.py",
            "avl": "backend/security/avl_gate.py"
        }

    async def can_handle(self, prompt: str, parsed_intent: ParsedGoalTuple) -> bool:
        body_lower = prompt.lower()
        # Avoid firing on pure skill/tool inventory questions unless architecture is explicitly asked
        arch_keywords = [
            "architecture", "architectural", "how are you built", "system design",
            "6 domains", "functional domains", "topological physics", "mlx engine",
            "lce", "avl gate", "discrete projection kernel", "pmet filtration",
            "vietoris-rips", "stella octangula", "barcode clock", "markov trace"
        ]
        return any(k in body_lower for k in arch_keywords)

    async def provide_grounding(self, prompt: str, parsed_intent: ParsedGoalTuple) -> Optional[GroundingResult]:
        body_lower = prompt.lower()
        parts = []

        # 1. Architecture Summary & Capabilities
        arch = self.inspector.get_architecture_summary()
        capabilities = self.inspector.get_system_capabilities()
        cap_summary = [f"- {v['name']}: {v['description']}" for v in capabilities.values()]
        parts.append(
            f"[AUTHENTIC SYSTEM ARCHITECTURE & 6-DOMAIN CAPABILITIES]\n"
            f"Title: {arch.get('title', 'Alluci Sovereign Agent Architecture Blueprint')}\n"
            f"Functional Domains:\n" + "\n".join(cap_summary)
        )

        # 2. Specific Subsystem Excerpts
        matched_subsystems = set()
        for trig, sub_path in self.subsystem_map.items():
            pattern = rf"\b{re.escape(trig)}\b"
            if re.search(pattern, body_lower) and sub_path not in matched_subsystems:
                matched_subsystems.add(sub_path)
                full_sub_path = os.path.join(self.project_root, sub_path)
                if os.path.exists(full_sub_path):
                    try:
                        with open(full_sub_path, "r", encoding="utf-8", errors="ignore") as sf:
                            sub_text = sf.read()
                        sub_excerpt = sub_text[:4000]
                        parts.append(
                            f"\n[INTROSPECTIVE SUBSYSTEM GROUNDING: `{sub_path}`]:\n"
                            f"```\n{sub_excerpt.strip()}\n```"
                        )
                    except Exception as sub_err:
                        logger.debug(f"[ArchitectureGrounding] Error reading subsystem {sub_path}: {sub_err}")
                if len(matched_subsystems) >= 2:
                    break

        directive = "INSTRUCTION: Explain the system architecture accurately and comprehensively based strictly on the verified architectural blueprints and subsystem sources above."
        return GroundingResult(content="\n\n".join(parts), specialized_directive=directive)


class TargetFileGroundingProvider(BaseGroundingProvider):
    """
    Grounds specific requests to read, review, or inspect source/documentation files on disk.
    """

    def __init__(self, inspector: Optional[LocalCodebaseInspector] = None):
        self.inspector = inspector or LocalCodebaseInspector()
        self.project_root = self.inspector.project_root

    async def can_handle(self, prompt: str, parsed_intent: ParsedGoalTuple) -> bool:
        body_lower = prompt.lower()
        file_pattern = r'([A-Za-z0-9_\-\.\/]+\.(?:md|py|ts|tsx|js|jsx|json|yaml|yml|sh|html|css|txt|sql|toml|ini|env|example|lock))\b'
        file_matches = re.findall(file_pattern, prompt, re.IGNORECASE)
        has_named_doc = any(k in body_lower for k in ["readme", "architecture.md", "package.json", "makefile"])
        return bool(file_matches) or has_named_doc

    async def provide_grounding(self, prompt: str, parsed_intent: ParsedGoalTuple) -> Optional[GroundingResult]:
        body_lower = prompt.lower()
        file_pattern = r'([A-Za-z0-9_\-\.\/]+\.(?:md|py|ts|tsx|js|jsx|json|yaml|yml|sh|html|css|txt|sql|toml|ini|env|example|lock))\b'
        file_matches = re.findall(file_pattern, prompt, re.IGNORECASE)
        target_files = list(file_matches)

        if "readme" in body_lower and not any("readme" in m.lower() for m in target_files):
            target_files.append("README.md")
        if "architecture.md" in body_lower and not any("architecture.md" in m.lower() for m in target_files):
            target_files.append("ARCHITECTURE.md")
        if "package.json" in body_lower and not any("package.json" in m.lower() for m in target_files):
            target_files.append("package.json")
        if "makefile" in body_lower and not any("makefile" in m.lower() for m in target_files):
            target_files.append("Makefile")

        parts = []
        for requested_file in target_files[:3]:
            clean_name = requested_file.strip("`'\" \t\n,;:")
            if not clean_name:
                continue

            resolved_path = None
            direct_check = os.path.abspath(os.path.join(self.project_root, clean_name))
            if os.path.exists(direct_check) and os.path.isfile(direct_check) and direct_check.startswith(self.project_root):
                resolved_path = direct_check
            else:
                target_base = os.path.basename(clean_name).lower()
                for root, dirs, files in os.walk(self.project_root):
                    dirs[:] = [d for d in dirs if d not in {".git", "node_modules", ".venv", "venv", "__pycache__", ".pytest_cache", "dist", "build", ".next", ".cache"}]
                    for f in files:
                        if f.lower() == target_base:
                            candidate = os.path.join(root, f)
                            if clean_name.lower() in candidate.lower():
                                resolved_path = candidate
                                break
                            if not resolved_path:
                                resolved_path = candidate
                    if resolved_path:
                        break

            if resolved_path and os.path.exists(resolved_path):
                try:
                    rel_path = os.path.relpath(resolved_path, self.project_root)
                    ext = os.path.splitext(resolved_path)[1].lower()
                    with open(resolved_path, "r", encoding="utf-8", errors="ignore") as f:
                        file_content = f.read()

                    total_lines = file_content.count("\n") + 1
                    if ext == ".md" and len(file_content) > 12000:
                        section_headers = [line for line in file_content.splitlines() if line.startswith("#")]
                        headers_summary = "\n".join(section_headers[:60])
                        excerpt = (
                            f"DOCUMENT OUTLINE & TABLE OF SECTIONS:\n{headers_summary}\n\n"
                            f"EXCERPT:\n{file_content[:14000]}\n"
                            f"... [Document continues across {total_lines} lines total] ..."
                        )
                    elif len(file_content) > 12000:
                        excerpt = file_content[:12000] + f"\n... [Truncated {len(file_content) - 12000} remaining bytes] ..."
                    else:
                        excerpt = file_content

                    parts.append(
                        f"[VERIFIED DISK CONTENT: `{rel_path}` ({total_lines} lines, {len(file_content):,} bytes)]:\n"
                        f"```\n{excerpt}\n```"
                    )
                except Exception as read_err:
                    logger.debug(f"[TargetFileGrounding] Error reading file {resolved_path}: {read_err}")

        if not parts:
            return None

        directive = "INSTRUCTION: Address the user directive accurately based on the verified local file contents provided above."
        return GroundingResult(content="\n\n".join(parts), specialized_directive=directive)


class GitStateGroundingProvider(BaseGroundingProvider):
    """
    Grounds inquiries regarding Git branch status, recent commits, and working tree changes.
    """

    def __init__(self, git_inspector: Optional[GitManifoldInspector] = None):
        self.git_inspector = git_inspector or GitManifoldInspector()

    async def can_handle(self, prompt: str, parsed_intent: ParsedGoalTuple) -> bool:
        body_lower = prompt.lower()
        return any(w in body_lower for w in ["git status", "git log", "recent commit", "git branch", "git diff", "git repo", "git repository"])

    async def provide_grounding(self, prompt: str, parsed_intent: ParsedGoalTuple) -> Optional[GroundingResult]:
        try:
            git_st = await self.git_inspector.get_git_status()
            recent_commits = await self.git_inspector.get_recent_commits(limit=5)

            status_lines = [
                f"Branch: {git_st.get('branch', 'unknown')}",
                f"Clean: {git_st.get('is_clean', True)}",
                f"Modified Files: {', '.join(git_st.get('modified_files', [])) or 'None'}",
                f"Untracked Files: {', '.join(git_st.get('untracked_files', [])) or 'None'}",
                "\nRecent Commits:"
            ]
            for c in recent_commits:
                status_lines.append(f"- [{c.get('commit_hash', '')[:7]}] {c.get('message', '')} ({c.get('relative_time', '')})")

            content = (
                f"[VERIFIED GIT REPOSITORY MANIFOLD STATE]\n"
                + "\n".join(status_lines)
            )
            directive = "INSTRUCTION: Report git repository and commit status accurately based on the verified git manifold state above."
            return GroundingResult(content=content, specialized_directive=directive)
        except Exception as e:
            logger.debug(f"[GitStateGrounding] Failed inspecting git state: {e}")
            return None


class ModularGroundingOrchestrator:
    """
    Orchestrates modular grounding providers. Evaluates query intent, executes active providers
    in parallel, and formats an isolated, unpolluted reference grounding envelope.
    """

    def __init__(self):
        self.inspector = LocalCodebaseInspector()
        self.git_inspector = GitManifoldInspector()
        self.providers: List[BaseGroundingProvider] = [
            SkillsAndToolsManifestProvider(self.inspector),
            ArchitectureGroundingProvider(self.inspector),
            TargetFileGroundingProvider(self.inspector),
            GitStateGroundingProvider(self.git_inspector)
        ]

    async def resolve_grounding(self, prompt: str, parsed_intent: ParsedGoalTuple) -> Tuple[str, Optional[str]]:
        """
        Executes active providers and returns (combined_grounding_block, specialized_directive).
        """
        grounding_blocks = []
        specialized_directive = None

        for provider in self.providers:
            try:
                if await provider.can_handle(prompt, parsed_intent):
                    result = await provider.provide_grounding(prompt, parsed_intent)
                    if result and result.content:
                        grounding_blocks.append(result.content)
                        # Priority for specialized directives (e.g. skills enumeration)
                        if result.specialized_directive and not specialized_directive:
                            specialized_directive = result.specialized_directive
            except Exception as p_err:
                logger.debug(f"[GroundingOrchestrator] Provider error {provider.__class__.__name__}: {p_err}")

        combined_grounding = "\n\n".join(grounding_blocks) if grounding_blocks else ""
        return combined_grounding, specialized_directive
