
from fastapi import APIRouter, HTTPException, Depends, Body, Request
from ..security.auth import verify_authenticated
from .. import services
from ..logging_config import get_logger

logger = get_logger("GeminiRouter")

router = APIRouter(tags=["Gemini Proxy"])

@router.post("/gemini/proxy", dependencies=[Depends(verify_authenticated)])
async def gemini_proxy(
    request: Request,
    prompt: str = Body(...),
    complexity: str = Body("MEDIUM"),
    privacy_level: str = Body("PUBLIC")
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

        # Route to the local Gemma 4 model (or failover)
        response = await services.router.get_response(
            prompt=prompt,
            system_instruction=system_instruction,
            complexity=complexity,
            privacy_level=privacy_level
        )
        return {"result": response}
    except Exception as e:
        logger.error(f"[ GEMINI_PROXY_ERROR ]: {e}")
        raise HTTPException(status_code=500, detail=str(e))
