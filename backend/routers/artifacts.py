"""
Artifact Management Router
===========================

Provides REST API endpoints for artifact creation, versioning, page management,
and file storage under `./workspace/artifacts/`.
"""

import os
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Literal, Sequence
from fastapi import APIRouter, HTTPException, Depends, Query, Body, Request
from fastapi.responses import FileResponse, Response
from sqlmodel import Session, select, col

from ..security.auth import verify_authenticated
from ..database import engine as db_engine
from ..models import ArtifactRecord, ArtifactVersionRecord, ArtifactPageRecord
from ..logging_config import get_logger

logger = get_logger("ArtifactsRouter")

router = APIRouter(tags=["Artifacts"])

ARTIFACTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "workspace", "artifacts"))
os.makedirs(ARTIFACTS_DIR, exist_ok=True)


def _build_topic_folder_path(category: str, title: str) -> str:
    import re, datetime
    clean_title = re.sub(r'[^a-zA-Z0-9]+', '_', title.lower()).strip('_')
    parts = [p for p in clean_title.split('_') if p][:4]
    slug = "_".join(parts) if parts else "artifact"
    date_str = datetime.date.today().strftime("%Y-%m-%d")
    folder_name = f"{date_str}_{slug}"
    cat_dir = category if category in ["research", "code", "presentations", "documents"] else "documents"
    path = os.path.join(ARTIFACTS_DIR, cat_dir, folder_name)
    os.makedirs(path, exist_ok=True)
    return path


def _get_artifact_storage_path(artifact_id: str, version: int, filename: str = "source.txt", title: str = "artifact", category: str = "documents") -> str:
    """Returns human-readable absolute file storage path under ./workspace/artifacts/<category>/<YYYY-MM-DD_topic_slug>/."""
    folder = _build_topic_folder_path(category, title)
    # Write metadata.json catalog index inside topic folder
    meta_path = os.path.join(folder, "metadata.json")
    if not os.path.exists(meta_path):
        import datetime
        try:
            with open(meta_path, "w", encoding="utf-8") as mf:
                json.dump({
                    "artifact_id": artifact_id,
                    "title": title,
                    "category": category,
                    "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
                }, mf, indent=2)
        except Exception:
            pass
    return os.path.join(folder, filename)


def _format_artifact_response(artifact: ArtifactRecord, pages: Sequence[ArtifactPageRecord]) -> Dict[str, Any]:
    """Formats an ArtifactRecord into canonical JSON structure."""
    parsed_meta = {}
    if artifact.metadata_json:
        try:
            parsed_meta = json.loads(artifact.metadata_json)
        except Exception:
            pass

    return {
        "id": artifact.id,
        "workspaceId": artifact.workspace_id,
        "ownerId": artifact.owner_id,
        "kind": artifact.kind,
        "title": artifact.title,
        "mimeType": artifact.mime_type,
        "status": artifact.status,
        "currentVersion": artifact.current_version,
        "sourceUri": artifact.source_uri,
        "content": artifact.content,
        "pages": [
            {
                "id": p.id,
                "index": p.page_index,
                "title": p.title,
                "thumbnailUrl": p.thumbnail_uri or "",
                "renderUrl": p.render_uri or "",
                "html": p.html_content or ""
            }
            for p in pages
        ],
        "metadata": parsed_meta,
        "createdAt": artifact.created_at.isoformat(),
        "updatedAt": artifact.updated_at.isoformat()
    }


@router.post("/artifacts", dependencies=[Depends(verify_authenticated)])
async def create_artifact(payload: Dict[str, Any] = Body(...)):
    """Creates a new durable artifact and stores its initial version."""
    title = payload.get("title", "Untitled Artifact")
    kind = payload.get("kind", "text")
    mime_type = payload.get("mimeType", "text/plain")
    content = payload.get("content", "")
    metadata = payload.get("metadata", {})
    pages_input = payload.get("pages", [])

    artifact_id = f"art_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)

    # Save initial version content to disk as an atomic triad
    topic_folder = _build_topic_folder_path(kind, title)
    assets_folder = os.path.join(topic_folder, "assets")
    os.makedirs(assets_folder, exist_ok=True)

    # Copy referenced visual figures to assets/ if detected in markdown
    copied_assets = []
    if content:
        import re, shutil
        fig_refs = re.findall(r'(\/?workspace\/artifacts\/extracted_figures\/[^\s\)\"\']+)', content)
        for ref_path in set(fig_refs):
            clean_ref = ref_path.lstrip("/")
            if os.path.exists(clean_ref):
                asset_name = os.path.basename(clean_ref)
                dest_path = os.path.join(assets_folder, asset_name)
                try:
                    shutil.copy2(clean_ref, dest_path)
                    copied_assets.append({"original": clean_ref, "bundled": f"./assets/{asset_name}"})
                except Exception as cp_err:
                    logger.debug(f"[Artifacts] Asset bundle copy notice: {cp_err}")

    # Persist source.md and source.html
    md_path = os.path.join(topic_folder, "source.md")
    html_path = os.path.join(topic_folder, "source.html")
    meta_path = os.path.join(topic_folder, "metadata.json")

    with open(md_path, "w", encoding="utf-8") as f_md:
        f_md.write(content or "")

    # Basic HTML render if not provided
    html_content = content or ""
    if not html_content.strip().startswith("<!DOCTYPE") and not html_content.strip().startswith("<html"):
        html_content = f"<!DOCTYPE html>\n<html>\n<head><meta charset='utf-8'><title>{title}</title></head>\n<body>\n<pre>{content}</pre>\n</body>\n</html>"

    with open(html_path, "w", encoding="utf-8") as f_html:
        f_html.write(html_content)

    meta_payload = {
        "artifact_id": artifact_id,
        "title": title,
        "category": kind,
        "mime_type": mime_type,
        "created_at": now.isoformat(),
        "bundled_assets": copied_assets,
        **(metadata if isinstance(metadata, dict) else {})
    }
    with open(meta_path, "w", encoding="utf-8") as f_meta:
        json.dump(meta_payload, f_meta, indent=2)

    file_path = md_path if kind in ["text", "markdown", "documents"] else html_path
    source_uri = f"/api/v1/artifacts/{artifact_id}/file"

    with Session(db_engine) as session:
        artifact = ArtifactRecord(
            id=artifact_id,
            workspace_id="default",
            owner_id="user",
            title=title,
            kind=kind,
            mime_type=mime_type,
            status="ready",
            current_version=1,
            source_uri=source_uri,
            content=content,
            metadata_json=json.dumps(meta_payload),
            created_at=now,
            updated_at=now
        )
        session.add(artifact)

        version_rec = ArtifactVersionRecord(
            id=f"ver_{uuid.uuid4().hex[:12]}",
            artifact_id=artifact_id,
            version=1,
            created_by="agent",
            reason="Initial creation",
            content=content,
            content_uri=file_path,
            created_at=now
        )
        session.add(version_rec)

        created_pages = []
        if pages_input and isinstance(pages_input, list):
            for idx, p in enumerate(pages_input):
                page_rec = ArtifactPageRecord(
                    id=f"pg_{uuid.uuid4().hex[:12]}",
                    artifact_id=artifact_id,
                    version=1,
                    page_index=idx,
                    title=p.get("title", f"Page {idx+1}"),
                    thumbnail_uri=p.get("thumbnailUrl"),
                    render_uri=p.get("renderUrl"),
                    html_content=p.get("html")
                )
                session.add(page_rec)
                created_pages.append(page_rec)

        session.commit()
        session.refresh(artifact)

    logger.info(f"[Artifacts] Created artifact '{title}' (ID: {artifact_id}, kind: {kind})")
    return _format_artifact_response(artifact, created_pages)


@router.get("/artifacts", dependencies=[Depends(verify_authenticated)])
async def list_artifacts(limit: int = Query(50, ge=1, le=500)):
    """Lists all active workspace artifacts."""
    with Session(db_engine) as session:
        artifacts = session.exec(
            select(ArtifactRecord)
            .order_by(col(ArtifactRecord.updated_at).desc())
            .limit(limit)
        ).all()

        results = []
        for art in artifacts:
            pages = session.exec(
                select(ArtifactPageRecord)
                .where(
                    ArtifactPageRecord.artifact_id == art.id,
                    ArtifactPageRecord.version == art.current_version
                )
                .order_by(col(ArtifactPageRecord.page_index).asc())
            ).all()
            results.append(_format_artifact_response(art, pages))

    return {"artifacts": results}


@router.get("/artifacts/{artifact_id}", dependencies=[Depends(verify_authenticated)])
async def get_artifact(artifact_id: str):
    """Retrieves metadata and page details for an artifact."""
    with Session(db_engine) as session:
        artifact = session.get(ArtifactRecord, artifact_id)
        if not artifact:
            raise HTTPException(status_code=404, detail=f"Artifact '{artifact_id}' not found")

        pages = session.exec(
            select(ArtifactPageRecord)
            .where(
                ArtifactPageRecord.artifact_id == artifact_id,
                ArtifactPageRecord.version == artifact.current_version
            )
            .order_by(col(ArtifactPageRecord.page_index).asc())
        ).all()

        return _format_artifact_response(artifact, pages)


@router.patch("/artifacts/{artifact_id}", dependencies=[Depends(verify_authenticated)])
async def update_artifact(artifact_id: str, payload: Dict[str, Any] = Body(...)):
    """Creates a new immutable version (v_{n+1}) of an existing artifact."""
    content = payload.get("content")
    reason = payload.get("reason", "Updated content")
    title = payload.get("title")

    with Session(db_engine) as session:
        artifact = session.get(ArtifactRecord, artifact_id)
        if not artifact:
            raise HTTPException(status_code=404, detail=f"Artifact '{artifact_id}' not found")

        next_version = artifact.current_version + 1
        now = datetime.now(timezone.utc)

        ext = ".html" if artifact.kind in ["html", "web"] else (".json" if artifact.kind == "data" else ".txt")
        file_path = _get_artifact_storage_path(artifact_id, next_version, f"source{ext}")
        if content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

        if title:
            artifact.title = title
        if content:
            artifact.content = content
        artifact.current_version = next_version
        artifact.updated_at = now
        session.add(artifact)

        version_rec = ArtifactVersionRecord(
            id=f"ver_{uuid.uuid4().hex[:12]}",
            artifact_id=artifact_id,
            version=next_version,
            created_by="agent",
            reason=reason,
            content=content,
            content_uri=file_path,
            created_at=now
        )
        session.add(version_rec)

        session.commit()
        session.refresh(artifact)

        pages = session.exec(
            select(ArtifactPageRecord)
            .where(
                ArtifactPageRecord.artifact_id == artifact_id,
                ArtifactPageRecord.version == next_version
            )
            .order_by(col(ArtifactPageRecord.page_index).asc())
        ).all()

        logger.info(f"[Artifacts] Updated artifact '{artifact_id}' to version {next_version}")
        return _format_artifact_response(artifact, pages)


@router.get("/artifacts/{artifact_id}/versions", dependencies=[Depends(verify_authenticated)])
async def list_artifact_versions(artifact_id: str):
    """Retrieves all version history records for an artifact."""
    with Session(db_engine) as session:
        versions = session.exec(
            select(ArtifactVersionRecord)
            .where(ArtifactVersionRecord.artifact_id == artifact_id)
            .order_by(col(ArtifactVersionRecord.version).desc())
        ).all()

        return {
            "artifact_id": artifact_id,
            "versions": [
                {
                    "id": v.id,
                    "version": v.version,
                    "createdBy": v.created_by,
                    "reason": v.reason,
                    "createdAt": v.created_at.isoformat()
                }
                for v in versions
            ]
        }


@router.get("/artifacts/{artifact_id}/file")
async def serve_artifact_file(artifact_id: str, version: Optional[int] = Query(None)):
    """Serves raw artifact content for safe sandboxed iframe rendering or download."""
    with Session(db_engine) as session:
        artifact = session.get(ArtifactRecord, artifact_id)
        if not artifact:
            raise HTTPException(status_code=404, detail="Artifact not found")

        target_version = version or artifact.current_version
        ext = ".html" if artifact.kind in ["html", "web"] else (".json" if artifact.kind == "data" else ".txt")
        file_path = _get_artifact_storage_path(artifact_id, target_version, f"source{ext}")

        if os.path.exists(file_path):
            return FileResponse(file_path, media_type=artifact.mime_type)

        if artifact.content:
            return Response(content=artifact.content, media_type=artifact.mime_type)

        raise HTTPException(status_code=404, detail="Artifact file payload not found")


@router.get("/artifacts/extracted_figures/{doc_slug}/{filename}")
async def serve_extracted_figure(doc_slug: str, filename: str):
    """Serves an extracted technical figure image directly."""
    # Sanitize doc_slug and filename to prevent path traversal
    safe_slug = os.path.basename(doc_slug)
    safe_filename = os.path.basename(filename)
    fig_path = os.path.abspath(os.path.join(ARTIFACTS_DIR, "extracted_figures", safe_slug, safe_filename))

    # Verify path is inside ARTIFACTS_DIR
    if not fig_path.startswith(ARTIFACTS_DIR):
        raise HTTPException(status_code=403, detail="Access denied")

    if not os.path.exists(fig_path):
        raise HTTPException(status_code=404, detail=f"Figure '{safe_filename}' not found")

    ext = os.path.splitext(safe_filename)[1].lower()
    media_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".svg": "image/svg+xml",
        ".webp": "image/webp",
        ".gif": "image/gif"
    }
    media_type = media_types.get(ext, "application/octet-stream")
    return FileResponse(fig_path, media_type=media_type)

