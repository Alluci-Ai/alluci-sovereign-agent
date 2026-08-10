
from typing import Optional, Literal, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Body, Request
from fastapi.responses import StreamingResponse
from ..security.auth import verify_authenticated
from .. import services
from ..logging_config import get_logger

logger = get_logger("GeminiRouter")
router = APIRouter(tags=["Gemini Proxy"])

import base64
import re
import io
import asyncio
import uuid
import time
from ..utils.doc_parser import extract_text_from_file_payload

async def _check_local_research_reports(prompt: str) -> Optional[str]:
    """
    Scans artifacts/research/*/deep_research_report.md on disk when prompt
    explicitly requests a research report or dossier, registering it as an ArtifactRecord
    and broadcasting an artifact.open event to slide open the side panel.
    """
    body_lower = prompt.lower()
    
    # Negative guardrail keywords: Never intercept educational, skill, or code analysis prompts
    exclude_keywords = ["skill", "hcd", "framework", "json", "code", "mindset", "methodology", "ethnographic", "concept", "definition"]
    if any(kw in body_lower for kw in exclude_keywords):
        return None
        
    action_verbs = ["show", "pull", "open", "display", "read", "view", "fetch"]
    target_nouns = ["report", "dossier"]
    
    is_explicit_request = any(verb in body_lower for verb in action_verbs) and any(noun in body_lower for noun in target_nouns)
    if is_explicit_request:
        import os, glob
        from .sessions import WORKSPACE_DIR
        found_reports = []

        # 1. Primary Search Location: ./workspace/artifacts/research/
        primary_base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "workspace", "artifacts", "research"))
        if os.path.exists(primary_base):
            for p in glob.glob(os.path.join(primary_base, "*", "deep_research_report.md")):
                found_reports.append((os.path.getmtime(p), p))

        # 2. Legacy Fallback Locations
        for search_agent in ["a32eb383", "rocco", "executive"]:
            research_base = os.path.join(WORKSPACE_DIR, search_agent, "artifacts", "research")
            if os.path.exists(research_base):
                for p in glob.glob(os.path.join(research_base, "*", "deep_research_report.md")):
                    found_reports.append((os.path.getmtime(p), p))

        if found_reports:
            # Topic-Aware Matching: Check if prompt contains words matching folder name (e.g. "sovereign")
            matched_report = None
            for _, rpath in found_reports:
                folder_name = os.path.basename(os.path.dirname(rpath)).lower()
                # Check for significant words (>3 chars) in prompt
                prompt_words = [w for w in body_lower.replace('"', '').replace("'", '').split() if len(w) > 3 and w not in action_verbs and w not in target_nouns]
                if any(pw in folder_name for pw in prompt_words):
                    matched_report = rpath
                    break

            if not matched_report:
                found_reports.sort(key=lambda x: x[0], reverse=True)
                matched_report = found_reports[0][1]

            latest_path = matched_report
            try:
                with open(latest_path, "r", encoding="utf-8") as rf:
                    rep_content = rf.read()
                
                folder_label = os.path.basename(os.path.dirname(latest_path))
                topic_title = folder_label.replace("_", " ").strip().title() if folder_label and folder_label != "artifacts" else "Sovereign Intelligence"

                # 1. Attempt DB creation (Zero-Duplication Pointer)
                import uuid
                art_id = f"art_{uuid.uuid4().hex[:12]}"
                try:
                    from .artifacts import create_artifact
                    art_payload = {
                        "title": f"Deep Research Report: {topic_title}",
                        "kind": "text",
                        "mimeType": "text/markdown",
                        "content": rep_content,
                        "metadata": {"agent": "rocco", "topic": topic_title, "file_path": latest_path}
                    }
                    art_res = await create_artifact(art_payload)
                    if isinstance(art_res, dict) and "id" in art_res:
                        art_id = art_res["id"]
                except Exception as db_err:
                    logger.warning(f"[ReportReader] DB pointer registration note (using direct disk payload): {db_err}")

                # 2. Direct Disk-to-Panel WebSocket Broadcast (Zero-DB-Dependency)
                from .. import services
                if services.orchestrator and hasattr(services.orchestrator, "ws_gateway") and services.orchestrator.ws_gateway:
                    await services.orchestrator.ws_gateway.broadcast_event('artifact.open', {
                        "type": "artifact.open",
                        "artifactId": art_id,
                        "title": f"Deep Research Report: {topic_title}",
                        "kind": "text",
                        "content": rep_content,
                        "mimeType": "text/markdown",
                        "source": "system"
                    })

                return f"Hello JJ. I have retrieved the **{topic_title}** report and opened it for you in your Artifact Workspace.\n\nYou can view, navigate, zoom, or download the full dossier in the side panel."
            except Exception as read_err:
                logger.error(f"[ReportReader] Failed to read report from disk: {read_err}")
    return None


def _process_attached_files(prompt: str, files: Optional[List[Dict[str, Any]]] = None) -> str:
    """Decodes and appends attached file contents (TXT, MD, PDF, JSON, CSV, DOCX, Code) to prompt context with KV cache safety bounds."""
    if not files:
        return prompt

    MAX_FILE_CHARS = 30000
    appended_text = prompt
    for file_obj in files:
        file_name = file_obj.get("name", "attached_file.txt")
        file_data = file_obj.get("data", "")
        file_mime = file_obj.get("mimeType", "").lower()

        decoded_content = extract_text_from_file_payload(file_name, file_data, file_mime)

        if decoded_content:
            if len(decoded_content) > MAX_FILE_CHARS:
                decoded_content = decoded_content[:MAX_FILE_CHARS] + f"\n... [ATTACHED FILE TRUNCATED AT {MAX_FILE_CHARS:,} CHARACTERS TO FIT KV CACHE BUDGET] ..."
            appended_text += f"\n\n--- [ATTACHED FILE: {file_name}] ---\n{decoded_content.strip()}\n--- [END ATTACHED FILE] ---"

    return appended_text


async def _intercept_memory_deletion_request(prompt: str) -> Optional[str]:
    """
    Detects memory deletion intent in chat prompts (e.g. 'delete memory', 'purge memory', 'scrub', 'delete [imessage]')
    and executes immediate database deletion via hlsm_manager.delete_by_pattern(), returning empirical results.
    """
    body_lower = prompt.lower()
    delete_keywords = [
        "delete memory", "delete memories", "purge memory", "purge memories", 
        "scrub memory", "scrub memories", "delete any [imessage]", "delete [imessage]",
        "delete imessage", "purge imessage", "scrub imessage"
    ]
    
    is_deletion_req = any(dk in body_lower for dk in delete_keywords) or (
        ("delete" in body_lower or "purge" in body_lower or "scrub" in body_lower or "clear" in body_lower) and
        ("memory" in body_lower or "memories" in body_lower or "hlsm" in body_lower or "imessage" in body_lower)
    )

    if not is_deletion_req:
        return None

    phone_match = re.search(r'\+?\d{1,3}[\s\-\.]?\(?\d{3}\)?[\s\-\.]?\d{3}[\s\-\.]?\d{4}', prompt)
    pattern_to_delete = ""
    if phone_match:
        pattern_to_delete = phone_match.group(0).strip()
    else:
        pattern_match = re.search(r'(?:from|pattern|tagged|matching|containing|for)\s+[\'"]?([^\'"\.\,\?\!\n]+)', prompt, re.IGNORECASE)
        if pattern_match:
            pattern_to_delete = pattern_match.group(1).strip()
        else:
            pattern_to_delete = re.sub(r'^(hello alluci,?\s*|can you search through your h-lsm memories and delete\s*|delete memory\s*|purge memory\s*)', '', prompt, flags=re.IGNORECASE).strip()

    if not pattern_to_delete:
        return None

    if hasattr(services, "hlsm_manager") and services.hlsm_manager:
        try:
            res = await services.hlsm_manager.delete_by_pattern(pattern_to_delete)
            total = res.get("total_deleted", 0)
            if total > 0:
                return (
                    f"✅ **H-LSM Memory Purge Complete**\n\n"
                    f"Successfully scanned all topological memory layers and permanently deleted **{total} matching memory entries** for `{pattern_to_delete}`.\n\n"
                    f"- **L0 Working Memory:** {res.get('deleted_l0', 0)} entries purged\n"
                    f"- **L1 Episodic Memory:** {res.get('deleted_l1', 0)} entries purged\n"
                    f"- **L2 Semantic Memory:** {res.get('deleted_l2', 0)} entries purged\n"
                    f"- **L3 Knowledge Graph:** {res.get('deleted_l3', 0)} entries purged"
                )
            else:
                return f"🔍 **H-LSM Memory Scan Complete**\n\nScanned memory layers for `{pattern_to_delete}`, but found 0 matching memory entries to delete."
        except Exception as err:
            logger.error(f"[GeminiRouter] Memory deletion interceptor error: {err}")
            return f"❌ **H-LSM Memory Purge Error:** Failed to execute memory deletion: {err}"

    return None


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
        # 1. Fast Memory Deletion Interceptor Check (< 5ms)
        mem_purge_reply = await _intercept_memory_deletion_request(prompt)
        if mem_purge_reply:
            return {"result": mem_purge_reply}

        # 2. Fast Local Hard Drive File Reader Check (< 50ms)
        local_report = _check_local_research_reports(effective_prompt)
        if local_report:
            return {"result": local_report}

        # 3. Fetch system context (lightweight capability index)
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

        msg_id = f"msg_{uuid.uuid4().hex[:12]}"
        analytics = getattr(services, "analytics", None)
        if analytics:
            analytics.record_message(session_key=session_id or "web_chat", role="user", content=prompt)
            analytics.record_message(session_key=session_id or "web_chat", role="assistant", content=response)
        if hasattr(services, "hlsm_manager") and services.hlsm_manager:
            asyncio.create_task(services.hlsm_manager.ingest_distilled_intent(session_key=session_id or "web_chat", message_id=msg_id, prompt=prompt, response=response))
            if files:
                for f in files:
                    fn, fdata, fmime = f.get("name", "attachment"), f.get("data", ""), f.get("mimeType", "")
                    p_text = extract_text_from_file_payload(fn, fdata, fmime)
                    if p_text and not p_text.startswith(("[BINARY", "[UNSUPPORTED")):
                        asyncio.create_task(services.hlsm_manager.ingest_document_payload(filename=fn, content=p_text, session_key=session_id or "web_chat"))

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
        # 1. Fast Memory Deletion Interceptor Check (< 5ms)
        mem_purge_reply = await _intercept_memory_deletion_request(prompt)

        # 2. Fast Local Hard Drive File Reader Check (< 50ms)
        local_report = await _check_local_research_reports(effective_prompt)

        system_instruction = ""
        orch = services.orchestrator
        if orch is not None and not local_report and not mem_purge_reply:
            system_instruction, _ = await orch._build_system_context(compact_index=True)

        # 3. 3-Layer Parallel Intent Switchboard (< 5ms Check)
        orchestrator_reply = None
        if orch is not None and not local_report and not mem_purge_reply:
            try:
                import re
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

            if mem_purge_reply:
                yield f"data: {json.dumps({'text': mem_purge_reply})}\n\n"
                return

            if local_report:
                yield f"data: {json.dumps({'text': local_report})}\n\n"
                return

            if orchestrator_reply:
                yield f"data: {json.dumps({'text': orchestrator_reply})}\n\n"
                return

            accumulated_chunks = []
            try:
                async for chunk in router_inst.get_response_stream(
                    prompt=effective_prompt,
                    system_instruction=system_instruction,
                    complexity=complexity,
                    privacy_level=privacy_level,
                    inference_mode=inference_mode,
                    session_id=session_id
                ):
                    accumulated_chunks.append(chunk)
                    yield f"data: {json.dumps({'text': chunk})}\n\n"
            except Exception as e:
                logger.error(f"[ STREAM_GENERATOR_ERROR ]: {e}")
                yield f"data: {json.dumps({'text': f'[ ERROR ]: {str(e)}'})}\n\n"

            # Async background recording of message_log & H-LSM intent pointers
            full_response = "".join(accumulated_chunks)
            if full_response.strip():
                try:
                    msg_id = f"msg_{uuid.uuid4().hex[:12]}"
                    analytics = getattr(services, "analytics", None)
                    if analytics:
                        analytics.record_message(session_key=session_id or "web_chat", role="user", content=prompt)
                        analytics.record_message(session_key=session_id or "web_chat", role="assistant", content=full_response)
                    if hasattr(services, "hlsm_manager") and services.hlsm_manager:
                        asyncio.create_task(services.hlsm_manager.ingest_distilled_intent(session_key=session_id or "web_chat", message_id=msg_id, prompt=prompt, response=full_response))
                        if files:
                            for f in files:
                                fn, fdata, fmime = f.get("name", "attachment"), f.get("data", ""), f.get("mimeType", "")
                                p_text = extract_text_from_file_payload(fn, fdata, fmime)
                                if p_text and not p_text.startswith(("[BINARY", "[UNSUPPORTED")):
                                    asyncio.create_task(services.hlsm_manager.ingest_document_payload(filename=fn, content=p_text, session_key=session_id or "web_chat"))
                except Exception as rec_err:
                    logger.debug(f"[GeminiRouter] Post-stream memory recording notice: {rec_err}")

        return StreamingResponse(event_generator(), media_type="text/event-stream")
    except Exception as e:
        logger.error(f"[ GEMINI_PROXY_STREAM_ERROR ]: {e}")
        raise HTTPException(status_code=500, detail=str(e))
