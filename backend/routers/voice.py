
import json
import asyncio
import re
from typing import Optional, Any
from ..logging_config import get_logger
from fastapi import APIRouter, HTTPException, Depends, Query, Response, File, UploadFile, Request, WebSocket, WebSocketDisconnect
from ..security.auth import verify_authenticated
try:
    from fastapi_csrf_protect import CsrfProtect # type: ignore
except ImportError:
    class CsrfProtect: # type: ignore
        async def validate_csrf(self, request):
            return None
from .. import services
from ..inference.voice_orchestrator import voice_orchestrator, DeviceTier

logger = get_logger("VoiceRouter")

router = APIRouter(tags=["Voice & Audio"])


def _clean_text_for_tts(text: str) -> str:
    """Strips Markdown syntax, special symbols, and quotes to produce clean, natural text for Kokoro TTS."""
    if not text:
        return ""
    # Strip Markdown links [text](url) -> text
    clean = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    # Strip Markdown bold/italic/strikethrough/headers (*, _, ~, #)
    clean = re.sub(r'[\*_~#]', '', clean)
    # Strip quotation marks, backticks, and bracket symbols
    clean = re.sub(r'[`"\'\[\]]', '', clean)
    # Normalize multiple whitespace
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean

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

    active_cognition_task: Optional[asyncio.Task] = None

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

                                # Cancel any previous zombie cognition/TTS stream task
                                if active_cognition_task and not active_cognition_task.done():
                                    active_cognition_task.cancel()
                                    try:
                                        await active_cognition_task
                                    except asyncio.CancelledError:
                                        pass

                                # Route to ModelRouter for LCE / Failover cognition
                                if final.get("requires_cognition", True) and auto_submit and services.router:
                                    async def _stream_tts_cognition(prompt_text: str):
                                        from ..inference.voice_orchestrator import voice_orchestrator as orch
                                        from ..security.memory_offloader import record_activity
                                        full_text_list = []
                                        sentence_buffer = []

                                        soul = getattr(services.orchestrator, "_cached_soul", {}) or {}
                                        voice_profile: str = str(soul.get("voiceProfile") or "af_bella")

                                        try:
                                            if services.router is not None:
                                                async for chunk in services.router.get_response_stream(prompt_text):
                                                    full_text_list.append(chunk)
                                                    sentence_buffer.append(chunk)

                                                    current_raw = "".join(sentence_buffer).strip()
                                                    words = current_raw.split()

                                                    # Check for sentence or micro-clause boundary (colons, commas, periods) when at least 4 words exist
                                                    if any(punct in chunk for punct in [".", "!", "?", "\n"]) or (len(words) >= 4 and any(clause_punct in chunk for clause_punct in [",", ";", ":"])):
                                                        clean_sentence = _clean_text_for_tts(current_raw)
                                                        if clean_sentence:
                                                            record_activity()
                                                            tts_result = await orch.synthesize_response(clean_sentence, voice_profile)
                                                            if tts_result.get("type") == "audio_pcm" and tts_result.get("data"):
                                                                await websocket.send_bytes(tts_result["data"])
                                                        sentence_buffer = []

                                            # Process remaining text in buffer
                                            remaining_raw = "".join(sentence_buffer).strip()
                                            clean_remaining = _clean_text_for_tts(remaining_raw)
                                            if clean_remaining:
                                                record_activity()
                                                tts_result = await orch.synthesize_response(clean_remaining, voice_profile)
                                                if tts_result.get("type") == "audio_pcm" and tts_result.get("data"):
                                                    await websocket.send_bytes(tts_result["data"])

                                            cognition_result = "".join(full_text_list)
                                            await websocket.send_json({
                                                "type": "cognition",
                                                "text": cognition_result,
                                                "is_final": True,
                                            })
                                        except asyncio.CancelledError:
                                            logger.info("[VOICE STREAM] Cognition/TTS task cancelled by new utterance or disconnect.")

                                    active_cognition_task = asyncio.create_task(_stream_tts_cognition(final["text"]))

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

    except (WebSocketDisconnect, RuntimeError, asyncio.CancelledError) as e:
        if active_cognition_task and not active_cognition_task.done():
            active_cognition_task.cancel()
        if isinstance(e, WebSocketDisconnect) or "Cannot call" in str(e):
            logger.info("[VOICE STREAM] Client disconnected.")
        else:
            logger.error(f"[VOICE STREAM] Error: {e}")
            try:
                await websocket.close(code=1011, reason=str(e))
            except Exception:
                pass
    except Exception as e:
        if active_cognition_task and not active_cognition_task.done():
            active_cognition_task.cancel()
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

