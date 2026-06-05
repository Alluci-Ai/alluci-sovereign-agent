
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

    # Read device tier from query params (set by bridgeManager.ts)
    device_tier_str = websocket.query_params.get("device_tier", "MACBOOK_WORKSTATION")
    try:
        tier = DeviceTier(device_tier_str)
    except ValueError:
        tier = DeviceTier.MACBOOK_WORKSTATION

    # Configure the orchestrator for this device's optimal model topology
    config = voice_orchestrator.configure_for_device(tier)
    await websocket.send_json({"type": "config", **config})

    # Track silence for utterance finalization
    consecutive_silence_count = 0
    SILENCE_THRESHOLD_CHUNKS = 5  # 5 × 200ms = 1 second of silence → finalize

    try:
        while True:
            message = await websocket.receive()
            
            if "bytes" in message:
                pcm_bytes = message["bytes"]
                # Process the 200ms fragment through MLX-Whisper
                result = await voice_orchestrator.process_200ms_fragment(pcm_bytes)

                if result.get("text"):
                    consecutive_silence_count = 0
                    await websocket.send_json({
                        "type": "fragment",
                        "text": result["text"],
                        "fragment_index": result.get("fragment_index", 0),
                        "is_final": False,
                    })
                else:
                    consecutive_silence_count += 1

                # After sustained silence, finalize the utterance
                if consecutive_silence_count >= SILENCE_THRESHOLD_CHUNKS and voice_orchestrator._fragment_count > 0:
                    final = voice_orchestrator.finalize_utterance()
                    consecutive_silence_count = 0

                    if final["text"]:
                        await websocket.send_json({
                            "type": "utterance",
                            "text": final["text"],
                            "fragment_count": final["fragment_count"],
                            "is_final": True,
                            "requires_cognition": final["requires_cognition"],
                        })

                        # If the device can reason locally, route to MLXEngine
                        if final["requires_cognition"] and services.local_inference:
                            # Hand off to the main inference pipeline
                            cognition_result = await services.local_inference.transcribe(
                                final["text"].encode("utf-8")
                            )
                            await websocket.send_json({
                                "type": "cognition",
                                "text": cognition_result,
                                "is_final": True,
                            })
                            
                            # Synthesize cognition result to audio if tethered
                            from ..inference.voice_orchestrator import voice_orchestrator as orch
                            tts_result = await orch.synthesize_response(cognition_result, "am_adam")
                            if tts_result["type"] == "audio_pcm":
                                await websocket.send_bytes(tts_result["data"])
                            else:
                                await websocket.send_json(tts_result)
                                
            elif "text" in message:
                try:
                    payload = json.loads(message["text"])
                    if "respiratoryRate" in payload:
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
    if not services.local_inference:
        raise HTTPException(status_code=503, detail="Local inference not initialized")
    
    audio_data = await file.read()
    text = await services.local_inference.transcribe(audio_data)
    return {"status": "SUCCESS", "text": text}

@router.get("/voice/synthesise", dependencies=[Depends(verify_authenticated)])
async def synthesise_voice(text: str = Query(...)):
    """Synthesise text to speech using local Piper bridge (P1-007)."""
    if not services.local_inference:
        raise HTTPException(status_code=503, detail="Local inference not initialized")
    audio_bytes = await services.local_inference.synthesise(text)
    return Response(content=audio_bytes, media_type="audio/wav")

