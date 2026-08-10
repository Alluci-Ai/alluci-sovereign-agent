
from typing import Optional, Literal, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Body, Request
from fastapi.responses import StreamingResponse
from ..security.auth import verify_authenticated
from .. import services
from ..logging_config import get_logger

logger = get_logger("GeminiRouter")

router = APIRouter(tags=["Gemini Proxy"])

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

import base64
import re
import io

def _extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """Extracts text streams from PDF raw bytes cleanly without requiring external binary tools."""
    text_chunks = []
    try:
        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        for page in reader.pages:
            t = page.extract_text()
            if t:
                text_chunks.append(t)
        if text_chunks:
            return "\n".join(text_chunks)
    except Exception:
        pass

    try:
        matches = re.findall(rb'\((.*?)\)', pdf_bytes)
        clean_strings = [
            m.decode('utf-8', errors='ignore').strip() 
            for m in matches 
            if len(m) > 2 and any(c.isalnum() for c in m.decode('utf-8', errors='ignore'))
        ]
        if clean_strings:
            return " ".join(clean_strings)
    except Exception:
        pass

    return pdf_bytes.decode('utf-8', errors='ignore')


def _process_attached_files(prompt: str, files: Optional[List[Dict[str, Any]]] = None) -> str:
    """Decodes and appends attached file contents (TXT, MD, PDF, JSON, CSV, DOCX) to prompt context with KV cache safety bounds."""
    if not files:
        return prompt

    MAX_FILE_CHARS = 30000
    appended_text = prompt
    for file_obj in files:
        file_name = file_obj.get("name", "attached_file.txt")
        file_data = file_obj.get("data", "")
        file_mime = file_obj.get("mimeType", "").lower()

        decoded_content = ""
        if file_data:
            try:
                raw_bytes = base64.b64decode(file_data)
                is_pdf = file_mime == "application/pdf" or file_name.lower().endswith(".pdf") or raw_bytes.startswith(b"%PDF")
                if is_pdf:
                    decoded_content = _extract_text_from_pdf_bytes(raw_bytes)
                else:
                    decoded_content = raw_bytes.decode("utf-8", errors="replace")
            except Exception as e:
                logger.warning(f"[GeminiRouter] Could not decode base64 for file {file_name}: {e}")
                decoded_content = str(file_data)

        if decoded_content:
            if len(decoded_content) > MAX_FILE_CHARS:
                decoded_content = decoded_content[:MAX_FILE_CHARS] + f"\n... [ATTACHED FILE TRUNCATED AT {MAX_FILE_CHARS:,} CHARACTERS TO FIT KV CACHE BUDGET] ..."
            appended_text += f"\n\n--- [ATTACHED FILE: {file_name}] ---\n{decoded_content.strip()}\n--- [END ATTACHED FILE] ---"

    return appended_text


@router.post("/gemini/proxy", dependencies=[Depends(verify_authenticated)])
async def gemini_proxy(
    request: Request,
    prompt: str = Body(...),
    files: Optional[List[Dict[str, Any]]] = Body(None),
    complexity: Literal["LOW", "MEDIUM", "HIGH"] = Body("MEDIUM"),
    privacy_level: Literal["PUBLIC", "SENSITIVE", "AIRGAPPED"] = Body("PUBLIC"),
    inference_mode: Literal["LOCAL", "CLOUD", "TACTICAL", "HYBRID"] = Body("HYBRID"),
    session_id: Optional[str] = Body(None)
):
    """
    Proxies requests to local or cloud models with Single-Pass execution.
    """
    router_inst = services.router
    if not router_inst:
        raise HTTPException(status_code=503, detail="Inference router not ready")

    effective_prompt = _process_attached_files(prompt, files)

    try:
        # 1. Fast Local Hard Drive File Reader Check (< 50ms)
        local_report = _check_local_research_reports(effective_prompt)
        if local_report:
            return {"result": local_report}

        # 2. Fetch system context (lightweight capability index)
        system_instruction = ""
        if services.orchestrator:
            system_instruction, _ = await services.orchestrator._build_system_context()

        # Single-Pass Response Generation
        response = await router_inst.get_response(
            prompt=effective_prompt,
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
    files: Optional[List[Dict[str, Any]]] = Body(None),
    complexity: Literal["LOW", "MEDIUM", "HIGH"] = Body("MEDIUM"),
    privacy_level: Literal["PUBLIC", "SENSITIVE", "AIRGAPPED"] = Body("PUBLIC"),
    inference_mode: Literal["LOCAL", "CLOUD", "TACTICAL", "HYBRID"] = Body("HYBRID"),
    session_id: Optional[str] = Body(None)
):
    """
    Proxies requests to local or cloud models with Instant TTFT (< 10ms) SSE token streaming.
    """
    router_inst = services.router
    if not router_inst:
        raise HTTPException(status_code=503, detail="Inference router not ready")

    effective_prompt = _process_attached_files(prompt, files)

    try:
        # 1. Fast Local Hard Drive File Reader Check (< 50ms)
        local_report = _check_local_research_reports(effective_prompt)

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

                if any(ck in body_lower for ck in cancellation_keywords) and any(w in body_lower for w in ["dag", "run", "research", "pipeline", "execution"]):
                    orchestrator_reply = await orch.handle_user_message(effective_prompt)
                elif any(ak in body_lower for ak in action_keywords) or proceed_pattern:
                    orchestrator_reply = await orch.handle_user_message(effective_prompt)
                    logger.info(f"[GeminiRouter] Handled orchestrator auto-dispatch for prompt: '{prompt[:50]}...'")
            except Exception as dispatch_err:
                logger.debug(f"[GeminiRouter] Intent switchboard note: {dispatch_err}")

        async def event_generator():
            import json

            # Instant TTFT heartbeat signal to keep UI responsive
            yield f"data: {json.dumps({'text': '', 'status': 'Ingesting document & initializing skill context...'})}\n\n"

            if local_report:
                yield f"data: {json.dumps({'text': local_report})}\n\n"
                return

            if orchestrator_reply:
                yield f"data: {json.dumps({'text': orchestrator_reply})}\n\n"
                return

            try:
                async for chunk in router_inst.get_response_stream(
                    prompt=effective_prompt,
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
