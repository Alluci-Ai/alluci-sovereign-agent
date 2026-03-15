
import logging
from ..logging_config import get_logger
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import PlainTextResponse
from sqlmodel import Session, select, text
from ..config import settings
from ..database import engine as db_engine
from ..models import SystemStatus, AuditEntry
from ..security.auth import verify_authenticated
from .. import services

logger = get_logger("SystemRouter")

router = APIRouter(tags=["System Status"])

@router.get("/health")
async def health_check():
    """Public Kubernetes-style liveness probe."""
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

@router.get("/api/system/health", dependencies=[Depends(verify_authenticated)])
async def get_detailed_health():
    """Runs diagnostic checks across primary modules for the Health dashboard."""
    import time
    from ..metrics import metrics
    
    # 1. Database
    db_status = "healthy"
    try:
        with Session(db_engine) as session:
            session.exec(text("SELECT 1"))
    except Exception:
        db_status = "unhealthy"
 
    # 2. Vault Security
    vault_status = "healthy" if services.vault else "warning"
 
    # 3. Model Router
    router_status = "unhealthy"
    if services.router:
        router_status = "warning"  # configured but providers might not be verified
 
    # 4. Local Inference
    local_inference_status = "healthy" if services.local_inference else "unhealthy"
 
    # 5. Bridges
    active_bridges = list(services.vault.get_active_vaults()) if services.vault else []
 
    # 6. Cron Engine Tasks
    cron_status = "healthy" if services.task_manager else "unhealthy"
 
    return {
        "database": db_status,
        "vault": vault_status,
        "model_router": router_status,
        "local_inference": local_inference_status,
        "bridges": len(active_bridges),
        "cron_engine": cron_status,
        "uptime": time.time() - metrics.start_time,
    }

@router.get("/ready")
async def readiness_check():
    """
    Public readiness check for Kubernetes health.
    """
    checks = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": "unstable",
        "orchestrator": "online" if services.orchestrator else "starting",
        "ace": "online" if services.ace else "offline",
    }
    try:
        with Session(db_engine) as session:
            session.exec(text("SELECT 1"))
        checks["database"] = "stable"
    except Exception as e:
        logger.error(f"[ HEALTH ]: Database integrity check failed: {e}")
        raise HTTPException(status_code=503, detail="Database unresponsive")

    if services.redis_client:
        try:
            await services.redis_client.ping()
            checks["redis"] = "stable"
        except Exception as e:
            logger.error(f"[ HEALTH ]: Redis ping failed: {e}")
            checks["redis"] = "failing"
    else:
        checks["redis"] = "inactive"

    return {"status": "ready", "checks": checks}

@router.get("/api/system/ready", dependencies=[Depends(verify_authenticated)])
async def api_readiness_check():
    """Protected readiness check."""
    return await readiness_check()

@router.get("/status", dependencies=[Depends(verify_authenticated)])
@router.get("/api/system/status", dependencies=[Depends(verify_authenticated)])
async def get_system_status():
    """High-level system status and resource metrics."""
    import psutil
    cpu = psutil.cpu_percent()
    mem = psutil.virtual_memory().percent
    
    return {
        "status": "active",
        "environment": settings.APP_ENV,
        "resources": {
            "cpu": f"{cpu}%",
            "memory": f"{mem}%",
        },
        "services": {
            "ace": "online" if services.ace else "offline",
            "vault": "mounted" if services.vault else "unmounted",
            "orchestrator": "ready" if services.orchestrator else "init"
        }
    }

@router.get("/metrics", response_class=PlainTextResponse)
async def get_prometheus_metrics():
    """Prometheus-compatible metrics endpoint."""
    from ..metrics import metrics
    return metrics.generate_latest()

@router.get("/api/audit/ledger", dependencies=[Depends(verify_authenticated)])
async def get_audit_ledger(limit: int = 50, offset: int = 0, status: Optional[str] = None):
    from ..security.audit_ledger import read_audit_log
    return await read_audit_log(limit=limit, offset=offset, status=status)

@router.post("/api/audit/entry", dependencies=[Depends(verify_authenticated)])
async def add_audit_entry(entry: AuditEntry):
    from ..security.audit_ledger import sync_audit_entry
    return await sync_audit_entry(entry)
