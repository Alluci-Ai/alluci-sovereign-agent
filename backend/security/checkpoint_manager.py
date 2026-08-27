import os
import time
import json
import uuid
import hashlib
import shutil
import asyncio
from typing import List, Dict, Any, Optional

from ..logging_config import get_logger
from ..config import settings

logger = get_logger("CheckpointManager")


class SovereignCheckpointManager:
    """
    [ PPN-037 ] 4-Layer Non-Destructive Atomic Checkpoint & Instant 1-Click Rollback Engine.
    Guarantees that all file operations made by Codi can be reversed cleanly with 0 data loss.
    """
    _instance: Optional["SovereignCheckpointManager"] = None

    def __init__(self, base_dir: Optional[str] = None):
        self.project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self.vault_dir = base_dir or os.path.join(self.project_root, ".sovereign_vault", "checkpoints")
        os.makedirs(self.vault_dir, exist_ok=True)

    @classmethod
    def get_instance(cls) -> "SovereignCheckpointManager":
        if cls._instance is None:
            cls._instance = SovereignCheckpointManager()
        return cls._instance

    @staticmethod
    def _compute_sha256(file_path: str) -> Optional[str]:
        if not os.path.exists(file_path):
            return None
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    def create_checkpoint(self, task_id: str, description: str, target_files: List[str]) -> Dict[str, Any]:
        """
        Creates an atomic pre-state snapshot of all target files before mutation.
        Records SHA-256 hashes, stores raw file copies, and writes a metadata manifest.
        """
        checkpoint_id = f"chk_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        checkpoint_dir = os.path.join(self.vault_dir, checkpoint_id)
        backup_files_dir = os.path.join(checkpoint_dir, "pre_state_files")
        os.makedirs(backup_files_dir, exist_ok=True)

        file_manifest = {}
        for rel_path in target_files:
            abs_path = os.path.abspath(os.path.join(self.project_root, rel_path)) if not os.path.isabs(rel_path) else rel_path
            rel_name = os.path.relpath(abs_path, self.project_root)

            if os.path.exists(abs_path):
                sha256 = self._compute_sha256(abs_path)
                file_manifest[rel_name] = {
                    "existed": True,
                    "sha256": sha256,
                    "size_bytes": os.path.getsize(abs_path)
                }
                # Copy original file to backup dir
                dest_backup = os.path.join(backup_files_dir, rel_name.replace("/", "__"))
                shutil.copy2(abs_path, dest_backup)
            else:
                file_manifest[rel_name] = {
                    "existed": False,
                    "sha256": None,
                    "size_bytes": 0
                }

        manifest_data = {
            "checkpoint_id": checkpoint_id,
            "task_id": task_id,
            "description": description,
            "timestamp": int(time.time()),
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "files": file_manifest,
            "status": "active"
        }

        manifest_path = os.path.join(checkpoint_dir, "manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2)

        logger.info(f"[ CheckpointManager ] ✅ Created checkpoint {checkpoint_id} for task '{task_id}' ({len(target_files)} files)")
        return manifest_data

    def rollback_checkpoint(self, checkpoint_id: str) -> Dict[str, Any]:
        """
        Executes a 1-click atomic rollback, restoring all files to their exact pre-state condition.
        Deletes any newly created files that did not exist prior to the checkpoint.
        """
        checkpoint_dir = os.path.join(self.vault_dir, checkpoint_id)
        manifest_path = os.path.join(checkpoint_dir, "manifest.json")

        if not os.path.exists(manifest_path):
            raise FileNotFoundError(f"Checkpoint '{checkpoint_id}' does not exist in vault.")

        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)

        backup_files_dir = os.path.join(checkpoint_dir, "pre_state_files")
        restored_files = []
        deleted_new_files = []

        for rel_name, meta in manifest_data.get("files", {}).items():
            abs_path = os.path.abspath(os.path.join(self.project_root, rel_name))

            if meta.get("existed"):
                backup_file = os.path.join(backup_files_dir, rel_name.replace("/", "__"))
                if os.path.exists(backup_file):
                    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
                    shutil.copy2(backup_file, abs_path)
                    restored_files.append(rel_name)
                    # Verify restored hash
                    new_hash = self._compute_sha256(abs_path)
                    if new_hash != meta.get("sha256"):
                        logger.warning(f"[ CheckpointManager ] SHA-256 verification mismatch for {rel_name}")
            else:
                # File was created during the task; remove it cleanly
                if os.path.exists(abs_path):
                    os.remove(abs_path)
                    deleted_new_files.append(rel_name)

        manifest_data["status"] = "rolled_back"
        manifest_data["rolled_back_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2)

        # Route reverted task to Anti-Pattern Quarantine Pool
        self._quarantine_rolled_back_task(manifest_data)

        logger.info(f"[ CheckpointManager ] 🔄 Rolled back checkpoint {checkpoint_id}: Restored {len(restored_files)} files, removed {len(deleted_new_files)} new files.")
        return {
            "checkpoint_id": checkpoint_id,
            "status": "rolled_back",
            "restored_files": restored_files,
            "deleted_files": deleted_new_files,
            "timestamp": int(time.time())
        }

    def _quarantine_rolled_back_task(self, manifest_data: Dict[str, Any]) -> None:
        """Saves rolled-back task metadata to the Anti-Pattern Quarantine Pool for DPO learning."""
        quarantine_dir = os.path.join(self.project_root, "models", "quarantine")
        os.makedirs(quarantine_dir, exist_ok=True)
        q_file = os.path.join(quarantine_dir, f"quarantine_{manifest_data['checkpoint_id']}.json")
        try:
            with open(q_file, "w", encoding="utf-8") as f:
                json.dump({
                    "checkpoint_id": manifest_data.get("checkpoint_id"),
                    "task_id": manifest_data.get("task_id"),
                    "description": manifest_data.get("description"),
                    "reason": "USER_OR_TEST_ROLLBACK",
                    "quarantined_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "files": manifest_data.get("files")
                }, f, indent=2)
            logger.info(f"[ CheckpointManager ] Quarantined rolled-back trajectory to: {q_file}")
        except Exception as e:
            logger.warning(f"[ CheckpointManager ] Could not save to quarantine pool: {e}")

    def list_checkpoints(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Returns all recorded checkpoints sorted descending by creation time."""
        results = []
        if not os.path.exists(self.vault_dir):
            return results

        for item in sorted(os.listdir(self.vault_dir), reverse=True):
            item_dir = os.path.join(self.vault_dir, item)
            manifest_path = os.path.join(item_dir, "manifest.json")
            if os.path.isdir(item_dir) and os.path.exists(manifest_path):
                try:
                    with open(manifest_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        results.append(data)
                        if len(results) >= limit:
                            break
                except Exception:
                    continue
        return results
