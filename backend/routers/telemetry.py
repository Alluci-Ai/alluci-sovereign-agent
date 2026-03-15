
import logging
from ..logging_config import get_logger
from fastapi import APIRouter, HTTPException, Depends
from ..models import TelemetryData
from ..security.auth import verify_authenticated
from .. import services

logger = get_logger("TelemetryRouter")

router = APIRouter(tags=["Telemetry"])

@router.post("/api/telemetry", dependencies=[Depends(verify_authenticated)])
async def post_telemetry(data: TelemetryData):
    """
    Ingests biometric telemetry from companion devices (Apple Watch, etc.)
    Unifies ACE processing, Sovereign Memory storage, and Harmonic Enhancer synchronization.
    """
    if not services.ace:
        raise HTTPException(status_code=503, detail="Affective Engine not initialized")
    
    # 1. Process data through the Affective Computing Engine (ACE)
    flow_result = services.ace.process_telemetry(data)
    
    source = data.device_id if hasattr(data, "device_id") and data.device_id else "companion_device"
    
    # 2. Cognitive Pipeline — Store affective state in Sovereign Memory
    if services.memory:
        try:
            await services.memory.store(
                content=f"Biometrics ({source}): {flow_result.get('mode')} - {flow_result.get('reason')}",
                metadata={
                    "type": "biometric_telemetry",
                    "source": source,
                    "valence": data.valence,
                    "arousal": data.arousal,
                    "focus": data.focus
                }
            )
        except Exception as e:
            logger.warning(f"Failed to store ACE state in memory: {e}")

    # 3. Forward to Orchestrator's Harmonic Enhancer (updates UI agent reflection)
    try:
        if services.orchestrator and hasattr(services.orchestrator, 'harmonic') and services.orchestrator.harmonic:
            from ..harmonic_enhancer import AttentionSignal
            signal = AttentionSignal(
                valence=data.valence or 0.5,
                arousal=data.arousal or 0.5,
                focus=data.focus or 0.5
            )
            await services.orchestrator.harmonic.tick(signal)
    except Exception as e:
        logger.warning(f"Harmonic Enhancer tick failed: {e}")
        
    logger.info(f"[ TELEMETRY ]: Biometrics ingested from {source}. Flow Status: {flow_result.get('mode')}")
    
    # Return the unified state response
    return {
        "status": "SUCCESS",
        "flow_state": flow_result,
        "resonance": services.ace.current_state["physical_vitality"],
        "flow_intervention": flow_result, # For legacy UI compat
        "current_metrics": {
            "stress_score": services.ace.current_state["stress_score"],
            "vitality": services.ace.current_state["physical_vitality"],
            "mode": services.ace.current_state["flow_mode"]
        }
    }
