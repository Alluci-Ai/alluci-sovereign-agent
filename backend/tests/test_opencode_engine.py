import pytest
import os
import tempfile
from backend.engine.opencode_engine import NativeOpenCodeHarness

@pytest.mark.asyncio
async def test_native_opencode_harness_ast_and_patch():
    with tempfile.TemporaryDirectory() as tmpdir:
        harness = NativeOpenCodeHarness()
        harness.project_root = tmpdir

        # 1. Test AST Syntax Validation
        valid_res = harness.validate_ast_syntax("sample.py", "def add(a, b):\n    return a + b\n")
        assert valid_res["valid"] is True

        invalid_res = harness.validate_ast_syntax("sample.py", "def broken_syntax(:\n")
        assert invalid_res["valid"] is False
        assert "SyntaxError" in invalid_res["error"]

        # 2. Test Atomic Patch Application
        patch_data = {
            "math_utils.py": "def multiply(x, y):\n    return x * y\n"
        }
        res = await harness.apply_verified_patch(
            task_id="task_opencode_001",
            description="Create math_utils.py",
            files_to_modify=patch_data
        )

        assert res["status"] == "applied"
        assert "math_utils.py" in res["files_modified"]
        assert os.path.exists(os.path.join(tmpdir, "math_utils.py"))

        # Verify content
        with open(os.path.join(tmpdir, "math_utils.py"), "r") as f:
            content = f.read()
        assert "def multiply(x, y):" in content
