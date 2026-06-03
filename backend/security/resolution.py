import asyncio
import logging
from typing import Dict, Any
from .exceptions import SecurityException
from ..logging_config import get_logger

logger = get_logger("SecurityResolutionManager")

class SecurityResolutionManager:
    """
    Manages interactive security resolutions.
    When a task throws a SecurityException, it asks this manager to wait for a resolution.
    The frontend calls a REST API to provide the resolution, which unlocks the event.
    """
    def __init__(self):
        # task_id -> {"event": asyncio.Event, "resolution": str}
        self._pending_resolutions: Dict[str, Dict[str, Any]] = {}

    async def request_resolution(self, task_id: str, exception: SecurityException) -> str:
        """
        Called by the DAG Executor when a task is blocked.
        Emits a WebSocket event to the frontend and suspends execution until the user responds.
        """
        self._pending_resolutions[task_id] = {
            "event": asyncio.Event(),
            "resolution": None
        }
        
        logger.info(f"Requesting interactive resolution for task {task_id}: {exception.message}")
        
        # Emit WebSocket event
        from .. import services
        if services.ws_gw:
            await services.ws_gw.broadcast_event(
                event_name="security.resolution_required",
                data={
                    "task_id": task_id,
                    "message": exception.message,
                    "exception_type": exception.exception_type,
                    "metadata": exception.metadata
                }
            )
        
        # Wait indefinitely for the API to trigger the event
        await self._pending_resolutions[task_id]["event"].wait()
        
        resolution = self._pending_resolutions[task_id]["resolution"]
        del self._pending_resolutions[task_id]
        return resolution

    def provide_resolution(self, task_id: str, resolution: str):
        """
        Called by the REST API when the user makes a choice on the frontend.
        Unlocks the suspended task.
        """
        if task_id in self._pending_resolutions:
            logger.info(f"Providing resolution '{resolution}' for task {task_id}")
            self._pending_resolutions[task_id]["resolution"] = resolution
            self._pending_resolutions[task_id]["event"].set()
            return True
        return False

resolution_manager = SecurityResolutionManager()
