import os
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends

from ..security.checkpoint_manager import SovereignCheckpointManager
from ..logging_config import get_logger
from .. import services

logger = get_logger("CheckpointsRouter")

router = APIRouter(prefix="/checkpoints", tags=["Sovereign Checkpoints & Rollback"])


@router.get("")
@router.get("/")
async def list_checkpoints(limit: int = 20) -> List[Dict[str, Any]]:
    """List recent atomic codebase checkpoints with SHA-256 metadata."""
    manager = SovereignCheckpointManager.get_instance()
    return manager.list_checkpoints(limit=limit)


@router.get("/{checkpoint_id}")
async def get_checkpoint(checkpoint_id: str) -> Dict[str, Any]:
    """Get details and manifest of a specific checkpoint."""
    manager = SovereignCheckpointManager.get_instance()
    checkpoints = manager.list_checkpoints(limit=100)
    for chk in checkpoints:
        if chk.get("checkpoint_id") == checkpoint_id:
            return chk
    raise HTTPException(status_code=404, detail=f"Checkpoint '{checkpoint_id}' not found.")


@router.post("/{checkpoint_id}/rollback")
async def rollback_checkpoint(checkpoint_id: str) -> Dict[str, Any]:
    """
    1-Click Atomic Rollback: Reverses all file changes made by Codi,
    restores pre-state file hashes, and emits real-time UI notification.
    """
    manager = SovereignCheckpointManager.get_instance()
    try:
        result = manager.rollback_checkpoint(checkpoint_id)

        # Broadcast real-time WebSocket event to update UI
        if services.ws_gw:
            await services.ws_gw.broadcast_event(
                event_type="codebase.rolled_back",
                data={
                    "checkpoint_id": checkpoint_id,
                    "restored_files": result.get("restored_files", []),
                    "deleted_files": result.get("deleted_files", [])
                }
            )

        return result
    except FileNotFoundError as fnf:
        raise HTTPException(status_code=404, detail=str(fnf))
    except Exception as e:
        logger.error(f"[ CheckpointsRouter ] Rollback error for {checkpoint_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Rollback failed: {str(e)}")
