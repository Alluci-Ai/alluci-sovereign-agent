"""
backend/routers/usage.py — Usage & Cost Analytics Gateway Endpoints
Sovereign Spec 4.0 - Usage Analytics & Telemetry API
"""

import io
import csv
from dateutil import parser
from datetime import date
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query, Request, Response

from ..security.auth import verify_authenticated, verify_token
from ..logging_config import get_logger
from .. import services

logger = get_logger("UsageRouter")

router = APIRouter(prefix="/usage", tags=["Usage & Analytics"])


def parse_date_query(d_str: Optional[str]) -> Optional[date]:
    if not d_str or d_str.strip() == "":
        return None
    try:
        return date.fromisoformat(d_str)
    except ValueError:
        try:
            return parser.parse(d_str).date()
        except Exception:
            return None


@router.get("/summary", dependencies=[Depends(verify_authenticated)])
async def get_usage_summary(
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None)
):
    """Returns high-level aggregate token and cost usage stats."""
    if not services.usage_tracker:
        raise HTTPException(status_code=503, detail="Usage tracker service unavailable")
    s_date = parse_date_query(start)
    e_date = parse_date_query(end)
    return services.usage_tracker.get_summary(start=s_date, end=e_date)


@router.get("/daily", dependencies=[Depends(verify_authenticated)])
async def get_usage_daily(
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None)
):
    """Returns daily time-series token and cost rollups for chart rendering."""
    if not services.usage_tracker:
        raise HTTPException(status_code=503, detail="Usage tracker service unavailable")
    s_date = parse_date_query(start)
    e_date = parse_date_query(end)
    return services.usage_tracker.get_daily(start=s_date, end=e_date)


@router.get("/sessions", dependencies=[Depends(verify_authenticated)])
async def get_usage_sessions(
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    limit: int = Query(1000, ge=1, le=5000)
):
    """Returns session-aggregated usage and cost breakdown."""
    if not services.usage_tracker:
        raise HTTPException(status_code=503, detail="Usage tracker service unavailable")
    s_date = parse_date_query(start)
    e_date = parse_date_query(end)
    return services.usage_tracker.get_sessions(start=s_date, end=e_date, limit=limit)


@router.get("/sessions/{session_key}/timeseries", dependencies=[Depends(verify_authenticated)])
async def get_session_timeseries(session_key: str):
    """Returns turn-by-turn cumulative cost and token time-series for a specific session."""
    if not services.usage_tracker:
        raise HTTPException(status_code=503, detail="Usage tracker service unavailable")
    return services.usage_tracker.get_session_timeseries(session_key)


@router.get("/sessions/export/csv")
async def export_usage_csv(
    request: Request,
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    auth_token: Optional[str] = Query(None, alias="token")
):
    """
    Exports session usage and cost breakdown as a downloadable CSV.
    Supports authentication via Bearer header or token query parameter for direct browser downloads.
    """
    if not services.usage_tracker:
        raise HTTPException(status_code=503, detail="Usage tracker service unavailable")

    # Authenticate token from header or query string parameter
    auth_header = request.headers.get("Authorization")
    user_payload = None
    if auth_header and auth_header.startswith("Bearer "):
        jwt_cred = auth_header.split(" ")[1]
        try:
            user_payload = verify_token(jwt_cred)
        except Exception:
            pass

    if not user_payload and auth_token:
        try:
            user_payload = verify_token(auth_token)
        except Exception:
            pass

    if not user_payload:
        raise HTTPException(status_code=401, detail="Authentication token required")

    s_date = parse_date_query(start)
    e_date = parse_date_query(end)
    data = services.usage_tracker.get_sessions(start=s_date, end=e_date, limit=5000)
    sessions_list = data.get("sessions", [])

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Session Key", "Agent", "Provider", "Models", "Total Input Tokens",
        "Total Output Tokens", "Cache Read", "Cache Write", "Total Cost ($)",
        "Turn Count", "Messages", "First Turn", "Last Turn"
    ])

    for s in sessions_list:
        writer.writerow([
            s.get("session_key", ""),
            s.get("agent", ""),
            s.get("provider", ""),
            ", ".join(s.get("models", [])),
            s.get("total_input", 0),
            s.get("total_output", 0),
            s.get("total_cache_read", 0),
            s.get("total_cache_write", 0),
            f"{s.get('total_cost', 0.0):.6f}",
            s.get("turn_count", 0),
            s.get("messages", 0),
            s.get("first_turn", ""),
            s.get("last_turn", "")
        ])

    csv_content = output.getvalue()
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=usage_export_{date.today().isoformat()}.csv"}
    )
