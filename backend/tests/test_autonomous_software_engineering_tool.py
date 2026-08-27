import pytest
pytestmark = pytest.mark.unit

import os
import tempfile
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock

from backend.app import app
from backend.tools.autonomous_software_engineering_tool import AutonomousSoftwareEngineeringTool
from backend.engine.opencode_engine import NativeOpenCodeHarness
from backend.security.checkpoint_manager import SovereignCheckpointManager


@pytest.fixture
def temp_workspace():
    with tempfile.TemporaryDirectory() as tmpdir:
        orig_cwd = os.getcwd()
        yield tmpdir
        os.chdir(orig_cwd)


@pytest.fixture
def opencode_tool(temp_workspace):
    tool = AutonomousSoftwareEngineeringTool()
    tool.project_root = temp_workspace
    tool.harness.project_root = temp_workspace
    return tool


def test_validate_ast_syntax_python_and_json(opencode_tool):
    # 1. Valid Python
    valid_py = opencode_tool.validate_ast_syntax("test.py", "def greet(name: str) -> str:\n    return f'Hello {name}'\n")
    assert valid_py["valid"] is True
    assert valid_py["language"] == "python"
    assert valid_py["error"] is None

    # 2. Invalid Python
    invalid_py = opencode_tool.validate_ast_syntax("bad.py", "def broken_syntax(:\n    pass\n")
    assert invalid_py["valid"] is False
    assert "SyntaxError" in invalid_py["error"]
    assert invalid_py["line"] == 1

    # 3. Valid JSON
    valid_json = opencode_tool.validate_ast_syntax("config.json", '{"name": "alluci", "active": true}')
    assert valid_json["valid"] is True

    # 4. Invalid JSON
    invalid_json = opencode_tool.validate_ast_syntax("bad.json", '{"name": "alluci", invalid}')
    assert invalid_json["valid"] is False
    assert "JSON Parse Error" in invalid_json["error"]

    # 5. TypeScript
    valid_ts = opencode_tool.validate_ast_syntax("Component.tsx", "export const Button = () => <button>Click</button>;")
    assert valid_ts["valid"] is True

    empty_ts = opencode_tool.validate_ast_syntax("Empty.ts", "   \n  ")
    assert empty_ts["valid"] is False


@pytest.mark.asyncio
async def test_run_lsp_diagnostics(opencode_tool):
    # Valid Python diagnostic check
    res = await opencode_tool.run_lsp_diagnostics("module.py", "def calc(x, y):\n    return x + y\n")
    assert res["status"] == "SUCCESS"
    assert res["error_count"] == 0

    # Broken syntax check
    res_bad = await opencode_tool.run_lsp_diagnostics("module.py", "def calc(:\n")
    assert res_bad["status"] == "DIAGNOSTIC_FAILURE"
    assert res_bad["error_count"] == 1


@pytest.mark.asyncio
async def test_create_checkpoint_and_patch_and_rollback(opencode_tool, temp_workspace):
    file_path = os.path.join(temp_workspace, "service.py")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("def original_function():\n    return 'v1'\n")

    # 1. Create atomic checkpoint
    chk_res = opencode_tool.create_atomic_checkpoint(
        task_id="task_refactor_01",
        description="Refactor service.py to v2",
        target_files=["service.py"]
    )
    assert chk_res["status"] == "SUCCESS"
    assert "checkpoint_id" in chk_res
    chk_id = chk_res["checkpoint_id"]

    # 2. Apply verified patch
    patch_res = await opencode_tool.apply_verified_patch(
        task_id="task_refactor_01",
        description="Update to v2",
        files_to_modify={"service.py": "def original_function():\n    return 'v2_updated'\n"}
    )
    assert patch_res["status"] == "applied"

    with open(file_path, "r", encoding="utf-8") as f:
        assert "v2_updated" in f.read()

    # 3. Rollback checkpoint
    rb_res = opencode_tool.rollback_checkpoint(chk_id)
    assert rb_res["status"] == "ROLLED_BACK"

    with open(file_path, "r", encoding="utf-8") as f:
        assert "return 'v1'" in f.read()


@pytest.mark.asyncio
async def test_run_automated_tests_sandboxing(opencode_tool):
    # 1. Denied command test
    denied = await opencode_tool.run_automated_tests("git push origin main")
    assert denied["status"] == "PERMISSION_DENIED"
    assert denied["code"] == 403

    # 2. Allowed benign test command
    allowed = await opencode_tool.run_automated_tests("python3 --version")
    assert allowed["status"] == "SUCCESS"
    assert allowed["exit_code"] == 0
    assert "Python" in (allowed["stdout"] + allowed["stderr"])


@pytest.mark.asyncio
async def test_request_hitl_approval(opencode_tool):
    res = await opencode_tool.request_hitl_approval(
        task_id="task_test_approval",
        context_summary="Refactoring auth module",
        unified_diff="+ def new_auth(): pass"
    )
    assert res["approved"] is True
    assert res["task_id"] == "task_test_approval"


@pytest.mark.asyncio
async def test_get_daemon_status(opencode_tool):
    status = await opencode_tool.get_daemon_status()
    assert "running" in status
    assert "port" in status
    assert "hostname" in status


def test_api_route_codi_tool_capability():
    client = TestClient(app)

    # 1. Test validate_ast_syntax capability
    resp = client.post(
        "/api/v1/tools/codi_tool_01/capability",
        json={
            "capability": "validate_ast_syntax",
            "params": {
                "file_path": "test_script.py",
                "proposed_code": "x = 42\nprint(x)\n"
            }
        }
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is True
    assert data["language"] == "python"

    # 2. Test get_daemon_status capability
    resp_daemon = client.post(
        "/api/v1/tools/codi_tool_01/capability",
        json={"capability": "get_daemon_status"}
    )
    assert resp_daemon.status_code == 200
    assert "running" in resp_daemon.json()

    # 3. Test unknown capability error handling
    resp_err = client.post(
        "/api/v1/tools/codi_tool_01/capability",
        json={"capability": "non_existent_capability"}
    )
    assert resp_err.status_code == 400
    assert "Unknown capability" in resp_err.json()["detail"]
