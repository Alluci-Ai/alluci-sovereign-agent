import os
import tempfile
import pytest
from backend.security.checkpoint_manager import SovereignCheckpointManager

def test_checkpoint_create_and_rollback():
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = SovereignCheckpointManager(base_dir=os.path.join(tmpdir, "checkpoints"))
        manager.project_root = tmpdir

        # 1. Create a test file
        test_file = os.path.join(tmpdir, "test_module.py")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("def original_function():\n    return 42\n")

        # 2. Create checkpoint
        chk = manager.create_checkpoint(
            task_id="task_test_001",
            description="Refactoring original_function",
            target_files=["test_module.py"]
        )

        assert chk["status"] == "active"
        checkpoint_id = chk["checkpoint_id"]
        assert "test_module.py" in chk["files"]
        assert chk["files"]["test_module.py"]["existed"] is True

        # 3. Simulate Codi mutating the file + creating a new file
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("def modified_function():\n    return 100\n")

        new_file = os.path.join(tmpdir, "new_module.py")
        with open(new_file, "w", encoding="utf-8") as f:
            f.write("# New helper file\n")

        # 4. Rollback
        rollback_res = manager.rollback_checkpoint(checkpoint_id)
        assert rollback_res["status"] == "rolled_back"
        assert "test_module.py" in rollback_res["restored_files"]

        # 5. Verify restored file content
        with open(test_file, "r", encoding="utf-8") as f:
            content = f.read()
        assert "def original_function():" in content
        assert "return 42" in content
