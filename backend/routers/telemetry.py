# backend/routers/telemetry.py
from ..logging_config import get_logger
from fastapi import APIRouter, HTTPException, Depends, Request
try:
    from fastapi_csrf_protect import CsrfProtect
except ImportError:
    class CsrfProtect:
        async def validate_csrf(self, request):
            return None
from ..models import TelemetryData
from ..security.auth import verify_authenticated
from .. import services

logger = get_logger("TelemetryRouter")
router = APIRouter(tags=["Telemetry"])


@router.post("/telemetry", dependencies=[Depends(verify_authenticated)])
async def post_telemetry(
    request: Request,
    csrf_protect: CsrfProtect = Depends(),
    data: TelemetryData = Depends(),
):
    """
    Ingests biometric telemetry from companion devices (Apple Watch, etc.)
    CSRF-protected via the singleton pattern.
    """
    await csrf_protect.validate_csrf(request)

    if not services.ace:
        raise HTTPException(status_code=503, detail="Affective Engine not initialized")

    flow_result = services.ace.process_telemetry(data)
    source = data.device_id if hasattr(data, "device_id") and data.device_id else "companion_device"

    if services.memory:
        try:
            await services.memory.store(
                content=f"Biometrics ({source}): {flow_result.get('mode')} - {flow_result.get('reason')}",
                metadata={
                    "type": "biometric_telemetry",
                    "source": source,
                    "valence": data.valence,
                    "arousal": data.arousal,
                    "focus": data.focus,
                },
            )
        except Exception as exc:
            logger.warning("Failed to store ACE state in memory: %s", exc)

    try:
        if (
            services.orchestrator
            and hasattr(services.orchestrator, "harmonic")
            and services.orchestrator.harmonic
        ):
            from ..harmonic_enhancer import AttentionSignal
            signal = AttentionSignal(
                valence=data.valence or 0.5,
                arousal=data.arousal or 0.5,
                focus=data.focus or 0.5,
            )
            await services.orchestrator.harmonic.tick(signal)
    except Exception as exc:
        logger.warning("Harmonic Enhancer tick failed: %s", exc)

    if services.ws_gw:
        try:
            await services.ws_gw.broadcast_event(
                "telemetry",
                {
                    "hr": data.hr,
                    "hrv": data.hrv,
                    "respiratory_rate": data.respiratory_rate,
                    "flow_intervention": flow_result,
                    "valence": data.valence,
                    "arousal": data.arousal,
                    "focus": data.focus
                }
            )
        except Exception as exc:
            logger.warning("Failed to broadcast telemetry: %s", exc)

    logger.info("[ TELEMETRY ]: Biometrics ingested from %s. Flow Status: %s",
                source, flow_result.get("mode"))
    return {
        "status": "SUCCESS",
        "flow_state": flow_result,
        "resonance": services.ace.current_state["physical_vitality"],
        "flow_intervention": flow_result,
        "current_metrics": {
            "stress_score": services.ace.current_state["stress_score"],
            "vitality": services.ace.current_state["physical_vitality"],
            "mode": services.ace.current_state["flow_mode"],
        },
    }
