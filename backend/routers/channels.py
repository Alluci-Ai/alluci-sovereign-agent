
import logging
from fastapi import APIRouter, HTTPException, Depends, Query, Body, Request, Response
from ..security.auth import verify_authenticated
from .. import services
import json
import secrets
import os
import asyncio
from fastapi.responses import HTMLResponse, PlainTextResponse

logger = logging.getLogger("ChannelsRouter")

# In-memory PKCE verifier store — replace with Redis in multi-worker deployment
_slack_pkce_states: Dict[str, str] = {}   # state → code_verifier

router = APIRouter(tags=["Bridge Channels"])

@router.get("/api/channels", dependencies=[Depends(verify_authenticated)])
async def list_channels():
    # Summarize all available communication manifolds
    return [
        {"id": cid, "status": getattr(adapter, "status", "idle"), "type": getattr(adapter, "channel_type", "unknown")}
        for cid, adapter in services.channel_registry.items()
    ]

@router.get("/api/channels/{channel_id}/config", dependencies=[Depends(verify_authenticated)])
async def get_channel_config(channel_id: str):
    adapter = services.channel_registry.get(channel_id)
    if not adapter:
        raise HTTPException(status_code=404, detail="Channel not found")
    return getattr(adapter, "config", {})

@router.put("/api/channels/{channel_id}/config", dependencies=[Depends(verify_authenticated)])
async def update_channel_config(channel_id: str, config: Dict[str, Any] = Body(...)):
    adapter = services.channel_registry.get(channel_id)
    if not adapter:
        raise HTTPException(status_code=404, detail="Channel not found")
    if hasattr(adapter, "update_config"):
        return await adapter.update_config(config)
    raise HTTPException(status_code=501, detail="Config update not supported for this channel")

@router.post("/api/channels/{channel_id}/connect", dependencies=[Depends(verify_authenticated)])
async def connect_channel(channel_id: str):
    adapter = services.channel_registry.get(channel_id)
    if not adapter:
        raise HTTPException(status_code=404, detail="Channel not found")
    if hasattr(adapter, "connect"):
        return await adapter.connect()
    raise HTTPException(status_code=501, detail="Direct connect not supported")

# --- Specialized Channel Routes ---

@router.get("/api/channels/iwatch/status", dependencies=[Depends(verify_authenticated)])
async def iwatch_status():
    adapter = services.channel_registry.get("iwatch")
    if not adapter:
        return {"status": "unloaded"}
    return {"status": "connected" if getattr(adapter, "is_connected", False) else "paired"}

@router.post("/api/channels/iwatch/pair")
async def iwatch_pair():
    """Step 1: Generate TOTP secret for pairing."""
    adapter = services.channel_registry.get("iwatch")
    if not adapter: raise HTTPException(404, "Adapter not found")
    import pyotp
    secret = pyotp.random_base32()
    adapter.pending_totp_secret = secret
    uri = pyotp.totp.TOTP(secret).provisioning_uri(name="Sovereign Agent", issuer_name="Alluci")
    return {"status": "SUCCESS", "secret": secret, "provisioning_uri": uri}

@router.post("/api/channels/iwatch/pair/verify")
async def iwatch_pair_verify(data: Dict[str, str] = Body(...)):
    """Step 2: Verify TOTP code."""
    code = data.get("code")
    if not code: raise HTTPException(400, "Missing 'code' parameter")
    adapter = services.channel_registry.get("iwatch")
    if not adapter: raise HTTPException(404, "Adapter not found")
    
    result = await adapter.submit_pairing_code(code)
    if result.get("paired"):
        credentials = result.get("credentials", {})
        if services.vault:
            from ..security.utils import log_system_event
            await services.vault.store_secret("channel_iwatch", credentials)
            await log_system_event("DEVICE_PAIR", "Apple Watch successfully paired.", "SUCCESS")
        return {"status": "SUCCESS", "message": "Apple Watch Paired."}
    raise HTTPException(status_code=401, detail=result.get("error", "Pairing failed"))

@router.get("/api/channels/wechat/qr-init")
async def wechat_qr_init():
    adapter = services.channel_registry.get("wechat")
    if hasattr(adapter, "init_qr"):
        return await adapter.init_qr()
    raise HTTPException(status_code=501, detail="WeChat QR flow not implemented")

@router.post("/api/channels/webchat/session/{id}/capture")
async def webchat_session_capture(id: str, data: Dict[str, Any] = Body(...)):
    adapter = services.channel_registry.get("webchat")
    if hasattr(adapter, "capture_session"):
        return await adapter.capture_session(id, data)
    raise HTTPException(status_code=501, detail="WebChat capture not implemented")

# --- Slack OAuth & Webhook ---

@router.get("/api/oauth/slack/start", dependencies=[Depends(verify_authenticated)])
async def slack_oauth_start():
    """
    Initiate Slack PKCE OAuth flow.
    Returns the authorization URL to redirect the user to.
    """
    adapter = services.channel_registry.get("slack")
    if not adapter:
        raise HTTPException(status_code=503, detail="Slack adapter not initialised.")

    daemon_url = os.getenv("DAEMON_PUBLIC_URL", "http://localhost:8000").rstrip("/")
    redirect_uri = f"{daemon_url}/api/oauth/slack/callback"
    state = secrets.token_urlsafe(32)

    try:
        authorize_url, code_verifier = adapter.build_oauth_url(redirect_uri, state)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to build OAuth URL: {e}")

    # Persist verifier keyed by state (5-minute TTL handled by cleanup task)
    _slack_pkce_states[state] = code_verifier
    
    # Also backup to Redis if available
    if services.redis_client:
        await services.redis_client.setex(f"slack_pkce_{state}", 600, code_verifier)

    return {
        "authorize_url": authorize_url,
        "state":         state,
    }

@router.get("/api/oauth/slack/callback")
async def slack_oauth_callback(
    code:  str = Query(None),
    state: str = Query(None),
    error: str = Query(None),
):
    """
    Handle Slack OAuth callback with PKCE code exchange.
    Completes via postMessage to the opener window.
    """
    def _respond(success: bool, detail: str = "") -> HTMLResponse:
        payload = json.dumps({
            "type":    "OAUTH_COMPLETE",
            "bridgeId": "slack",
            "success": success,
            "error":   detail,
        })
        return HTMLResponse(
            f"<html><head><script>"
            f"window.opener && window.opener.postMessage({payload}, window.location.origin);"
            f"window.close();"
            f"</script></head><body>OAuth Complete. Closing window...</body></html>"
        )

    if error:
        logger.warning(f"[SLACK OAUTH] User denied or error: {error}")
        return _respond(False, error)

    if not code or not state:
        return _respond(False, "missing_code_or_state")

    # Try local state first, then fallback to Redis
    code_verifier = _slack_pkce_states.pop(state, None)
    if not code_verifier and services.redis_client:
        v = await services.redis_client.get(f"slack_pkce_{state}")
        if v:
            code_verifier = v.decode("utf-8")
            await services.redis_client.delete(f"slack_pkce_{state}")

    if not code_verifier:
        logger.warning(f"[SLACK OAUTH] Unknown or expired state: {state}")
        return _respond(False, "invalid_or_expired_state")

    adapter = services.channel_registry.get("slack")
    if not adapter:
        return _respond(False, "adapter_not_ready")

    daemon_url = os.getenv("DAEMON_PUBLIC_URL", "http://localhost:8000").rstrip("/")
    redirect_uri = f"{daemon_url}/api/oauth/slack/callback"

    try:
        creds = await adapter.handle_oauth_callback(
            code=code,
            state=state,
            code_verifier=code_verifier,
            redirect_uri=redirect_uri,
        )
        # Persist to vault
        if services.vault:
            from ..security.utils import log_system_event
            await services.vault.store_secret("channel_slack", creds)
            await log_system_event("OAUTH_COMPLETE", "Slack OAuth completed successfully.", "SUCCESS")
        return _respond(True)
    except Exception as e:
        logger.error(f"[SLACK OAUTH] Token exchange failed: {e}")
        return _respond(False, str(e))

@router.post("/api/webhook/slack")
async def slack_webhook(request: Request):
    """
    Events API endpoint. Handles signature verification and dispatches to adapter.
    """
    body = await request.body()
    timestamp = request.headers.get("X-Slack-Request-Timestamp")
    signature = request.headers.get("X-Slack-Signature")
    
    adapter = services.channel_registry.get("slack")
    if not adapter:
        raise HTTPException(status_code=404, detail="Slack adapter not found")
    
    # Verify Signature (SL-001)
    if not adapter.verify_signature(body, timestamp, signature):
        logger.warning(f"Slack webhook signature verification failed from {request.client.host}")
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    try:
        payload = json.loads(body)
        return await adapter.process_webhook(payload)
    except Exception as e:
        logger.error(f"Slack webhook processing error: {e}")
        return {"status": "error", "detail": str(e)}

# --- WhatsApp Webhooks ---

@router.get("/api/webhook/whatsapp")
async def whatsapp_webhook_verify(
    mode:      str = Query(None, alias="hub.mode"),
    token:     str = Query(None, alias="hub.verify_token"),
    challenge: str = Query(None, alias="hub.challenge"),
):
    """Responds to Meta's hub.challenge subscription verification."""
    adapter = services.channel_registry.get("whatsapp")
    if not adapter:
        raise HTTPException(status_code=503, detail="Adapter not ready")

    result = adapter.verify_webhook(mode or "", token or "", challenge or "")
    if result is not None:
        return PlainTextResponse(content=result)

    raise HTTPException(status_code=403, detail="Verification failed.")

@router.post("/api/webhook/whatsapp")
async def whatsapp_webhook_post(request: Request):
    """
    Receives inbound events from Meta WhatsApp Cloud API.
    Verifies X-Hub-Signature-256 before processing.
    """
    raw_body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")

    adapter = services.channel_registry.get("whatsapp")
    if not adapter:
        return {"ok": False, "error": "Adapter not ready"}

    # HMAC verification — reject unsigned payloads
    if not adapter.verify_signature(raw_body, signature):
        logger.warning("[WHATSAPP] Rejected POST webhook — HMAC verification failed.")
        raise HTTPException(status_code=403, detail="Invalid webhook signature.")

    try:
        body = json.loads(raw_body)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body.")

    parsed_list = await adapter.process_webhook_event(body)
    if parsed_list and services.orchestrator:
        for msg in parsed_list:
            asyncio.create_task(services.orchestrator.handle_inbound_message(msg))

    return {"ok": True}

@router.post("/api/channels/icloud/2fa")
async def icloud_2fa(data: Dict[str, str] = Body(...)):
    adapter = services.channel_registry.get("icloud")
    if hasattr(adapter, "submit_2fa"):
        return await adapter.submit_2fa(data.get("code"))
    raise HTTPException(status_code=501, detail="iCloud 2FA not implemented")
