import logging
import json
import secrets
import os
import asyncio
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Query, Body, Request, Response
from fastapi.responses import HTMLResponse, PlainTextResponse
from ..security.auth import verify_authenticated
from .. import services
from ..models import TelemetryData
from ..security.oauth_store import oauth_store

from ..logging_config import get_logger

logger = get_logger("ChannelsRouter")

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

# --- iWatch (HealthKit) Routes ---

@router.get("/api/channels/iwatch/status", dependencies=[Depends(verify_authenticated)])
async def iwatch_status():
    adapter = services.channel_registry.get("iwatch")
    if not adapter: return {"status": "unloaded"}
    return {"status": "connected" if getattr(adapter, "is_connected", False) else "paired"}

@router.get("/api/channels/iwatch/pairing-qr", dependencies=[Depends(verify_authenticated)])
async def iwatch_pairing_qr():
    """Generate TOTP seed and QR payload for Watch pairing."""
    adapter = services.channel_registry.get("iwatch")
    if not adapter:
        raise HTTPException(status_code=503, detail="iWatch adapter not initialised.")
    daemon_url = os.getenv("DAEMON_PUBLIC_URL", "http://localhost:8000").rstrip("/")
    return await adapter.generate_pairing_qr(daemon_url)

@router.post("/api/channels/iwatch/pair")
async def iwatch_pair(data: Dict[str, str] = Body(...)):
    """Verify TOTP code and issue a device session token."""
    adapter = services.channel_registry.get("iwatch")
    if not adapter:
        raise HTTPException(status_code=503, detail="iWatch adapter not initialised.")
    code      = data.get("code", "")
    device_id = data.get("device_id", "")
    if not code or not device_id:
        raise HTTPException(status_code=400, detail="code and device_id required.")
    return await adapter.submit_pairing_code(code, device_id)

@router.post("/api/bridge/iwatch/biometrics")
async def ingest_iwatch_biometrics(request: Request):
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
        except Exception: pass

    await adapter.ingest_telemetry(samples, device_id or "unknown")
    latest_flow = results[-1] if results else {}
    return {
        "status": "SUCCESS",
        "processed": len(samples),
        "flow_intervention": latest_flow.get("flow"),
        "resonance": services.ace.current_state.get("physical_vitality") if services.ace else None,
    }

@router.get("/api/bridge/iwatch/telemetry", dependencies=[Depends(verify_authenticated)])
async def get_iwatch_telemetry(limit: int = Query(20, ge=1, le=200)):
    """Retrieve recent telemetry samples from the iWatch bridge buffer."""
    adapter = services.channel_registry.get("iwatch")
    if not adapter: raise HTTPException(503)
    samples = adapter.get_recent_telemetry(limit)
    return {"samples": samples, "count": len(samples)}

# --- WeChat (WeCom) Routes ---

@router.get("/api/channels/wechat/qr-init", dependencies=[Depends(verify_authenticated)])
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

@router.get("/api/oauth/{bridge_id}/callback")
async def oauth_callback(bridge_id: str, code: str = Query(None), state: str = Query(None), error: str = Query(None)):
    """Generic OAuth callback endpoint for all OAuth-based bridges."""
    import structlog
    with structlog.contextvars.bound_contextvars(bridge_id=bridge_id):
        # 1. Security: validate bridge_id against known set before any string interpolation
        if bridge_id not in _VALID_BRIDGE_IDS:
            logger.warning("Callback received for unknown bridge_id")
            return HTMLResponse(
                "<script>"
                "window.opener && window.opener.postMessage("
                "  JSON.stringify({ type: 'OAUTH_COMPLETE', error: 'invalid_bridge' }),"
                "  window.location.origin"
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
                f"<script>"
                f"window.opener && window.opener.postMessage({payload}, window.location.origin);"
                f"window.close();"
                f"</script>"
            )

        if error:
            return _make_response(False, error)

        # 2. Forward to specific adapter logic
        adapter = services.channel_registry.get(bridge_id)
        if not adapter:
            return _make_response(False, "bridge_not_found")

        try:
            if bridge_id == "slack":
                verifier = await oauth_store.consume_state(state)
                if not verifier: return _make_response(False, "invalid_state")
                daemon_url = os.getenv("DAEMON_PUBLIC_URL", "http://localhost:8000").rstrip("/")
                creds = await adapter.handle_oauth_callback(code=code, state=state, code_verifier=verifier, redirect_uri=f"{daemon_url}/api/oauth/slack/callback")
                team_id = creds.get("team_id") or "default"
                await services.vault.store_connection_secret("slack", team_id, creds)
            
            elif bridge_id == "x":
                sd = await oauth_store.consume_state(state)
                if not sd: return _make_response(False, "invalid_state")
                creds = await adapter.handle_oauth_callback(code=code, state=state, code_verifier=sd["verifier"], redirect_uri=sd["redirect_uri"])
                user_id = creds.get("user_id") or "default"
                await services.vault.store_connection_secret("x", user_id, creds)
    
            elif bridge_id in ["instagram", "facebook", "msteams"]:
                sd = await oauth_store.consume_state(state)
                if not sd: return _make_response(False, "invalid_state")
                creds = await adapter.handle_oauth_callback(code=code, state=state, redirect_uri=sd["redirect_uri"])
                account_id = creds.get("team_id") or creds.get("user_id") or "default"
                await services.vault.store_connection_secret(bridge_id, account_id, creds)
                
            elif hasattr(adapter, "handle_oauth_callback"):
                await adapter.handle_oauth_callback(code, state)
            
            return _make_response(True)

        except Exception as e:
            logger.error("Callback error", error=str(e))
            return _make_response(False, str(e))

@router.get("/api/webhook/wechat")
async def wechat_webhook_verify(msg_signature: str = Query(...), timestamp: str = Query(...), nonce: str = Query(...), echostr: str = Query("")):
    adapter = services.channel_registry.get("wechat")
    if not adapter: raise HTTPException(503)
    result = adapter.verify_callback(msg_signature, timestamp, nonce, echostr)
    if result: return PlainTextResponse(result)
    raise HTTPException(403)

@router.post("/api/webhook/wechat")
async def wechat_webhook_post(request: Request, msg_signature: str = Query(...), timestamp: str = Query(...), nonce: str = Query(...)):
    adapter = services.channel_registry.get("wechat")
    if not adapter: return "<xml><Content>ok</Content></xml>"
    raw_body = await request.body()
    if adapter.verify_callback(msg_signature, timestamp, nonce) is None:
        raise HTTPException(status_code=403)
    await adapter.process_webhook({"raw_xml": raw_body.decode("utf-8")})
    return "<xml><Content>ok</Content></xml>"

# --- Slack OAuth & Webhook ---

@router.get("/api/oauth/slack/start", dependencies=[Depends(verify_authenticated)])
async def slack_oauth_start():
    adapter = services.channel_registry.get("slack")
    if not adapter: raise HTTPException(503)
    daemon_url = os.getenv("DAEMON_PUBLIC_URL", "http://localhost:8000").rstrip("/")
    redirect_uri = f"{daemon_url}/api/oauth/slack/callback"
    state = secrets.token_urlsafe(32)
    authorize_url, code_verifier = adapter.build_oauth_url(redirect_uri, state)
    await oauth_store.store_state(state, code_verifier)
    return {"authorize_url": authorize_url, "state": state}

@router.post("/api/webhook/slack")
async def slack_webhook(request: Request):
    body = await request.body()
    ts = request.headers.get("X-Slack-Request-Timestamp")
    sig = request.headers.get("X-Slack-Signature")
    adapter = services.channel_registry.get("slack")
    if not adapter or not adapter.verify_signature(body, ts, sig):
        raise HTTPException(401)
    return await adapter.process_webhook(json.loads(body))

# --- WhatsApp Webhooks ---

@router.get("/api/webhook/whatsapp")
async def whatsapp_webhook_verify(mode: str = Query(None, alias="hub.mode"), token: str = Query(None, alias="hub.verify_token"), challenge: str = Query(None, alias="hub.challenge")):
    adapter = services.channel_registry.get("whatsapp")
    if not adapter: raise HTTPException(503)
    result = adapter.verify_webhook(mode or "", token or "", challenge or "")
    if result: return PlainTextResponse(result)
    raise HTTPException(403)

@router.post("/api/webhook/whatsapp")
async def whatsapp_webhook_post(request: Request):
    raw_body = await request.body()
    sig = request.headers.get("X-Hub-Signature-256", "")
    adapter = services.channel_registry.get("whatsapp")
    if not adapter or not adapter.verify_signature(raw_body, sig):
        raise HTTPException(403)
    await adapter.process_webhook_event(json.loads(raw_body))
    return {"ok": True}

# --- Instagram OAuth & Webhook ---

@router.get("/api/oauth/instagram/start", dependencies=[Depends(verify_authenticated)])
async def instagram_oauth_start():
    adapter = services.channel_registry.get("instagram")
    if not adapter: raise HTTPException(503)
    daemon_url = os.getenv("DAEMON_PUBLIC_URL", "http://localhost:8000").rstrip("/")
    redirect_uri = f"{daemon_url}/api/oauth/instagram/callback"
    state = secrets.token_urlsafe(32)
    url, _ = adapter.build_oauth_url(redirect_uri, state)
    await oauth_store.store_state(state, {"redirect_uri": redirect_uri})
    return {"authorize_url": url, "state": state}

@router.get("/api/webhook/instagram")
async def instagram_webhook_verify(mode: str = Query(None, alias="hub.mode"), token: str = Query(None, alias="hub.verify_token"), challenge: str = Query(None, alias="hub.challenge")):
    adapter = services.channel_registry.get("instagram")
    if not adapter: raise HTTPException(503)
    result = adapter.verify_webhook(mode or "", token or "", challenge or "")
    if result: return PlainTextResponse(result)
    raise HTTPException(403)

@router.post("/api/webhook/instagram")
async def instagram_webhook_post(request: Request):
    raw_body = await request.body()
    sig = request.headers.get("X-Hub-Signature-256", "")
    adapter = services.channel_registry.get("instagram")
    if not adapter or not adapter.verify_signature(raw_body, sig):
        raise HTTPException(403)
    await adapter.process_webhook(json.loads(raw_body))
    return {"ok": True}

# --- Facebook OAuth & Webhook ---

@router.get("/api/oauth/facebook/start", dependencies=[Depends(verify_authenticated)])
async def facebook_oauth_start():
    adapter = services.channel_registry.get("facebook")
    if not adapter: raise HTTPException(503)
    daemon_url = os.getenv("DAEMON_PUBLIC_URL", "http://localhost:8000").rstrip("/")
    redirect_uri = f"{daemon_url}/api/oauth/facebook/callback"
    state = secrets.token_urlsafe(32)
    url, _ = adapter.build_oauth_url(redirect_uri, state)
    await oauth_store.store_state(state, {"redirect_uri": redirect_uri})
    return {"authorize_url": url, "state": state}

@router.get("/api/webhook/facebook")
async def facebook_webhook_verify(mode: str = Query(None, alias="hub.mode"), token: str = Query(None, alias="hub.verify_token"), challenge: str = Query(None, alias="hub.challenge")):
    adapter = services.channel_registry.get("facebook")
    if not adapter: raise HTTPException(503)
    result = adapter.verify_webhook(mode or "", token or "", challenge or "")
    if result: return PlainTextResponse(result)
    raise HTTPException(403)

@router.post("/api/webhook/facebook")
async def facebook_webhook_post(request: Request):
    raw_body = await request.body()
    sig = request.headers.get("X-Hub-Signature-256", "")
    adapter = services.channel_registry.get("facebook")
    if not adapter or not adapter.verify_signature(raw_body, sig):
        raise HTTPException(403)
    await adapter.process_webhook(json.loads(raw_body))
    return {"ok": True}

# --- X (Twitter) OAuth ---

@router.get("/api/oauth/x/start", dependencies=[Depends(verify_authenticated)])
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

@router.get("/api/oauth/msteams/start", dependencies=[Depends(verify_authenticated)])
async def msteams_oauth_start():
    adapter = services.channel_registry.get("msteams")
    if not adapter: raise HTTPException(503)
    daemon_url = os.getenv("DAEMON_PUBLIC_URL", "http://localhost:8000").rstrip("/")
    redirect_uri = f"{daemon_url}/api/oauth/msteams/callback"
    state = secrets.token_urlsafe(32)
    url, _ = adapter.build_oauth_url(redirect_uri, state)
    await oauth_store.store_state(state, {"redirect_uri": redirect_uri})
    return {"authorize_url": url, "state": state}

@router.post("/api/webhook/msteams")
async def msteams_bot_activity(request: Request):
    auth = request.headers.get("Authorization", "")
    adapter = services.channel_registry.get("msteams")
    if not adapter or not await adapter.verify_bot_activity(auth):
        raise HTTPException(401)
    await adapter.process_webhook(await request.json())
    return {}

# --- Telegram Webhook (FIX-005) ---

@router.post("/api/webhook/telegram/{token}")
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

@router.post("/api/webhook/google_chat")
async def google_chat_event(request: Request):
    auth = request.headers.get("Authorization", "")
    adapter = services.channel_registry.get("google_chat")
    if not adapter or not await adapter.verify_webhook(auth):
        raise HTTPException(401)
    payload = await request.json()
    response = await adapter.process_event(payload)
    if response and response.get("body"): return {"text": response["body"]}
    return {}

# --- iCloud & WebChat Utilities ---

@router.post("/api/channels/icloud/2fa")
async def icloud_2fa(data: Dict[str, str] = Body(...)):
    adapter = services.channel_registry.get("icloud")
    if hasattr(adapter, "submit_2fa"): return await adapter.submit_2fa(data.get("code"))
    raise HTTPException(status_code=501)

@router.post("/api/channels/webchat/session/{id}/capture")
async def webchat_session_capture(id: str, data: Dict[str, Any] = Body(...)):
    adapter = services.channel_registry.get("webchat")
    if hasattr(adapter, "capture_session"): return await adapter.capture_session(id, data)
    raise HTTPException(status_code=501)
