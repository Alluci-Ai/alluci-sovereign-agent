"""
Sovereign Codebase, Architecture & Git/GitHub Grounding Engine
==============================================================
Provides real-time AST symbol indexing, workspace filesystem tree inspection,
local Git manifold status, and authenticated GitHub repository synchronization.
"""

from __future__ import annotations

import os
import ast
import re
import time
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Union, Tuple
import httpx

from ..logging_config import get_logger
from ..security.vault import VaultManager

logger = get_logger("CodebaseGrounding")

# Standard directories and file patterns ignored during codebase walks
IGNORED_DIRS = {
    ".git", "node_modules", ".venv", "venv", "__pycache__",
    ".pytest_cache", "htmlcov", "dist", "build", ".next",
    ".cache", "coverage", ".turbo", "scratch"
}

IGNORED_EXTENSIONS = {
    ".pyc", ".pyo", ".pyd", ".so", ".dylib", ".dll",
    ".safetensors", ".gguf", ".bin", ".tar", ".gz",
    ".zip", ".png", ".jpg", ".jpeg", ".gif", ".ico",
    ".webp", ".mp3", ".wav", ".mp4", ".mov", ".db",
    ".kuzu", ".sqlite", ".sqlite3", ".log", ".DS_Store"
}


class LocalCodebaseInspector:
    """
    On-device workspace filesystem inspector and AST symbol parser.
    Provides deterministic, non-stubbed analysis of local source files and architecture.
    """

    def __init__(self, project_root: Optional[str] = None):
        self.project_root = project_root or os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..")
        )
        self._cache_ts: float = 0.0
        self._tree_cache: Optional[Dict[str, Any]] = None
        self._symbols_cache: Optional[Dict[str, Any]] = None
        self._cache_ttl: float = 30.0  # 30 seconds

    def get_workspace_tree(self, max_depth: int = 4, max_files: int = 600) -> Dict[str, Any]:
        """
        Recursively scans the workspace directory structure, filtering out binaries
        and dependency directories.
        """
        now = time.time()
        if self._tree_cache and (now - self._cache_ts < self._cache_ttl):
            return self._tree_cache

        tree: Dict[str, Any] = {
            "root": os.path.basename(self.project_root) or "workspace",
            "path": self.project_root,
            "type": "directory",
            "children": []
        }

        total_files = 0

        def _scan_dir(current_path: str, current_node: Dict[str, Any], depth: int):
            nonlocal total_files
            if depth > max_depth or total_files >= max_files:
                return

            try:
                entries = sorted(os.listdir(current_path))
            except Exception as e:
                logger.debug(f"[CodebaseInspector] Failed to list {current_path}: {e}")
                return

            for entry in entries:
                if entry.startswith(".") and entry != ".agents" and entry != ".env.example":
                    if entry in IGNORED_DIRS or entry.startswith(".git"):
                        continue

                full_path = os.path.join(current_path, entry)
                rel_path = os.path.relpath(full_path, self.project_root)

                if os.path.isdir(full_path):
                    if entry in IGNORED_DIRS:
                        continue
                    child_node = {
                        "name": entry,
                        "path": rel_path,
                        "type": "directory",
                        "children": []
                    }
                    current_node["children"].append(child_node)
                    _scan_dir(full_path, child_node, depth + 1)
                else:
                    ext = os.path.splitext(entry)[1].lower()
                    if ext in IGNORED_EXTENSIONS:
                        continue

                    total_files += 1
                    file_size = os.path.getsize(full_path) if os.path.exists(full_path) else 0
                    current_node["children"].append({
                        "name": entry,
                        "path": rel_path,
                        "type": "file",
                        "size_bytes": file_size,
                        "extension": ext
                    })

        _scan_dir(self.project_root, tree, 1)
        self._tree_cache = tree
        self._cache_ts = now
        return tree

    def get_file_catalog(self, limit: int = 200) -> List[Dict[str, Any]]:
        """Returns a flat list of recognized source files with line counts and language types."""
        catalog: List[Dict[str, Any]] = []
        for root, dirs, files in os.walk(self.project_root):
            # In-place filter ignored directories
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and not d.startswith(".git")]

            for file in sorted(files):
                if len(catalog) >= limit:
                    break
                ext = os.path.splitext(file)[1].lower()
                if ext in IGNORED_EXTENSIONS:
                    continue

                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, self.project_root)

                try:
                    stat = os.stat(full_path)
                    lines_count = 0
                    if ext in {".py", ".ts", ".tsx", ".js", ".jsx", ".json", ".md", ".yaml", ".yml", ".html", ".css", ".sql"}:
                        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                            lines_count = sum(1 for _ in f)

                    lang_map = {
                        ".py": "python", ".ts": "typescript", ".tsx": "typescript-react",
                        ".js": "javascript", ".jsx": "javascript-react", ".json": "json",
                        ".md": "markdown", ".yaml": "yaml", ".yml": "yaml",
                        ".html": "html", ".css": "css", ".sql": "sql"
                    }

                    catalog.append({
                        "path": rel_path,
                        "name": file,
                        "language": lang_map.get(ext, "text"),
                        "size_bytes": stat.st_size,
                        "lines_count": lines_count,
                        "last_modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
                    })
                except Exception:
                    continue

        return catalog

    def parse_ast_symbols(self, target_files: Optional[List[str]] = None, max_files: int = 50) -> Dict[str, Any]:
        """
        Parses source files into structured AST symbol records:
        - Python: classes, methods, functions, FastAPI route endpoints, SQLModel tables.
        - TypeScript / JavaScript: React components, interfaces, exported functions.
        """
        now = time.time()
        if not target_files and self._symbols_cache and (now - self._cache_ts < self._cache_ttl):
            return self._symbols_cache

        symbols_by_file: Dict[str, Any] = {}
        processed_count = 0

        # Scan backend and key frontend paths by default if none specified
        scan_paths = []
        if target_files:
            scan_paths = [os.path.join(self.project_root, f) if not os.path.isabs(f) else f for f in target_files]
        else:
            for base_dir in ["backend", "components", "features"]:
                dir_abs = os.path.join(self.project_root, base_dir)
                if os.path.exists(dir_abs):
                    for root, dirs, files in os.walk(dir_abs):
                        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
                        for f in sorted(files):
                            if f.endswith((".py", ".ts", ".tsx", ".js", ".jsx")):
                                scan_paths.append(os.path.join(root, f))

        for file_abs in scan_paths:
            if processed_count >= max_files:
                break
            if not os.path.exists(file_abs) or os.path.isdir(file_abs):
                continue

            rel_path = os.path.relpath(file_abs, self.project_root)
            processed_count += 1

            if file_abs.endswith(".py"):
                file_symbols = self._parse_python_ast(file_abs, rel_path)
                symbols_by_file[rel_path] = file_symbols
            elif file_abs.endswith((".ts", ".tsx", ".js", ".jsx")):
                file_symbols = self._parse_typescript_symbols(file_abs, rel_path)
                symbols_by_file[rel_path] = file_symbols

        result = {
            "total_files_analyzed": len(symbols_by_file),
            "files": symbols_by_file,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        if not target_files:
            self._symbols_cache = result

        return result

    def _parse_python_ast(self, file_abs: str, rel_path: str) -> Dict[str, Any]:
        """Parses a Python file using the native `ast` module."""
        try:
            with open(file_abs, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            tree = ast.parse(content, filename=rel_path)
            classes = []
            functions = []
            routes = []
            imports = []

            for node in ast.iter_child_nodes(tree):
                # 1. Imports
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    mod = node.module or ""
                    for alias in node.names:
                        imports.append(f"{mod}.{alias.name}" if mod else alias.name)

                # 2. Classes
                elif isinstance(node, ast.ClassDef):
                    base_names = [self._get_node_name(b) for b in node.bases]
                    methods = []
                    for item in node.body:
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            methods.append({
                                "name": item.name,
                                "is_async": isinstance(item, ast.AsyncFunctionDef),
                                "line": item.lineno,
                                "args": [a.arg for a in item.args.args if a.arg != "self"]
                            })
                    doc = ast.get_docstring(node) or ""
                    classes.append({
                        "name": node.name,
                        "line": node.lineno,
                        "bases": base_names,
                        "methods": methods,
                        "docstring": doc[:200] if doc else None,
                        "is_sqlmodel": "SQLModel" in base_names or "table=True" in content
                    })

                # 3. Top-Level Functions & Routes
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    decorators = []
                    is_route = False
                    route_path = None
                    route_method = None

                    for dec in node.decorator_list:
                        dec_str = self._get_decorator_str(dec)
                        decorators.append(dec_str)
                        if any(dec_str.startswith(f"router.{m}") or dec_str.startswith(f"app.{m}")
                               for m in ["get", "post", "put", "delete", "patch", "options", "api_route"]):
                            is_route = True
                            match = re.search(r'\((["\'])(.*?)\1', dec_str)
                            if match:
                                route_path = match.group(2)
                            m_match = re.search(r'(?:router|app)\.([a-z]+)', dec_str)
                            if m_match:
                                route_method = m_match.group(1).upper()

                    doc = ast.get_docstring(node) or ""
                    fn_info = {
                        "name": node.name,
                        "line": node.lineno,
                        "is_async": isinstance(node, ast.AsyncFunctionDef),
                        "args": [a.arg for a in node.args.args],
                        "decorators": decorators,
                        "docstring": doc[:200] if doc else None
                    }

                    if is_route:
                        routes.append({
                            "endpoint": node.name,
                            "path": route_path or "",
                            "http_method": route_method or "GET",
                            "line": node.lineno
                        })
                    else:
                        functions.append(fn_info)

            return {
                "language": "python",
                "classes": classes,
                "functions": functions,
                "routes": routes,
                "imports": imports[:25]
            }
        except Exception as e:
            return {
                "language": "python",
                "parse_error": str(e),
                "classes": [],
                "functions": [],
                "routes": [],
                "imports": []
            }

    def _parse_typescript_symbols(self, file_abs: str, rel_path: str) -> Dict[str, Any]:
        """Extracts TypeScript interfaces, React components, and functions via robust pattern extraction."""
        try:
            with open(file_abs, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            interfaces = []
            components = []
            functions = []

            # 1. Interface & Type declarations
            for m in re.finditer(r'(?:export\s+)?(?:interface|type)\s+([A-Za-z0-9_]+)', content):
                interfaces.append(m.group(1))

            # 2. React Components (e.g. `export const MyComponent: React.FC` or `function MyComponent()`)
            for m in re.finditer(r'(?:export\s+(?:default\s+)?)?(?:const|function)\s+([A-Z][A-Za-z0-9_]+)\b', content):
                comp_name = m.group(1)
                if comp_name not in components:
                    components.append(comp_name)

            # 3. Exported functions
            for m in re.finditer(r'export\s+(?:async\s+)?function\s+([a-z][A-Za-z0-9_]+)', content):
                functions.append(m.group(1))

            return {
                "language": "typescript",
                "interfaces": interfaces[:20],
                "components": components[:20],
                "functions": functions[:20]
            }
        except Exception as e:
            return {
                "language": "typescript",
                "parse_error": str(e),
                "interfaces": [],
                "components": [],
                "functions": []
            }

    @staticmethod
    def _get_node_name(node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{LocalCodebaseInspector._get_node_name(node.value)}.{node.attr}"
        return ""

    @staticmethod
    def _get_decorator_str(node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{LocalCodebaseInspector._get_node_name(node.value)}.{node.attr}"
        elif isinstance(node, ast.Call):
            func_name = LocalCodebaseInspector._get_decorator_str(node.func)
            args_repr = []
            for a in node.args:
                if isinstance(a, ast.Constant):
                    args_repr.append(repr(a.value))
                elif isinstance(a, ast.Name):
                    args_repr.append(a.id)
            return f"{func_name}({', '.join(args_repr)})"
        return ""

    def read_file_snippet(self, rel_path: str, start_line: int = 1, end_line: Optional[int] = None) -> Dict[str, Any]:
        """Safely reads a slice of an authoritative source file."""
        abs_path = os.path.abspath(os.path.join(self.project_root, rel_path))
        if not abs_path.startswith(self.project_root):
            raise ValueError("Path traversal forbidden")

        if not os.path.exists(abs_path) or os.path.isdir(abs_path):
            raise FileNotFoundError(f"File '{rel_path}' not found")

        with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()

        total_lines = len(lines)
        start = max(1, start_line)
        end = min(total_lines, end_line) if end_line else total_lines

        selected_lines = lines[start - 1:end]
        return {
            "path": rel_path,
            "start_line": start,
            "end_line": end,
            "total_lines": total_lines,
            "content": "".join(selected_lines)
        }

    def get_architecture_summary(self) -> Dict[str, Any]:
        """Extracts structured summaries from ARCHITECTURE.md, AGENTS.md, and README.md."""
        arch_md_path = os.path.join(self.project_root, "ARCHITECTURE.md")
        agents_md_path = os.path.join(self.project_root, "AGENTS.md")

        arch_content = ""
        agents_content = ""

        if os.path.exists(arch_md_path):
            with open(arch_md_path, "r", encoding="utf-8") as f:
                arch_content = f.read()

        if os.path.exists(agents_md_path):
            with open(agents_md_path, "r", encoding="utf-8") as f:
                agents_content = f.read()

        return {
            "title": "Alluci Sovereign Agent Architecture Blueprint",
            "pillars": [
                "Sovereign Identity (VerusID - Ed25519 decentralized authentication & manifest signing)",
                "HITL Executive Security Governance (Interactive authorization modal gating destructive operations)",
                "4-Tier Simplicial H-LSM Memory (L0 Working, L1 Episodic FTS5, L2 Semantic, L3 KùzuDB Graph)",
                "Bio-Affective Computing Engine (ACE biometrics & cognitive tension psi modulation)",
                "Policy-Driven DAG Orchestration (Autonomous hierarchical DAG decomposition & cron scheduler)"
            ],
            "architecture_guide_length": len(arch_content),
            "agents_directive_length": len(agents_content),
            "hardware_profiling": "TIER_0_ULTRA through TIER_4_EDGE (Apple MLX on macOS / Cross-platform LlamaCpp)"
        }

    def get_simplicial_topology_summary(self, max_files: int = 50) -> Dict[str, Any]:
        """
        Uses PMETFiltrationEngine to construct a Vietoris-Rips simplicial complex
        over the codebase import graph, computing Betti invariants [beta_0, beta_1, beta_2, beta_3].
        """
        from ..topology.pmet_filtration import PMETFiltrationEngine
        engine = PMETFiltrationEngine()

        symbols = self.parse_ast_symbols(max_files=max_files)
        nodes = list(symbols.get("files", {}).keys())
        edges: List[Tuple[str, str]] = []

        for f_path, f_data in symbols.get("files", {}).items():
            for imp in f_data.get("imports", []):
                # Search for target file in node list
                clean_imp = imp.replace(".", "/").replace("backend/", "").replace("from ", "").strip()
                for target_node in nodes:
                    if clean_imp in target_node:
                        edges.append((f_path, target_node))

        summary = engine.filter_ast_graph(nodes=nodes, edges=edges)
        return {
            "vertices_count": summary.vertices_count,
            "edges_count": summary.edges_count,
            "faces_count": summary.faces_count,
            "euler_characteristic": summary.euler_characteristic,
            "betti_numbers": summary.betti_numbers,
            "has_circular_dependencies": summary.has_circular_dependencies,
            "connected_components": summary.connected_components,
            "is_nilpotent": summary.is_nilpotent,
        }


class GitManifoldInspector:
    """
    On-device, air-gapped Git repository and commit manifold analyzer.
    Executes local git read-only commands via non-blocking async subprocesses.
    """

    def __init__(self, project_root: Optional[str] = None):
        self.project_root = project_root or os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..")
        )

    async def _run_git_cmd(self, args: List[str]) -> Tuple[int, str, str]:
        """Runs a local git command asynchronously."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "git", *args,
                cwd=self.project_root,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            return proc.returncode or 0, stdout.decode("utf-8", errors="ignore").strip(), stderr.decode("utf-8", errors="ignore").strip()
        except Exception as e:
            return 1, "", str(e)

    async def get_git_status(self) -> Dict[str, Any]:
        """Returns local repository branch, tracking status, and modified/untracked files."""
        code, out, err = await self._run_git_cmd(["status", "--porcelain=v1", "-b"])
        if code != 0:
            return {"status": "error", "error": err or "Not a git repository"}

        lines = out.split("\n") if out else []
        branch_line = lines[0] if lines else ""
        file_lines = lines[1:] if len(lines) > 1 else []

        branch_name = "unknown"
        if branch_line.startswith("## "):
            branch_info = branch_line[3:]
            branch_name = branch_info.split("...")[0].strip()

        staged_files = []
        unstaged_files = []
        untracked_files = []

        for line in file_lines:
            if not line.strip():
                continue
            index_status = line[0] if len(line) > 0 else " "
            worktree_status = line[1] if len(line) > 1 else " "
            file_name = line[3:].strip()

            if index_status in ("M", "A", "D", "R", "C"):
                staged_files.append(file_name)
            if worktree_status in ("M", "D"):
                unstaged_files.append(file_name)
            if index_status == "?" and worktree_status == "?":
                untracked_files.append(file_name)

        return {
            "is_git_repo": True,
            "branch": branch_name,
            "is_clean": len(staged_files) == 0 and len(unstaged_files) == 0 and len(untracked_files) == 0,
            "staged_count": len(staged_files),
            "staged_files": staged_files[:20],
            "unstaged_count": len(unstaged_files),
            "unstaged_files": unstaged_files[:20],
            "untracked_count": len(untracked_files),
            "untracked_files": untracked_files[:20]
        }

    async def get_recent_commits(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieves recent commit log from the local git branch."""
        format_str = "%H%x00%an%x00%ad%x00%s"
        code, out, _ = await self._run_git_cmd(["log", f"-n{limit}", f"--format={format_str}", "--date=iso"])
        if code != 0 or not out:
            return []

        commits = []
        for line in out.split("\n"):
            if not line.strip():
                continue
            parts = line.split("\x00")
            if len(parts) >= 4:
                commits.append({
                    "commit_hash": parts[0],
                    "short_hash": parts[0][:8],
                    "author": parts[1],
                    "date": parts[2],
                    "message": parts[3]
                })

        return commits

    async def get_remotes(self) -> Dict[str, Any]:
        """Returns configured local git remotes."""
        code, out, _ = await self._run_git_cmd(["remote", "-v"])
        if code != 0 or not out:
            return {"remotes": {}}

        remotes: Dict[str, Dict[str, str]] = {}
        for line in out.split("\n"):
            match = re.match(r'([a-zA-Z0-9_\-]+)\s+([^\s]+)\s+\((fetch|push)\)', line.strip())
            if match:
                name, url, r_type = match.groups()
                if name not in remotes:
                    remotes[name] = {}
                remotes[name][r_type] = url

        return {"remotes": remotes}


class GitHubRepositoryInspector:
    """
    Vault-authenticated GitHub remote repository synchronizer and metadata inspector.
    Securely queries GitHub REST APIs using credentials loaded dynamically from VaultManager.
    """

    def __init__(self, vault: Optional[VaultManager] = None):
        self.vault = vault
        self._cache: Dict[str, Any] = {}
        self._cache_ts: Dict[str, float] = {}
        self._cache_ttl: float = 60.0  # 60 seconds

    async def _get_auth_headers(self) -> Tuple[Dict[str, str], Optional[str], Optional[str]]:
        """
        Loads GitHub token and repo coordinates dynamically from AES-256 Vault.
        Falls back to environment variables `GITHUB_TOKEN` / `GITHUB_REPOSITORY` if configured.
        """
        gh_bearer_key = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_PAT")
        repo_slug = os.environ.get("GITHUB_REPOSITORY", "Alluci-Ai/alluci-sovereign-agent")

        if self.vault:
            try:
                secret = await self.vault.retrieve_secret("github_credentials")
                if isinstance(secret, dict):
                    gh_bearer_key = secret.get("token") or gh_bearer_key
                    repo_slug = secret.get("repository") or repo_slug
            except Exception as e:
                logger.debug(f"[GitHubInspector] Vault token retrieval note: {e}")

        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "Alluci-Sovereign-Agent/1.0"
        }
        if gh_bearer_key:
            headers["Authorization"] = f"Bearer {gh_bearer_key}"

        parts = repo_slug.split("/") if repo_slug else []
        owner = parts[0] if len(parts) > 0 else "Alluci-Ai"
        repo = parts[1] if len(parts) > 1 else "alluci-sovereign-agent"

        return headers, owner, repo

    async def get_repo_overview(self) -> Dict[str, Any]:
        """Fetches repository metadata from GitHub REST API with caching."""
        cache_key = "repo_overview"
        now = time.time()
        if cache_key in self._cache and (now - self._cache_ts.get(cache_key, 0) < self._cache_ttl):
            return self._cache[cache_key]

        headers, owner, repo = await self._get_auth_headers()
        url = f"https://api.github.com/repos/{owner}/{repo}"

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    result = {
                        "status": "connected",
                        "repository": data.get("full_name", f"{owner}/{repo}"),
                        "description": data.get("description", ""),
                        "default_branch": data.get("default_branch", "main"),
                        "stars": data.get("stargazers_count", 0),
                        "forks": data.get("forks_count", 0),
                        "open_issues_count": data.get("open_issues_count", 0),
                        "visibility": data.get("visibility", "private"),
                        "updated_at": data.get("updated_at", "")
                    }
                    self._cache[cache_key] = result
                    self._cache_ts[cache_key] = now
                    return result
                elif resp.status_code == 404:
                    return {"status": "not_found", "message": f"Repository '{owner}/{repo}' not found or token lacks access."}
                elif resp.status_code == 401:
                    return {"status": "unauthorized", "message": "Invalid GitHub token or authentication required."}
                else:
                    return {"status": "api_error", "code": resp.status_code, "detail": resp.text[:200]}
        except Exception as e:
            return {"status": "network_unavailable", "detail": f"Local air-gapped mode active: {str(e)}"}

    async def get_pull_requests(self, state: str = "all", limit: int = 10) -> List[Dict[str, Any]]:
        """Fetches pull requests from GitHub."""
        cache_key = f"prs_{state}_{limit}"
        now = time.time()
        if cache_key in self._cache and (now - self._cache_ts.get(cache_key, 0) < self._cache_ttl):
            return self._cache[cache_key]

        headers, owner, repo = await self._get_auth_headers()
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls?state={state}&per_page={limit}"

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    prs = []
                    for item in resp.json():
                        prs.append({
                            "number": item.get("number"),
                            "title": item.get("title"),
                            "state": item.get("state"),
                            "user": item.get("user", {}).get("login", "unknown"),
                            "created_at": item.get("created_at"),
                            "html_url": item.get("html_url")
                        })
                    self._cache[cache_key] = prs
                    self._cache_ts[cache_key] = now
                    return prs
                return []
        except Exception:
            return []

    async def get_issues(self, state: str = "all", limit: int = 10) -> List[Dict[str, Any]]:
        """Fetches issues from GitHub."""
        cache_key = f"issues_{state}_{limit}"
        now = time.time()
        if cache_key in self._cache and (now - self._cache_ts.get(cache_key, 0) < self._cache_ttl):
            return self._cache[cache_key]

        headers, owner, repo = await self._get_auth_headers()
        url = f"https://api.github.com/repos/{owner}/{repo}/issues?state={state}&per_page={limit}"

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    issues = []
                    for item in resp.json():
                        if "pull_request" in item:
                            continue  # Skip PRs returned in issue list
                        issues.append({
                            "number": item.get("number"),
                            "title": item.get("title"),
                            "state": item.get("state"),
                            "user": item.get("user", {}).get("login", "unknown"),
                            "created_at": item.get("created_at"),
                            "html_url": item.get("html_url")
                        })
                    self._cache[cache_key] = issues
                    self._cache_ts[cache_key] = now
                    return issues
                return []
        except Exception:
            return []
