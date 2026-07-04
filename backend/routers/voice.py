
from ..logging_config import get_logger
from fastapi import APIRouter, HTTPException, Depends, Query, Response, File, UploadFile, Request, WebSocket, WebSocketDisconnect
from ..security.auth import verify_authenticated
try:
    from fastapi_csrf_protect import CsrfProtect
except ImportError:
    class CsrfProtect:
        async def validate_csrf(self, request):
            return None
from .. import services
from ..inference.voice_orchestrator import voice_orchestrator, DeviceTier
import json
import asyncio

logger = get_logger("VoiceRouter")

router = APIRouter(tags=["Voice & Audio"])


# ────────────────────────────────────────────────────────
# [ SOVEREIGN_VOICE_STREAM ] Bidirectional WebSocket
# ────────────────────────────────────────────────────────

@router.websocket("/voice/stream")
async def ws_voice_stream(websocket: WebSocket):
    """
    [ PPN-030 ] Bidirectional streaming voice endpoint.
    Accepts inbound 200ms PCM binary frames from the frontend VAD worklet,
    transcribes them natively via MLX-Whisper on Apple Silicon,
    and streams partial text predictions back to the client in real-time.
    """
    await websocket.accept()
    from ..security.memory_offloader import start_memory_offloader_loop, record_activity
    asyncio.create_task(start_memory_offloader_loop())
    record_activity()

    # Read device tier and auto_submit from query params
    device_tier_str = websocket.query_params.get("device_tier", "MACBOOK_WORKSTATION")
    auto_submit = websocket.query_params.get("auto_submit", "false").lower() == "true"
    try:
        tier = DeviceTier(device_tier_str)
    except ValueError:
        tier = DeviceTier.MACBOOK_WORKSTATION

    # Configure the orchestrator for this device's optimal model topology
    config = voice_orchestrator.configure_for_device(tier)
    await websocket.send_json({"type": "config", **config})

    try:
        while True:
            message = await websocket.receive()
            
            if "bytes" in message:
                record_activity()
                pcm_bytes = message["bytes"]
                # Process the 200ms fragment through MLX-Whisper
                result = await voice_orchestrator.process_200ms_fragment(pcm_bytes)

                if result.get("text"):
                    await websocket.send_json({
                        "type": "fragment",
                        "text": result["text"],
                        "fragment_index": result.get("fragment_index", 0),
                        "is_final": False,
                    })

            elif "text" in message:
                try:
                    payload = json.loads(message["text"])
                    
                    if payload.get("type") == "control" and payload.get("action") == "finalize_utterance":
                        if voice_orchestrator._fragment_count > 0:
                            final = voice_orchestrator.finalize_utterance()
                            if final["text"]:
                                await websocket.send_json({
                                    "type": "utterance",
                                    "text": final["text"],
                                    "fragment_count": final["fragment_count"],
                                    "is_final": True,
                                    "requires_cognition": final.get("requires_cognition", True),
                                })

                                # Route to ModelRouter for LCE / Failover cognition
                                if final.get("requires_cognition", True) and auto_submit and services.router:
                                    from ..inference.voice_orchestrator import voice_orchestrator as orch
                                    from ..security.memory_offloader import record_activity
                                    full_text_list = []
                                    sentence_buffer = []

                                    async for chunk in services.router.get_response_stream(final["text"]):
                                        full_text_list.append(chunk)
                                        sentence_buffer.append(chunk)

                                        # Check for sentence boundary
                                        if any(punct in chunk for punct in [".", "!", "?", "\n"]):
                                            sentence = "".join(sentence_buffer).strip()
                                            if sentence:
                                                record_activity()
                                                tts_result = await orch.synthesize_response(sentence, "am_adam")
                                                if tts_result["type"] == "audio_pcm":
                                                    await websocket.send_bytes(tts_result["data"])
                                                sentence_buffer = []

                                    # Process remaining text in buffer
                                    remaining = "".join(sentence_buffer).strip()
                                    if remaining:
                                        record_activity()
                                        tts_result = await orch.synthesize_response(remaining, "am_adam")
                                        if tts_result["type"] == "audio_pcm":
                                            await websocket.send_bytes(tts_result["data"])

                                    cognition_result = "".join(full_text_list)
                                    await websocket.send_json({
                                        "type": "cognition",
                                        "text": cognition_result,
                                        "is_final": True,
                                    })
                                    
                    elif "respiratoryRate" in payload:
                        # Feed into anti-spoof
                        from ..ace.anti_spoof import AntiSpoofKernel
                        kernel = AntiSpoofKernel()
                        # Dummy audio features for now
                        is_human = kernel.verify_liveness({"jitter": 0.05, "breath_pauses_per_min": 15}, payload["respiratoryRate"])
                        if not is_human:
                            logger.warning("Anti-spoofing failed. Terminating connection.")
                            await websocket.close(code=1008, reason="Liveness check failed")
                            return
                except json.JSONDecodeError:
                    pass

    except WebSocketDisconnect:
        logger.info("[VOICE STREAM] Client disconnected.")
    except Exception as e:
        logger.error(f"[VOICE STREAM] Error: {e}")
        try:
            await websocket.close(code=1011, reason=str(e))
        except Exception:
            pass


# ────────────────────────────────────────────────────────
# [ LEGACY_REST ] Batch transcription (backward compatibility)
# ────────────────────────────────────────────────────────

@router.post("/voice/transcribe", dependencies=[Depends(verify_authenticated)])
async def transcribe_voice(request: Request, file: UploadFile = File(...),
    csrf_protect: CsrfProtect = Depends(),):
    await csrf_protect.validate_csrf(request)
    """Transcribes audio using local Whisper bridge (P1-007)."""
    from ..security.memory_offloader import record_activity
    record_activity()
    if not services.local_inference:
        raise HTTPException(status_code=503, detail="Local inference not initialized")
    
    audio_data = await file.read()
    text = await services.local_inference.transcribe(audio_data)
    return {"status": "SUCCESS", "text": text}

@router.get("/voice/synthesise", dependencies=[Depends(verify_authenticated)])
async def synthesise_voice(text: str = Query(...)):
    """Synthesise text to speech using local Piper bridge (P1-007)."""
    from ..security.memory_offloader import record_activity
    record_activity()
    if not services.local_inference:
        raise HTTPException(status_code=503, detail="Local inference not initialized")
    audio_bytes = await services.local_inference.synthesise(text)
    return Response(content=audio_bytes, media_type="audio/wav")

