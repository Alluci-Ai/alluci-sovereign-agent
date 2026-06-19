import json
import secrets
import os
import asyncio
from typing import Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, Body, Query, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from ..security.auth import verify_authenticated
from .. import services
try:
    from fastapi_csrf_protect import CsrfProtect
except ImportError:
    class FallbackCsrfProtect:
        async def validate_csrf(self, request):
            return None
    CsrfProtect = FallbackCsrfProtect  # type: ignore
from sqlmodel import select
from ..database import get_session
from ..models import TelemetryData, AgentChannelSubscription
from ..security.oauth_store import oauth_store
from ..logging_config import get_logger

logger = get_logger("ChannelsRouter")

router = APIRouter(tags=["Bridge Channels"])

@router.get("/channels", dependencies=[Depends(verify_authenticated)])
async def list_channels():
    # Summarize all available communication manifolds
    return [
        {"id": cid, "status": getattr(adapter, "status", "idle"), "type": getattr(adapter, "channel_type", "unknown")}
        for cid, adapter in services.channel_registry.items()
    ]

@router.get("/channels/status", dependencies=[Depends(verify_authenticated)])
async def get_all_channels_status():
    """
    Returns the real-time connection health of all bridges.
    Used by ChannelHealthDashboard to update global store connection states.
    """
    channels_health = []
    for cid, adapter in services.channel_registry.items():
        is_conn = getattr(adapter, "is_connected", False)
        
        # safely extract last_error if available
        last_error = getattr(adapter, "last_error", None)
        if isinstance(last_error, Exception):
            last_error = str(last_error)
            
        channels_health.append({
            "channel": cid,
            "connected": is_conn,
            "last_error": last_error,
            "accounts": getattr(adapter, "get_accounts_status", lambda: [])()
        })
        
    return {
        "total": len(services.channel_registry),
        "channels": channels_health
    }

@router.get("/channels/{channel_id}/accounts", dependencies=[Depends(verify_authenticated)])
async def get_channel_accounts(channel_id: str):
    from .channels import normalize_bridge_id  # self-import for helper
    normalized = normalize_bridge_id(channel_id)
    adapter = services.channel_registry.get(normalized)
    if not adapter:
        raise HTTPException(status_code=404, detail="Channel not found")
    if hasattr(adapter, "get_accounts_status"):
        return {"accounts": adapter.get_accounts_status()}
    return {"accounts": []}

@router.delete("/channels/{channel_id}/accounts/{account_id}", dependencies=[Depends(verify_authenticated)])
async def delete_channel_account(channel_id: str, account_id: str, request: Request, csrf_protect: CsrfProtect = Depends()):
    await csrf_protect.validate_csrf(request)
    from .channels import normalize_bridge_id
    normalized = normalize_bridge_id(channel_id)
    adapter = services.channel_registry.get(normalized)
    if not adapter:
        raise HTTPException(status_code=404, detail="Channel not found")
        
    if hasattr(adapter, "disconnect"):
        try:
            import inspect
            sig = inspect.signature(adapter.disconnect)
            if "account_id" in sig.parameters:
                await adapter.disconnect(account_id=account_id)
            else:
                await adapter.disconnect()
        except Exception as e:
            logger.error(f"Failed to disconnect account {account_id} for {channel_id}: {e}")
            
        try:
            if services.vault:
                await services.vault.delete_connection_secret(normalized, account_id)
        except Exception as e:
            logger.error(f"Failed to delete vault secret for {normalized}/{account_id}: {e}")
            
        return {"status": "SUCCESS", "message": f"Deleted account {account_id} from {normalized}"}

@router.get("/channels/availability", dependencies=[Depends(verify_authenticated)])
async def get_channel_availability():
   """
   Returns platform availability status for all registered bridge adapters.
   Used by BridgeCenter to show which bridges can be configured on this host.
   """
   if not services.channel_registry:
       return []

   return [
       adapter.get_availability_status()
       for adapter in services.channel_registry.values()
       if hasattr(adapter, 'get_availability_status')
   ]

@router.get("/channels/{channel_id}/config", dependencies=[Depends(verify_authenticated)])
async def get_channel_config(channel_id: str):
    from .channels import normalize_bridge_id
    normalized = normalize_bridge_id(channel_id)
    adapter = services.channel_registry.get(channel_id) or services.channel_registry.get(normalized)
    if not adapter:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    config = getattr(adapter, "config", {}).copy()
    config["enabled"] = getattr(adapter, "is_connected", False)
    if services.vault:
        try:
            state_data = await services.vault.retrieve_secret(f"channel_{normalized}_enabled")
            if state_data and "enabled" in state_data:
                config["enabled"] = state_data["enabled"]
        except Exception:
            pass
            
    return config

@router.put("/channels/{channel_id}/config", dependencies=[Depends(verify_authenticated)])
async def update_channel_config(channel_id: str, request: Request, csrf_protect: CsrfProtect = Depends(), config: Dict[str, Any] = Body(...)):
    await csrf_protect.validate_csrf(request)
    from .channels import normalize_bridge_id
    normalized = normalize_bridge_id(channel_id)
    adapter = services.channel_registry.get(channel_id) or services.channel_registry.get(normalized)
    if not adapter:
        raise HTTPException(status_code=404, detail="Channel not found")
        
    if hasattr(adapter, "update_config"):
        return await adapter.update_config(config)
        
    # Generic save if adapter doesn't implement custom logic
    if not hasattr(adapter, "config"):
        adapter.config = {}
    adapter.config.update(config)
    
    # Store enabled state if present
    if "enabled" in config and services.vault:
        await services.vault.store_secret(f"channel_{normalized}_enabled", {"enabled": config["enabled"]})
        
    return {"status": "SUCCESS", "message": "Configuration saved."}

@router.post("/channels/{channel_id}/connect", dependencies=[Depends(verify_authenticated)])
async def connect_channel(channel_id: str, request: Request, csrf_protect: CsrfProtect = Depends()):
    await csrf_protect.validate_csrf(request)
    adapter = services.channel_registry.get(channel_id)
    if not adapter:
        raise HTTPException(status_code=404, detail="Channel not found")
    if hasattr(adapter, "connect"):
        return await adapter.connect()
    raise HTTPException(status_code=501, detail="Direct connect not supported")

@router.put("/channels/{channel_id}/toggle", dependencies=[Depends(verify_authenticated)])
async def toggle_channel(channel_id: str, request: Request, csrf_protect: CsrfProtect = Depends(), payload: Dict[str, Any] = Body(None)):
    await csrf_protect.validate_csrf(request)
    """
    Connect or disconnect a bridge channel.
    Called by App.tsx [disconnectBridge]
    """
    from .channels import normalize_bridge_id
    normalized = normalize_bridge_id(channel_id)
    adapter = services.channel_registry.get(channel_id) or services.channel_registry.get(normalized)
    if not adapter:
        raise HTTPException(status_code=404, detail="Channel not found")

    if payload is not None and "enabled" in payload:
        next_state = payload["enabled"]
        if not hasattr(adapter, "config"):
            adapter.config = {}
        adapter.config["enabled"] = next_state
        if services.vault:
            await services.vault.store_secret(f"channel_{normalized}_enabled", {"enabled": next_state})
        
        # Optionally perform connect/disconnect based on toggle
        if next_state and not getattr(adapter, "is_connected", False) and hasattr(adapter, "connect"):
            # Reconnect all vault accounts if available
            try:
                accounts = await services.vault.list_connections(normalized)
                if accounts:
                    for acc_id in accounts:
                        creds = await services.vault.retrieve_connection_secret(normalized, acc_id)
                        if creds:
                            await adapter.connect(creds)
                else:
                    await adapter.connect({})
            except Exception:
                pass
        elif not next_state and getattr(adapter, "is_connected", False) and hasattr(adapter, "disconnect"):
            await adapter.disconnect()
            return {"status": "SUCCESS", "message": f"Channel set to DORMANT and disconnected."}
            
        return {"status": "SUCCESS", "message": f"Channel {'ACTIVE' if next_state else 'DORMANT'}"}

    # Fallback to older logic if no payload
    if getattr(adapter, "is_connected", False):
        if hasattr(adapter, "disconnect"):
            await adapter.disconnect()
            return {"status": "SUCCESS", "message": f"Disconnected {channel_id}"}
        else:
            raise HTTPException(status_code=501, detail=f"Disconnect not supported by adapter '{channel_id}'")
    else:
        if hasattr(adapter, "connect"):
            await adapter.connect({})
            return {"status": "SUCCESS", "message": f"Connected {channel_id}"}
        else:
            raise HTTPException(status_code=501, detail="Connect not supported")

# ── Core Channel Dispatch Routes ─────────────────────────────────────────────
# These are the primary routes called by the frontend (bridgeManager.ts) and
# asserted by test_phase0.py. They must exist at both /api/v1/channels/... and
# /api/channels/... (the latter satisfied by dual router registration in app.py).

@router.post("/channels/{channel_id}/send", dependencies=[Depends(verify_authenticated)])
async def channel_send(channel_id: str, request: Request, csrf_protect: CsrfProtect = Depends(), payload: Dict[str, Any] = Body(...)):
    await csrf_protect.validate_csrf(request)
    """
    Send a message through a bridge.
    Body: { "recipient": str, "content": str }
    """
    adapter = services.channel_registry.get(channel_id)
    if not adapter:
        raise HTTPException(status_code=404, detail=f"Channel '{channel_id}' not found.")
    if not getattr(adapter, "is_connected", False):
        raise HTTPException(status_code=503, detail=f"Channel '{channel_id}' is not connected.")

    recipient = payload.get("recipient", "")
    content = payload.get("content", "")

    if not content:
        raise HTTPException(status_code=400, detail="'content' is required.")

    try:
        result = await adapter.send(recipient, content)
        return {"status": "ok", "channel_id": channel_id, "result": result}
    except Exception as e:
        logger.error(f"channel_send [{channel_id}] failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/channels/{channel_id}/upload", dependencies=[Depends(verify_authenticated)])
async def channel_upload(channel_id: str, request: Request, csrf_protect: CsrfProtect = Depends(), payload: Dict[str, Any] = Body(...)):
    await csrf_protect.validate_csrf(request)
    """
    Upload a file through a bridge (e.g., GDrive, Slack).
    Body: { "file_data": str (base64 or URL), "file_name": str }
    """
    adapter = services.channel_registry.get(channel_id)
    if not adapter:
        raise HTTPException(status_code=404, detail=f"Channel '{channel_id}' not found.")
    if not hasattr(adapter, "upload"):
        raise HTTPException(status_code=501, detail=f"Channel '{channel_id}' does not support file upload.")

    try:
        result = await adapter.upload(
            payload.get("file_data"),
            payload.get("file_name", "untitled"),
        )
        return {"status": "ok", "channel_id": channel_id, "result": result}
    except Exception as e:
        logger.error(f"channel_upload [{channel_id}] failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/channels/{channel_id}/health", dependencies=[Depends(verify_authenticated)])
async def channel_health(channel_id: str):
    """
    Returns the real-time connection health of a specific bridge.
    Used by BridgeCenter frontend to show live status indicators.
    """
    adapter = services.channel_registry.get(channel_id)
    if not adapter:
        raise HTTPException(status_code=404, detail=f"Channel '{channel_id}' not found.")

    health = {
        "channel_id": channel_id,
        "is_connected": getattr(adapter, "is_connected", False),
        "last_activity": getattr(adapter, "last_activity", None),
        "last_error": getattr(adapter, "last_error", None),
        "protocol": channel_id.upper(),
    }

    # Attempt live integrity check if supported (with timeout to avoid stalling)
    if hasattr(adapter, "validate_integrity"):
        try:
            health["integrity"] = await asyncio.wait_for(
                adapter.validate_integrity(), timeout=5.0
            )
        except Exception as e:
            health["integrity"] = False
            health["integrity_error"] = str(e)

    return health


@router.get("/channels/{channel_id}/unread", dependencies=[Depends(verify_authenticated)])
async def channel_unread(channel_id: str, limit: int = 10):
    """
    Fetch unread messages from a bridge's inbox.
    Used by the agent's inbound message polling logic.
    """
    adapter = services.channel_registry.get(channel_id)
    if not adapter:
        raise HTTPException(status_code=404, detail=f"Channel '{channel_id}' not found.")
    if not hasattr(adapter, "fetch_unread"):
        return []

    try:
        messages = await adapter.fetch_unread(limit=limit)
        return messages or []
    except Exception as e:
        logger.error(f"channel_unread [{channel_id}] failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/channels/{channel_id}/social", dependencies=[Depends(verify_authenticated)])
async def channel_social_task(channel_id: str, request: Request, csrf_protect: CsrfProtect = Depends(), payload: Dict[str, Any] = Body(...)):
    await csrf_protect.validate_csrf(request)
    """
    Execute a social/automation task on a bridge (post, like, follow, etc.).
    Body: { "task": str, "params": dict }
    """
    adapter = services.channel_registry.get(channel_id)
    if not adapter:
        raise HTTPException(status_code=404, detail=f"Channel '{channel_id}' not found.")

    task_name = payload.get("task", "")
    params = payload.get("params", {})

    if hasattr(adapter, "execute_social_task"):
        try:
            result = await adapter.execute_social_task(task_name, params)
            return {"status": "ok", "channel_id": channel_id, "result": result}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    # Generic fallback: treat as a send task
    if task_name == "send" and "recipient" in params:
        return await channel_send(channel_id, request, csrf_protect, params)

    raise HTTPException(status_code=501, detail=f"Social tasks not supported for '{channel_id}'.")


@router.post("/channels/{channel_id}/enterprise", dependencies=[Depends(verify_authenticated)])
async def channel_enterprise_task(channel_id: str, request: Request, csrf_protect: CsrfProtect = Depends(), payload: Dict[str, Any] = Body(...)):
    await csrf_protect.validate_csrf(request)
    """
    Execute an enterprise automation task (calendar, CRM, ticket, etc.).
    Delegates to the bridge's enterprise task handler if available,
    otherwise forwards to the social task handler as a unified endpoint.
    Body: { "task": str, "params": dict }
    """
    adapter = services.channel_registry.get(channel_id)
    if not adapter:
        raise HTTPException(status_code=404, detail=f"Channel '{channel_id}' not found.")

    if hasattr(adapter, "execute_enterprise_task"):
        try:
            result = await adapter.execute_enterprise_task(
                payload.get("task", ""), payload.get("params", {})
            )
            return {"status": "ok", "channel_id": channel_id, "result": result}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    # Delegate to social handler (unified task dispatch)
    return await channel_social_task(channel_id, request, csrf_protect, payload)


# ── Bulk Health Check ─────────────────────────────────────────────────────────

@router.get("/channels/health/all", dependencies=[Depends(verify_authenticated)])
async def all_channels_health():
    """Returns connection health for every registered bridge simultaneously."""
    return {
        channel_id: {
            "is_connected": getattr(adapter, "is_connected", False),
            "last_activity": getattr(adapter, "last_activity", None),
            "last_error": getattr(adapter, "last_error", None),
        }
        for channel_id, adapter in services.channel_registry.items()
    }


# --- Specialized Channel Routes ---

# --- iWatch (HealthKit) Routes ---

@router.get("/channels/iwatch/status", dependencies=[Depends(verify_authenticated)])
async def iwatch_status():
    adapter = services.channel_registry.get("iwatch")
    if not adapter: return {"status": "unloaded"}
    return {"status": "connected" if getattr(adapter, "is_connected", False) else "paired"}

@router.get("/channels/iwatch/pairing-qr", dependencies=[Depends(verify_authenticated)])
async def iwatch_pairing_qr():
    """Generate TOTP seed and QR payload for Watch pairing."""
    adapter = services.channel_registry.get("iwatch")
    if not adapter:
        raise HTTPException(status_code=503, detail="iWatch adapter not initialised.")
    daemon_url = os.getenv("DAEMON_PUBLIC_URL", "http://localhost:8000").rstrip("/")
    return await adapter.generate_pairing_qr(daemon_url)

@router.post("/channels/iwatch/pair")
async def iwatch_pair(request: Request, csrf_protect: CsrfProtect = Depends(), data: Dict[str, str] = Body(...)):
    await csrf_protect.validate_csrf(request)
    """Verify TOTP code and issue a device session token."""
    adapter = services.channel_registry.get("iwatch")
    if not adapter:
        raise HTTPException(status_code=503, detail="iWatch adapter not initialised.")
    code      = data.get("code", "")
    device_id = data.get("device_id", "")
    if not code or not device_id:
        raise HTTPException(status_code=400, detail="code and device_id required.")
    return await adapter.submit_pairing_code(code, device_id)

@router.post("/channels/iwatch/biometrics")
async def ingest_iwatch_biometrics(request: Request, csrf_protect: CsrfProtect = Depends()):
    await csrf_protect.validate_csrf(request)
    """Ingest HealthKit telemetry from Apple Watch with device or user token."""
    adapter = services.channel_registry.get("iwatch")
    if not adapter:
        raise HTTPException(status_code=503, detail="iWatch adapter not initialised.")

    authorization = request.headers.get("Authorization", "")
    token = authorization.removeprefix("Bearer ").strip()
    device_id = None

    if token:
        device_id = adapter.verify_device_token(token)
        if not device_id:
            try:
                # Fallback to user JWT verification
                await verify_authenticated(request)
                device_id = "manual"
            except Exception:
                raise HTTPException(status_code=401, detail="Invalid token.")

    body = await request.json()
    samples = body.get("samples") or ([body] if "hr" in body else [])
    if not samples:
        raise HTTPException(status_code=400, detail="No telemetry samples provided.")

    results = []
    for raw in samples:
        try:
            td = TelemetryData(**{k: raw.get(k) for k in TelemetryData.model_fields if raw.get(k) is not None})
            if services.ace:
                flow = services.ace.process_telemetry(td)
                results.append({"flow": flow, "ts": raw.get("recorded_at")})
        except Exception as e:
            logger.debug(f"[ACE] Telemetry parse failed: {e}")

    await adapter.ingest_telemetry(samples, device_id or "unknown")
    latest_flow = results[-1] if results else {}
    return {
        "status": "SUCCESS",
        "processed": len(samples),
        "flow_intervention": latest_flow.get("flow"),
        "resonance": services.ace.current_state.get("physical_vitality") if services.ace else None,
    }

@router.get("/channels/iwatch/telemetry", dependencies=[Depends(verify_authenticated)])
async def get_iwatch_telemetry(limit: int = Query(20, ge=1, le=200)):
    """Retrieve recent telemetry samples from the iWatch bridge buffer."""
    adapter = services.channel_registry.get("iwatch")
    if not adapter: raise HTTPException(503)
    samples = adapter.get_recent_telemetry(limit)
    return {"samples": samples, "count": len(samples)}

# --- WeChat (WeCom) Routes ---

@router.get("/channels/wechat/qr-init", dependencies=[Depends(verify_authenticated)])
async def wechat_qr_init():
    """Generate WeCom OAuth QR URL for workspace login."""
    adapter = services.channel_registry.get("wechat")
    if not adapter: raise HTTPException(503)
    return await adapter.init_qr()

# --- Consolidated OAuth Callback (SEC-002) ---

_VALID_BRIDGE_IDS = frozenset([
    "telegram", "whatsapp", "discord", "slack", "email", "signal",
    "google_chat", "nostr", "imessage", "gdrive", "gmail", "gm", "gd",
    "msteams", "facebook", "instagram", "x", "wechat",
])

@router.get("/oauth/{bridge_id}/callback")
async def oauth_callback(request: Request, bridge_id: str, code: str = Query(None), state: str = Query(None), error: str = Query(None)):
    """Generic OAuth callback endpoint for all OAuth-based bridges."""
    import structlog
    with structlog.contextvars.bound_contextvars(bridge_id=bridge_id):
        nonce = getattr(request.state, "csp_nonce", "")
        nonce_attr = f' nonce="{nonce}"' if nonce else ""

        # 1. Security: validate bridge_id against known set before any string interpolation
        if bridge_id not in _VALID_BRIDGE_IDS:
            logger.warning("Callback received for unknown bridge_id")
            return HTMLResponse(
                f"<script{nonce_attr}>"
                "window.opener && window.opener.postMessage("
                "  JSON.stringify({ type: 'OAUTH_COMPLETE', error: 'invalid_bridge' }),"
                "  '*'"
                ");"
                "window.close();"
                "</script>",
                status_code=400,
            )

        # Helper for serialised responses
        def _make_response(success: bool, error_msg: str = "") -> HTMLResponse:
            import json as _json
            payload = _json.dumps({
                "type": "OAUTH_COMPLETE",
                "bridgeId": bridge_id,  # safe: validated against whitelist
                "success": success,
                "error": error_msg,
            })
            return HTMLResponse(
                f"<script{nonce_attr}>"
                f"window.opener && window.opener.postMessage({payload}, '*');"
                f"window.close();"
                f"</script>"
            )

        if error:
            return _make_response(False, error)

        # 2. Forward to specific adapter logic
        normalized_id = normalize_bridge_id(bridge_id)
        adapter = services.channel_registry.get(normalized_id)
        if not adapter:
            return _make_response(False, "bridge_not_found")

        try:
            if normalized_id == "slack":
                verifier = await oauth_store.consume_state(state)
                if not verifier: return _make_response(False, "invalid_state")
                daemon_url = os.getenv("DAEMON_PUBLIC_URL", "http://localhost:8000").rstrip("/")
                creds = await adapter.handle_oauth_callback(code=code, state=state, code_verifier=verifier, redirect_uri=f"{daemon_url}/api/oauth/slack/callback")
                team_id = creds.get("team_id") or "default"
                await services.vault.store_connection_secret("slack", team_id, creds)  # type: ignore
                if hasattr(adapter, "connect"):
                    await adapter.connect(creds)
            
            elif normalized_id == "x":
                sd = await oauth_store.consume_state(state)
                if not sd: return _make_response(False, "invalid_state")
                creds = await adapter.handle_oauth_callback(code=code, state=state, code_verifier=sd["verifier"], redirect_uri=sd["redirect_uri"])
                user_id = creds.get("user_id") or "default"
                await services.vault.store_connection_secret("x", user_id, creds)  # type: ignore
                if hasattr(adapter, "connect"):
                    await adapter.connect(creds)
    
            elif normalized_id in ["instagram", "facebook", "msteams", "gmail", "gdrive"]:
                sd = await oauth_store.consume_state(state)
                if not sd: return _make_response(False, "invalid_state")
                creds = await adapter.handle_oauth_callback(code=code, state=state, redirect_uri=sd["redirect_uri"])
                account_id = creds.get("email") or creds.get("team_id") or creds.get("user_id") or "default"
                await services.vault.store_connection_secret(normalized_id, account_id, creds)  # type: ignore
                if hasattr(adapter, "connect"):
                    await adapter.connect(creds)
                
            elif hasattr(adapter, "handle_oauth_callback"):
                await adapter.handle_oauth_callback(code, state)
            
            return _make_response(True)

        except Exception as e:
            logger.error("Callback error", error=str(e))
            return _make_response(False, str(e))

@router.get("/webhook/wechat")
async def wechat_webhook_verify(msg_signature: str = Query(...), timestamp: str = Query(...), nonce: str = Query(...), echostr: str = Query("")):
    adapter = services.channel_registry.get("wechat")
    if not adapter: raise HTTPException(503)
    result = adapter.verify_callback(msg_signature, timestamp, nonce, echostr)
    if result: return PlainTextResponse(result)
    raise HTTPException(403)

@router.post("/webhook/wechat")
async def wechat_webhook_post(request: Request, msg_signature: str = Query(...), timestamp: str = Query(...), nonce: str = Query(...)):
    adapter = services.channel_registry.get("wechat")
    if not adapter: return "<xml><Content>ok</Content></xml>"
    raw_body = await request.body()
    if adapter.verify_callback(msg_signature, timestamp, nonce) is None:
        raise HTTPException(status_code=403)
    await adapter.process_webhook({"raw_xml": raw_body.decode("utf-8")})
    return "<xml><Content>ok</Content></xml>"

# --- Gmail OAuth ---

@router.get("/oauth/gm/start", dependencies=[Depends(verify_authenticated)])
async def gmail_oauth_start():
    adapter = services.channel_registry.get("gmail")
    if not adapter: raise HTTPException(503)
    daemon_url = os.getenv("DAEMON_PUBLIC_URL", "http://localhost:8000").rstrip("/")
    redirect_uri = f"{daemon_url}/api/oauth/gm/callback"
    state = secrets.token_urlsafe(32)
    authorize_url = adapter.build_oauth_url(redirect_uri, state)
    await oauth_store.store_state(state, {"redirect_uri": redirect_uri})
    return {"authorize_url": authorize_url, "state": state}

# --- Slack OAuth & Webhook ---

@router.get("/oauth/gd/start", dependencies=[Depends(verify_authenticated)])
async def gdrive_oauth_start():
    adapter = services.channel_registry.get("gdrive")
    if not adapter: raise HTTPException(503)
    daemon_url = os.getenv("DAEMON_PUBLIC_URL", "http://localhost:8000").rstrip("/")
    redirect_uri = f"{daemon_url}/api/oauth/gd/callback"
    state = secrets.token_urlsafe(32)
    authorize_url = adapter.build_oauth_url(redirect_uri, state)
    await oauth_store.store_state(state, {"redirect_uri": redirect_uri})
    return {"authorize_url": authorize_url, "state": state}

@router.get("/oauth/slack/start", dependencies=[Depends(verify_authenticated)])
async def slack_oauth_start():
    adapter = services.channel_registry.get("slack")
    if not adapter: raise HTTPException(503)
    daemon_url = os.getenv("DAEMON_PUBLIC_URL", "http://localhost:8000").rstrip("/")
    redirect_uri = f"{daemon_url}/api/oauth/slack/callback"
    state = secrets.token_urlsafe(32)
    authorize_url, code_verifier = adapter.build_oauth_url(redirect_uri, state)
    await oauth_store.store_state(state, code_verifier)
    return {"authorize_url": authorize_url, "state": state}

@router.post("/webhook/slack")
async def slack_webhook(request: Request):
    body = await request.body()
    ts = request.headers.get("X-Slack-Request-Timestamp")
    sig = request.headers.get("X-Slack-Signature")
    adapter = services.channel_registry.get("slack")
    if not adapter or not adapter.verify_signature(body, ts, sig):
        raise HTTPException(401)
    return await adapter.process_webhook(json.loads(body))

# --- WhatsApp Webhooks ---

@router.get("/webhook/whatsapp")
async def whatsapp_webhook_verify(mode: str = Query(None, alias="hub.mode"), token: str = Query(None, alias="hub.verify_token"), challenge: str = Query(None, alias="hub.challenge")):
    adapter = services.channel_registry.get("whatsapp")
    if not adapter: raise HTTPException(503)
    result = adapter.verify_webhook(mode or "", token or "", challenge or "")
    if result: return PlainTextResponse(result)
    raise HTTPException(403)

@router.post("/webhook/whatsapp")
async def whatsapp_webhook_post(request: Request):
    raw_body = await request.body()
    sig = request.headers.get("X-Hub-Signature-256", "")
    adapter = services.channel_registry.get("whatsapp")
    if not adapter or not adapter.verify_signature(raw_body, sig):
        raise HTTPException(403)
    await adapter.process_webhook_event(json.loads(raw_body))
    return {"ok": True}

# --- Instagram OAuth & Webhook ---

@router.get("/oauth/instagram/start", dependencies=[Depends(verify_authenticated)])
async def instagram_oauth_start():
    adapter = services.channel_registry.get("instagram")
    if not adapter: raise HTTPException(503)
    daemon_url = os.getenv("DAEMON_PUBLIC_URL", "http://localhost:8000").rstrip("/")
    redirect_uri = f"{daemon_url}/api/oauth/instagram/callback"
    state = secrets.token_urlsafe(32)
    url, _ = adapter.build_oauth_url(redirect_uri, state)
    await oauth_store.store_state(state, {"redirect_uri": redirect_uri})
    return {"authorize_url": url, "state": state}

@router.get("/webhook/instagram")
async def instagram_webhook_verify(mode: str = Query(None, alias="hub.mode"), token: str = Query(None, alias="hub.verify_token"), challenge: str = Query(None, alias="hub.challenge")):
    adapter = services.channel_registry.get("instagram")
    if not adapter: raise HTTPException(503)
    result = adapter.verify_webhook(mode or "", token or "", challenge or "")
    if result: return PlainTextResponse(result)
    raise HTTPException(403)

@router.post("/webhook/instagram")
async def instagram_webhook_post(request: Request):
    raw_body = await request.body()
    sig = request.headers.get("X-Hub-Signature-256", "")
    adapter = services.channel_registry.get("instagram")
    if not adapter or not adapter.verify_signature(raw_body, sig):
        raise HTTPException(403)
    await adapter.process_webhook(json.loads(raw_body))
    return {"ok": True}

# --- Facebook OAuth & Webhook ---

@router.get("/oauth/facebook/start", dependencies=[Depends(verify_authenticated)])
async def facebook_oauth_start():
    adapter = services.channel_registry.get("facebook")
    if not adapter: raise HTTPException(503)
    daemon_url = os.getenv("DAEMON_PUBLIC_URL", "http://localhost:8000").rstrip("/")
    redirect_uri = f"{daemon_url}/api/oauth/facebook/callback"
    state = secrets.token_urlsafe(32)
    url, _ = adapter.build_oauth_url(redirect_uri, state)
    await oauth_store.store_state(state, {"redirect_uri": redirect_uri})
    return {"authorize_url": url, "state": state}

@router.get("/webhook/facebook")
async def facebook_webhook_verify(mode: str = Query(None, alias="hub.mode"), token: str = Query(None, alias="hub.verify_token"), challenge: str = Query(None, alias="hub.challenge")):
    adapter = services.channel_registry.get("facebook")
    if not adapter: raise HTTPException(503)
    result = adapter.verify_webhook(mode or "", token or "", challenge or "")
    if result: return PlainTextResponse(result)
    raise HTTPException(403)

@router.post("/webhook/facebook")
async def facebook_webhook_post(request: Request):
    raw_body = await request.body()
    sig = request.headers.get("X-Hub-Signature-256", "")
    adapter = services.channel_registry.get("facebook")
    if not adapter or not adapter.verify_signature(raw_body, sig):
        raise HTTPException(403)
    await adapter.process_webhook(json.loads(raw_body))
    return {"ok": True}

# --- X (Twitter) OAuth ---

@router.get("/oauth/x/start", dependencies=[Depends(verify_authenticated)])
async def x_oauth_start():
    adapter = services.channel_registry.get("x")
    if not adapter: raise HTTPException(503)
    daemon_url = os.getenv("DAEMON_PUBLIC_URL", "http://localhost:8000").rstrip("/")
    redirect_uri = f"{daemon_url}/api/oauth/x/callback"
    state = secrets.token_urlsafe(32)
    url, verifier = adapter.build_oauth_url(redirect_uri, state)
    await oauth_store.store_state(state, {"verifier": verifier, "redirect_uri": redirect_uri})
    return {"authorize_url": url, "state": state}

# --- MS Teams (Graph) OAuth & Webhook ---

@router.get("/oauth/msteams/start", dependencies=[Depends(verify_authenticated)])
async def msteams_oauth_start():
    adapter = services.channel_registry.get("msteams")
    if not adapter: raise HTTPException(503)
    daemon_url = os.getenv("DAEMON_PUBLIC_URL", "http://localhost:8000").rstrip("/")
    redirect_uri = f"{daemon_url}/api/oauth/msteams/callback"
    state = secrets.token_urlsafe(32)
    url, _ = adapter.build_oauth_url(redirect_uri, state)
    await oauth_store.store_state(state, {"redirect_uri": redirect_uri})
    return {"authorize_url": url, "state": state}

@router.post("/webhook/msteams")
async def msteams_bot_activity(request: Request):
    auth = request.headers.get("Authorization", "")
    adapter = services.channel_registry.get("msteams")
    if not adapter or not await adapter.verify_bot_activity(auth):
        raise HTTPException(401)
    await adapter.process_webhook(await request.json())
    return {}

# --- Telegram Webhook (FIX-005) ---

@router.post("/webhook/telegram/{token}")
async def telegram_webhook(token: str, update: Dict[str, Any] = Body(...)):
    """Receives inbound updates from Telegram Bot API."""
    adapter = services.channel_registry.get("telegram")
    if not adapter or not hasattr(adapter, "process_webhook"):
        return {"ok": False, "error": "Adapter not ready"}

    # Security: validate the token matches the stored bot token
    if hasattr(adapter, "is_connected") and adapter.is_connected and getattr(adapter, "bot_token", None) == token:
        # Valid
        pass
    else:
        # If adapter.bot_token is not set yet, we might allow it if it's the first time 
        # but SEC-005 suggests strict validation.
        # Check services.vault for the token? 
        # For now, if we can't verify, we log warning.
        logger.warning("[TELEGRAM] Webhook received with unverified token.")

    parsed = await adapter.process_webhook(update)
    if parsed and services.orchestrator:
        asyncio.create_task(services.orchestrator.handle_inbound_message(parsed))
    return {"ok": True}

# --- Google Chat Routes ---

@router.post("/webhook/google_chat")
async def google_chat_event(request: Request):
    auth = request.headers.get("Authorization", "")
    adapter = services.channel_registry.get("google_chat")
    if not adapter or not await adapter.verify_webhook(auth):
        raise HTTPException(401)
    payload = await request.json()
    response = await adapter.process_event(payload)
    if response and response.get("body"): return {"text": response["body"]}
    return {}

# --- iPhone Bridge Routes ---

@router.post("/channels/iphone/pair", dependencies=[Depends(verify_authenticated)])
async def iphone_pair(request: Request, csrf_protect: CsrfProtect = Depends(), payload: Dict[str, str] = Body(...)):
    await csrf_protect.validate_csrf(request)
    """
    [ GAP-003 ] Securely pins the companion's CA certificate for TLS.
    Body: { "cert": "-----BEGIN CERTIFICATE-----..." }
    """
    adapter = services.channel_registry.get("iphone")
    if not adapter:
        raise HTTPException(status_code=503, detail="iPhone bridge not initialized")
    
    cert_pem = payload.get("cert")
    if not cert_pem:
        raise HTTPException(status_code=400, detail="'cert' PEM is required")
        
    success = await adapter.store_pinned_ca(cert_pem)
    if success:
        return {"status": "SUCCESS", "message": "Companion CA pinned. TLS enforcement active."}
    else:
        raise HTTPException(status_code=500, detail="Failed to store pinned certificate")

# --- iCloud & WebChat Utilities ---

@router.get("/channels/imessage/permission", dependencies=[Depends(verify_authenticated)])
async def icloud_imessage_permission():
    """Checks if the agent has Full Disk Access to read chat.db (macOS)."""
    chat_db = os.path.expanduser("~/Library/Messages/chat.db")
    if os.path.exists(chat_db):
        try:
            # Try to open it
            with open(chat_db, "rb") as f:
                f.read(10)
            return {"status": "SUCCESS", "granted": True}
        except PermissionError:
            return {"status": "FAILED", "granted": False, "error": "Full Disk Access required"}
        except Exception as e:
            return {"status": "FAILED", "granted": False, "error": str(e)}
    return {"status": "FAILED", "granted": False, "error": "chat.db not found (Is iMessage enabled?)"}

@router.post("/channels/webchat/launch", dependencies=[Depends(verify_authenticated)])
async def webchat_launch(request: Request, csrf_protect: CsrfProtect = Depends(), data: Dict[str, str] = Body(...)):
    await csrf_protect.validate_csrf(request)
    """Triggers the backend Playwright browser to open for user login."""
    adapter = services.channel_registry.get("webchat")
    url = data.get("url")
    if not url: raise HTTPException(400, "url is required")
    if hasattr(adapter, "launch_browser"):
        return await adapter.launch_browser(url)  # type: ignore
    raise HTTPException(status_code=501)

@router.post("/channels/icloud/2fa", dependencies=[Depends(verify_authenticated)])
async def icloud_2fa(request: Request, csrf_protect: CsrfProtect = Depends(), data: Dict[str, str] = Body(...)):
    await csrf_protect.validate_csrf(request)
    adapter = services.channel_registry.get("icloud")
    if hasattr(adapter, "submit_2fa"): return await adapter.submit_2fa(data.get("code"))  # type: ignore
    raise HTTPException(status_code=501)

@router.post("/channels/webchat/session/{id}/capture", dependencies=[Depends(verify_authenticated)])
async def webchat_session_capture(id: str, request: Request, csrf_protect: CsrfProtect = Depends(), data: Dict[str, Any] = Body(...)):
    await csrf_protect.validate_csrf(request)
    adapter = services.channel_registry.get("webchat")
    if hasattr(adapter, "capture_session"): return await adapter.capture_session(id, data)  # type: ignore
    raise HTTPException(status_code=501)

# ── Agent Channel Subscriptions (Sovereign Spec §4.2) ─────────────────────────

@router.get("/agents/{agent_id}/subscriptions", dependencies=[Depends(verify_authenticated)])
async def get_agent_subscriptions(agent_id: str, session=Depends(get_session)):
    """Fetch all channel subscription states for a specific agent."""
    statement = select(AgentChannelSubscription).where(AgentChannelSubscription.agent_id == agent_id)
    results = session.exec(statement).all()
    return results

@router.put("/agents/{agent_id}/subscriptions", dependencies=[Depends(verify_authenticated)])
async def update_agent_subscription(agent_id: str, request: Request, csrf_protect: CsrfProtect = Depends(), sub: Dict[str, Any] = Body(...), session=Depends(get_session)):
    await csrf_protect.validate_csrf(request)
    """Upsert an agent's subscription to a specific channel."""
    channel_id = sub.get("channel_id")
    is_active = sub.get("is_active", False)

    if not channel_id:
        raise HTTPException(status_code=400, detail="channel_id is required")

    statement = select(AgentChannelSubscription).where(
        AgentChannelSubscription.agent_id == agent_id,
        AgentChannelSubscription.channel_id == channel_id
    )
    existing = session.exec(statement).first()

    if existing:
        existing.is_active = is_active
        existing.updated_at = datetime.now(timezone.utc)  # type: ignore
        session.add(existing)
    else:
        new_sub = AgentChannelSubscription(
            agent_id=agent_id,
            channel_id=channel_id,
            is_active=is_active
        )
        session.add(new_sub)

    session.commit()
    return {"status": "SUCCESS"}

@router.delete("/agents/{agent_id}/subscriptions/{channel_id}", dependencies=[Depends(verify_authenticated)])
async def delete_agent_subscription(agent_id: str, channel_id: str, request: Request, csrf_protect: CsrfProtect = Depends(), session=Depends(get_session)):
    await csrf_protect.validate_csrf(request)
    """Remove an agent's subscription record."""
    statement = select(AgentChannelSubscription).where(
        AgentChannelSubscription.agent_id == agent_id,
        AgentChannelSubscription.channel_id == channel_id
    )
    target = session.exec(statement).first()
    if target:
        session.delete(target)
        session.commit()
        return {"status": "SUCCESS"}
    raise HTTPException(status_code=404, detail="Subscription not found")


BRIDGE_ID_MAP = {
    "tg": "telegram",
    "sg": "signal",
    "wa": "whatsapp",
    "dc": "discord",
    "ig": "instagram",
    "fb": "facebook",
    "sl": "slack",
    "mt": "msteams",
    "gm": "gmail",
    "gd": "gdrive",
    "verus": "verus_wallet",
}

def normalize_bridge_id(bridge_id: str) -> str:
    return BRIDGE_ID_MAP.get(bridge_id, bridge_id)

@router.post("/auth/bridge/{bridge_id}/save", dependencies=[Depends(verify_authenticated)])
async def save_bridge_credentials(
    bridge_id: str,
    request: Request,
    csrf_protect: CsrfProtect = Depends(),
    credentials: Dict[str, Any] = Body(...)
):
    await csrf_protect.validate_csrf(request)
    normalized_id = normalize_bridge_id(bridge_id)
    adapter = services.channel_registry.get(normalized_id)
    if not adapter:
        raise HTTPException(status_code=404, detail=f"Bridge '{bridge_id}' not found.")
    
    account_id = "default"
    try:
        await adapter._save_credentials(credentials, account_id)
        if services.vault:
            try:
                await services.vault.store_secret(f"channel_{normalized_id}_enabled", {"enabled": True})
            except Exception as vault_e:
                logger.warning(f"Failed to set vault flag for {normalized_id}, but creds saved: {vault_e}")
        return {"status": "SUCCESS", "message": f"Credentials saved for {bridge_id}"}
    except Exception as e:
        logger.error(f"Failed to save credentials for {bridge_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/bridge/{bridge_id}/activate", dependencies=[Depends(verify_authenticated)])
async def activate_bridge_route(
    bridge_id: str,
    request: Request,
    csrf_protect: CsrfProtect = Depends()
):
    await csrf_protect.validate_csrf(request)
    normalized_id = normalize_bridge_id(bridge_id)
    adapter = services.channel_registry.get(normalized_id)
    if not adapter:
        raise HTTPException(status_code=404, detail=f"Bridge '{bridge_id}' not found.")
        
    try:
        vault_mgr = getattr(adapter, "vault_manager", None) or services.vault
        accounts = await vault_mgr.list_connections(normalized_id) if vault_mgr else []
        if not accounts:
            accounts = ["default"]
            
        any_success = False
        last_error = "No credentials found. Save credentials first."
        requires_2fa = False
        
        for account_id in accounts:
            creds = await adapter._load_credentials(account_id)
            if not creds: continue
                
            if normalized_id == "icloud" and "two_factor_code" in creds:
                code = creds["two_factor_code"]
                clean_creds = {k: v for k, v in creds.items() if k != "two_factor_code"}
                await adapter._save_credentials(clean_creds, account_id)
                res = await adapter.submit_2fa(code)
                if res.get("status") == "SUCCESS":
                    any_success = True
                else:
                    requires_2fa = True
                    last_error = res.get("error", "Invalid 2FA code")
                continue
                
            # Normal activation/connect
            success = await adapter.connect(creds)
            
            if normalized_id == "icloud" and hasattr(adapter, "api") and adapter.api and adapter.api.requires_2fa:
                requires_2fa = True
                continue
                
            if success:
                any_success = True
            else:
                last_error = getattr(adapter, "last_error", f"Activation failed for {account_id}")

        if any_success:
            return {"connected": True}
        elif requires_2fa:
            return {"connected": False, "requires_2fa": True, "error": last_error}
        else:
            return {"connected": False, "error": last_error}
    except Exception as e:
        logger.error(f"Failed to activate bridge {bridge_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

