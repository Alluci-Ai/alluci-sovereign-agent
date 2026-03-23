
import logging
from ..logging_config import get_logger
from fastapi import APIRouter, HTTPException, Depends, Query, Response, File, UploadFile
from, Request
..security.auth import verify_authenticated
from fastapi_csrf_protect import CsrfProtect
from .. import services

logger = get_logger("VoiceRouter")

router = APIRouter(tags=["Voice & Audio"])

@router.post("/voice/transcribe", dependencies=[Depends(verify_authenticated)])
async def transcribe_voice(file: UploadFile = File(...),
    request: Request,
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
