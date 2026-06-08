# backend/routers/egress.py
"""Egress configuration management router.
Provides admin endpoints to view and update allowed LLM hosts and rotation schedule.
All endpoints are protected by admin authentication (verify_admin dependency).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
import yaml, json, os
from typing import Optional
from pathlib import Path

from ..security.auth import verify_admin  # assume admin auth dependency exists

router = APIRouter()

# Paths for configuration files (mounted as volumes)
BASE_DIR = Path(__file__).resolve().parent.parent
ALLOWED_HOSTS_PATH = BASE_DIR / "allowed_llm_hosts.yaml"
ROTATION_SCHEDULE_PATH = BASE_DIR / "rotation_schedule.json"

class AllowedHosts(BaseModel):
    hosts: list[str] = Field(..., description="List of allowed LLM hostnames")

class RotationSchedule(BaseModel):
    interval_days: int = Field(30, ge=1, description="Rotation interval in days")
    last_rotated: Optional[str] = Field(None, description="ISO timestamp of last rotation")

def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {"hosts": []}
    with open(path, "r") as f:
        return yaml.safe_load(f) or {}

def _save_yaml(path: Path, data: dict) -> None:
    with open(path, "w") as f:
        yaml.safe_dump(data, f)

def _load_json(path: Path) -> dict:
    if not path.exists():
        return {"interval_days": 30, "last_rotated": None}
    with open(path, "r") as f:
        return json.load(f)

def _save_json(path: Path, data: dict) -> None:
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

@router.get("/egress/hosts", response_model=AllowedHosts, tags=["admin"])
def get_allowed_hosts(admin: None = Depends(verify_admin)):
    data = _load_yaml(ALLOWED_HOSTS_PATH)
    return AllowedHosts(hosts=data.get("hosts", []))

@router.post("/egress/hosts", response_model=AllowedHosts, status_code=status.HTTP_200_OK, tags=["admin"])
def update_allowed_hosts(payload: AllowedHosts, admin: None = Depends(verify_admin)):
    _save_yaml(ALLOWED_HOSTS_PATH, {"hosts": payload.hosts})
    return payload

@router.get("/egress/rotation", response_model=RotationSchedule, tags=["admin"])
def get_rotation_schedule(admin: None = Depends(verify_admin)):
    data = _load_json(ROTATION_SCHEDULE_PATH)
    return RotationSchedule(**data)

@router.post("/egress/rotation", response_model=RotationSchedule, status_code=status.HTTP_200_OK, tags=["admin"])
def update_rotation_schedule(payload: RotationSchedule, admin: None = Depends(verify_admin)):
    _save_json(ROTATION_SCHEDULE_PATH, payload.model_dump())
    return payload

# Optional: endpoint to trigger manual rotation
@router.post("/egress/rotate", status_code=status.HTTP_202_ACCEPTED, tags=["admin"])
def trigger_rotation(admin: None = Depends(verify_admin)):
    # This would enqueue a background task; placeholder implementation
    # For now, just update last_rotated timestamp
    from datetime import datetime, timezone
    schedule = _load_json(ROTATION_SCHEDULE_PATH)
    schedule["last_rotated"] = datetime.now(timezone.utc).isoformat()
    _save_json(ROTATION_SCHEDULE_PATH, schedule)
    return {"detail": "Rotation triggered"}
