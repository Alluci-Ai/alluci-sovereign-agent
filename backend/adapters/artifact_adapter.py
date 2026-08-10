"""
Artifact Adapter for Orchestrator Tool Execution
=================================================

Handles semantic artifact creation, updates, opening, and exporting
via the backend Artifact API.
"""

from typing import Dict, Any, Optional
from .base import Adapter
from ..routers.artifacts import create_artifact, update_artifact, get_artifact
from ..logging_config import get_logger

logger = get_logger("ArtifactAdapter")


class ArtifactAdapter(Adapter):
    name: str = "artifact"
    description: str = "Creates, updates, opens, and exports durable visual and code workspace artifacts"

    async def execute(self, args: Dict[str, Any]) -> Any:
        action = args.get("action", "create")
        
        if action in ["create", "artifact_create"]:
            payload = {
                "title": args.get("title", "Untitled Artifact"),
                "kind": args.get("kind", "text"),
                "mimeType": args.get("mimeType", "text/plain"),
                "content": args.get("content", ""),
                "metadata": args.get("metadata", {}),
                "pages": args.get("pages", [])
            }
            res = await create_artifact(payload)
            return {
                "status": "success",
                "artifactId": res["id"],
                "version": res["currentVersion"],
                "title": res["title"],
                "kind": res["kind"],
                "message": f"Created artifact '{res['title']}' (ID: {res['id']})"
            }

        elif action in ["update", "artifact_update"]:
            artifact_id = args.get("artifactId") or args.get("id")
            if not artifact_id:
                return {"status": "error", "message": "Missing required 'artifactId'"}

            payload = {
                "content": args.get("content"),
                "reason": args.get("reason", "Agent update"),
                "title": args.get("title")
            }
            res = await update_artifact(artifact_id, payload)
            return {
                "status": "success",
                "artifactId": res["id"],
                "version": res["currentVersion"],
                "title": res["title"],
                "message": f"Updated artifact '{res['title']}' to version {res['currentVersion']}"
            }

        elif action in ["open", "artifact_open"]:
            artifact_id = args.get("artifactId") or args.get("id")
            if not artifact_id:
                return {"status": "error", "message": "Missing required 'artifactId'"}

            res = await get_artifact(artifact_id)
            return {
                "status": "success",
                "artifactId": res["id"],
                "artifact": res,
                "message": f"Opened artifact '{res['title']}'"
            }

        elif action in ["export", "artifact_export"]:
            artifact_id = str(args.get("artifactId") or args.get("id") or "")
            if not artifact_id:
                return {"status": "error", "message": "Missing required 'artifactId'"}
            fmt = str(args.get("format", "html"))
            res = await get_artifact(artifact_id)
            return {
                "status": "success",
                "artifactId": artifact_id,
                "format": fmt,
                "downloadUrl": res.get("sourceUri"),
                "message": f"Exported artifact '{artifact_id}' as {fmt}"
            }

        return {"status": "error", "message": f"Unknown artifact action '{action}'"}
