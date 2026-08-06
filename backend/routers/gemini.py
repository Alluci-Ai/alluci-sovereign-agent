
from typing import Optional, Literal
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
def _check_local_research_reports(prompt: str) -> Optional[str]:
    """
    Scans artifacts/research/*/deep_research_report.md on disk when prompt
    explicitly requests a research report or dossier, returning the exact raw markdown.
    Uses compound phrase matching and negative guardrails to avoid out-of-context triggers.
    """
    body_lower = prompt.lower()
    
    # Negative guardrail keywords: Never intercept educational, skill, or code analysis prompts
    exclude_keywords = ["skill", "hcd", "framework", "json", "code", "mindset", "methodology", "ethnographic", "concept", "definition"]
    if any(kw in body_lower for kw in exclude_keywords):
        return None
        
    explicit_phrases = [
        "pull up the report", "show the report", "read the report", "open the report",
        "display the dossier", "view the research dossier", "show me the deep research report",
        "fetch latest research report", "open the deep research dossier", "show research dossier",
        "pull up research report"
    ]
    
    is_explicit_request = any(phrase in body_lower for phrase in explicit_phrases)
    if is_explicit_request:
        import os, glob
        from .sessions import WORKSPACE_DIR
        found_reports = []
        for search_agent in ["a32eb383", "rocco", "executive"]:
            research_base = os.path.join(WORKSPACE_DIR, search_agent, "artifacts", "research")
            if os.path.exists(research_base):
                pattern = os.path.join(research_base, "*", "deep_research_report.md")
                for p in glob.glob(pattern):
                    found_reports.append((os.path.getmtime(p), p))
            flat_p = os.path.join(WORKSPACE_DIR, search_agent, "artifacts", "deep_research_report.md")
            if os.path.exists(flat_p):
                found_reports.append((os.path.getmtime(flat_p), flat_p))

        if found_reports:
            found_reports.sort(key=lambda x: x[0], reverse=True)
            latest_path = found_reports[0][1]
            try:
                with open(latest_path, "r", encoding="utf-8") as rf:
                    rep_content = rf.read()
                file_url = f"file://{os.path.abspath(latest_path)}"
                folder_label = os.path.basename(os.path.dirname(latest_path))
                return f"### 📊 Retrieved Deep Research Report (`{folder_label}`)\n\nDirect dossier link: [{os.path.basename(latest_path)}]({file_url})\n\n---\n\n{rep_content.strip()}"
            except Exception as read_err:
                logger.error(f"[ReportReader] Failed to read report from disk: {read_err}")
    return None

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
    Proxies requests to local or cloud models with Single-Pass execution.
    """
    if not services.router:
        raise HTTPException(status_code=503, detail="Inference router not ready")
    
    try:
        # 1. Fast Local Hard Drive File Reader Check (< 50ms)
        local_report = _check_local_research_reports(prompt)
        if local_report:
            return {"result": local_report}

        # 2. Fetch system context (lightweight capability index)
        system_instruction = ""
        if services.orchestrator:
            system_instruction, _ = await services.orchestrator._build_system_context()

        # Single-Pass Response Generation
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
    Proxies requests to local or cloud models with Instant TTFT (< 10ms) SSE token streaming.
    """
    if not services.router:
        raise HTTPException(status_code=503, detail="Inference router not ready")
    
    try:
        # 1. Fast Local Hard Drive File Reader Check (< 50ms)
        local_report = _check_local_research_reports(prompt)

        system_instruction = ""
        orch = services.orchestrator
        if orch is not None and not local_report:
            system_instruction, _ = await orch._build_system_context(compact_index=True)

        # 2. 3-Layer Parallel Intent Switchboard (< 5ms Check)
        orchestrator_reply = None
        if orch is not None and not local_report:
            try:
                import asyncio, re
                body_lower = prompt.lower()
                action_keywords = ["rocco", "deep research", "deep web research", "spin up", "execute dag", "run script", "schedule cron", "scour the web"]
                proceed_pattern = bool(re.search(r'\b(proceed|approve|execute|\d+\s*runs?)\b', body_lower))
                cancellation_keywords = ["stop", "cancel", "abort", "halt", "terminate"]
                
                if any(ck in body_lower for ck in cancellation_keywords) and any(w in body_lower for w in ["dag", "run", "research", "pipeline", "execution", "this"]):
                    orchestrator_reply = await orch.handle_user_message(prompt)
                elif any(ak in body_lower for ak in action_keywords) or proceed_pattern:
                    orchestrator_reply = await orch.handle_user_message(prompt)
                    logger.info(f"[GeminiRouter] Handled orchestrator auto-dispatch for prompt: '{prompt[:50]}...'")
            except Exception as dispatch_err:
                logger.debug(f"[GeminiRouter] Intent switchboard note: {dispatch_err}")

        async def event_generator():
            import json

            if local_report:
                yield f"data: {json.dumps({'text': local_report})}\n\n"
                return

            if orchestrator_reply:
                yield f"data: {json.dumps({'text': orchestrator_reply})}\n\n"
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
