
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends, Body
from ..security.auth import verify_authenticated
from .. import services

logger = logging.getLogger("CronsRouter")

router = APIRouter(tags=["Cron Scheduler"])

@router.get("/api/cron/jobs", dependencies=[Depends(verify_authenticated)])
async def list_cron_jobs():
    """List all cron jobs."""
    if not services.cron_engine:
        raise HTTPException(status_code=503, detail="Cron engine not initialized")
    return services.cron_engine.list_jobs()

@router.get("/api/cron/jobs/{job_id}", dependencies=[Depends(verify_authenticated)])
async def get_cron_job(job_id: int):
    """Get a specific cron job."""
    if not services.cron_engine:
        raise HTTPException(status_code=503, detail="Cron engine not initialized")
    job = services.cron_engine.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@router.post("/api/cron/jobs", dependencies=[Depends(verify_authenticated)])
async def create_cron_job(data: Dict[str, Any] = Body(...)):
    """Create a new scheduled task."""
    if not services.cron_engine:
        raise HTTPException(status_code=503, detail="Cron engine not initialized")
    return await services.cron_engine.create_job(data)

@router.delete("/api/cron/jobs/{job_id}", dependencies=[Depends(verify_authenticated)])
async def delete_cron_job(job_id: int):
    """Remove a scheduled task."""
    if not services.cron_engine:
        raise HTTPException(status_code=503, detail="Cron engine not initialized")
    success = await services.cron_engine.delete_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"status": "SUCCESS"}
