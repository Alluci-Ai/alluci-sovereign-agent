
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

    # Execution/Creation Guardrail: Never intercept commands attempting to trigger a NEW research run
    execution_keywords = ["do deep", "do web", "conduct", "run", "deep research", "deep web research", "scour", "investigate", "rocco", "spin up", "execute dag", "research grants", "grants"]
    if any(ek in body_lower for ek in execution_keywords):
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
    Detects memory deletion intent in chat prompts using 3 Hard Security Guards and triggers
    a mandatory Human-in-the-Loop (HITL) Executive Approval Gate prior to memory modification.
    """
    import re, uuid
    body_lower = prompt.lower()

    # Guard 1: Technical & Code Context Bypass (html, clear_cache(), code, scripts, apps)
    technical_code_terms = ["cache", "mx.metal", "clear_cache", "html", "code", "app", "dashboard", "script", "css", "component"]
    if any(t in body_lower for t in technical_code_terms):
        return None  # Bypass memory interceptor completely!

    # Guard 2: Flexible Regex Intent Matching for Memory Purge Requests
    purge_regex = r'\b(delete|purge|scrub|clear|forget|wipe|remove)\b.*\b(memor(y|ies)|h-lsm|imessage|signal|slack|telegram|whatsapp|email)\b'
    if not re.search(purge_regex, body_lower):
        return None

    # Pattern Extraction: Extract channel tags, phone numbers, or target filters
    channel_tag = ""
    tag_match = re.search(r'\[(IMESSAGE|SIGNAL|SLACK|TELEGRAM|WHATSAPP|SMS|EMAIL)\]', prompt, re.IGNORECASE)
    if tag_match:
        channel_tag = f"[{tag_match.group(1).upper()}]"

    phone_match = re.search(r'\+?\d{1,3}[\s\-\.]?\(?\d{3}\)?[\s\-\.]?\d{3}[\s\-\.]?\d{4}|\b\d{5,6}\b', prompt)
    extracted_target = ""
    if phone_match:
        extracted_target = phone_match.group(0).strip().rstrip(":")
    else:
        pattern_match = re.search(r'(?:from|pattern|tagged|matching|containing|for)\s+[\'"]?([^\'"\.\,\?\!\n]+)', prompt, re.IGNORECASE)
        if pattern_match:
            extracted_target = pattern_match.group(1).strip().rstrip(":")
        else:
            extracted_target = re.sub(r'^(hello alluci,?\s*|can you search through your h-lsm memories and delete\s*|delete memory\s*|delete memories\s*|purge memory\s*|purge memories\s*)', '', prompt, flags=re.IGNORECASE).strip().rstrip(":")

    # Build final composite pattern to delete (preserving channel tag if present)
    if channel_tag and extracted_target:
        pattern_to_delete = f"{channel_tag} {extracted_target}".strip()
    elif extracted_target:
        pattern_to_delete = extracted_target
    elif channel_tag:
        pattern_to_delete = channel_tag
    else:
        pattern_to_delete = prompt.strip()

    # Guard 3: Minimum 3-Character Pattern Guard & Stop-Word Filtering
    stop_words = ["a", "an", "the", "for", "and", "all", "in", "of", "to", "or", "is", "my", "me", "me."]
    if len(pattern_to_delete) < 3 or pattern_to_delete.lower() in stop_words:
        logger.warning(f"[MemoryGuard] Blocked unsafe short memory deletion pattern: '{pattern_to_delete}'")
        return None

    # HITL Gate: Emit Executive Approval Request instead of executing autonomously
    from .. import services
    if services.orchestrator and hasattr(services.orchestrator, "ws_gateway") and services.orchestrator.ws_gateway:
        req_id = f"approval_mem_{uuid.uuid4().hex[:8]}"
        await services.orchestrator.ws_gateway.broadcast_event('security.resolution_required', {
            "type": "security.resolution_required",
            "task_id": req_id,
            "approval_id": req_id,
            "action": "HLSM_MEMORY_PURGE",
            "exception_type": "HLSM_MEMORY_PURGE",
            "pattern": pattern_to_delete,
            "metadata": {"pattern": pattern_to_delete},
            "title": "H-LSM Memory Purge Approval Required",
            "description": f"Alluci is requesting permission to scan and permanently delete all H-LSM memory entries matching pattern: '{pattern_to_delete}'.",
            "impact": "Permanent deletion of matching entries across L0 Working, L1 Episodic, L2 Semantic, and L3 Knowledge Graph layers."
        })
        return (
            f"⚠️ **H-LSM Executive Approval Required**\n\n"
            f"Scanning and memory deletion for pattern `{pattern_to_delete}` requires explicit human-in-the-loop verification.\n\n"
            f"Please approve or decline the pending approval request modal to execute memory deletion."
        )

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
        local_report = await _check_local_research_reports(effective_prompt)
        if local_report:
            return {"result": local_report}

        # 3. Fetch system context (lightweight capability index)
        system_instruction = ""
        if services.orchestrator:
            ctx_res = await services.orchestrator._build_system_context()
            system_instruction = ctx_res[0] if isinstance(ctx_res, (tuple, list)) else str(ctx_res)

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
            ctx_res = await orch._build_system_context(compact_index=True)
            system_instruction = ctx_res[0] if isinstance(ctx_res, (tuple, list)) else str(ctx_res)

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
            chat_intro_sent = False
            has_artifact_block = False
            body_lower = prompt.lower()
            is_artifact_req = any(w in body_lower for w in ["artifact", "slide deck", "presentation", "html app", "web app", "code file"])

            if is_artifact_req:
                # 1. Immediately stream start status message when artifact task begins
                yield f"data: {json.dumps({'text': 'I am generating your Executive Presentation in standalone HTML5/CSS and will surface it in your Artifact Workspace when it finishes.'})}\n\n"
                chat_intro_sent = True

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
                    full_so_far = "".join(accumulated_chunks)

                    # Check if stream entered artifact payload block
                    has_artifact_block = "# ARTIFACT:" in full_so_far or "```artifact" in full_so_far or "## SLIDE 1" in full_so_far

                    if not is_artifact_req and not has_artifact_block:
                        yield f"data: {json.dumps({'text': chunk})}\n\n"

                # 2. Yield final completion status message when artifact task finishes
                if is_artifact_req or has_artifact_block:
                    done_text = "\n\nYour Executive Presentation is ready and surfaced in your Artifact Workspace."
                    yield f"data: {json.dumps({'text': done_text})}\n\n"

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
                    
                    # Intercept dynamic artifacts (presentation, html, code, text) and surface side panel
                    asyncio.create_task(_process_dynamic_artifact_block(full_response, prompt))
                except Exception as post_err:
                    logger.debug(f"[GeminiRouter] Post-stream artifact/memory note: {post_err}")

        return StreamingResponse(event_generator(), media_type="text/event-stream")
    except Exception as e:
        logger.error(f"[ GEMINI_PROXY_STREAM_ERROR ]: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _clean_inline_markdown(text: str) -> str:
    """
    Transforms raw Markdown bold/italic syntax and stray asterisks into clean HTML <strong> tags.
    """
    import re
    # 1. Clean bold syntax: **text** -> <strong>text</strong>
    t = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
    # 2. Clean mismatched/nested bold: *text:** or *text:* or **text:* -> <strong>text</strong>
    t = re.sub(r'\*+([^*:]+)(?::\*+|\*\*|\*)', r'<strong>\1</strong>', t)
    # 3. Clean remaining italic markers: *text* -> <em>text</em>
    t = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', t)
    # 4. Strip any remaining stray leading/trailing asterisks or colon-asterisk artifacts
    t = re.sub(r'^\*+\s*', '', t)
    t = re.sub(r'\s*\*+$', '', t)
    return t.strip()


def _build_html5_presentation_deck(title: str, content_raw: str) -> str:
    """
    Converts raw slide text into a self-contained, standalone HTML5 presentation slide deck
    with embedded responsive CSS variables (light/dark HIG mode) and glassmorphism styling.
    """
    import re
    if content_raw.strip().startswith("<!DOCTYPE html") or content_raw.strip().startswith("<html"):
        return content_raw

    # Locate the first actual slide header (e.g. ## SLIDE 1, # Title, or first '---' followed by '#')
    first_slide_match = re.search(r'(?:---|##\s*SLIDE\s*1|##\s*Slide\s*1|#\s*TITLE:|#\s*Title:|\n(?=##\s+[A-Z]))', content_raw, flags=re.I)
    if first_slide_match:
        clean_text = content_raw[first_slide_match.start():].strip()
    else:
        clean_text = content_raw.strip()

    # Strip leading '---' or '# ARTIFACT:' metadata lines
    clean_text = re.sub(r'^(---|#\s*ARTIFACT:[^\n]*|\n)+', '', clean_text, flags=re.I).strip()
    slides_raw = re.split(r'\n(?=---|## SLIDE|## Slide)', clean_text)
    
    slides_html = []
    for idx, slide_block in enumerate(slides_raw):
        block_clean = slide_block.replace("---", "").strip()
        if not block_clean:
            continue
        
        lines = [l.strip() for l in block_clean.split("\n") if l.strip()]
        slide_title = f"Slide {idx + 1}"
        eyebrow = "EXECUTIVE STRATEGY 2026"
        
        if lines and lines[0].startswith("#"):
            slide_title = re.sub(r'^#+\s*(SLIDE\s*\d+:?)?\s*', '', lines[0], flags=re.I).strip()
            slide_title = _clean_inline_markdown(slide_title)
        
        if idx == 0:
            eyebrow = "STRATEGIC IMPERATIVE"
        elif "spectrum" in slide_title.lower() or "utility" in slide_title.lower():
            eyebrow = "CORE PARADIGM SPECTRUM"
        elif "technical" in slide_title.lower() or "stack" in slide_title.lower():
            eyebrow = "SOVEREIGN ARCHITECTURE MANDATE"
        elif "financial" in slide_title.lower() or "roadmap" in slide_title.lower():
            eyebrow = "FINANCIAL & CAPITAL HORIZON"

        body_lines = lines[1:] if lines and lines[0].startswith("#") else lines
        cards_html = []
        current_card_title = "Core Directives"
        current_bullets = []

        for line in body_lines:
            if line.startswith("###") or line.startswith("**1.") or line.startswith("**2.") or line.startswith("**3.") or line.startswith("**I.") or line.startswith("**II.") or line.startswith("**III.") or line.startswith("**Phase"):
                if current_bullets:
                    b_html = "".join([f"<li>{b}</li>" for b in current_bullets])
                    cards_html.append(f'<div class="card"><h3>{_clean_inline_markdown(current_card_title)}</h3><ul>{b_html}</ul></div>')
                    current_bullets = []
                sec_raw = re.sub(r'^(###|\*\*[\w\.]+\*\*)\s*', '', line).replace('**', '').strip()
                current_card_title = _clean_inline_markdown(sec_raw)
            elif line.startswith("*") or line.startswith("-"):
                b_text = re.sub(r'^[\*\-]\s*', '', line)
                b_formatted = _clean_inline_markdown(b_text)
                if b_formatted:
                    current_bullets.append(b_formatted)
            elif ":" in line and not line.startswith("#"):
                b_formatted = _clean_inline_markdown(line)
                if b_formatted:
                    current_bullets.append(b_formatted)

        if current_bullets:
            b_html = "".join([f"<li>{b}</li>" for b in current_bullets])
            cards_html.append(f'<div class="card"><h3>{_clean_inline_markdown(current_card_title)}</h3><ul>{b_html}</ul></div>')

        grid_content = "".join(cards_html) if cards_html else f'<div class="card"><p>{_clean_inline_markdown(block_clean)}</p></div>'

        slides_html.append(f'''
        <section class="slide" id="slide-{idx+1}">
          <div class="slide-header">
            <div class="eyebrow">✦ {eyebrow}</div>
            <h2>{slide_title}</h2>
          </div>
          <div class="grid">
            {grid_content}
          </div>
          <div class="slide-footer">
            <span>ALLUCI SOVEREIGN AGENT • TECHNICAL STRATEGY</span>
            <span class="slide-counter">SLIDE 0{idx+1} / 0{len(slides_raw)}</span>
          </div>
        </section>
        ''')

    all_slides = "".join(slides_html)
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
  :root {{
    --bg-primary: #070B12;
    --bg-card: rgba(255, 255, 255, 0.03);
    --border-card: rgba(255, 255, 255, 0.08);
    --text-primary: #FFFFFF;
    --text-secondary: #94A3B8;
    --accent: #10B981;
    --accent-blue: #38BDF8;
  }}
  @media (prefers-color-scheme: light) {{
    :root {{
      --bg-primary: #F8FAFC;
      --bg-card: #FFFFFF;
      --border-card: #E2E8F0;
      --text-primary: #0F172A;
      --text-secondary: #475569;
      --accent: #059669;
      --accent-blue: #0284C7;
    }}
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; padding: 24px;
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", Roboto, sans-serif;
    background: var(--bg-primary);
    color: var(--text-primary);
  }}
  .slide-deck {{ display: flex; flex-direction: column; gap: 32px; max-width: 1100px; margin: 0 auto; }}
  .slide {{
    background: var(--bg-card);
    border: 1px solid var(--border-card);
    border-radius: 16px;
    padding: 32px;
    box-shadow: 0 20px 50px rgba(0,0,0,0.3);
    backdrop-filter: blur(12px);
  }}
  .slide-header {{ margin-bottom: 20px; }}
  .eyebrow {{
    font-family: monospace; font-size: 11px; letter-spacing: 0.2em;
    text-transform: uppercase; color: var(--accent); font-weight: 700; margin-bottom: 8px;
  }}
  h2 {{ font-size: 24px; font-weight: 800; margin: 0; color: var(--text-primary); letter-spacing: -0.02em; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; margin: 20px 0; }}
  .card {{
    background: rgba(255,255,255,0.02);
    border: 1px solid var(--border-card);
    border-radius: 12px; padding: 20px;
  }}
  .card h3 {{ font-size: 15px; font-weight: 700; margin: 0 0 12px 0; color: var(--accent-blue); }}
  ul {{ margin: 0; padding-left: 20px; }}
  li {{ font-size: 13.5px; margin-bottom: 10px; color: var(--text-secondary); line-height: 1.6; }}
  strong {{ color: var(--text-primary); font-weight: 700; }}
  .slide-footer {{
    display: flex; justify-content: space-between; align-items: center;
    border-top: 1px solid var(--border-card); padding-top: 16px; margin-top: 24px;
    font-family: monospace; font-size: 10px; color: var(--text-secondary);
  }}
  .slide-counter {{ color: var(--accent); font-weight: 700; }}
</style>
</head>
<body>
  <div class="slide-deck">
    {all_slides}
  </div>
</body>
</html>'''


async def _process_dynamic_artifact_block(full_response: str, prompt: str):
    """
    Parses LLM responses for dynamic artifact blocks or artifact creation prompts.
    Saves the file under ./workspace/artifacts/{kind}/{YYYY-MM-DD}_{title_slug}/
    and broadcasts artifact.open over WebSocket to slide open the side panel.
    """
    import re, os, uuid, json, datetime
    body_lower = prompt.lower()
    
    # Check for explicit ```artifact block
    art_match = re.search(r'```artifact\s+kind=["\']?([a-zA-Z0-9_\-]+)["\']?\s+title=["\']?([^"\n]+)["\']?\n([\s\S]*?)```', full_response)
    
    kind, title, content = None, None, None
    if art_match:
        kind = art_match.group(1).lower()
        title = art_match.group(2).strip()
        content = art_match.group(3).strip()
    else:
        # Fallback heuristic for prompts asking for presentation / html / code artifacts
        is_artifact_req = any(w in body_lower for w in ["artifact", "slide deck", "presentation", "html app", "web app", "code file"])
        if is_artifact_req:
            if "presentation" in body_lower or "slide" in body_lower or "deck" in body_lower:
                kind = "presentation"
                title_m = re.search(r'# TITLE:\s*([^\n]+)', full_response)
                title = title_m.group(1).strip() if title_m else "Executive Presentation"
                content = full_response
            elif "html" in body_lower or "web app" in body_lower or "dashboard" in body_lower:
                kind = "html"
                title = "Interactive Web Application"
                code_m = re.search(r'```(?:html|xml)?\n([\s\S]*?)```', full_response)
                content = code_m.group(1).strip() if code_m else full_response
            elif "code" in body_lower or "python" in body_lower or "typescript" in body_lower:
                kind = "code"
                title = "Code Source File"
                code_m = re.search(r'```(?:python|typescript|js|ts|cpp|c|sh|json)?\n([\s\S]*?)```', full_response)
                content = code_m.group(1).strip() if code_m else full_response

    if not kind or not content or not title:
        return

    # Convert presentation artifacts into standalone HTML5 presentation slide decks
    if kind == "presentation":
        content = _build_html5_presentation_deck(title, content)
        kind = "presentation"

    clean_title = re.sub(r'[^a-zA-Z0-9]+', '_', (title or "artifact").lower()).strip('_')
    slug_parts = [p for p in clean_title.split('_') if p][:4]
    slug = "_".join(slug_parts) if slug_parts else "artifact"
    date_str = datetime.date.today().strftime("%Y-%m-%d")
    folder_name = f"{date_str}_{slug}"

    artifacts_base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "workspace", "artifacts"))
    cat_dir = "presentations" if kind in ["presentation", "html"] else ("code" if kind == "code" else "documents")
    save_dir = os.path.join(artifacts_base, cat_dir, folder_name)
    os.makedirs(save_dir, exist_ok=True)

    ext = ".html" if kind in ["presentation", "html", "web"] else ".txt"
    file_path = os.path.join(save_dir, f"source{ext}")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    meta_path = os.path.join(save_dir, "metadata.json")
    art_id = f"art_{uuid.uuid4().hex[:12]}"
    try:
        with open(meta_path, "w", encoding="utf-8") as mf:
            json.dump({
                "artifact_id": art_id,
                "title": title,
                "category": kind,
                "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
            }, mf, indent=2)
    except Exception:
        pass

    from .. import services
    if services.orchestrator and hasattr(services.orchestrator, "ws_gateway") and services.orchestrator.ws_gateway:
        await services.orchestrator.ws_gateway.broadcast_event('artifact.open', {
            "type": "artifact.open",
            "artifactId": art_id,
            "title": title,
            "kind": kind,
            "content": content,
            "mimeType": "text/html" if kind in ["presentation", "html", "web"] else "text/markdown",
            "source": "system",
            "completion_message": "Your Executive Presentation is ready and surfaced in your Artifact Workspace."
        })
        logger.info(f"[GeminiRouter] Intercepted and broadcasted dynamic artifact '{title}' ({kind})")
