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


def _get_artifact_storage_path(artifact_id: str, version: int, filename: str = "source.txt") -> str:
    """Returns absolute file storage path under ./workspace/artifacts/<artifact_id>/versions/<version>/."""
    path = os.path.join(ARTIFACTS_DIR, artifact_id, "versions", str(version))
    os.makedirs(path, exist_ok=True)
    return os.path.join(path, filename)


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

    # Save initial version content to disk
    ext = ".html" if kind in ["html", "web"] else (".json" if kind == "data" else ".txt")
    file_path = _get_artifact_storage_path(artifact_id, 1, f"source{ext}")
    if content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

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
            metadata_json=json.dumps(metadata) if metadata else None,
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
