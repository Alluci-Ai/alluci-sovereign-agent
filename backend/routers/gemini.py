
from typing import Optional, Literal, List, Dict, Any, Tuple
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

async def _check_local_workspace_file_or_report(prompt: str) -> Optional[str]:
    """
    Scans the local workspace filesystem for requested files (e.g., README.md, ARCHITECTURE.md,
    source files, configuration, or deep research reports) when prompt explicitly requests to
    view, show, read, open, or fetch a file. Reads the verbatim content from disk,
    registers it as an ArtifactRecord, and broadcasts an artifact.open event to open the side panel.
    """
    body_lower = prompt.lower().strip()

    # 1. Negative guardrail keywords: Never intercept educational prompts or explicit commands to generate/write new code
    execution_keywords = [
        "do deep", "do web", "conduct", "run", "deep research", "deep web research",
        "scour", "investigate", "rocco", "spin up", "execute dag", "create a new", "write a new", "build a new"
    ]
    if any(ek in body_lower for ek in execution_keywords):
        return None

    action_verbs = ["show", "pull", "open", "display", "read", "view", "fetch", "get", "print", "cat"]
    has_action_verb = any(re.search(rf'\b{re.escape(verb)}\b', body_lower) for verb in action_verbs)

    # Check for research report request
    target_report_nouns = ["report", "dossier"]
    is_report_request = has_action_verb and any(re.search(rf'\b{re.escape(noun)}\b', body_lower) for noun in target_report_nouns)

    # Check for file request: explicit file name/path with extension or keywords
    file_pattern = r'([A-Za-z0-9_\-\.\/]+\.(?:md|py|ts|tsx|js|jsx|json|yaml|yml|sh|html|css|txt|sql|toml|ini|env|example|lock))\b'
    file_matches = re.findall(file_pattern, prompt, re.IGNORECASE)

    explicit_named_files = []
    if "readme" in body_lower and not any("readme" in m.lower() for m in file_matches):
        explicit_named_files.append("README.md")
    if "architecture" in body_lower and any(w in body_lower for w in ["file", "md", "doc", "document"]) and not any("architecture" in m.lower() for m in file_matches):
        explicit_named_files.append("ARCHITECTURE.md")
    if "agents.md" in body_lower or ("agents" in body_lower and "directive" in body_lower):
        explicit_named_files.append("AGENTS.md")

    target_files = file_matches + explicit_named_files

    # If not a report request and no target file detected, or no action verb for general file, return None
    if not is_report_request and (not target_files or not has_action_verb):
        return None

    import os, glob
    from .sessions import WORKSPACE_DIR
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    # Case A: Research Report Request
    if is_report_request and not target_files:
        found_reports = []
        primary_base = os.path.join(project_root, "workspace", "artifacts", "research")
        if os.path.exists(primary_base):
            for p in glob.glob(os.path.join(primary_base, "*", "deep_research_report.md")):
                found_reports.append((os.path.getmtime(p), p))

        for search_agent in ["a32eb383", "rocco", "executive"]:
            research_base = os.path.join(WORKSPACE_DIR, search_agent, "artifacts", "research")
            if os.path.exists(research_base):
                for p in glob.glob(os.path.join(research_base, "*", "deep_research_report.md")):
                    found_reports.append((os.path.getmtime(p), p))

        if found_reports:
            matched_report = None
            prompt_words = [w for w in body_lower.replace('"', '').replace("'", '').split() if len(w) > 3 and w not in action_verbs and w not in target_report_nouns]
            for _, rpath in found_reports:
                folder_name = os.path.basename(os.path.dirname(rpath)).lower()
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

                return f"Hello JJ. I have retrieved the **{topic_title}** report from disk and opened it for you in your Artifact Workspace.\n\nYou can view, navigate, zoom, or download the full dossier in the side panel."
            except Exception as read_err:
                logger.error(f"[ReportReader] Failed to read report from disk: {read_err}")
                return None

    # Case B: Specific Local Workspace File Request
    for requested_file in target_files:
        clean_name = requested_file.strip("`'\" \t\n,;:")
        if not clean_name:
            continue

        resolved_path = None
        # 1. Direct path check
        direct_check = os.path.abspath(os.path.join(project_root, clean_name))
        if os.path.exists(direct_check) and os.path.isfile(direct_check) and direct_check.startswith(project_root):
            resolved_path = direct_check
        else:
            # 2. Search workspace by basename
            target_base = os.path.basename(clean_name).lower()
            for root, dirs, files in os.walk(project_root):
                dirs[:] = [d for d in dirs if d not in {".git", "node_modules", ".venv", "venv", "__pycache__", ".pytest_cache", "dist", "build", ".next", ".cache"}]
                for f in files:
                    if f.lower() == target_base:
                        candidate = os.path.join(root, f)
                        if clean_name.lower() in candidate.lower():
                            resolved_path = candidate
                            break
                        if not resolved_path:
                            resolved_path = candidate
                if resolved_path:
                    break

        if resolved_path and os.path.exists(resolved_path):
            try:
                rel_path = os.path.relpath(resolved_path, project_root)
                with open(resolved_path, "r", encoding="utf-8", errors="ignore") as f:
                    file_content = f.read()

                total_lines = file_content.count("\n") + 1
                ext = os.path.splitext(resolved_path)[1].lower()
                mime_map = {
                    ".md": "text/markdown", ".py": "text/x-python", ".ts": "text/typescript",
                    ".tsx": "text/typescript-jsx", ".js": "text/javascript", ".json": "application/json",
                    ".yaml": "text/yaml", ".yml": "text/yaml", ".html": "text/html", ".css": "text/css",
                    ".sh": "text/x-sh", ".sql": "text/x-sql", ".txt": "text/plain"
                }
                mime_type = mime_map.get(ext, "text/plain")

                # Register artifact and open in panel
                import uuid
                art_id = f"art_{uuid.uuid4().hex[:12]}"
                try:
                    from .artifacts import create_artifact
                    art_payload = {
                        "title": f"Workspace File: {rel_path}",
                        "kind": "code" if ext in {".py", ".ts", ".tsx", ".js", ".json", ".sh", ".sql"} else "text",
                        "mimeType": mime_type,
                        "content": file_content,
                        "metadata": {"file_path": rel_path, "lines": total_lines, "size_bytes": len(file_content)}
                    }
                    art_res = await create_artifact(art_payload)
                    if isinstance(art_res, dict) and "id" in art_res:
                        art_id = art_res["id"]
                except Exception as db_err:
                    logger.debug(f"[FileReader] Artifact DB registration note: {db_err}")

                from .. import services
                if services.orchestrator and hasattr(services.orchestrator, "ws_gateway") and services.orchestrator.ws_gateway:
                    await services.orchestrator.ws_gateway.broadcast_event('artifact.open', {
                        "type": "artifact.open",
                        "artifactId": art_id,
                        "title": f"Workspace File: {rel_path}",
                        "kind": "code" if ext in {".py", ".ts", ".tsx", ".js", ".json", ".sh", ".sql"} else "text",
                        "content": file_content,
                        "mimeType": mime_type,
                        "source": "system"
                    })

                # Format grounded chat return
                if len(file_content) <= 12000:
                    code_lang = ext.lstrip(".") if ext else ""
                    if ext == ".md":
                        preview_body = file_content
                    else:
                        preview_body = f"```{code_lang}\n{file_content}\n```"
                    return f"Hello JJ. I have retrieved `{rel_path}` directly from the local filesystem ({total_lines} lines) and opened it in your Artifact Workspace.\n\n{preview_body}"
                else:
                    first_lines = "\n".join(file_content.splitlines()[:80])
                    code_lang = ext.lstrip(".") if ext else ""
                    return f"Hello JJ. I have retrieved `{rel_path}` directly from the local filesystem ({total_lines} lines, {len(file_content):,} bytes) and opened the complete document in your Artifact Workspace side panel.\n\nHere is an excerpt of the first 80 lines:\n\n```{code_lang}\n{first_lines}\n...\n```"

            except Exception as read_err:
                logger.error(f"[FileReader] Failed to read local file {resolved_path}: {read_err}")
                return f"Error reading local file `{clean_name}` from disk: {read_err}"

        # If a specific named file was explicitly requested and not found
        if has_action_verb:
            return f"File `{clean_name}` was not found on the local filesystem. Please verify the relative path or file name."

    return None


async def _check_web_search_grounding(prompt: str) -> Optional[str]:
    """
    Detects if the user query asks for web/internet search or deep research, or if answering
    requires live external facts/market data. Executes via WebSearchAdapter and returns verified markdown snippets with URLs.
    """
    body_lower = prompt.lower().strip()
    search_prefixes = [
        "search the web for", "search online for", "search duckduckgo for",
        "search google for", "look up online for", "look up online",
        "search the internet for", "web search for", "web search:",
        "google search:", "deep research on", "deep research into",
        "do deep research on", "do deep research for", "run deep research on",
        "research the latest", "search for", "find online information on",
        "find online information about", "find online facts about",
        "find out about", "browse the web for", "look up the latest",
        "find latest news on", "find current pricing for", "search:"
    ]

    query = None
    for trig in search_prefixes:
        if trig in body_lower:
            idx = body_lower.find(trig) + len(trig)
            query = prompt[idx:].strip(" :\"'?")
            break

    # Also detect explicit "search: <query>" or "research: <query>" or queries ending in "online" or "on the web"
    if not query:
        if any(body_lower.startswith(p) for p in ["search ", "google ", "lookup ", "research "]):
            words = prompt.split(maxsplit=1)
            if len(words) > 1 and len(words[1].strip()) > 3:
                query = words[1].strip(" :\"'?")

    # Epistemic detection: prompt asks for 2026/current external developments, competitor market pricing, or live releases
    if not query:
        temporal_external_triggers = [
            "latest developments in", "current pricing for", "recent news regarding",
            "what happened with", "who is the current ceo of", "latest release of"
        ]
        for trig in temporal_external_triggers:
            if trig in body_lower:
                idx = body_lower.find(trig)
                query = prompt[idx:].strip(" :\"'?")
                break

    if not query or len(query.strip()) < 3:
        return None

    try:
        from ..adapters.web_search import WebSearchAdapter
        adapter = WebSearchAdapter()
        
        is_deep_research = any(w in body_lower for w in ["deep research", "compare", " vs ", "benchmarks", "market analysis", "pricing breakdown"])
        if is_deep_research:
            search_res = await adapter.expand_and_harvest(query.strip())
        else:
            search_res = await adapter.execute(query.strip())
            
        if isinstance(search_res, dict) and search_res.get("status") == "success" and search_res.get("results"):
            results = search_res["results"][:8]
            formatted_results = []
            for i, r in enumerate(results, 1):
                title = r.get("title", "Untitled")
                link = r.get("link", "")
                snippet = r.get("snippet", "")
                formatted_results.append(f"{i}. [{title}]({link})\n   {snippet}")

            provider_label = search_res.get("provider", "web")
            return (
                f"[AUTHENTIC WEB RESEARCH GROUNDING ({provider_label.upper()}): '{query}']\n"
                + "\n\n".join(formatted_results)
            )
    except Exception as search_err:
        logger.debug(f"[GeminiRouter] Web search grounding extraction notice: {search_err}")
    return None


def _process_attached_files(prompt: str, files: Optional[List[Dict[str, Any]]] = None) -> str:
    """Decodes and appends attached file contents (TXT, MD, PDF, JSON, CSV, DOCX, Code) to prompt context with KV cache safety bounds."""
    if not files:
        return prompt

    MAX_FILE_CHARS = 150000
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


async def _check_codebase_and_architecture_context(prompt: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Delegates to ModularGroundingOrchestrator to retrieve strictly scoped, non-polluted
    grounding context based on prompt intent. Returns (grounding_content, specialized_directive).
    """
    try:
        from ..engine.intent_decomposer import IntentDecomposer
        from ..engine.grounding_providers import ModularGroundingOrchestrator
        
        decomposer = IntentDecomposer()
        parsed_intent = decomposer.decompose(prompt)
        orch = ModularGroundingOrchestrator()
        grounding, directive = await orch.resolve_grounding(prompt, parsed_intent)
        return (grounding if grounding else None, directive)
    except Exception as e:
        logger.debug(f"[GeminiRouter] Modular grounding resolution notice: {e}")
        return None, None


async def _check_url_grounding(urls: List[str]) -> Tuple[Optional[str], List[str], List[str]]:
    """
    Extracts, scrapes, and parses markdown from real-time URLs provided in user prompt.
    Asynchronously ingests content into H-LSM memory fabric.
    Returns (grounding_text, sha256_list, url_titles).
    """
    if not urls:
        return None, [], []
    
    import hashlib
    from ..ingestion_services.scraper import fetch_and_extract_markdown
    from .. import services
    
    grounding_blocks = []
    shas = []
    titles = []
    
    for url in urls[:5]:
        try:
            markdown = await fetch_and_extract_markdown(url)
            if markdown and len(markdown.strip()) > 50:
                url_sha = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
                shas.append(url_sha)
                
                first_h1 = re.search(r'^#\s+([^\n]+)', markdown, re.MULTILINE)
                title = first_h1.group(1).strip() if first_h1 else url
                titles.append(title)
                
                # Dynamic Ingestion into H-LSM Memory Fabric
                if hasattr(services, "hlsm_manager") and services.hlsm_manager:
                    try:
                        await services.hlsm_manager.ingest_document_payload(
                            filename=url,
                            content=markdown,
                            session_key="url_realtime_ingest"
                        )
                    except Exception as ing_err:
                        logger.debug(f"[GeminiRouter] URL H-LSM ingestion notice: {ing_err}")

                grounding_blocks.append(
                    f"[VERIFIED REAL-TIME URL SOURCE GROUNDING: {url} | Title: {title} | SHA-256: {url_sha[:12]}]:\n"
                    f"{markdown}"
                )
        except Exception as e:
            logger.warning(f"[GeminiRouter] URL scraping error for {url}: {e}")
            
    if grounding_blocks:
        return "\n\n".join(grounding_blocks), shas, titles
    return None, [], []


async def _check_document_grounding(prompt: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Detects single and multi-document inquiries:
    1. Specific page requests (e.g., 'pages 6, 7, 8 and 9', 'page 12', 'pages 4-7 of Hoffman')
       -> Retrieves exact verbatim page text.
    2. Comprehensive document overview/summary/formula/question requests
       -> Synthesizes hierarchical multi-page overview from L3 PageNode & ConceptNode entities.
    Returns (grounding_text, doc_sha256, doc_name).
    """
    body_lower = prompt.lower()
    from .. import services

    # Identify all document references in prompt
    doc_keywords = []
    fname_matches = re.findall(r'([A-Za-z0-9_\-]+\.(?:pdf|docx|txt|md))\b', prompt, re.IGNORECASE)
    if fname_matches:
        doc_keywords.extend(fname_matches)
    
    candidates = [
        "objects of consciousness", "hoffman", "cimc", "consciousness", 
        "whitepaper", "paper", "report", "document", "manuscript", "treatise"
    ]
    for c in candidates:
        if c in body_lower and c not in doc_keywords:
            doc_keywords.append(c)

    # Check for specific page requests (single document)
    page_match = re.search(r'\bpages?\s*([0-9\s,\-andto]+)', prompt, re.IGNORECASE)
    if page_match:
        doc_query = doc_keywords[0] if doc_keywords else ""
        raw_nums_str = page_match.group(1).strip()
        page_numbers = []
        if "-" in raw_nums_str or "to" in raw_nums_str:
            range_parts = re.split(r'-|\bto\b', raw_nums_str)
            if len(range_parts) == 2 and range_parts[0].strip().isdigit() and range_parts[1].strip().isdigit():
                start_p, end_p = int(range_parts[0].strip()), int(range_parts[1].strip())
                page_numbers = list(range(min(start_p, end_p), max(start_p, end_p) + 1))
        
        if not page_numbers:
            digits = re.findall(r'\b\d+\b', raw_nums_str)
            page_numbers = [int(d) for d in digits if int(d) < 1000]

        if page_numbers and len(page_numbers) <= 50:
            if hasattr(services, "hlsm_manager") and services.hlsm_manager:
                try:
                    page_records = await services.hlsm_manager.retrieve_page_range(
                        document_query=doc_query,
                        page_numbers=page_numbers
                    )
                    if page_records:
                        page_blocks = []
                        doc_name = page_records[0].get("filename", doc_query or "Document")
                        for p in page_records:
                            p_num = p.get("page_number", 0)
                            p_txt = p.get("text", "").strip()
                            p_hdr = p.get("header", f"--- [PAGE {p_num}] ---")
                            if p_txt:
                                page_blocks.append(f"{p_hdr}\n{p_txt}")
                        
                        if page_blocks:
                            joined_pages = "\n\n".join(page_blocks)
                            grounding = f"[AUTHENTIC SOURCE DOCUMENT PAGE GROUNDING (Document: {doc_name} | Requested Pages: {', '.join(str(p) for p in page_numbers)})]:\n{joined_pages}"
                            return grounding, None, doc_name
                except Exception as e:
                    logger.debug(f"[GeminiRouter] Page grounding resolution notice: {e}")

    # General document inquiries and multi-document synthesis
    if doc_keywords and hasattr(services, "hlsm_manager") and services.hlsm_manager:
        synthesized_blocks = []
        doc_shas = []
        doc_names = []
        
        # Deduplicate queries to target distinct documents
        unique_queries = []
        for dk in doc_keywords:
            if not any(dk in u or u in dk for u in unique_queries):
                unique_queries.append(dk)
                
        for q in unique_queries[:3]:
            try:
                synth_res = await services.hlsm_manager.synthesize_document_hierarchical_overview(q, as_dict=True)
                if synth_res and isinstance(synth_res, dict):
                    doc_sha = synth_res.get("sha256")
                    doc_name = synth_res.get("name")
                    if doc_sha and doc_sha not in doc_shas:
                        doc_shas.append(doc_sha)
                        doc_names.append(doc_name)
                        synthesized_blocks.append(
                            f"[AUTHENTIC SOURCE DOCUMENT: {synth_res.get('title')} (`{doc_name}`) | SHA-256: {doc_sha[:12]}]:\n"
                            f"{synth_res.get('text')}"
                        )
            except Exception as e:
                logger.debug(f"[GeminiRouter] Multi-doc overview synthesis notice for {q}: {e}")

        if synthesized_blocks:
            combined_text = "\n\n".join(synthesized_blocks)
            first_sha = doc_shas[0] if len(doc_shas) == 1 else None
            label = " & ".join(doc_names) if doc_names else "Document"
            return combined_text, first_sha, label

    return None, None, None


# Backward-compatibility alias
_check_document_page_grounding = _check_document_grounding



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
    Proxies requests to local or cloud models with Single-Pass execution and dynamic intent decomposition.
    """
    router_inst = services.router
    if not router_inst:
        raise HTTPException(status_code=503, detail="Inference router not ready")

    from ..engine.intent_decomposer import IntentDecomposer, IntentType
    decomposer = IntentDecomposer()
    parsed_intent = decomposer.decompose(prompt)

    raw_user_prompt = _process_attached_files(prompt, files)

    try:
        # 1. Fast Memory Deletion Interceptor Check (< 5ms)
        mem_purge_reply = await _intercept_memory_deletion_request(prompt)
        if mem_purge_reply:
            return {"result": mem_purge_reply}

        # 2. Fast Local Hard Drive & Workspace File / Report Reader Check (< 50ms)
        local_file_or_report = await _check_local_workspace_file_or_report(raw_user_prompt)
        if local_file_or_report:
            return {"result": local_file_or_report}

        # 3. Dynamic Real-Time URL Scraping & Ingestion Check (< 250ms)
        url_grounding, url_shas, url_titles = await _check_url_grounding(parsed_intent.detected_urls)

        # 4. Dynamic Document Page & Overview Grounding Check (< 15ms)
        doc_grounding, doc_sha256, doc_name = await _check_document_grounding(raw_user_prompt)

        # 5. Dynamic Web Search Grounding Check (< 500ms)
        web_grounding = await _check_web_search_grounding(raw_user_prompt)

        # 6. Dynamic Codebase & Architecture Grounding Check (< 15ms)
        code_grounding, specialized_directive = await _check_codebase_and_architecture_context(prompt)

        # 7. Dynamic 4-Tier H-LSM Context Hydration across L1/L2/L3 (Tri-Hybrid RRF with SHA-256 scoping)
        memory_block = ""
        effective_doc_sha = doc_sha256 or (url_shas[0] if len(url_shas) == 1 else None)
        if hasattr(services, "hlsm_manager") and services.hlsm_manager and parsed_intent.intent_type != IntentType.SYSTEM_INTROSPECTION:
            try:
                psi = 0.0
                if hasattr(services, "ace") and services.ace:
                    affective = services.ace.get_affective_state()
                    psi = min(1.0, affective.tension / 1024.0)
                memory_ctx = await services.hlsm_manager.retrieve_context(
                    objective=parsed_intent.core_objective,
                    psi=psi,
                    session_key=session_id or "web_chat",
                    doc_sha256=effective_doc_sha
                )
                memory_block = memory_ctx.to_prompt_block()
            except Exception as mem_err:
                logger.debug(f"[GeminiRouter] Dynamic H-LSM hydration notice: {mem_err}")

        # Construct Authoritative Grounded Prompt
        grounding_blocks = []
        if url_grounding:
            grounding_blocks.append(url_grounding)
        if doc_grounding:
            grounding_blocks.append(doc_grounding)
        if web_grounding:
            grounding_blocks.append(f"[WEB SEARCH GROUNDING DATA]:\n{web_grounding}")
        if code_grounding and not files and not doc_grounding and not url_grounding:
            grounding_blocks.append(f"[AUTHENTIC DISK GROUNDING & MANIFESTS]:\n{code_grounding}")
        if memory_block:
            grounding_blocks.append(f"[RECALLED H-LSM MEMORY CONTEXT]:\n{memory_block}")

        if grounding_blocks:
            combined_grounding = "\n\n".join(grounding_blocks)
            
            # Formulate Dynamic Adaptive Directive via CognitiveDirectiveRegistry
            from ..engine.directive_registry import CognitiveDirectiveRegistry
            directive_registry = CognitiveDirectiveRegistry()
            
            source_labels = []
            if doc_name:
                source_labels.append(doc_name)
            if url_titles:
                source_labels.extend(url_titles)
            elif parsed_intent.detected_urls:
                source_labels.extend(parsed_intent.detected_urls)
            
            source_label = " & ".join(source_labels) if source_labels else "THE REFERENCE SOURCE"
            
            if doc_grounding or url_grounding:
                directive = directive_registry.synthesize_directive(parsed_intent.directive_modality, source_label)
            elif files:
                directive = "INSTRUCTION: Answer the User Directive directly, comprehensively, and accurately based on the provided document text and reference grounding context above. Ground all factual claims strictly in the authentic reference data provided."
            else:
                directive = specialized_directive or directive_registry.synthesize_directive(parsed_intent.directive_modality, source_label)

            effective_prompt = (
                f"### USER DIRECTIVE / QUESTION:\n"
                f"{raw_user_prompt.strip()}\n\n"
                f"--- REFERENCE GROUNDING CONTEXT (Use strictly as factual reference to answer the User Directive above) ---\n"
                f"{combined_grounding}\n"
                f"--- END OF REFERENCE CONTEXT ---\n\n"
                f"{directive}"
            )
        else:
            effective_prompt = raw_user_prompt

        # Fetch system context
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
                        asyncio.create_task(services.hlsm_manager.ingest_document_payload(
                            filename=fn,
                            content=p_text,
                            session_key=session_id or "web_chat",
                            metadata={"mime_type": fmime, "file_data": fdata}
                        ))
        if response:
            asyncio.create_task(_process_dynamic_artifact_block(response, prompt))

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

    from ..engine.intent_decomposer import IntentDecomposer, IntentType
    decomposer = IntentDecomposer()
    parsed_intent = decomposer.decompose(prompt)

    raw_user_prompt = _process_attached_files(prompt, files)

    try:
        # 1. Fast Memory Deletion Interceptor Check (< 5ms)
        mem_purge_reply = await _intercept_memory_deletion_request(prompt)

        # 2. Fast Local Hard Drive & Workspace File / Report Reader Check (< 50ms)
        local_file_or_report = await _check_local_workspace_file_or_report(raw_user_prompt)

        # 3. Dynamic Real-Time URL Scraping & Ingestion Check (< 250ms)
        url_grounding, url_shas, url_titles = await _check_url_grounding(parsed_intent.detected_urls)

        # 4. Dynamic Document Page & Overview Grounding Check (< 15ms)
        doc_grounding, doc_sha256, doc_name = await _check_document_grounding(raw_user_prompt)

        # 5. Dynamic Web Search Grounding Check (< 500ms)
        web_grounding = await _check_web_search_grounding(raw_user_prompt)

        # 6. Dynamic Codebase & Architecture Grounding Check (< 15ms)
        code_grounding, specialized_directive = await _check_codebase_and_architecture_context(prompt)

        # 7. Dynamic 4-Tier H-LSM Context Hydration across L1/L2/L3 (Tri-Hybrid RRF with SHA-256 scoping)
        memory_block = ""
        effective_doc_sha = doc_sha256 or (url_shas[0] if len(url_shas) == 1 else None)
        if hasattr(services, "hlsm_manager") and services.hlsm_manager and parsed_intent.intent_type != IntentType.SYSTEM_INTROSPECTION:
            try:
                psi = 0.0
                if hasattr(services, "ace") and services.ace:
                    affective = services.ace.get_affective_state()
                    psi = min(1.0, affective.tension / 1024.0)
                memory_ctx = await services.hlsm_manager.retrieve_context(
                    objective=parsed_intent.core_objective,
                    psi=psi,
                    session_key=session_id or "web_chat",
                    doc_sha256=effective_doc_sha
                )
                memory_block = memory_ctx.to_prompt_block()
            except Exception as mem_err:
                logger.debug(f"[GeminiRouter] Dynamic H-LSM hydration notice: {mem_err}")

        # Construct Authoritative Grounded Prompt
        grounding_blocks = []
        if url_grounding:
            grounding_blocks.append(url_grounding)
        if doc_grounding:
            grounding_blocks.append(doc_grounding)
        if web_grounding:
            grounding_blocks.append(f"[WEB SEARCH GROUNDING DATA]:\n{web_grounding}")
        if code_grounding and not files and not doc_grounding and not url_grounding:
            grounding_blocks.append(f"[AUTHENTIC DISK GROUNDING & MANIFESTS]:\n{code_grounding}")
        if memory_block:
            grounding_blocks.append(f"[RECALLED H-LSM MEMORY CONTEXT]:\n{memory_block}")

        if grounding_blocks:
            combined_grounding = "\n\n".join(grounding_blocks)
            
            # Formulate Dynamic Adaptive Directive via CognitiveDirectiveRegistry
            from ..engine.directive_registry import CognitiveDirectiveRegistry
            directive_registry = CognitiveDirectiveRegistry()
            
            source_labels = []
            if doc_name:
                source_labels.append(doc_name)
            if url_titles:
                source_labels.extend(url_titles)
            elif parsed_intent.detected_urls:
                source_labels.extend(parsed_intent.detected_urls)
            
            source_label = " & ".join(source_labels) if source_labels else "THE REFERENCE SOURCE"
            
            if doc_grounding or url_grounding:
                directive = directive_registry.synthesize_directive(parsed_intent.directive_modality, source_label)
            elif files:
                directive = "INSTRUCTION: Answer the User Directive directly, comprehensively, and accurately based on the provided document text and reference grounding context above. Ground all factual claims strictly in the authentic reference data provided."
            else:
                directive = specialized_directive or directive_registry.synthesize_directive(parsed_intent.directive_modality, source_label)

            effective_prompt = (
                f"### USER DIRECTIVE / QUESTION:\n"
                f"{raw_user_prompt.strip()}\n\n"
                f"--- REFERENCE GROUNDING CONTEXT (Use strictly as factual reference to answer the User Directive above) ---\n"
                f"{combined_grounding}\n"
                f"--- END OF REFERENCE CONTEXT ---\n\n"
                f"{directive}"
            )
        else:
            effective_prompt = raw_user_prompt

        # 5. Dreaming Cycle GPU Preemption on User Interactive Chat
        try:
            if services.cron_engine and getattr(services.settings, "DREAMING_CYCLE_YIELD_ON_USER_ACTIVITY", True):
                services.cron_engine.preempt_dreaming()
        except Exception as pe:
            logger.debug(f"[GeminiRouter] Preemption notice: {pe}")

        system_instruction = ""
        orch = services.orchestrator
        if doc_grounding:
            # PURE ACADEMIC GROUNDING: Strip all internal sovereign agent architecture, tools, and PPN/DPK context
            system_instruction = (
                "You are a rigorous, objective academic research analyst. Your sole function is to provide an exact, factual, "
                "and unbiased analysis of the provided source document without referencing external system architectures, "
                "unrelated cognitive frameworks, or unverified claims. Base all conclusions strictly on the provided document text."
            )
        elif orch is not None and not local_file_or_report and not mem_purge_reply:
            ctx_res = await orch._build_system_context(compact_index=True)
            system_instruction = ctx_res[0] if isinstance(ctx_res, (tuple, list)) else str(ctx_res)

        # 6. Semantic Intent Action Switchboard (< 5ms Check)
        orchestrator_reply = None
        if orch is not None and not local_file_or_report and not mem_purge_reply:
            try:
                body_lower = prompt.lower()
                cancellation_keywords = ["stop", "cancel", "abort", "halt", "terminate"]
                is_cancel = any(ck in body_lower for ck in cancellation_keywords) and any(w in body_lower for w in ["dag", "run", "research", "pipeline", "execution"])

                if is_cancel:
                    orchestrator_reply = await orch.handle_user_message(effective_prompt)
                elif (
                    parsed_intent.is_actionable_dag
                    and not files
                    and parsed_intent.intent_type not in (
                        IntentType.INFORMATIONAL_QA,
                        IntentType.SYSTEM_INTROSPECTION,
                        IntentType.GENERAL_CONVERSATIONAL
                    )
                ):
                    orchestrator_reply = await orch.handle_user_message(effective_prompt)
                    logger.info(f"[GeminiRouter] Handled orchestrator auto-dispatch for intent '{parsed_intent.intent_type.value}': '{prompt[:50]}...'")
            except Exception as dispatch_err:
                logger.debug(f"[GeminiRouter] Intent switchboard note: {dispatch_err}")

        async def event_generator():
            import json

            # Instant TTFT heartbeat signal to keep UI responsive
            yield f"data: {json.dumps({'text': '', 'status': 'Ingesting document & initializing skill context...'})}\n\n"

            if mem_purge_reply:
                yield f"data: {json.dumps({'text': mem_purge_reply})}\n\n"
                return

            if local_file_or_report:
                yield f"data: {json.dumps({'text': local_file_or_report})}\n\n"
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
                        if files:
                            for f in files:
                                fn, fdata, fmime = f.get("name", "attachment"), f.get("data", ""), f.get("mimeType", "")
                                p_text = extract_text_from_file_payload(fn, fdata, fmime)
                                if p_text and not p_text.startswith(("[BINARY", "[UNSUPPORTED")):
                                    asyncio.create_task(services.hlsm_manager.ingest_document_payload(
                                        filename=fn,
                                        content=p_text,
                                        session_key=session_id or "web_chat",
                                        metadata={"mime_type": fmime, "file_data": fdata}
                                    ))
                    
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


def _build_html5_research_dossier(title: str, markdown_content: str) -> str:
    """Renders a styled HTML5 document for research deliverables adhering to Triad Bundle Law."""
    import html
    escaped_title = html.escape(title)
    lines = markdown_content.split("\n")
    html_body_lines = []
    in_code = False
    for line in lines:
        if line.startswith("```"):
            if in_code:
                html_body_lines.append("</pre></code>")
                in_code = False
            else:
                html_body_lines.append("<pre><code>")
                in_code = True
            continue
        if in_code:
            html_body_lines.append(html.escape(line))
            continue
        if line.startswith("# "):
            html_body_lines.append(f"<h1>{html.escape(line[2:].strip())}</h1>")
        elif line.startswith("## "):
            html_body_lines.append(f"<h2>{html.escape(line[3:].strip())}</h2>")
        elif line.startswith("### "):
            html_body_lines.append(f"<h3>{html.escape(line[4:].strip())}</h3>")
        elif line.startswith(("- ", "* ")):
            html_body_lines.append(f"<li>{html.escape(line[2:].strip())}</li>")
        elif line.strip():
            html_body_lines.append(f"<p>{html.escape(line.strip())}</p>")
        else:
            html_body_lines.append("<br/>")
    
    body_html = "\n".join(html_body_lines)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{escaped_title}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #e2e8f0; background: #0f172a; max-width: 900px; margin: 0 auto; padding: 2rem; }}
  h1 {{ color: #38bdf8; border-bottom: 2px solid #334155; padding-bottom: 0.5rem; }}
  h2 {{ color: #818cf8; margin-top: 1.5rem; }}
  h3 {{ color: #cbd5e1; }}
  pre {{ background: #1e293b; padding: 1rem; border-radius: 8px; overflow-x: auto; border: 1px solid #334155; }}
  code {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; color: #38bdf8; }}
  p {{ margin-bottom: 1rem; }}
  li {{ margin-bottom: 0.5rem; }}
</style>
</head>
<body>
{body_html}
</body>
</html>"""


async def _process_dynamic_artifact_block(full_response: str, prompt: str, output_dir: Optional[str] = None):
    """
    Parses LLM responses for dynamic artifact blocks, slide decks, or comprehensive research dossiers.
    Saves the deliverable under ./workspace/artifacts/{category}/{YYYY-MM-DD}_{title_slug}/ as an atomic triad
    (metadata.json, source.md, source.html) and broadcasts artifact.open over WebSocket to slide open the side panel.
    """
    import re, os, uuid, json, datetime
    body_lower = prompt.lower()
    
    # 1. Check for explicit ```artifact block
    art_match = re.search(r'```artifact\s+kind=["\']?([a-zA-Z0-9_\-]+)["\']?\s+title=["\']?([^"\n]+)["\']?\n([\s\S]*?)```', full_response)
    
    kind, title, content = None, None, None
    if art_match:
        kind = art_match.group(1).lower()
        title = art_match.group(2).strip()
        content = art_match.group(3).strip()
    else:
        # Fallback heuristic for prompts asking for presentation / html / code / research artifacts
        is_artifact_req = any(w in body_lower for w in ["artifact", "slide deck", "presentation", "html app", "web app", "code file"])
        is_research_req = (
            len(full_response) > 150 and any(w in body_lower for w in [
                "comprehensive", "deep analysis", "overview", "whitepaper", "treatise", 
                "objects of consciousness", "cimc", "explain in detail", "research dossier", "paper", "document"
            ])
        ) or ("# " in full_response and "## " in full_response)
        
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
        elif is_research_req:
            from ..engine.intent_decomposer import IntentDecomposer
            from ..engine.directive_registry import CognitiveDirectiveRegistry
            
            p_intent = IntentDecomposer().decompose(prompt)
            cat_name, default_title = CognitiveDirectiveRegistry().get_artifact_metadata(p_intent.directive_modality, "Document")
            kind = cat_name
            
            first_h1 = re.search(r'^#\s+([^\n]+)', full_response, re.MULTILINE)
            if first_h1:
                title = first_h1.group(1).strip()
            elif "objects of consciousness" in body_lower or "hoffman" in body_lower:
                title = "Objects of Consciousness — Comprehensive Treatise Analysis"
            elif "cimc" in body_lower or "machine consciousness" in body_lower:
                title = "CIMC Whitepaper — Comprehensive Research Dossier"
            else:
                title = default_title
            content = full_response

    if not kind or not content or not title:
        return

    # Convert presentation artifacts into standalone HTML5 presentation slide decks
    if kind == "presentation":
        html_content = _build_html5_presentation_deck(title, content)
        md_content = content
    elif kind in ["html", "web"]:
        html_content = content
        md_content = f"# {title}\n\n```html\n{content}\n```"
    elif kind == "code":
        html_content = f"<pre><code>{content}</code></pre>"
        md_content = content
    else:
        # High-grade academic HTML5 dossier styling for all analytical, narrative, and research categories
        html_content = _build_html5_research_dossier(title, content)
        md_content = content

    clean_title = re.sub(r'[^a-zA-Z0-9]+', '_', (title or "artifact").lower()).strip('_')
    slug_parts = [p for p in clean_title.split('_') if p][:4]
    slug = "_".join(slug_parts) if slug_parts else "artifact"
    date_str = datetime.date.today().strftime("%Y-%m-%d")
    folder_name = f"{date_str}_{slug}"

    artifacts_base = os.path.abspath(output_dir) if output_dir else os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "workspace", "artifacts"))
    cat_dir = kind if kind in ["comparisons", "critiques", "articles", "contrarian", "narratives", "creative", "mathematics", "research", "presentations", "code"] else "research"
    save_dir = os.path.join(artifacts_base, cat_dir, folder_name)
    os.makedirs(save_dir, exist_ok=True)

    # Persist Atomic Triad Bundle
    md_file_path = os.path.join(save_dir, "source.md")
    with open(md_file_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    html_file_path = os.path.join(save_dir, "source.html")
    with open(html_file_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    meta_path = os.path.join(save_dir, "metadata.json")
    art_id = f"art_{uuid.uuid4().hex[:12]}"
    try:
        with open(meta_path, "w", encoding="utf-8") as mf:
            json.dump({
                "artifact_id": art_id,
                "title": title,
                "category": kind,
                "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "triad_bundle": {
                    "source_md": "source.md",
                    "source_html": "source.html",
                    "metadata": "metadata.json"
                }
            }, mf, indent=2)
    except Exception:
        pass

    from .. import services
    if services.orchestrator and hasattr(services.orchestrator, "ws_gateway") and services.orchestrator.ws_gateway:
        completion_msg = (
            "Your Comprehensive Research Dossier is ready and surfaced in your Artifact Panel." 
            if kind == "research" else 
            "Your Executive Presentation is ready and surfaced in your Artifact Workspace."
        )
        await services.orchestrator.ws_gateway.broadcast_event('artifact.open', {
            "type": "artifact.open",
            "artifactId": art_id,
            "title": title,
            "kind": kind,
            "content": md_content,
            "mimeType": "text/markdown" if kind == "research" else ("text/html" if kind in ["presentation", "html", "web"] else "text/markdown"),
            "source": "system",
            "completion_message": completion_msg
        })
        logger.info(f"[GeminiRouter] Intercepted and broadcasted dynamic artifact '{title}' ({kind}) -> {save_dir}")
