import logging
from typing import List, Optional
from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel

from .. import services

router = APIRouter(prefix="/sync", tags=["Sync"])
logger = logging.getLogger("SyncRouter")

class OfflineInteraction(BaseModel):
    id: str
    timestamp: str
    user_prompt: str
    agent_response: str
    inferred_intent: Optional[str] = None

class EdgeRecoveryPayload(BaseModel):
    device_id: str
    interactions: List[OfflineInteraction]

async def _ingest_offline_queue(payload: EdgeRecoveryPayload):
    """
    Background worker that ingests offline interactions into the core cognitive orchestrator.
    """
    logger.info(f"Initiating edge recovery ingestion for device '{payload.device_id}'. Processing {len(payload.interactions)} interactions.")
    
    if not services.orchestrator:
        logger.error("Orchestrator not initialized. Cannot ingest offline queue.")
        return

    for interaction in payload.interactions:
        # Construct an artificial "SYSTEM_INGESTION" prompt that forces the 31B model
        # to parse the context and route the user's intent to memory, tasks, or DAGs.
        ingestion_prompt = (
            f"SYSTEM_INGESTION: User interacted with the offline Edge model at {interaction.timestamp}.\n"
            f"User Prompt: '{interaction.user_prompt}'\n"
            f"Edge Response: '{interaction.agent_response}'\n"
            f"Please analyze this historical offline interaction. Extract any long-term memories to the H-LSM, "
            f"and register any implied tasks or workflow executions."
        )
        
        # Package it as an inbound message payload
        message_payload = {
            "from": payload.device_id,
            "protocol": "EDGE_RECOVERY",
            "body": ingestion_prompt,
            "session_key": f"sync_{payload.device_id}_{interaction.id}"
        }
        
        try:
            await services.orchestrator.handle_inbound_message(message_payload)
            logger.debug(f"Successfully ingested offline interaction {interaction.id}")
        except Exception as e:
            logger.error(f"Failed to ingest offline interaction {interaction.id}: {e}")

@router.post("/edge-recovery")
async def sync_edge_recovery(payload: EdgeRecoveryPayload, background_tasks: BackgroundTasks):
    """
    Receives an asynchronous payload of offline Voice/Edge interactions from the companion device
    (e.g., iPhone) and queues them for cognitive ingestion by the Workstation's primary model.
    """
    # Fire and forget: We hand the payload to the background queue so the iPhone can
    # immediately receive a 200 OK and clear its local SQLite database.
    background_tasks.add_task(_ingest_offline_queue, payload)
    
    return {
        "status": "success",
        "message": f"Queued {len(payload.interactions)} interactions for cognitive ingestion."
    }
