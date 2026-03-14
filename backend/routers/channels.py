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

logger = logging.getLogger("ChannelsRouter")

# Per-bridge PKCE/state stores — replace with Redis in multi-worker deployments
_slack_pkce_states: Dict[str, str] = {}   # state → code_verifier
_oauth_states: Dict[str, Dict[str, Any]] = {
    "instagram": {},  # state → {"verifier": ..., "redirect_uri": ...}
    "facebook":  {},
    "x":         {},  # state → {"verifier": ..., "redirect_uri": ...}
    "msteams":   {},
}

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

@router.get("/api/oauth/wechat/callback")
async def wechat_oauth_callback(code: str = Query(None), state: str = Query(None)):
    payload = json.dumps({"type": "OAUTH_COMPLETE", "bridgeId": "wechat", "success": bool(code)})
    return HTMLResponse(f"<script>window.opener&&window.opener.postMessage({payload},window.location.origin);window.close();</script>")

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
    _slack_pkce_states[state] = code_verifier
    return {"authorize_url": authorize_url, "state": state}

@router.get("/api/oauth/slack/callback")
async def slack_oauth_callback(code: str = Query(None), state: str = Query(None), error: str = Query(None)):
    def _resp(ok: bool, err: str = ""):
        p = json.dumps({"type":"OAUTH_COMPLETE","bridgeId":"slack","success":ok,"error":err})
        return HTMLResponse(f"<script>window.opener&&window.opener.postMessage({p},window.location.origin);window.close();</script>")
    if error: return _resp(False, error)
    verifier = _slack_pkce_states.pop(state, None)
    if not verifier: return _resp(False, "invalid_state")
    adapter = services.channel_registry.get("slack")
    if not adapter: return _resp(False, "not_ready")
    try:
        daemon_url = os.getenv("DAEMON_PUBLIC_URL", "http://localhost:8000").rstrip("/")
        creds = await adapter.handle_oauth_callback(code=code, state=state, code_verifier=verifier, redirect_uri=f"{daemon_url}/api/oauth/slack/callback")
        await services.vault.store_secret("channel_slack", creds)
        return _resp(True)
    except Exception as e: return _resp(False, str(e))

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
    _oauth_states["instagram"][state] = {"redirect_uri": redirect_uri}
    return {"authorize_url": url, "state": state}

@router.get("/api/oauth/instagram/callback")
async def instagram_oauth_callback(code: str = Query(None), state: str = Query(None), error: str = Query(None)):
    def _resp(ok: bool, err: str = ""):
        p = json.dumps({"type":"OAUTH_COMPLETE","bridgeId":"instagram","success":ok,"error":err})
        return HTMLResponse(f"<script>window.opener&&window.opener.postMessage({p},window.location.origin);window.close();</script>")
    if error: return _resp(False, error)
    sd = _oauth_states["instagram"].pop(state, None)
    if not sd: return _resp(False, "invalid_state")
    adapter = services.channel_registry.get("instagram")
    if not adapter: return _resp(False, "not_ready")
    try:
        creds = await adapter.handle_oauth_callback(code=code, state=state, redirect_uri=sd["redirect_uri"])
        await services.vault.store_secret("channel_instagram", creds)
        return _resp(True)
    except Exception as e: return _resp(False, str(e))

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
    _oauth_states["facebook"][state] = {"redirect_uri": redirect_uri}
    return {"authorize_url": url, "state": state}

@router.get("/api/oauth/facebook/callback")
async def facebook_oauth_callback(code: str = Query(None), state: str = Query(None), error: str = Query(None)):
    def _resp(ok: bool, err: str = ""):
        p = json.dumps({"type":"OAUTH_COMPLETE","bridgeId":"facebook","success":ok,"error":err})
        return HTMLResponse(f"<script>window.opener&&window.opener.postMessage({p},window.location.origin);window.close();</script>")
    if error: return _resp(False, error)
    sd = _oauth_states["facebook"].pop(state, None)
    if not sd: return _resp(False, "invalid_state")
    adapter = services.channel_registry.get("facebook")
    if not adapter: return _resp(False, "not_ready")
    try:
        creds = await adapter.handle_oauth_callback(code=code, state=state, redirect_uri=sd["redirect_uri"])
        await services.vault.store_secret("channel_facebook", creds)
        return _resp(True)
    except Exception as e: return _resp(False, str(e))

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
    _oauth_states["x"][state] = {"verifier": verifier, "redirect_uri": redirect_uri}
    return {"authorize_url": url, "state": state}

@router.get("/api/oauth/x/callback")
async def x_oauth_callback(code: str = Query(None), state: str = Query(None), error: str = Query(None)):
    def _resp(ok: bool, err: str = ""):
        p = json.dumps({"type":"OAUTH_COMPLETE","bridgeId":"x","success":ok,"error":err})
        return HTMLResponse(f"<script>window.opener&&window.opener.postMessage({p},window.location.origin);window.close();</script>")
    if error: return _resp(False, error)
    sd = _oauth_states["x"].pop(state, None)
    if not sd: return _resp(False, "invalid_state")
    adapter = services.channel_registry.get("x")
    if not adapter: return _resp(False, "not_ready")
    try:
        creds = await adapter.handle_oauth_callback(code=code, state=state, code_verifier=sd["verifier"], redirect_uri=sd["redirect_uri"])
        await services.vault.store_secret("channel_x", creds)
        return _resp(True)
    except Exception as e: return _resp(False, str(e))

# --- MS Teams (Graph) OAuth & Webhook ---

@router.get("/api/oauth/msteams/start", dependencies=[Depends(verify_authenticated)])
async def msteams_oauth_start():
    adapter = services.channel_registry.get("msteams")
    if not adapter: raise HTTPException(503)
    daemon_url = os.getenv("DAEMON_PUBLIC_URL", "http://localhost:8000").rstrip("/")
    redirect_uri = f"{daemon_url}/api/oauth/msteams/callback"
    state = secrets.token_urlsafe(32)
    url, _ = adapter.build_oauth_url(redirect_uri, state)
    _oauth_states["msteams"][state] = {"redirect_uri": redirect_uri}
    return {"authorize_url": url, "state": state}

@router.get("/api/oauth/msteams/callback")
async def msteams_oauth_callback(code: str = Query(None), state: str = Query(None), error: str = Query(None)):
    def _resp(ok: bool, err: str = ""):
        p = json.dumps({"type":"OAUTH_COMPLETE","bridgeId":"msteams","success":ok,"error":err})
        return HTMLResponse(f"<script>window.opener&&window.opener.postMessage({p},window.location.origin);window.close();</script>")
    if error: return _resp(False, error)
    sd = _oauth_states["msteams"].pop(state, None)
    if not sd: return _resp(False, "invalid_state")
    adapter = services.channel_registry.get("msteams")
    if not adapter: return _resp(False, "not_ready")
    try:
        creds = await adapter.handle_oauth_callback(code=code, state=state, redirect_uri=sd["redirect_uri"])
        await services.vault.store_secret("channel_msteams", creds)
        return _resp(True)
    except Exception as e: return _resp(False, str(e))

@router.post("/api/webhook/msteams")
async def msteams_bot_activity(request: Request):
    auth = request.headers.get("Authorization", "")
    adapter = services.channel_registry.get("msteams")
    if not adapter or not await adapter.verify_bot_activity(auth):
        raise HTTPException(401)
    await adapter.process_webhook(await request.json())
    return {}

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
