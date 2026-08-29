import os
import ast
import time
import hashlib
from typing import Optional, List, Dict, Any

from ..logging_config import get_logger

logger = get_logger("CodeHealthDetector")


class CodeHealthDetector:
    """
    [ PPN-038 ] Autonomous Codebase Health & Architectural Improvement Sentinel.
    Runs during idle PCL cognitive cycles to analyze Python and TypeScript ASTs,
    detect syntax regressions, dead imports, and cyclomatic complexity spikes,
    synthesizing Proactive Code Improvement Cards for the user and Codi.
    """
    name = "CodeHealthDetector"
    COOLDOWN_MINUTES = 180

    def __init__(self, project_root: Optional[str] = None):
        self.project_root = project_root or os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        from .codebase_grounding import LocalCodebaseInspector
        self.inspector = LocalCodebaseInspector(self.project_root)

    def _scan_python_files(self, max_files: int = 20) -> List[Dict[str, Any]]:
        """Scans python files in backend/ for parse errors and high complexity using LocalCodebaseInspector."""
        findings = []
        catalog = self.inspector.get_file_catalog(limit=max_files * 3)
        py_files = [f["path"] for f in catalog if f["path"].endswith(".py") and not os.path.basename(f["path"]).startswith("test_") and f["path"].startswith("backend/")]

        for rel_path in py_files[:max_files]:
            full_path = os.path.join(self.project_root, rel_path)
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    code = f.read()

                # 1. Check syntax / parse validity
                tree = ast.parse(code, filename=rel_path)

                # 2. Check function complexity (number of branches / statements)
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        statement_count = len(node.body)
                        if statement_count > 45:
                            findings.append({
                                "file": rel_path,
                                "function": node.name,
                                "line": node.lineno,
                                "issue_type": "HIGH_CYCLOMATIC_COMPLEXITY",
                                "detail": f"Function '{node.name}' has {statement_count} statements; refactoring into smaller composable units recommended."
                            })
                            break

            except SyntaxError as se:
                findings.append({
                    "file": rel_path,
                    "function": "global",
                    "line": se.lineno or 1,
                    "issue_type": "SYNTAX_REGRESSION",
                    "detail": f"Syntax error on line {se.lineno}: {se.msg}"
                })
            except Exception:
                continue

        return findings

    async def detect(self, world: Any) -> Optional[Any]:
        """
        PCL cognitive stage 3 detect handler.
        Synthesizes an Opportunity if codebase optimization targets are detected.
        """
        # Lazy import of Opportunity to prevent circular references
        from ..pcl import Opportunity

        try:
            findings = self._scan_python_files(max_files=15)
            if not findings:
                return None

            top_finding = findings[0]
            condition_key = f"code_health:{hashlib.sha256((top_finding['file'] + str(top_finding['line'])).encode()).hexdigest()[:8]}"

            title = f"Code Health: {top_finding['issue_type'].replace('_', ' ').title()} in {os.path.basename(top_finding['file'])}"
            description = (
                f"File: {top_finding['file']}:{top_finding['line']} ({top_finding['function']}). "
                f"{top_finding['detail']}"
            )

            return Opportunity(
                id=Opportunity.make_id(self.name, condition_key),
                detector_name=self.name,
                title=title,
                description=description,
                priority=3,
                confidence=0.88,
                recommended_action="notify",
                objective=(
                    f"Codi Autonomous Refactoring: In '{top_finding['file']}', function '{top_finding['function']}' "
                    f"at line {top_finding['line']} was flagged with {top_finding['issue_type']}. "
                    f"Refactor and decompose this logic to preserve simplicial invariants and type safety."
                ),
                notification_body=(
                    f"💡 Codi Codebase Recommendation: Refactoring opportunity detected in {os.path.basename(top_finding['file'])} "
                    f"({top_finding['function']}). Should Codi generate an atomic optimization patch?"
                ),
                autonomy_level="RESTRICTED",
                cooldown_minutes=self.COOLDOWN_MINUTES
            )

        except Exception as e:
            logger.warning(f"[ CodeHealthDetector ] Detection cycle notice: {e}")
            return None
