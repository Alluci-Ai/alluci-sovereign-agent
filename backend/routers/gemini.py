
from typing import Optional, Dict, Any, Literal
from fastapi import APIRouter, HTTPException, Depends, Body, Request
from fastapi.responses import StreamingResponse
from ..security.auth import verify_authenticated
from .. import services
from ..logging_config import get_logger

logger = get_logger("GeminiRouter")

router = APIRouter(tags=["Gemini Proxy"])

@router.post("/gemini/proxy", dependencies=[Depends(verify_authenticated)])
async def gemini_proxy(
    request: Request,
    prompt: str = Body(...),
    complexity: Literal["LOW", "MEDIUM", "HIGH"] = Body("MEDIUM"),
    privacy_level: Literal["PUBLIC", "SENSITIVE", "AIRGAPPED"] = Body("PUBLIC"),
    inference_mode: Literal["LOCAL", "CLOUD", "TACTICAL", "HYBRID"] = Body("HYBRID"),
    session_id: Optional[str] = Body(None)
):
    """
    Proxies requests to the local Gemma 4 model or fallback providers.
    Bypasses the need for a client-side Google API key by using the Sovereign LCE.
    """
    if not services.router:
        raise HTTPException(status_code=503, detail="Inference router not ready")
    
    try:
        # Fetch the full Soul Manifest context for personality injection
        system_instruction = ""
        if services.orchestrator:
            system_instruction = await services.orchestrator._build_system_context()

        # Attempt Chat Auto-Dispatch first
        if services.orchestrator:
            dispatch_msg = await services.orchestrator.attempt_auto_dispatch(prompt)
            if dispatch_msg:
                return {"result": dispatch_msg}

        # Route to the local Gemma 4 model (or failover)
        response = await services.router.get_response(
            prompt=prompt,
            system_instruction=system_instruction,
            complexity=complexity,
            privacy_level=privacy_level,
            inference_mode=inference_mode,
            session_id=session_id
        )
        return {"result": response}
    except Exception as e:
        logger.error(f"[ GEMINI_PROXY_ERROR ]: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/gemini/proxy/stream", dependencies=[Depends(verify_authenticated)])
async def gemini_proxy_stream(
    request: Request,
    prompt: str = Body(...),
    complexity: Literal["LOW", "MEDIUM", "HIGH"] = Body("MEDIUM"),
    privacy_level: Literal["PUBLIC", "SENSITIVE", "AIRGAPPED"] = Body("PUBLIC"),
    inference_mode: Literal["LOCAL", "CLOUD", "TACTICAL", "HYBRID"] = Body("HYBRID"),
    session_id: Optional[str] = Body(None)
):
    """
    Proxies requests to the local Gemma 4 model or fallback providers with SSE token streaming.
    """
    if not services.router:
        raise HTTPException(status_code=503, detail="Inference router not ready")
    
    try:
        system_instruction = ""
        if services.orchestrator:
            system_instruction = await services.orchestrator._build_system_context()

        async def event_generator():
            import json
            
            # Attempt Chat Auto-Dispatch first
            if services.orchestrator:
                dispatch_msg = await services.orchestrator.attempt_auto_dispatch(prompt)
                if dispatch_msg:
                    yield f"data: {json.dumps({'text': dispatch_msg})}\n\n"
                    return
                    
            try:
                async for chunk in services.router.get_response_stream(
                    prompt=prompt,
                    system_instruction=system_instruction,
                    complexity=complexity,
                    privacy_level=privacy_level,
                    inference_mode=inference_mode,
                    session_id=session_id
                ):
                    yield f"data: {json.dumps({'text': chunk})}\n\n"
            except Exception as e:
                logger.error(f"[ STREAM_GENERATOR_ERROR ]: {e}")
                yield f"data: {json.dumps({'text': f'[ ERROR ]: {str(e)}'})}\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")
    except Exception as e:
        logger.error(f"[ GEMINI_PROXY_STREAM_ERROR ]: {e}")
        raise HTTPException(status_code=500, detail=str(e))
