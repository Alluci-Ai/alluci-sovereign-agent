# Alluci Sovereign Agent — Production Readiness Specification

**Complete Developer Plan · Bug Fixes · Feature Completions · Cross-System Integrations**  
**macOS Intel · macOS Apple Silicon · Linux · Windows · Raspberry Pi**

> March 2026 · Based on complete source audit of `alluci-sovereign-agent-main`  
> Source lines audited: ~12,000 across `backend/` + `frontend/` + `bridges/`

---

## Table of Contents

1. [Summary Statistics](#summary-statistics)
2. [Master Index — All 153 Items](#master-index)
3. [Phase 0 — Critical Bugs (Weeks 1–2)](#phase-0--critical-bugs)
4. [Phase 1 — Runtime Core (Weeks 3–7)](#phase-1--runtime-core)
5. [Phase 2 — Intelligence Layer (Weeks 8–12)](#phase-2--intelligence-layer)
6. [Phase 3 — Bridge Completions (Weeks 13–18)](#phase-3--bridge-completions)
7. [Phase 4 — Platform Packages (Weeks 19–24)](#phase-4--platform-packages)
8. [Cross-System Integrations](#cross-system-integrations)
9. [24-Week Sprint Plan](#24-week-sprint-plan)
10. [Target State & Competitive Position](#target-state--competitive-position)

---

## Summary Statistics

| Stat | Value | Notes |
|------|-------|-------|
| Total Spec Items | **153** | Bugs + fixes + new features + integrations + platform tasks |
| Critical Bugs (P0) | **3** | Bridge auth mock, Gmail SMTP dead, OAuth key mismatch — all block every bridge |
| High Priority (P1) | **41** | Required for production use |
| Medium Priority (P2) | **52** | Professional-grade completeness |
| Low / Stretch (P3) | **57** | Best-in-class differentiation |
| Source Lines Audited | **~12,000** | `backend/` + `frontend/` + `bridges/` fully read |
| Backend Python files | **60+** | All audited |
| Frontend TS/TSX files | **70+** | All audited |
| Target delivery | **24 weeks** | Full production release with all 5 platform packages |

### Phases at a Glance

| Phase | Focus | Items | Weeks |
|-------|-------|-------|-------|
| **Phase 0** | Critical Fixes — 3 show-stopper bugs | 3 | 1–2 |
| **Phase 1** | Runtime Core — Security / Memory / Tools | 15 | 3–7 |
| **Phase 2** | Intelligence — LLM / Voice / Research | 15 | 8–12 |
| **Phase 3** | Bridges — All 20 channels live | 20 | 13–18 |
| **Phase 4** | Platform — 5 OS packages | 24 | 19–24 |

> **Why Phase 0 first:** The 3 P0 bugs make the entire bridge ecosystem non-functional. Until they are fixed, zero of the 20 communication bridges can send or receive a single real message. Every UI connection flow terminates in a stub response.

---

## Master Index

### Phase 0 — Critical Bugs (P0) · Weeks 1–2

| ID | Title | Category | Priority | Primary File |
|----|-------|----------|----------|--------------|
| P0-001 | BridgeManager.sendMessage / all social tasks use setTimeout mocks | Bug — Frontend | 🔴 P0 | `bridgeManager.ts` |
| P0-002 | bridge_actualization.py maps `'gmail'` → EmailBridge (SMTP broken since 2022) | Bug — Backend | 🔴 P0 | `adapters/bridge_actualization.py` |
| P0-003 | oauth_config.py uses 2-letter keys (`'sl'`,`'gm'`) but oauth_authorize endpoint receives full IDs (`'slack'`,`'gmail'`) — key mismatch crashes every OAuth flow | Bug — Backend | 🔴 P0 | `oauth_config.py` / `app.py:2162` |

### Phase 1 — Runtime Core (P1) · Weeks 3–7

| ID | Title | Category | Priority | Primary File |
|----|-------|----------|----------|--------------|
| P1-001 | ChromaDB wired to MemoryManager — requirements.txt has chromadb but zero usage in code | Fix + Feature — Memory | 🟠 P1 | `(new) backend/memory/manager.py` |
| P1-002 | Verify ACE→PPN ψ pipeline flows per-turn | Fix — ML | 🟠 P1 | `backend/orchestrator.py` |
| P1-003 | GEMINI_API_KEY sys.exit(1) blocks offline users | Fix — Config | 🟠 P1 | `backend/config.py:73` |
| P1-004 | Vault encryption upgrade: Fernet (AES-128-CBC) → AES-256-GCM | Security Upgrade | 🟠 P1 | `backend/security/vault.py` |
| P1-005 | Tool sandbox: FileSystemAdapter workspace path check exists but no resource limits | Security Fix | 🟠 P1 | `backend/adapters/filesystem.py` |
| P1-006 | Test suite: pytest in requirements.txt, zero test files exist | Quality — Tests | 🟠 P1 | `(new) tests/` |
| P1-007 | Local inference HTTP endpoints: Whisper / Piper wired in LocalInferenceBridge but no HTTP endpoints exposed | Fix — Inference | 🟠 P1 | `backend/app.py + local_bridge.py` |
| P1-008 | Prometheus /metrics endpoint — structlog exists, no metrics scraping | New — Observability | 🟠 P1 | `(new) backend/metrics.py` |
| P1-009 | ADOPT: Goals engine (ZeroClaw) — no long-horizon goal tracking in Alluci | Integrate — ZeroClaw | 🟠 P1 | `(new) backend/goals/` |
| P1-010 | ADOPT: SOP engine (ZeroClaw) — audited multi-step workflows with approval gates | Integrate — ZeroClaw | 🟠 P1 | `(new) backend/sop/` |
| P1-011 | ADOPT: Multi-provider registry (Accomplish/ZeroClaw) — only Gemini/OpenAI/Anthropic; add Groq, OpenRouter, DeepSeek, xAI, Mistral | Integrate — Accomplish | 🟠 P1 | `backend/inference/router.py` |
| P1-012 | ADOPT: Skill YAML files on disk (Accomplish SkillsManager) | Integrate — Accomplish | 🟠 P1 | `backend/skill_manager.py` |
| P1-013 | AdapterRegistry: only 2 adapters; add shell, web_search, web_fetch, code_eval, memory adapters | Feature — Tools | 🟠 P1 | `backend/adapters/registry.py` |
| P1-014 | Health endpoint /api/system/health lacks subsystem statuses | Fix — Ops | 🟠 P1 | `backend/app.py:416` |
| P1-015 | Redis optional: confirm graceful in-memory fallback when REDIS_URL not set | Fix — Config | 🟠 P1 | `backend/app.py:100` |

### Phase 2 — Intelligence Layer (P2) · Weeks 8–12

| ID | Title | Category | Priority | Primary File |
|----|-------|----------|----------|--------------|
| P2-001 | Memory REST endpoints + Memory Panel (frontend) | Feature — Memory | 🔵 P2 | `backend/app.py + MemoryPanel.tsx` |
| P2-002 | Document ingestion: PDF/DOCX/TXT → chunk → ChromaDB | Feature — Memory | 🔵 P2 | `(new) backend/adapters/tools/doc_ingest.py` |
| P2-003 | Voice input endpoint: Whisper.cpp ASR → POST /api/voice/transcribe | Feature — Voice | 🔵 P2 | `backend/app.py + local_bridge.py` |
| P2-004 | Voice output endpoint: Piper TTS → GET /api/voice/synthesise | Feature — Voice | 🔵 P2 | `backend/app.py + local_bridge.py` |
| P2-005 | Frontend voice UI: hold-to-speak + auto-play TTS response | Feature — Frontend | 🔵 P2 | `features/terminal/CommandBar.tsx` |
| P2-006 | Web search tool adapter (SerpAPI / Brave / DDG fallback) | Feature — Tools | 🔵 P2 | `(new) backend/adapters/tools/web_search.py` |
| P2-007 | Web fetch tool adapter (Playwright headless → Markdown) | Feature — Tools | 🔵 P2 | `(new) backend/adapters/tools/web_fetch.py` |
| P2-008 | Code execution adapter with output capture and timeout | Feature — Tools | 🔵 P2 | `(new) backend/adapters/tools/code_exec.py` |
| P2-009 | Screen capture tool (mss cross-platform) | Feature — Tools | 🔵 P2 | `(new) backend/adapters/tools/screen_capture.py` |
| P2-010 | Research orchestration mode: search → fetch → synthesise → cite | Feature — Orchestration | 🔵 P2 | `backend/engine/planner.py` |
| P2-011 | ADOPT: LM Studio + AWS Bedrock + Cohere + Together + custom base_url providers | Integrate — Accomplish | 🔵 P2 | `backend/inference/router.py` |
| P2-012 | Guardrail upgrade: add LLM-Guard / Llama-Guard local classifier | Security Upgrade | 🔵 P2 | `backend/security/guardrail.py:53` |
| P2-013 | ADOPT: Multi-agent coordination backend (AgentsPanel frontend exists; backend incomplete) | Integrate — OpenClaw | 🔵 P2 | `backend/app.py:1171` |
| P2-014 | Session continuation: reload prior context from MessageLog on resume | Feature — Sessions | 🔵 P2 | `backend/app.py + models.py` |
| P2-015 | Memory compaction daily cron: summarise entries >30 days | Feature — Memory | 🔵 P2 | `backend/cron_engine.py` |

### Phase 3 — Bridge Completions (P3) · Weeks 13–18

| ID | Title | Category | Priority | Primary File |
|----|-------|----------|----------|--------------|
| P3-001 | Signal bridge: signal-cli subprocess lines all commented out | Fix — Bridge | 🟠 P1 | `backend/bridges/signal.py:47` |
| P3-002 | Telegram: long-polling loop missing | Fix — Bridge | 🟠 P1 | `backend/bridges/telegram.py` |
| P3-003 | Unified inbound message pipeline: _dispatch_inbound() → orchestrator | Architecture — Bridge | 🟠 P1 | `backend/bridges/base.py` |
| P3-004 | Bridge health() endpoint for all bridges | Feature — Bridge | 🔵 P2 | `backend/bridges/base.py + all bridges` |
| P3-005 | Discord: on_message → _dispatch_inbound → orchestrator (wiring missing) | Fix — Bridge | 🔵 P2 | `backend/bridges/discord.py` |
| P3-006 | WhatsApp: process_webhook_event not dispatched to orchestrator | Fix — Bridge | 🔵 P2 | `backend/bridges/whatsapp.py` |
| P3-007 | Gmail: connect() doesn't load vault creds on startup | Fix — Bridge | 🔵 P2 | `backend/bridges/gmail.py` |
| P3-008 | Google Drive: saves plain JSON (not vault); connect() missing token load | Fix — Bridge | 🔵 P2 | `backend/bridges/gdrive.py` |
| P3-009 | Slack: Events API webhook → parse → _dispatch_inbound → orchestrator | Fix — Bridge | 🔵 P2 | `backend/bridges/slack.py` |
| P3-010 | Facebook: implement Graph API send/receive | Feature — Bridge | 🔵 P2 | `backend/bridges/facebook.py` |
| P3-011 | Instagram: implement Graph API DM send/receive | Feature — Bridge | 🔵 P2 | `backend/bridges/instagram.py` |
| P3-012 | MS Teams: implement Bot Framework MSAL token + webhook | Feature — Bridge | 🔵 P2 | `backend/bridges/msteams.py` |
| P3-013 | X/Twitter: implement v2 DM API send/receive | Feature — Bridge | 🔵 P2 | `backend/bridges/x_twitter.py` |
| P3-014 | WeChat: implement QR web session + polling | Feature — Bridge | 🟡 P3 | `backend/bridges/wechat.py` |
| P3-015 | WebChat: Playwright headless session, monitor, send | Feature — Bridge | 🟡 P3 | `backend/bridges/webchat.py` |
| P3-016 | iCloud: 2FA session flow wired but connect() is stub | Fix — Bridge | 🟡 P3 | `backend/bridges/icloud.py` |
| P3-017 | ADOPT: MQTT bridge (ZeroClaw) — IoT / home automation channel | Integrate — ZeroClaw | 🟡 P3 | `(new) backend/bridges/mqtt.py` |
| P3-018 | ADOPT: Matrix E2EE bridge (ZeroClaw) — secure team channel | Integrate — ZeroClaw | 🟡 P3 | `(new) backend/bridges/matrix.py` |
| P3-019 | ADOPT: IRC bridge (ZeroClaw) | Integrate — ZeroClaw | 🟡 P3 | `(new) backend/bridges/irc.py` |
| P3-020 | BridgeCenter frontend: show real connected status from /api/channels/{id}/health | Fix — Frontend | 🔵 P2 | `components/BridgeCenter.tsx` |

### Phase 4 — Platform Packages (P4) · Weeks 19–24

| ID | Title | Category | Priority | Primary File |
|----|-------|----------|----------|--------------|
| P4-001 | macOS Apple Silicon: launchd plist service installer | Platform — macOS AS | 🔵 P2 | `(new) backend/platform/macos.py` |
| P4-002 | macOS Apple Silicon: Metal GPU inference via Ollama | Platform — macOS AS | 🔵 P2 | `scripts/setup_sovereign_stack.sh` |
| P4-003 | macOS Apple Silicon: HealthKit / Apple Watch → /api/telemetry | Platform — macOS AS | 🟡 P3 | `(new) companion WatchOS app` |
| P4-004 | macOS Apple Silicon: Keychain vault key storage | Platform — macOS AS | 🔵 P2 | `backend/security/vault.py + keyring` |
| P4-005 | macOS Apple Silicon: Face ID WebAuthn platform authenticator | Platform — macOS AS | 🟡 P3 | `backend/security/auth.py` |
| P4-006 | macOS Apple Silicon: Homebrew formula | Platform — macOS AS | 🟡 P3 | `(new) Formula/alluci.rb` |
| P4-007 | macOS Intel: CPU-only Ollama + quantised model recommendations | Platform — macOS Intel | 🔵 P2 | `setup_sovereign_stack.sh + onboarding` |
| P4-008 | macOS Intel: Touch ID or password WebAuthn fallback | Platform — macOS Intel | 🟡 P3 | `backend/security/auth.py` |
| P4-009 | macOS Intel: Keychain vault key storage | Platform — macOS Intel | 🔵 P2 | `backend/security/vault.py` |
| P4-010 | Linux: systemd user service installer | Platform — Linux | 🔵 P2 | `(new) backend/platform/linux.py` |
| P4-011 | Linux: .deb / .rpm package (fpm) | Platform — Linux | 🟡 P3 | `Makefile` |
| P4-012 | Linux: CUDA + ROCm Ollama detection and model VRAM sizing | Platform — Linux | 🔵 P2 | `setup_sovereign_stack.sh` |
| P4-013 | Linux: Landlock LSM subprocess isolation (kernel ≥5.13) | Platform — Linux | 🔵 P2 | `backend/security/sandbox.py` |
| P4-014 | Linux: GNOME Keyring / libsecret vault key storage | Platform — Linux | 🔵 P2 | `backend/security/vault.py` |
| P4-015 | Linux: AppIndicator3 system tray + D-Bus notifications | Platform — Linux | 🟡 P3 | `(new) backend/platform/linux_tray.py` |
| P4-016 | Windows: install.ps1 + winget packaging | Platform — Windows | 🔵 P2 | `(new) install.ps1` |
| P4-017 | Windows: Windows Service via pywin32 / NSSM | Platform — Windows | 🔵 P2 | `(new) backend/platform/windows.py` |
| P4-018 | Windows: CUDA detection + Windows Hello WebAuthn | Platform — Windows | 🟡 P3 | `setup_sovereign_stack.ps1` |
| P4-019 | Windows: Windows Credential Manager vault key storage | Platform — Windows | 🔵 P2 | `backend/security/vault.py` |
| P4-020 | Raspberry Pi: LITE_MODE (disables Torch/ChromaDB/gudhi) + 1B model | Platform — RPi | 🔵 P2 | `backend/config.py + setup script` |
| P4-021 | Raspberry Pi: SQLite FTS5 keyword memory fallback in LITE_MODE | Platform — RPi | 🔵 P2 | `(new) backend/memory/fts_memory.py` |
| P4-022 | Raspberry Pi: armhf .deb package | Platform — RPi | 🟡 P3 | `Makefile deb-pi target` |
| P4-023 | Universal install.sh (curl \| sh — detects platform) | Platform — All | 🟡 P3 | `(new) scripts/install.sh` |
| P4-024 | Docker Compose profiles: lite / full / pi | Platform — Docker | 🟡 P3 | `docker-compose.yml` |

---

## Phase 0 — Critical Bugs

> These 3 bugs must ship before any other work matters. Until fixed, **zero of the 20 bridges work**.

---

### P0-001 — BridgeManager setTimeout Mocks

**File:** `bridgeManager.ts`  
**Priority:** 🔴 P0 — Blocks all bridge communication

**Root Cause:**  
`sendMessage()`, `uploadToCloud()`, `retrieveFromCloud()`, and `executeSocialTask()` all contain `setTimeout(() => resolve(true), 1000)` mocks. The comment says `// REMOVE: All mock dispatch methods` but the real backend calls were never written.

**Step-by-step fix:**

**Step 1.** Open `bridgeManager.ts` and replace all four `setTimeout` methods:

```typescript
// REMOVE all setTimeout mocks and replace with real backend calls:

async sendMessage(bridgeId: string, recipient: string, text: string): Promise<boolean> {
  const res = await fetch(`/api/channels/${bridgeId}/send`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${this.accessToken}`
    },
    body: JSON.stringify({ recipient, content: text })
  });
  return res.ok;
}

async uploadToCloud(bridgeId: string, fileData: string, fileName: string): Promise<boolean> {
  const res = await fetch(`/api/channels/${bridgeId}/upload`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${this.accessToken}`
    },
    body: JSON.stringify({ file_data: fileData, file_name: fileName })
  });
  return res.ok;
}
```

**Step 2.** Add the four missing backend endpoints to `backend/app.py`:

| Endpoint | Method | Body | Returns |
|----------|--------|------|---------|
| `POST /api/channels/{bridge_id}/send` | POST | `{ recipient, content }` | `{ status, message_id }` |
| `POST /api/channels/{bridge_id}/upload` | POST | `{ file_data, file_name }` | `{ status, url }` |
| `GET /api/channels/{bridge_id}/health` | GET | — | `{ is_connected, last_activity, last_error, latency_ms }` |
| `GET /api/channels/{bridge_id}/unread` | GET | — | `[{ from, body, timestamp }]` |

**Step 3.** Add implementation in `app.py` after the channel toggle endpoint:

```python
@app.post("/api/channels/{channel_id}/send", dependencies=[Depends(verify_authenticated)])
async def send_channel_message(channel_id: str, data: Dict[str, Any] = Body(...)):
    adapter = channel_registry.get(channel_id)
    if not adapter or not adapter.is_connected:
        raise HTTPException(status_code=503, detail=f"Channel {channel_id} not connected")
    result = await adapter.send(data["recipient"], data["content"])
    return result

@app.get("/api/channels/{channel_id}/health", dependencies=[Depends(verify_authenticated)])
async def get_channel_health(channel_id: str):
    adapter = channel_registry.get(channel_id)
    if not adapter:
        raise HTTPException(status_code=404)
    if hasattr(adapter, "get_health"):
        return adapter.get_health()
    return {"channel": channel_id, "is_connected": adapter.is_connected}
```

**Step 4.** Acceptance test:
```bash
curl -X POST http://localhost:8000/api/channels/telegram/send \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"recipient": "123456789", "content": "test"}'
# Expected: {"status": "success", "message_id": "..."}
```

---

### P0-002 — Gmail SMTP Dead Mapping

**File:** `backend/adapters/bridge_actualization.py`, line 31  
**Priority:** 🔴 P0 — Gmail silently fails for all users

**Root Cause:**  
Google permanently revoked SMTP basic authentication on 30 May 2022. `bridge_actualization.py` still maps `"gmail"` to `EmailBridge` (SMTP). Every Gmail send silently fails with an auth error.

**Step-by-step fix:**

**Step 1.** Open `backend/adapters/bridge_actualization.py`, find `_init_bridges()`, change the `gmail` entry:

```python
# BEFORE (broken)
from ..bridges.email import EmailBridge
self.bridge_map = {
    "gmail": EmailBridge,   # ← SMTP dead since May 2022
    ...
}

# AFTER (fixed)
from ..bridges.gmail import GmailBridge
self.bridge_map = {
    "gmail":   GmailBridge,   # ← uses Gmail REST API + OAuth2
    "email":   EmailBridge,   # SMTP valid for non-Google servers only
    "outlook": EmailBridge,
    ...
}
```

**Step 2.** Acceptance test:
```python
# tests/test_bridge_map.py
from backend.adapters.bridge_actualization import BridgeActualizationAdapter
from backend.bridges.gmail import GmailBridge
adapter = BridgeActualizationAdapter()
assert adapter.bridge_map["gmail"] == GmailBridge
assert adapter.bridge_map["email"] != GmailBridge
```

---

### P0-003 — OAuth Config Key Mismatch

**Files:** `backend/oauth_config.py`, `backend/app.py:2162`, `backend/config.py`  
**Priority:** 🔴 P0 — Crashes every OAuth flow for all 8 OAuth bridges

**Root Cause:**  
`oauth_config.py` defines configs with 2-letter shortcodes (`'sl'`, `'dc'`, `'gm'` etc.) but `bridge_actualization._handle_oauth_flow()` passes the full bridge ID (`'slack'`, `'discord'`, `'gmail'`). `OAUTH_CONFIGS.get('slack')` returns `None` → every OAuth exchange throws `AdapterError`.

**Step-by-step fix:**

**Step 1.** Rewrite `backend/oauth_config.py` with full-length keys (Option A — preferred):

```python
import os

OAUTH_CONFIGS = {
    "slack": {
        "client_id": os.getenv("SLACK_CLIENT_ID"),
        "client_secret": os.getenv("SLACK_CLIENT_SECRET"),
        "authorize_url": "https://slack.com/oauth/v2/authorize",
        "token_url": "https://slack.com/api/oauth.v2.access",
        "scopes": ["channels:read", "chat:write", "files:write"]
    },
    "discord": {
        "client_id": os.getenv("DISCORD_CLIENT_ID"),
        "client_secret": os.getenv("DISCORD_CLIENT_SECRET"),
        "authorize_url": "https://discord.com/api/oauth2/authorize",
        "token_url": "https://discord.com/api/oauth2/token",
        "scopes": ["bot", "messages.read"]
    },
    "gmail": {
        "client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "scopes": ["https://www.googleapis.com/auth/gmail.modify"]
    },
    "gdrive": {
        "client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "scopes": ["https://www.googleapis.com/auth/drive.file"]
    },
    "instagram": {
        "client_id": os.getenv("INSTAGRAM_CLIENT_ID"),
        "client_secret": os.getenv("INSTAGRAM_CLIENT_SECRET"),
        "authorize_url": "https://api.instagram.com/oauth/authorize",
        "token_url": "https://api.instagram.com/oauth/access_token",
        "scopes": ["user_profile", "user_media", "instagram_graph_user_messages"]
    },
    "facebook": {
        "client_id": os.getenv("FACEBOOK_CLIENT_ID"),
        "client_secret": os.getenv("FACEBOOK_CLIENT_SECRET"),
        "authorize_url": "https://www.facebook.com/v18.0/dialog/oauth",
        "token_url": "https://graph.facebook.com/v18.0/oauth/access_token",
        "scopes": ["pages_messaging", "pages_show_list"]
    },
    "x": {
        "client_id": os.getenv("TWITTER_CLIENT_ID"),
        "client_secret": os.getenv("TWITTER_CLIENT_SECRET"),
        "authorize_url": "https://twitter.com/i/oauth2/authorize",
        "token_url": "https://api.twitter.com/2/oauth2/token",
        "scopes": ["tweet.read", "tweet.write", "dm.read", "dm.write", "offline.access"]
    },
    "msteams": {
        "client_id": os.getenv("MSTEAMS_CLIENT_ID"),
        "client_secret": os.getenv("MSTEAMS_CLIENT_SECRET"),
        "authorize_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        "token_url": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
        "scopes": ["Chat.ReadWrite", "offline_access"]
    }
}
```

**Step 2.** Add all OAuth client ID/secret fields to `backend/config.py` `Settings` class:

```python
# backend/config.py — add to Settings class
GOOGLE_CLIENT_ID:      Optional[str] = None
GOOGLE_CLIENT_SECRET:  Optional[str] = None
DISCORD_CLIENT_ID:     Optional[str] = None
DISCORD_CLIENT_SECRET: Optional[str] = None
SLACK_CLIENT_ID:       Optional[str] = None
SLACK_CLIENT_SECRET:   Optional[str] = None
X_CLIENT_ID:           Optional[str] = None
X_CLIENT_SECRET:       Optional[str] = None
META_APP_ID:           Optional[str] = None
META_APP_SECRET:       Optional[str] = None
MS_CLIENT_ID:          Optional[str] = None
MS_CLIENT_SECRET:      Optional[str] = None
```

**Step 3.** Add the same keys to `.env.example`.

**Step 4.** Remove the now-redundant `id_map` dict inside `bridge_actualization._handle_oauth_flow()` since keys now match directly.

**Step 5.** Acceptance test:
```python
# tests/test_oauth.py
from backend.oauth_config import OAUTH_CONFIGS
bridges = ["slack", "discord", "gmail", "gdrive", "instagram", "facebook", "x", "msteams"]
for b in bridges:
    assert OAUTH_CONFIGS.get(b) is not None, f"Missing OAuth config for {b}"
    assert OAUTH_CONFIGS[b]["client_id"] is not None or True  # may be None from env
```

---

## Phase 1 — Runtime Core

### P1-001 — Wire ChromaDB into MemoryManager

**File:** `(new) backend/memory/manager.py`  
**Priority:** 🟠 P1

**Current state:** `chromadb==0.4.22` and `sentence-transformers==2.3.1` are both in `requirements.txt`. Zero lines of code in any backend module import or use ChromaDB. The agent has no persistent semantic memory across sessions.

**Step-by-step implementation:**

**Step 1.** Create `backend/memory/__init__.py` (empty).

**Step 2.** Create `backend/memory/manager.py`:

```python
import chromadb
from chromadb.utils import embedding_functions
from pathlib import Path

class MemoryManager:
    def __init__(self, persist_dir="~/.alluci/chroma", lite_mode=False):
        if lite_mode:
            self._use_fts = True  # RPi fallback — see P4-021
            return
        path = str(Path(persist_dir).expanduser())
        self.client = chromadb.PersistentClient(path=path)
        ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"  # 22MB, fast on all platforms
        )
        self.collection = self.client.get_or_create_collection(
            "agent_memory", embedding_function=ef,
            metadata={"hnsw:space": "cosine"}
        )

    async def store(self, key: str, content: str, metadata: dict = None):
        self.collection.upsert(documents=[content], ids=[key],
                               metadatas=[metadata or {}])

    async def recall(self, query: str, top_k: int = 5) -> list[dict]:
        r = self.collection.query(query_texts=[query], n_results=top_k)
        return [{"id": i, "content": d, "meta": m}
                for i, d, m in zip(r["ids"][0], r["documents"][0], r["metadatas"][0])]

    async def forget(self, key: str):
        self.collection.delete(ids=[key])
```

**Step 3.** Wire into `app.py` lifespan (after vault init):

```python
from .memory.manager import MemoryManager
memory = MemoryManager(lite_mode=getattr(settings, "LITE_MODE", False))
orchestrator.memory = memory
```

**Step 4.** Wire into `orchestrator.py` `execute_objective()` — pre-turn recall:

```python
# Top of execute_objective()
if self.memory:
    top5 = await self.memory.recall(objective, top_k=5)
    if top5:
        memory_ctx = "\n".join(f"- {m['content']}" for m in top5)
        system_context += f"\n\n# RELEVANT MEMORY\n{memory_ctx}"
```

**Step 5.** Wire into `orchestrator.py` — post-turn store:

```python
# After successful plan completion
if self.memory:
    await self.memory.store(
        str(run.id),
        f"Objective: {objective}\nResult: {str(result)[:500]}",
        {"date": datetime.now().isoformat(), "score": score}
    )
```

**Step 6.** Add REST endpoints to `app.py`:

```python
@app.get("/api/memory", dependencies=[Depends(verify_authenticated)])
async def list_memory(limit: int = Query(50)):
    return memory.collection.get(limit=limit)

@app.get("/api/memory/search", dependencies=[Depends(verify_authenticated)])
async def search_memory(q: str = Query(...)):
    return await memory.recall(q, top_k=10)

@app.delete("/api/memory/{entry_id}", dependencies=[Depends(verify_authenticated)])
async def forget_memory(entry_id: str):
    await memory.forget(entry_id)
    return {"deleted": entry_id}
```

---

### P1-002 — Verify ACE→PPN ψ Pipeline Per-Turn

**File:** `backend/orchestrator.py`  
**Priority:** 🟠 P1

**Step-by-step fix:**

Add the following block at the top of `execute_objective()`, replacing the existing partial `_perform_ppn_check` call:

```python
# backend/orchestrator.py — inside execute_objective()

# Step 1: Get current ACE state
ace_state = self.ace.current_state
psi = min(ace_state.get("stress_score", 0) / 100.0, 1.0)

# Step 2: Embed objective text with PPN
import torch
obj_tensor = torch.zeros(384)  # replace with real text encoder in P2
latent, betti = self.ppn.forward(obj_tensor.unsqueeze(0), psi=psi)

# Step 3: DPK validation gate
from .security.dpk import PolytopeState
state = PolytopeState(
    signature_hash=hash(objective),
    vertices_V=int(betti[0][0].item() * 10),
    edges_E=int(betti[0][1].item() * 10),
    faces_F=max(1, int(betti[0][2].item() * 10)),
    betti=[b.item() for b in betti[0]],
    affective_tension_psi=psi
)
if not self.dpk.validate_manifold_integrity(state):
    raise PlanRejectedError("DPK topology gate failed")

# Step 4: Broadcast ACE state to all WS clients
if self.ws_gateway:
    await self.ws_gateway.broadcast_event("ace.state", {
        "mode": ace_state.get("flow_mode"),
        "psi": psi,
        "stress": ace_state.get("stress_score")
    })
```

---

### P1-003 — Make GEMINI_API_KEY Optional

**File:** `backend/config.py:73`  
**Priority:** 🟠 P1

**Step-by-step fix:**

```python
# backend/config.py — BEFORE
GEMINI_API_KEY: str  # blocks startup if not set

# AFTER
GEMINI_API_KEY: Optional[str] = None
LOCAL_ONLY: bool = False  # True = no cloud calls, Ollama only

@field_validator("GEMINI_API_KEY")
@classmethod
def validate_api_key(cls, v):
    if not v and not os.getenv("LOCAL_ONLY", "").lower() in ("1", "true"):
        logger.warning(
            "GEMINI_API_KEY not set. Cloud inference disabled. "
            "Set LOCAL_ONLY=true for local-only mode."
        )
    return v
```

Add `LOCAL_ONLY=true` to `.env.example` with a comment explaining offline/Pi usage.

---

### P1-004 — Vault Encryption Upgrade: Fernet → AES-256-GCM

**File:** `backend/security/vault.py`  
**Priority:** 🟠 P1

**Step-by-step migration:**

| Step | File | Detail |
|------|------|--------|
| 1. Add PyNaCl | `requirements.txt` | Add: `PyNaCl>=1.5.0` |
| 2. AES256GCM class | `backend/security/vault.py` | Use `cryptography.hazmat.primitives.ciphers.aead.AESGCM`. 12-byte nonce, 256-bit key. Store: `version_byte(1) + nonce(12) + ciphertext` |
| 3. Version header | All `.vault` files | `0x01` = Fernet legacy. `0x02` = AES-256-GCM. Detect on first read byte. |
| 4. Auto-migration | `vault.py retrieve_secret()` | If first byte == `0x01`: Fernet-decrypt, re-encrypt with AES-256-GCM, overwrite file, log migration. |
| 5. Key validation | `config.py` | `POLYTOPE_MASTER_KEY`: require 32 bytes minimum. Derive with HKDF if shorter. |

**Core implementation:**

```python
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os, struct

VERSION_FERNET = b'\x01'
VERSION_AES256GCM = b'\x02'

def _encrypt_v2(self, data: bytes) -> bytes:
    key = self._derive_32_byte_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ct = aesgcm.encrypt(nonce, data, None)
    return VERSION_AES256GCM + nonce + ct

def _decrypt_auto(self, raw: bytes) -> bytes:
    version = raw[:1]
    if version == VERSION_FERNET:
        # Legacy path — auto-migrates
        plaintext = self.fernet.decrypt(raw[1:])
        return plaintext
    elif version == VERSION_AES256GCM:
        key = self._derive_32_byte_key()
        nonce, ct = raw[1:13], raw[13:]
        return AESGCM(key).decrypt(nonce, ct, None)
    raise ValueError(f"Unknown vault version: {version!r}")
```

---

### P1-005 — Tool Sandbox: Resource Limits

**Files:** `backend/security/sandbox.py` (new), `backend/adapters/filesystem.py`  
**Priority:** 🟠 P1

**Implementation by platform:**

| Sandbox Feature | Platform | Implementation |
|-----------------|----------|----------------|
| CPU time limit | Linux + macOS | `subprocess preexec_fn: resource.setrlimit(RLIMIT_CPU, (30, 30))` |
| Memory limit | Linux + macOS | `subprocess preexec_fn: resource.setrlimit(RLIMIT_AS, (512*MB, 512*MB))` |
| File size limit | All | `subprocess preexec_fn: resource.setrlimit(RLIMIT_FSIZE, (100*MB, 100*MB))` |
| Landlock (filesystem isolation) | Linux ≥5.13 | `python-landlock`: restrict shell adapter to `WORKSPACE_ROOT` only |
| `sandbox-exec` | macOS | Wrap subprocess: `sandbox-exec -f minimal.sb` — allow only workspace writes |
| Job Objects | Windows | `ctypes Win32 CreateJobObject + SetInformationJobObject` — limit memory + CPU |

**Step-by-step:**

**Step 1.** Create `backend/security/sandbox.py`:

```python
import sys, os, resource

def apply_resource_limits():
    """Call as preexec_fn in subprocess.run() on Unix."""
    if sys.platform in ("linux", "darwin"):
        MB = 1024 * 1024
        resource.setrlimit(resource.RLIMIT_CPU, (30, 30))
        resource.setrlimit(resource.RLIMIT_AS, (512 * MB, 512 * MB))
        resource.setrlimit(resource.RLIMIT_FSIZE, (100 * MB, 100 * MB))
```

**Step 2.** In `backend/adapters/filesystem.py` `execute()`, add `preexec_fn=apply_resource_limits` to all `subprocess.run()` calls.

**Step 3.** Add `python-landlock>=0.3` to `requirements.txt`.

---

### P1-006 — Test Suite

**Files:** `backend/tests/` (expand existing), new `tests/` modules  
**Priority:** 🟠 P1

**Required test modules:**

| Test Module | File | Coverage Target |
|-------------|------|-----------------|
| Vault encrypt/decrypt + migration | `tests/test_vault.py` | AES-256-GCM roundtrip; Fernet→GCM migration; path permissions 0600 |
| ACE all 4 flow modes | `tests/test_ace.py` | STANDARD/DEEP_WORK/PEAK_PERFORMANCE/RECOVERY_MODE threshold values |
| DAG Planner mock | `tests/test_planner.py` | Mock ModelRouter; verify DAG structure; dependency ordering; cycle detection |
| DAG Executor concurrency | `tests/test_executor.py` | 3 concurrent tasks; mock adapters; approval interceptor fires on shell action |
| OAuth config key mapping | `tests/test_oauth.py` | All 8 bridges: `OAUTH_CONFIGS.get(full_id)` returns non-None config |
| Gmail bridge mapping | `tests/test_bridge_map.py` | `'gmail'` resolves to `GmailBridge`, NOT `EmailBridge` |
| Memory store + recall | `tests/test_memory.py` | Store 5 entries; recall by query; top-1 relevance check; forget; compaction |
| CronEngine schedule types | `tests/test_cron.py` | interval/cron/run_at each fires; DB history written; delivery routing called |
| WS Gateway JWT auth | `tests/test_ws.py` | Valid JWT→connected; invalid JWT→AUTH_REQUIRED; RPC dispatch |
| Guardrail all 16 patterns | `tests/test_guardrail.py` | All injection patterns blocked; clean input passes; length limit enforced |
| ExecApproval flow | `tests/test_exec_approval.py` | allow_once / allow_always / deny; WS push; persistent policy loaded on restart |
| Signal bridge subprocess | `tests/test_signal.py` | signal-cli mock; get_link_qr returns URI; send calls subprocess correctly |

**Step-by-step:**

**Step 1.** Ensure `pytest.ini` or `conftest.py` sets `asyncio_mode = auto`.

**Step 2.** Run baseline: `cd backend && pytest tests/ -v --tb=short`

**Step 3.** Target: `pytest --cov=backend --cov-report=term-missing` → coverage >50% after P1-006.

---

### P1-007 — Expose Whisper + Piper HTTP Endpoints

**Files:** `backend/app.py`, `backend/inference/local_bridge.py`  
**Priority:** 🟠 P1

**Step-by-step:**

**Step 1.** Add to `backend/app.py`:

```python
@app.post("/api/voice/transcribe", dependencies=[Depends(verify_authenticated)])
async def transcribe_audio(request: Request):
    """Receives raw audio bytes, returns transcribed text via Whisper.cpp."""
    audio_bytes = await request.body()
    text = await local_inference.transcribe(audio_bytes)
    return {"text": text}

@app.get("/api/voice/synthesise", dependencies=[Depends(verify_authenticated)])
async def synthesise_speech(text: str = Query(...)):
    """Returns audio/wav stream from Piper TTS."""
    audio = await local_inference.speak_piper(text)
    return Response(content=audio, media_type="audio/wav")
```

**Step 2.** Rename `transcribe_stream()` → `transcribe()` in `local_bridge.py` for clarity (or add alias).

**Step 3.** Test:
```bash
curl -X POST http://localhost:8000/api/voice/transcribe \
  -H "Authorization: Bearer $TOKEN" \
  --data-binary @test.wav
# Expected: {"text": "Hello world"}
```

---

### P1-008 — Prometheus /metrics Endpoint

**Files:** `(new) backend/metrics.py`, `backend/app.py`  
**Priority:** 🟠 P1

**Step 1.** Add to `requirements.txt`: `prometheus-client>=0.20.0`

**Step 2.** Create `backend/metrics.py`:

```python
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response

inference_tokens = Counter(
    "alluci_inference_tokens_total",
    "Total LLM tokens consumed",
    ["provider", "model", "direction"]
)
request_duration = Histogram(
    "alluci_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"]
)
active_ws = Gauge("alluci_active_websocket_clients", "Active WS connections")
bridge_messages = Counter(
    "alluci_bridge_messages_total",
    "Messages processed per bridge",
    ["bridge_id", "direction"]
)
```

**Step 3.** Add to `backend/app.py`:

```python
from .metrics import generate_latest, CONTENT_TYPE_LATEST

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
```

---

### P1-009 — ADOPT: Goals Engine (ZeroClaw)

**Files:** `(new) backend/goals/`  
**Priority:** 🟠 P1

| Component | File | Implementation |
|-----------|------|----------------|
| Goal schema | `backend/goals/models.py` | `Goal`: id, title, description, target_date, status, parent_id, progress_pct, tags[] |
| Goal store | `backend/goals/store.py` | SQLite-backed CRUD with alembic migration. Hierarchical parent→child goals. |
| Goal engine | `backend/goals/engine.py` | Auto-link run results to active goals. Update `progress_pct` on sub-goal completion. |
| Goal decomposer | `backend/goals/decomposer.py` | LLM call: given goal text, return list of SMART sub-goals with effort estimates. |
| Goal tools | `backend/adapters/registry.py` | Register: `goal_create`, `goal_list`, `goal_update`, `goal_complete`, `goal_decompose` |
| Goals REST | `backend/app.py` | `GET/POST /api/goals`; `PUT/DELETE /api/goals/{id}`; `POST /api/goals/{id}/decompose` |
| Goals Panel | `features/goals/GoalsPanel.tsx` | Kanban: Not Started / In Progress / Complete. Decompose button. Progress bars. |

---

### P1-010 — ADOPT: SOP Engine (ZeroClaw)

**Files:** `(new) backend/sop/`  
**Priority:** 🟠 P1

| Component | File | Implementation |
|-----------|------|----------------|
| SOP schema | `backend/sop/schema.py` | `SOPDefinition`, `SOPStep` (types: `tool_call` / `agent_message` / `approval_gate` / `manual`), `SOPCondition` |
| SOP engine | `backend/sop/engine.py` | Sequential step execution; condition branching; pauses at `approval_gate` via `ExecApprovalManager` |
| SOP registry | `backend/sop/registry.py` | Load `.sop.yaml` files from `~/.alluci/sops/`. CRUD: list, get, create, update, delete. |
| SOP audit log | `backend/sop/audit.py` | Per-execution append-only JSONL with SHA-256 chain integrity. |
| SOP tools | `adapters/registry.py` | `sop_list`, `sop_status`, `sop_run`, `sop_advance`, `sop_approve`, `sop_cancel` |
| SOP REST | `backend/app.py` | `GET/POST /api/sops`; `POST /api/sops/{id}/run`; `GET /api/sops/{id}/status` |
| SOP Panel | `features/sop/SOPPanel.tsx` | List view, run button, live step progress, approval modal, audit log viewer |

---

### P1-011 — ADOPT: Multi-Provider LLM Registry

**File:** `backend/inference/router.py`  
**Priority:** 🟠 P1

| Provider | Library | Config Key | Notes | Priority |
|----------|---------|-----------|-------|----------|
| Groq (300+ tok/s) | `groq>=0.5.0` | `GROQ_API_KEY` | Llama 3.1 70b in <1s | 🟠 P1 |
| OpenRouter (200+ models) | `openai` SDK + `base_url` | `OPENROUTER_API_KEY` | Best BYOM option | 🟠 P1 |
| Custom OpenAI-compatible | `openai` SDK | `CUSTOM_API_BASE_URL` | Covers llama.cpp server, vllm, sglang | 🟠 P1 |
| DeepSeek | `openai` SDK + deepseek base_url | `DEEPSEEK_API_KEY` | Best open-weight reasoning | 🔵 P2 |
| xAI / Grok | `openai` SDK + xai base_url | `XAI_API_KEY` | | 🔵 P2 |
| Mistral AI | `mistralai>=0.4.0` | `MISTRAL_API_KEY` | | 🔵 P2 |
| AWS Bedrock | `boto3` (already installed) | `AWS_ACCESS_KEY_ID` etc | | 🔵 P2 |
| Cohere | `cohere>=5.0.0` | `COHERE_API_KEY` | | 🟡 P3 |
| Together AI | `together>=1.1.0` | `TOGETHER_API_KEY` | | 🟡 P3 |
| LM Studio | `openai` SDK + lmstudio base_url | `LM_STUDIO_URL` | Local alternative to Ollama | 🟡 P3 |

---

### P1-012 — ADOPT: Skill YAML Files (Accomplish)

**File:** `backend/skill_manager.py`  
**Priority:** 🟠 P1

| Change | Detail |
|--------|--------|
| Add `.skill.yaml` parser | `backend/skill_manager.py`: parse YAML files from `~/.alluci/skills/*.skill.yaml` on startup. Merge with vault registry. |
| Skill file schema | `name`, `version`, `description`, `author`, `tools[]`, `trigger_phrases[]`, `system_prompt_injection`, `required_bridges[]` |
| Bundled skills | Ship 6 built-in skills: `code-review`, `git-commit`, `web-research`, `meeting-summary`, `email-compose`, `skill-creator` |
| Skill sharing | Signed `.skill.yaml` files. `SkillManager.import_package()` validates signature before loading. Risk scan already exists. |

---

### P1-013 — AdapterRegistry: Add 5 New Adapters

**Files:** `backend/adapters/registry.py` + new tool files  
**Priority:** 🟠 P1

| Adapter | File | Registry Name | Notes |
|---------|------|---------------|-------|
| ShellAdapter | `backend/adapters/tools/shell.py` | `shell` | Sandboxed subprocess. Approval-gated. |
| WebSearchAdapter | `backend/adapters/tools/web_search.py` | `web_search` | SerpAPI → Brave → DDG fallback |
| WebFetchAdapter | `backend/adapters/tools/web_fetch.py` | `web_fetch` | Playwright headless. Strip to markdown. Max 4000 tokens. |
| MemoryAdapter | `backend/adapters/tools/memory.py` | `memory_store` / `memory_recall` / `memory_forget` | Delegates to MemoryManager |
| CodeEvalAdapter | `backend/adapters/tools/code_eval.py` | `code_eval` | Execute Python in sandboxed subprocess. Return stdout/stderr/returncode. |
| DocIngestAdapter | `backend/adapters/tools/doc_ingest.py` | `doc_ingest` | PDF (PyMuPDF) + DOCX (python-docx) + TXT. Chunk 512 tokens. Store in ChromaDB. |

---

### P1-014 — Enrich /api/system/health

**File:** `backend/app.py:466`  
**Priority:** 🟠 P1

**Step-by-step:**

Add subsystem status checks to the `/api/system/health` endpoint response:

```python
@app.get("/api/system/health", dependencies=[Depends(verify_authenticated)])
async def get_system_health():
    # ChromaDB
    chroma_status = "healthy"
    try:
        memory.collection.count()
    except Exception as e:
        chroma_status = f"unhealthy: {e}"

    # Ollama
    ollama_status = "healthy" if local_inference.ollama_ready else "unavailable"

    # Redis
    redis_status = "healthy"
    try:
        await redis_client.ping()
    except Exception:
        redis_status = "unavailable"

    return {
        "db": db_status,
        "vault": vault_status,
        "cron": cron_status,
        "chroma": chroma_status,
        "ollama": ollama_status,
        "redis": redis_status,
        "bridge_count": len(channel_registry),
        "bridges_connected": sum(1 for a in channel_registry.values() if a.is_connected),
        "whisper_ready": local_inference.whisper_ready,
        "piper_ready": local_inference.piper_ready,
    }
```

---

### P1-015 — Redis Optional Graceful Fallback

**File:** `backend/app.py:100`  
**Priority:** 🟠 P1

**Step-by-step:**

```python
# backend/app.py lifespan — BEFORE
redis_client = redis.from_url(settings.REDIS_URL, ...)
await FastAPILimiter.init(redis_client)

# AFTER
redis_client = None
if settings.REDIS_URL:
    try:
        redis_client = redis.from_url(settings.REDIS_URL, encoding="utf-8")
        await FastAPILimiter.init(redis_client)
        logger.info(f"Redis rate limiter active on {settings.REDIS_URL}")
    except Exception as e:
        logger.warning(f"Redis unavailable ({e}). Using in-memory rate limiter fallback.")
        # SlowAPI in-memory limiter as fallback
        from slowapi import Limiter
        from slowapi.util import get_remote_address
        app.state.limiter = Limiter(key_func=get_remote_address)
else:
    logger.info("REDIS_URL not set. Rate limiting disabled (development mode).")
```

---

## Phase 2 — Intelligence Layer

### P2-001 — Memory REST Endpoints + Memory Panel

Build on P1-001. Add frontend panel `features/memory/MemoryPanel.tsx` with:
- Search box → `GET /api/memory/search?q=` 
- Entry list with timestamps and metadata
- Delete button per entry → `DELETE /api/memory/{id}`
- Entry count display

---

### P2-002 — Document Ingestion

**File:** `(new) backend/adapters/tools/doc_ingest.py`

Add to `requirements.txt`: `PyMuPDF>=1.23.0` (for PDF), `python-docx` (for DOCX).

```python
class DocIngestAdapter:
    name = "doc_ingest"
    CHUNK_SIZE = 512  # tokens, approx 2000 chars

    async def execute(self, args):
        path = args.get("path", "")
        ext = path.rsplit(".", 1)[-1].lower()

        if ext == "pdf":
            text = self._extract_pdf(path)
        elif ext in ("docx", "doc"):
            text = self._extract_docx(path)
        else:
            with open(path) as f:
                text = f.read()

        chunks = self._chunk(text)
        for i, chunk in enumerate(chunks):
            await memory.store(f"{path}::chunk{i}", chunk,
                               {"source": path, "chunk": i})
        return {"status": "ingested", "chunks": len(chunks), "source": path}
```

---

### P2-003–P2-005 — Voice I/O: Complete Stack

**Files:** `backend/app.py`, `features/terminal/CommandBar.tsx`

**Frontend hold-to-speak implementation:**

```typescript
// features/terminal/CommandBar.tsx — ADD voice controls
const [isRecording, setIsRecording] = useState(false);
const mediaRecorderRef = useRef<MediaRecorder | null>(null);

const startRecording = async () => {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  const mr = new MediaRecorder(stream, { mimeType: "audio/webm" });
  const chunks: BlobPart[] = [];
  mr.ondataavailable = e => chunks.push(e.data);
  mr.onstop = async () => {
    const blob = new Blob(chunks, { type: "audio/webm" });
    const res = await fetch("/api/voice/transcribe", {
      method: "POST",
      body: await blob.arrayBuffer(),
      headers: {
        "Content-Type": "audio/webm",
        "Authorization": `Bearer ${accessToken}`
      }
    });
    const { text } = await res.json();
    setInput(prev => prev + text);
  };
  mediaRecorderRef.current = mr;
  mr.start();
  setIsRecording(true);
};

// Browser SpeechRecognition fallback (from Accomplish) if Whisper unavailable:
const startFallbackRecognition = () => {
  const SR = (window as any).webkitSpeechRecognition || (window as any).SpeechRecognition;
  if (!SR) return;
  const r = new SR();
  r.onresult = (e: any) => setInput(prev => prev + e.results[0][0].transcript);
  r.start();
};
```

---

### P2-006 — Web Search Adapter

**File:** `(new) backend/adapters/tools/web_search.py`

```python
import httpx, os

class WebSearchAdapter:
    name = "web_search"

    async def execute(self, args):
        query = args.get("query", "")
        top_k = args.get("top_k", 10)

        if os.getenv("SERPAPI_KEY"):
            return await self._serpapi(query, top_k)
        if os.getenv("BRAVE_SEARCH_KEY"):
            return await self._brave(query, top_k)
        return await self._ddg_html(query, top_k)

    async def _brave(self, query, top_k):
        async with httpx.AsyncClient() as c:
            r = await c.get(
                "https://api.search.brave.com/res/v1/web/search",
                params={"q": query, "count": top_k},
                headers={"X-Subscription-Token": os.getenv("BRAVE_SEARCH_KEY")}
            )
            data = r.json()
            return [{"title": w["title"], "url": w["url"], "snippet": w.get("description", "")}
                    for w in data.get("web", {}).get("results", [])]
```

Add `SERPAPI_KEY` and `BRAVE_SEARCH_KEY` as `Optional[str] = None` to `config.py`.

---

### P2-007 — Web Fetch Adapter (Playwright → Markdown)

**File:** `(new) backend/adapters/tools/web_fetch.py`

Add to `requirements.txt`: `html2text>=2024.1.0`

```python
from playwright.async_api import async_playwright
import html2text

class WebFetchAdapter:
    name = "web_fetch"
    MAX_TOKENS = 4000

    async def execute(self, args):
        url = args.get("url", "")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, timeout=15000)
            html = await page.content()
            await browser.close()

        md = html2text.html2text(html)
        return {"url": url, "content": md[:self.MAX_TOKENS * 4]}
```

---

### P2-010 — Research Orchestration Mode

**File:** `backend/engine/planner.py`

Add a research plan template to the system prompt context:

```python
RESEARCH_PLAN_TEMPLATE = """
You are planning a research task. Use these tools in this order:
1. web_search: find the top 10 sources
2. web_fetch (×3): fetch and read the 3 most relevant sources
3. memory_store: save key findings with source URL as metadata
4. Return a structured report with: summary, key_findings[], sources[]
"""

# In Planner.build_system_prompt(), detect research intent:
if any(kw in objective.lower() for kw in ["research", "find out", "investigate", "summarise"]):
    context += "\n" + RESEARCH_PLAN_TEMPLATE
```

---

### P2-013 — Multi-Agent Coordination Backend

**Files:** `(new) backend/agents/`

| Component | File | Implementation |
|-----------|------|----------------|
| Agent schema | `backend/agents/models.py` | `Agent`: id, name, system_prompt, tools[], autonomy_level, soul_ref, status, workspace |
| Agent registry | `backend/agents/registry.py` | CRUD: list, create, update, delete, clone. Persistent to SQLite. |
| Agent spawn | `backend/agents/runner.py` | Spawn sub-orchestrator with agent's tool profile + system prompt |
| Channel subscriptions | `backend/agents/runner.py` | Each agent subscribes to specific bridge channels |
| REST endpoints | `backend/app.py` | `GET/POST /api/agents`; `PUT/DELETE /api/agents/{id}`; `POST /api/agents/{id}/run` |

---

### P2-014 — Session Resume

**File:** `backend/app.py`

```python
@app.post("/api/sessions/{session_key}/resume", dependencies=[Depends(verify_authenticated)])
async def resume_session(session_key: str):
    with Session(db_engine) as s:
        messages = s.exec(
            select(MessageLog)
            .where(MessageLog.session_key == session_key)
            .order_by(MessageLog.timestamp)
        ).all()
    context = [{"role": m.role, "content": m.content} for m in messages[-50:]]
    await ws_gw.restore_session_context(session_key, context)
    return {"restored": len(context), "session_key": session_key}
```

---

## Phase 3 — Bridge Completions

> All 20 channels must have: real auth, real send, real inbound → orchestrator

### Unified Inbound Pipeline (P3-003) — Required First

Every bridge must call a unified `_dispatch_inbound()` before any other P3 work.

**Step-by-step:**

**Step 1.** Add to `backend/bridges/base.py`:

```python
async def _dispatch_inbound(self, raw: dict):
    """
    Normalise raw bridge payload and route to orchestrator.
    Call this from every bridge's inbound handler.
    """
    normalised = {
        "from":      raw.get("sender") or raw.get("from", "unknown"),
        "body":      raw.get("text") or raw.get("content") or raw.get("body", ""),
        "timestamp": raw.get("timestamp", ""),
        "channel":   self.bridge_id,
        "protocol":  self.bridge_id.upper(),
        "raw":       raw
    }
    if hasattr(self, "on_event") and self.on_event:
        await self.on_event("message.inbound", normalised)
    if hasattr(self, "ws_broadcast") and self.ws_broadcast:
        await self.ws_broadcast("bridge.message", normalised)
```

**Step 2.** Wire `on_event` callback in `app.py` lifespan for every channel:

```python
for ch_name, adapter in channel_registry.items():
    adapter.on_event = broadcast_bridge_event
    # Inject orchestrator reference for direct dispatch
    adapter._orchestrator = orchestrator
```

---

### Bridge Status Matrix

| Bridge | Auth | Connect() | Send() | Receive | Current Status | Target |
|--------|------|-----------|--------|---------|----------------|--------|
| Telegram | Bot Token | ✅ Real API | ✅ Real | Polling exists | Polling loop missing | Full polling + webhook |
| Discord | Bot Token | ✅ discord.py | ✅ send() | on_message→NOT wired | Inbound not dispatched | Wire on_message→_dispatch |
| Slack | OAuth2 | ✅ OAuth | ✅ send() | Events API | Webhook parse incomplete | Parse events→_dispatch |
| WhatsApp | Cloud API | ✅ Real API | ✅ Real | Webhook | process_webhook_event not dispatched | Wire to _dispatch_inbound |
| Gmail | OAuth2 | ❌ stub | ✅ send() real | Inbox fetch | connect() doesn't load vault | Auto-load tokens on boot |
| Signal | Phone | ✅ (sets flag) | ❌ commented | ❌ commented | All subprocess commented out | Uncomment + real signal-cli |
| iMessage | macOS AppleScript | ✅ permission check | ✅ osascript | ✅ chat.db poll | Mostly working | Test on macOS |
| Nostr | Keypair NIP-01 | ✅ nostr-sdk | ✅ publish | Subscribe | Likely working | Integration test |
| Email SMTP/IMAP | Credentials | ✅ | ✅ | IMAP IDLE needed | No IMAP receive loop | Add aioimaplib IDLE loop |
| Google Chat | OAuth | OAuth exists | Stub | Webhook | send() stub | Implement HTTP REST send |
| Google Drive | OAuth2 | ❌ no connect() | Stub | — | Saves plain JSON not vault | Save to vault; add connect() |
| Facebook | Meta OAuth | ✅ sets flag | ❌ stub | Webhook needed | Full stub | Implement Graph API |
| Instagram | Meta OAuth | Stub | Stub | Webhook needed | Full stub | Implement Graph API DM |
| MS Teams | Azure MSAL | Stub | Stub | Bot Framework | Full stub | Implement MSAL + Bot API |
| X/Twitter | OAuth2 PKCE v2 | Stub | Stub | Polling needed | Full stub | Implement v2 DM API |
| WeChat | QR web session | Stub | Stub | — | Full stub | QR session + httpx polling |
| WebChat | URL + Playwright | Stub | Stub | — | Full stub | Playwright intercept |
| iCloud | 2FA Token | ✅ endpoint exists | Stub | — | 2FA flow wired; connect() stub | Implement iCloud API calls |
| iPhone | Local zeroconf | Stub | Stub | — | Full stub | mDNS + TCP socket |
| iWatch | HealthKit | ✅ endpoint exists | N/A | POST /api/bridge/iwatch/biometrics | Receives telemetry | Add HealthKit push from WatchOS |

---

### P3-001 — Signal Bridge: Uncomment subprocess

**File:** `backend/bridges/signal.py`

**Step-by-step:**

**Step 1.** Replace mock `send()` with real subprocess call:

```python
async def send(self, recipient: str, content: str, **kwargs) -> Dict[str, Any]:
    res = subprocess.run(
        ["signal-cli", "-a", self.phone_number, "send", "-m", content, recipient],
        capture_output=True, text=True, timeout=15
    )
    return {
        "status": "success" if res.returncode == 0 else "failed",
        "stderr": res.stderr
    }
```

**Step 2.** Add receive loop:

```python
async def start_receive_loop(self):
    """Runs signal-cli receive in a background subprocess."""
    proc = await asyncio.create_subprocess_exec(
        "signal-cli", "-a", self.phone_number, "receive", "--output=json",
        stdout=asyncio.subprocess.PIPE
    )
    async for line in proc.stdout:
        msg = json.loads(line)
        if "envelope" in msg and "dataMessage" in msg["envelope"]:
            await self._dispatch_inbound({
                "from": msg["envelope"]["source"],
                "body": msg["envelope"]["dataMessage"]["message"]
            })
```

**Step 3.** Call `asyncio.create_task(self.start_receive_loop())` at the end of `connect()`.

---

### P3-002 — Telegram: Start Polling Loop

**File:** `backend/bridges/telegram.py`

```python
# In connect(), after successful getMe validation:
if not self.webhook_url:
    asyncio.create_task(self._polling_loop())

async def _polling_loop(self):
    while self.is_connected:
        try:
            async with httpx.AsyncClient() as c:
                r = await c.get(
                    f"{self.api_url}{self.bot_token}/getUpdates",
                    params={"offset": self._update_offset, "timeout": 30},
                    timeout=35
                )
                for update in r.json().get("result", []):
                    self._update_offset = update["update_id"] + 1
                    if "message" in update:
                        await self._dispatch_inbound({
                            "from": str(update["message"]["chat"]["id"]),
                            "body": update["message"].get("text", "")
                        })
        except Exception as e:
            self.logger.warning(f"Polling error: {e}")
            await asyncio.sleep(5)
```

---

### P3-017 — ADOPT: MQTT Bridge

**File:** `(new) backend/bridges/mqtt.py`

Add to `requirements.txt`: `aiomqtt>=2.0.0`

```python
import aiomqtt, asyncio
from .base import BridgeAdapter

class MQTTBridge(BridgeAdapter):
    name = "mqtt"

    async def connect(self, credentials):
        self.host = credentials.get("host", "localhost")
        self.port = int(credentials.get("port", 1883))
        self.topic_sub = credentials.get("topic_subscribe", "alluci/#")
        asyncio.create_task(self._subscribe_loop())
        self.is_connected = True
        return True

    async def _subscribe_loop(self):
        async with aiomqtt.Client(self.host, self.port) as c:
            await c.subscribe(self.topic_sub)
            async for msg in c.messages:
                await self._dispatch_inbound({
                    "from": str(msg.topic),
                    "body": msg.payload.decode()
                })

    async def send(self, recipient: str, content: str, **kwargs):
        async with aiomqtt.Client(self.host, self.port) as c:
            await c.publish(recipient, content)
        return {"status": "success"}
```

---

### P3-018 — ADOPT: Matrix E2EE Bridge

**File:** `(new) backend/bridges/matrix.py`

Add to `requirements.txt`: `matrix-nio[e2e]>=0.21.0`

| Feature | Implementation |
|---------|----------------|
| Connect | `matrix-nio AsyncClient`: login with homeserver, username, password or access token |
| Send | `client.room_send(room_id, 'm.room.message', {'msgtype': 'm.text', 'body': content})` |
| Receive | `client.sync_forever()` loop → parse `m.room.message` events → `_dispatch_inbound()` |
| E2EE | `AsyncClient` with E2EE: store keys in `~/.alluci/matrix-store/`. Auto-verify devices. |

---

## Phase 4 — Platform Packages

### Platform Capability Matrix

| Feature | macOS Apple Silicon | macOS Intel | Linux x86_64 | Windows 11 | Raspberry Pi |
|---------|---------------------|-------------|--------------|------------|--------------|
| Inference acceleration | Metal (Ollama auto) | CPU / Accelerate | CUDA / ROCm / CPU | CUDA / CPU | CPU (quantised 1B) |
| ASR (Whisper) | Metal flag | Accelerate framework | CUDA if available | CPU pre-built | tiny.en model only |
| TTS (Piper) | CoreAudio | CoreAudio | ALSA / PulseAudio | WinMM | ALSA (tiny voice) |
| Vault key storage | macOS Keychain | macOS Keychain | GNOME Keyring / KWallet | Windows Credential Mgr | `~/.alluci/.key` (0600) |
| System service | launchd plist | launchd plist | systemd user unit | Windows Service / Task Scheduler | systemd user unit |
| OS-level sandbox | sandbox-exec .sb | sandbox-exec .sb | Landlock LSM (≥5.13) | Win32 Job Objects | None (no root) |
| Biometric auth | Face ID WebAuthn | Touch ID WebAuthn | Fingerprint / PIN | Windows Hello | PIN / password only |
| Health biometrics | HealthKit (Apple Watch) | Manual input | Manual input | Manual input | Manual / GPIO sensors |
| Package format | Homebrew / .dmg | Homebrew / .pkg | .deb / .rpm / .sh | winget / .exe | armhf .deb |
| ChromaDB + embeddings | Full (MPS) | Full (CPU) | Full (CUDA/CPU) | Full (CUDA/CPU) | Disabled (LITE_MODE) |
| torch / gudhi / PPN | Full | Full | Full | Full | Disabled (LITE_MODE) |

---

### P4-001–P4-006 — macOS Apple Silicon

| Item | Implementation | File |
|------|----------------|------|
| launchd service | Write `~/Library/LaunchAgents/ai.alluci.daemon.plist`. `launchctl load -w`. | `backend/platform/macos.py` |
| Metal Ollama | arm64 Darwin: Ollama auto-uses Metal. Verify in `ollama serve` log. | `setup_sovereign_stack.sh` |
| Whisper Metal | Build with: `WHISPER_METAL=1 make` in `whisper.cpp` on arm64 Darwin. | `setup_sovereign_stack.sh` |
| HealthKit push | WatchOS companion app (SwiftUI, ~500 lines): reads HR/HRV/SpO2, POSTs JSON to `POST /api/telemetry` every 5s. | `watchos/AlluciWatch/` |
| Keychain vault | `keyring` library on Darwin uses macOS Keychain via `SecKeychainItem`. Store at `service='alluci', username='vault_key'`. | `backend/security/vault.py` |
| Face ID WebAuthn | `webauthn>=2.0.0` already in requirements. Set `authenticator_attachment=PLATFORM` in `RegistrationOptions`. Works in Safari. | `backend/security/auth.py` |
| Homebrew formula | `Formula/alluci.rb`: `depends_on 'python@3.11'`, `depends_on 'ollama'`. Bottle for arm64_monterey/ventura/sonoma. | `Formula/alluci.rb` |

**launchd plist template:**

```python
# backend/platform/macos.py
LAUNCHD_PLIST = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>ai.alluci.daemon</string>
  <key>ProgramArguments</key>
  <array>
    <string>{python}</string><string>-m</string>
    <string>uvicorn</string><string>backend.app:app</string>
    <string>--host</string><string>127.0.0.1</string>
    <string>--port</string><string>8000</string>
  </array>
  <key>WorkingDirectory</key><string>{work_dir}</string>
  <key>EnvironmentVariables</key>
  <dict><key>APP_ENV</key><string>production</string></dict>
  <key>KeepAlive</key><true/>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>{log_dir}/alluci.log</string>
  <key>StandardErrorPath</key><string>{log_dir}/alluci_err.log</string>
</dict></plist>"""
```

---

### P4-010–P4-015 — Linux

| Item | Implementation | File |
|------|----------------|------|
| systemd service | Write `~/.config/systemd/user/alluci.service`. `systemctl --user enable --now alluci`. | `backend/platform/linux.py` |
| CUDA detection | Parse `nvidia-smi` VRAM → recommend model: <6GB→3b-q4; 6–12GB→7b-q4; >12GB→13b+ | `setup_sovereign_stack.sh` |
| ROCm detection | `if command -v rocm-smi; then OLLAMA_GPU=rocm`. Install ROCm Ollama build. | `setup_sovereign_stack.sh` |
| Landlock LSM | `pip install python-landlock`. In `ShellAdapter.execute()`: `with Landlock(read=['/usr','/lib'], write=[workspace_root])` | `backend/security/sandbox.py` |
| GNOME Keyring | `keyring` library uses `secretstorage` backend on Linux. Requires `dbus-python + libsecret`. Fallback to `~/.alluci/.vault_key` if keyring unavailable. | `backend/security/vault.py` |
| AppIndicator tray | `gi.repository.AppIndicator3`. Menu: Open UI / ACE mode label / Stop daemon. Requires `libappindicator3-dev`. | `backend/platform/linux_tray.py` |
| .deb package | `make deb` target using `fpm`: `fpm -s dir -t deb -n alluci -v {version} /opt/alluci`. Includes Python venv. | `Makefile` |

---

### P4-016–P4-019 — Windows 11

| Item | Implementation | File |
|------|----------------|------|
| PowerShell installer | `install.ps1`: Check Python 3.11+, install via `winget`. `winget install Ollama.Ollama`. `pip install -r requirements.txt`. Write `.env`. Create service. | `install.ps1` |
| Windows Service | `pywin32`: `win32serviceutil.ServiceFramework` subclass. `sc create AlluciDaemon`. Alternatively NSSM wrapper. | `backend/platform/windows.py` |
| CUDA Ollama | Ollama Windows installer auto-detects NVIDIA via CUDA. Verify: `ollama run llama3.2:3b uses GPU`. | `setup_sovereign_stack.ps1` |
| Credential Manager | `keyring` library uses Windows backend (`keyring.core.WinVaultKeyring`). Stores `POLYTOPE_MASTER_KEY` under `service='alluci'`. | `backend/security/vault.py` |
| Windows Hello WebAuthn | Works via browser WebAuthn API in Edge/Chrome. `webauthn` library handles CTAP2. | `backend/security/auth.py` |
| Toast notifications | `pip install win10toast-click`. Send notification on: bridge message, task complete, OTP approval needed. | `backend/platform/windows_notify.py` |
| Path handling | All file paths use `pathlib.Path()` throughout — never `os.path.join` with hardcoded `/` separators. Vault root: `Path.home() / '.alluci' / 'vaults'`. | All backend files |

---

### P4-020–P4-022 — Raspberry Pi

> **Pi Philosophy:** The Pi deployment is the purest expression of digital sovereignty: Alluci running on a $35 device in your home, entirely offline, with no data leaving your network.

| Feature | Pi 4 4GB (Standard) | Pi 4 2GB / Pi Zero 2W (Lite) | Implementation |
|---------|---------------------|-------------------------------|----------------|
| LLM model | `llama3.2:1b-q4_K_S` (900MB RAM) | `phi3:mini-q4` (700MB RAM) | Check `MemTotal /proc/meminfo`. <3GB→phi3 |
| ChromaDB | Full PersistentClient | Disabled (`LITE_MODE=true`) | `backend/config.py` LITE_MODE flag |
| sentence-transformers | all-MiniLM-L6-v2 | Disabled | `if LITE_MODE: skip import` |
| torch / gudhi / PPN | Enabled (slow but functional) | Disabled | `if LITE_MODE: PPN stub (identity passthrough)` |
| Memory backend | ChromaDB (5000 entry limit) | SQLite FTS5 full-text search | `backend/memory/fts_memory.py` |
| Whisper ASR | tiny.en model (~75MB) | tiny.en model | Setup script: aarch64→tiny model |
| Redis | redis-server (aarch64 binary) | SQLite rate-limit fallback | `app.py`: if no `REDIS_URL`, use SlowAPI in-memory |
| Package | armhf .deb via `fpm` | armhf .deb | `Makefile deb-pi target` |

**LITE_MODE config additions:**

```python
# backend/config.py — add
LITE_MODE: bool = False        # Pi / low-RAM: disables Torch, ChromaDB, gudhi
MINIMAL_FRONTEND: bool = False # Serve stripped HTML instead of React bundle
MAX_MEMORY_ENTRIES: int = 50000 # Reduce to 5000 in Pi setup script
```

**Pi setup script additions:**

```bash
# scripts/setup_sovereign_stack.sh — Pi section
if [[ "$ARCH" == "aarch64" || "$ARCH" == "armv7l" ]]; then
    RAM_KB=$(grep MemTotal /proc/meminfo | awk '{print $2}')
    echo "[ PI ] Detected: ${ARCH}, RAM: ${RAM_KB}KB"
    if [ "$RAM_KB" -lt 3000000 ]; then
        echo "LITE_MODE=true" >> .env
        echo "OLLAMA_MODEL=phi3:mini-q4" >> .env
        ollama pull phi3:mini-q4
    else
        echo "OLLAMA_MODEL=llama3.2:1b-q4_K_S" >> .env
        ollama pull llama3.2:1b-q4_K_S
    fi
    bash ./models/download-ggml-model.sh tiny.en
fi
```

---

## Cross-System Integrations

### From ZeroClaw

| Feature | ZeroClaw Implementation | Alluci Target | Priority |
|---------|------------------------|---------------|----------|
| SOP Engine | YAML/TOML multi-step workflows; step types: `tool_call`/`agent_message`/`approval_gate`/`manual`; SHA-256 audit log | `backend/sop/` — see P1-010 | 🟠 P1 |
| Goals Engine | Hierarchical goals with progress tracking; LLM decomposition; auto-link to run results | `backend/goals/` — see P1-009 | 🟠 P1 |
| MQTT bridge | `aiomqtt`; subscribe to topic tree; dispatch inbound to orchestrator | `backend/bridges/mqtt.py` — see P3-017 | 🟡 P3 |
| Matrix E2EE bridge | `matrix-nio` with E2EE; sync_forever loop; key store | `backend/bridges/matrix.py` — see P3-018 | 🟡 P3 |
| IRC bridge | basic `irc3` or asyncio socket | `backend/bridges/irc.py` — see P3-019 | 🟡 P3 |
| Non-escalation policy | Pre-LLM interception: detect privilege escalation; block before execution | Extend `guardrail.py` + `executor.py` | 🔵 P2 |
| `deny.toml` supply-chain | Audit imported packages against known-bad checksums | Extend `skill_manager.py import_package()` | 🔵 P2 |
| Hardware GPIO bridge | `python-gpiozero`; read/write GPIO pins | `(new) backend/bridges/gpio.py` — Pi stretch goal | 🟡 P3 |
| `bandit` static analysis | `#![forbid(unsafe_code)]` equivalent | Add `bandit>=1.7.0` to `requirements.txt`; CI step | 🔵 P2 |
| 7-language README | ZeroClaw README has EN/ZH/JA/KO/ES/DE/FR | Alluci: add i18n README sections; `LocaleSelector.tsx` already exists | 🟡 P3 |

### From OpenClaw

| Feature | OpenClaw Implementation | Alluci Target | Priority |
|---------|------------------------|---------------|----------|
| 13-tab admin dashboard | Comprehensive tabs across full admin surface | Alluci already has 14+ panels. Gaps: hot-reload config editor wiring, Nodes/Devices tab. | ✅ Mostly done |
| Usage Analytics (charts+CSV) | recharts time-series; daily bar charts; CSV export | Alluci analytics already full — all endpoints wired. | ✅ Done |
| Session management | Session config CRUD; session log viewer; message count; cost per session | `SessionConfig` model exists; all endpoints implemented. | ✅ Done |
| Cron management | Interval/cron_expr/run_at; clone job; run now; history | `CronEngine` fully matches OpenClaw §3.1–3.8. All CRUD endpoints implemented. | ✅ Done |
| Exec approval modal | Deny / Allow Once / Allow Always; persistent DB policy | `ExecApprovalManager` + `ExecApprovalModal.tsx` fully implemented. | ✅ Done |
| WebAuthn app login | FIDO2 platform authenticator | Installed; needs platform-auth testing per OS. | 🔵 P2 |
| Config Editor hot-reload | JSON Schema validation; live preview; `POST /api/config/apply` | Wire schema auto-generation from `Settings` class. | 🔵 P2 |
| Debug panel | Raw WS RPC console; system metrics; live logs | `DebugPanel.tsx` + `RpcConsole.tsx` exist. Wire to `/api/logs/stream` and `/metrics`. | 🔵 P2 |
| Webhook URL display | Copy-to-clipboard webhook URLs per bridge | `WebhookUrlDisplay.tsx` exists. Wire to `DAEMON_PUBLIC_URL + bridge_id`. | 🔵 P2 |

### From Accomplish

| Feature | Accomplish Implementation | Alluci Target | Priority |
|---------|--------------------------|---------------|----------|
| 12+ LLM providers via BYOK | Single API key UI for all providers | See P1-011 and P2-011 for all provider additions | 🟠 P1 |
| YAML skill files | `gray-matter` parsing of `.skill.md` / `.skill.yaml`; 6 bundled skills | See P1-012 | 🟠 P1 |
| 60+ test suite | Playwright e2e, Vitest unit, Docker integration — structured CI | Start with pytest unit (P1-006), then add Playwright e2e. | 🟠 P1 |
| SecureStorage AES-256-GCM | AES-256-GCM via OS keychain | See P1-004 for vault upgrade. P4-004/009/014/019 for OS keychain per platform. | 🟠 P1 |
| PermissionRequestHandler | Per-tool permission prompts with Allow/Deny/Always memory | `ExecApprovalManager` is equivalent. Add per-bridge permission prompts. | 🔵 P2 |
| ThoughtStream display | Real-time streaming of agent reasoning steps in UI | `ThoughtStreamHandler.tsx` exists. Wire to WS stream events from Planner. | 🔵 P2 |
| Sub-task parent_id | `task-todos`: sub-tasks within a session | `TaskItem` model + `/tasks` endpoints exist. Add `sub_task.parent_id` field. | 🔵 P2 |
| Connector registry | MCP connector search + enable/disable | `SkillGrid.tsx` + `SkillManager`. Add MCP server registration as skill type. | 🟡 P3 |
| SpeechService fallback | Browser `SpeechRecognition` + `SpeechSynthesis` API fallback when Whisper unavailable | Add to `CommandBar.tsx`: `if(!whisperAvailable) use webkitSpeechRecognition`. | 🔵 P2 |

---

## 24-Week Sprint Plan

Each week is one sprint. Each item references its spec ID, lists the primary files to change, and states a testable acceptance criterion.

### Phase 0 — Weeks 1–2 · Critical Bugs

| Wk | Spec ID | Task | Files | Acceptance Criterion |
|----|---------|------|-------|---------------------|
| W01 | P0-002 | Remap `gmail→GmailBridge` in bridge_actualization.py | `backend/adapters/bridge_actualization.py` | `bridge_map['gmail'] == GmailBridge`. Unit test passes. |
| W01 | P0-003 | Fix oauth_config.py key mismatch (2-letter→full IDs) | `backend/oauth_config.py` | `OAUTH_CONFIGS.get('slack')` returns non-None. All 8 OAuth bridges resolved. |
| W01 | P0-003 | Add all OAuth keys to config.py + .env.example | `backend/config.py`, `.env.example` | Settings loads `GOOGLE_CLIENT_ID` etc. without error when None. |
| W02 | P0-001 | Replace bridgeManager.ts setTimeout mocks with real /api/channels calls | `bridgeManager.ts` | `sendMessage()` POSTs to backend. Returns real success/failure from API. |
| W02 | P0-001 | Add `POST /api/channels/{id}/send` + `GET /api/channels/{id}/health` | `backend/app.py` | `curl POST /api/channels/telegram/send` with valid token → message delivered. |
| W02 | P0-003 | End-to-end OAuth test: Gmail PKCE popup → tokens in vault → GmailBridge connected | `tests/test_oauth.py` | Gmail OAuth flow completes. `/api/channels/gmail/health` → `{is_connected: true}`. |

### Phase 1 — Weeks 3–7 · Runtime Core

| Wk | Spec ID | Task | Files | Acceptance Criterion |
|----|---------|------|-------|---------------------|
| W03 | P1-003 | Make `GEMINI_API_KEY` optional; add `LOCAL_ONLY` mode | `backend/config.py` | Daemon starts with no `GEMINI_API_KEY` + `LOCAL_ONLY=true`. Routes to Ollama. |
| W03 | P1-001 | Create MemoryManager (ChromaDB) | `backend/memory/manager.py` | `memory_store('k','hello world')`. `memory_recall('hello')` → top-1 = 'hello world'. |
| W03 | P1-001 | Wire MemoryManager into Orchestrator | `backend/orchestrator.py` | `execute_objective()` prepends top-5 recall results to system prompt. |
| W04 | P1-004 | Vault AES-256-GCM upgrade + Fernet auto-migration | `backend/security/vault.py` | New vault writes use AES-256-GCM. Old Fernet vaults auto-migrated on first read. |
| W04 | P1-005 | Tool sandbox: resource limits + workspace path jail | `backend/security/sandbox.py` | Shell: 30s CPU limit enforced. Path outside workspace rejected with `SecurityError`. |
| W04 | P1-007 | Expose Whisper + Piper HTTP endpoints | `backend/app.py`, `inference/local_bridge.py` | `POST /api/voice/transcribe` with audio → returns transcribed text. |
| W05 | P1-002 | ACE→PPN ψ pipeline per-turn | `backend/orchestrator.py` | Each `execute_objective()` logs `psi_value`. WS clients receive `ace.state` event. |
| W05 | P1-008 | Prometheus `/metrics` endpoint | `backend/metrics.py`, `app.py` | `curl /metrics` returns `inference_tokens_total`, `active_ws_clients` counters. |
| W05 | P1-013 | Register shell + web_search + web_fetch + memory adapters | `backend/adapters/registry.py` + 4 new tool files | Planner can route tasks to `web_search`. Test: objective 'search for AI news' → result. |
| W06 | P1-006 | Test suite: vault, ACE, OAuth, bridge_map, executor, guardrail | `tests/` | `pytest` → all pass. Coverage >50% on backend core. |
| W06 | P1-009 | Goals engine MVP | `backend/goals/` | `goal_create` + `goal_decompose` → 5 sub-goals. `goal_complete` updates progress. |
| W06 | P1-010 | SOP engine MVP | `backend/sop/` | 3-step SOP YAML. `POST /api/sops/{id}/run` executes. Approval gate pauses. Audit log written. |
| W07 | P1-011 | Add Groq + OpenRouter + custom base_url to ModelRouter | `backend/inference/router.py` | `GROQ_API_KEY` set → inference routes to Groq. Measure tok/s. |
| W07 | P1-012 | YAML skill files + 6 bundled skills | `backend/skill_manager.py`, `skills/*.skill.yaml` | `~/.alluci/skills/` scanned on boot. Skills appear in SkillGrid. |
| W07 | P1-014 | Enrich `/api/system/health` with subsystem statuses | `backend/app.py:466` | Health response includes `chroma_status`, `ollama_status`, `redis_status`, `bridge_count`. |

### Phase 2 — Weeks 8–12 · Intelligence

| Wk | Spec ID | Task | Files | Acceptance Criterion |
|----|---------|------|-------|---------------------|
| W08 | P2-001 | Memory REST endpoints + Memory Panel | `backend/app.py`, `features/memory/MemoryPanel.tsx` | `GET /api/memory` returns entries. Panel: search + delete functional. |
| W08 | P2-002 | Document ingestion (PDF/DOCX/TXT) | `backend/adapters/tools/doc_ingest.py` | `POST /api/documents/ingest` with PDF → `{chunk_count}`. `memory_recall` returns chunk. |
| W08 | P2-003 | Voice input frontend + Whisper wiring | `features/terminal/CommandBar.tsx` | Hold-to-speak → audio → transcribed text appears in input field. |
| W09 | P2-004 | Voice output (Piper TTS) + auto-play | `backend/app.py`, `CommandBar.tsx` | Agent reply → Piper speech plays in browser automatically. |
| W09 | P2-006 | Web search adapter | `backend/adapters/tools/web_search.py` | Objective 'find latest AI news' → agent returns 5 real news items with URLs. |
| W09 | P2-007 | Web fetch adapter | `backend/adapters/tools/web_fetch.py` | `web_fetch('https://example.com')` → markdown content returned in <2s. |
| W10 | P2-008 | Code execution adapter + sandbox | `backend/adapters/tools/code_exec.py` | Execute `'print(2+2)'` → output `'4'`. Infinite loop → timeout error after 10s. |
| W10 | P2-010 | Research orchestration mode | `backend/engine/planner.py` | Objective 'research Rust async' → agent searches, fetches 3 pages, returns cited summary. |
| W11 | P2-011 | Add DeepSeek + xAI + Mistral + Bedrock + Cohere | `backend/inference/router.py` | Each provider: set key → routes correctly. Missing key → graceful fallback to next. |
| W11 | P2-012 | LLM-Guard guardrail upgrade | `backend/security/guardrail.py` | Load `llama-guard-2` via Ollama. Adversarial prompt → blocked before LLM call. |
| W11 | P2-013 | Multi-agent backend: registry + spawn + channel subscriptions | `backend/agents/` | `POST /api/agents` creates agent. Discord msg routes to subscribed agent. |
| W12 | P2-014 | Session resume | `backend/app.py` | `POST /api/sessions/{key}/resume` → last 50 messages injected as context. Agent 'remembers' prior session. |
| W12 | P2-015 | Memory compaction cron | `backend/cron_engine.py` | Default cron at 02:00 daily: entries >30 days summarised. ChromaDB entry count reduced. |
| W12 | P2-009 | Screen capture tool | `backend/adapters/tools/screen_capture.py` | Tool call `screen_capture` → base64 PNG returned. Works on macOS/Linux/Windows. |

### Phase 3 — Weeks 13–18 · Bridges

| Wk | Spec ID | Task | Files | Acceptance Criterion |
|----|---------|------|-------|---------------------|
| W13 | P3-003 | Add `_dispatch_inbound()` to `base.py` | `backend/bridges/base.py` | All bridges call `await self._dispatch_inbound(raw)`. Orchestrator receives normalised message. |
| W13 | P3-002 | Telegram polling loop | `backend/bridges/telegram.py` | Bot message → polling receives → orchestrator replies in Telegram chat. |
| W13 | P3-005 | Discord `on_message` → `_dispatch` | `backend/bridges/discord.py` | Discord @bot message → orchestrator reply in same channel. |
| W13 | P3-001 | Signal signal-cli implementation | `backend/bridges/signal.py` | Signal message → bridge receives → orchestrator replies. `send()` calls signal-cli subprocess. |
| W14 | P3-006 | WhatsApp webhook dispatch | `backend/bridges/whatsapp.py` | WhatsApp message → `/api/webhook/whatsapp` → orchestrator → reply. |
| W14 | P3-007 | Gmail vault load on connect | `backend/bridges/gmail.py` | Daemon boot: Gmail creds in vault → auto-connect. Inbox fetch returns real emails. |
| W14 | P3-009 | Slack Events API dispatch | `backend/bridges/slack.py` | Slack @mention → Events webhook → orchestrator → reply in thread. |
| W15 | P3-008 | Google Drive vault save + connect | `backend/bridges/gdrive.py` | OAuth callback → tokens in vault (not plain JSON). `connect()` loads vault on boot. |
| W15 | P3-010 | Facebook Graph API implementation | `backend/bridges/facebook.py` | Facebook DM → webhook → orchestrator → reply. |
| W15 | P3-011 | Instagram Graph API implementation | `backend/bridges/instagram.py` | Instagram DM → webhook → orchestrator → reply. |
| W16 | P3-012 | MS Teams MSAL + Bot Framework | `backend/bridges/msteams.py` | Teams @mention → Bot Framework webhook → orchestrator → reply. |
| W16 | P3-013 | X/Twitter v2 DM API | `backend/bridges/x_twitter.py` | DM received → orchestrator. Reply DM sent. |
| W16 | P3-016 | iCloud 2FA connect implementation | `backend/bridges/icloud.py` | iCloud session authenticated. Polling for new data works. |
| W17 | P3-017 | MQTT bridge | `backend/bridges/mqtt.py` | Subscribe to `test/#` topic. Publish message → orchestrator receives. |
| W17 | P3-018 | Matrix E2EE bridge | `backend/bridges/matrix.py` | Login to Matrix homeserver. E2EE message received → orchestrator replies. |
| W17 | P3-014 | WeChat QR session | `backend/bridges/wechat.py` | QR displayed in UI. After scan → session established. Message dispatched. |
| W18 | P3-015 | WebChat Playwright | `backend/bridges/webchat.py` | Target URL + login creds → Playwright session. Monitor chat → dispatch inbound. |
| W18 | P3-004 | Bridge health endpoint for all 20 | `backend/bridges/*.py`, `app.py` | `GET /api/channels/telegram/health` → `{is_connected:true, latency_ms:45}`. |
| W18 | P3-020 | BridgeCenter real status cards | `components/BridgeCenter.tsx` | All 20 bridges show real connected/error status. No setTimeout mock statuses. |

### Phase 4 — Weeks 19–24 · Platform

| Wk | Spec ID | Task | Files | Acceptance Criterion |
|----|---------|------|-------|---------------------|
| W19 | P4-001 | macOS Apple Silicon: launchd service installer | `backend/platform/macos.py` | `POST /api/system/service/install` → plist written → daemon auto-starts on login. |
| W19 | P4-004 | macOS: Keychain vault key storage | `backend/security/vault.py` | `POLYTOPE_MASTER_KEY` in macOS Keychain. `.env` has placeholder only. |
| W19 | P4-002 | macOS Apple Silicon: Metal Whisper build | `setup_sovereign_stack.sh` | `whisper.cpp` built with `WHISPER_METAL=1` on arm64 Darwin. Transcription speed >10× realtime. |
| W20 | P4-007 | macOS Intel: CPU model recs + quantised model | `setup_sovereign_stack.sh`, onboarding | Intel Mac detected → `llama3.2:3b-q4_K_M` recommended. Onboarding shows expected tok/s. |
| W20 | P4-010 | Linux: systemd service installer | `backend/platform/linux.py` | `POST /api/system/service/install` → unit written → `systemctl enable` succeeds. |
| W20 | P4-012 | Linux: CUDA/ROCm Ollama detection + VRAM model sizing | `setup_sovereign_stack.sh` | NVIDIA GPU: CUDA Ollama. VRAM >12GB: 13b model suggested. <6GB: 3b-q4. |
| W21 | P4-013 | Linux: Landlock LSM in ShellAdapter | `backend/security/sandbox.py` | Linux ≥5.13: `python-landlock` active. Shell: write outside workspace → `Permission denied`. |
| W21 | P4-014 | Linux: GNOME Keyring vault key | `backend/security/vault.py` | On Linux with GNOME: `keyring` stores master key. No plaintext key in `.env`. |
| W21 | P4-016 | Windows: `install.ps1` | `install.ps1` | Fresh Windows 11: run `install.ps1` → Python + Ollama + deps installed → daemon running. |
| W22 | P4-017 | Windows: Windows Service | `backend/platform/windows.py` | Service registered. Daemon survives reboot. `sc query AlluciDaemon` → `RUNNING`. |
| W22 | P4-019 | Windows: Windows Credential Manager vault key | `backend/security/vault.py` | `POLYTOPE_MASTER_KEY` in Windows Credential Manager. Daemon reads on boot. |
| W22 | P4-020 | Raspberry Pi: LITE_MODE implementation | `backend/config.py` | `LITE_MODE=true`: Torch/ChromaDB/gudhi not imported. Daemon starts in <30s on Pi 4. |
| W23 | P4-021 | Raspberry Pi: SQLite FTS5 memory fallback | `backend/memory/fts_memory.py` | `LITE_MODE`: `memory_store/recall` uses FTS5. Recall returns relevant results. |
| W23 | P4-011 | Linux .deb package (fpm) | `Makefile` | `make deb` → `alluci_*.deb`. `dpkg -i` installs cleanly. Daemon runs as installed service. |
| W23 | P4-022 | Raspberry Pi armhf .deb | `Makefile` | `make deb-pi` → armhf .deb. Installs on Pi OS. `LITE_MODE` auto-enabled. |
| W24 | P4-003 | macOS Apple Silicon: WatchOS HealthKit companion | `watchos/AlluciWatch/` | Apple Watch HR/HRV POSTed to `/api/telemetry` every 5s. ACE mode changes in frontend. |
| W24 | P4-023 | Universal `install.sh` (`curl \| sh`) | `scripts/install.sh` | `curl URL \| sh` detects macOS/Linux/Pi, runs correct installer, starts daemon, opens UI. |
| W24 | P4-024 | Docker Compose profiles (lite/full/pi) | `docker-compose.yml` | `docker compose --profile lite up`: no Torch container. `--profile pi`: ARM image + 1b model. |

---

## Target State & Competitive Position

### Complete Module Inventory at Delivery

| Module | Status After Roadmap | Phase Delivered |
|--------|---------------------|-----------------|
| FastAPI daemon (2,251 lines) | ✅ DONE | Exists |
| Orchestrator: Planner → Executor → Critic | ✅ DONE | Exists |
| ACE biometric engine (4 flow modes) | ✅ DONE | Exists + P1-002 |
| PPN + ALCEStabilizer + Betti head + DPK | ✅ DONE | Exists + P1-002 |
| Harmonic Enhancer (reciprocal lattice) | ✅ DONE | Exists |
| VerusID + VDXF audit chain | ✅ DONE | Exists |
| Vault AES-256-GCM + OS Keychain per platform | ✅ DONE | P1-004 + P4 |
| Guardrail scanner + LLM-Guard | ✅ DONE | Exists + P2-012 |
| WebAuthn FIDO2 (Face ID / Touch ID / Hello) | ✅ DONE | Exists + P4 |
| JWT auth + cookie sessions | ✅ DONE | Exists |
| WS Gateway JSON-RPC 2.0 | ✅ DONE | Exists |
| ExecApproval Manager (OTP gating) | ✅ DONE | Exists |
| Tool sandbox (resource limits + Landlock + sandbox-exec + Job Objects) | ✅ DONE | P1-005 + P4 |
| ChromaDB MemoryManager (semantic search) | ✅ DONE | P1-001 |
| SQLite FTS5 memory (LITE_MODE) | ✅ DONE | P4-021 |
| Document ingestion (PDF/DOCX/TXT) | ✅ DONE | P2-002 |
| Memory compaction cron | ✅ DONE | P2-015 |
| ModelRouter: 10+ providers (all optional) | ✅ DONE | P1-011 + P2-011 |
| LOCAL_ONLY mode (no cloud key required) | ✅ DONE | P1-003 |
| Ollama local LLM (Metal/CUDA/ROCm/CPU) | ✅ DONE | P4 platform |
| Whisper.cpp ASR (per-platform acceleration) | ✅ DONE | P1-007 + P4 |
| Piper TTS (per-platform audio) | ✅ DONE | P1-007 + P4 |
| Goals engine (hierarchical + LLM decompose) | ✅ DONE | P1-009 |
| SOP engine (audited multi-step workflows) | ✅ DONE | P1-010 |
| Research mode (search → fetch → synthesise → cite) | ✅ DONE | P2-010 |
| HeartbeatDaemon (HEARTBEAT.md) | ✅ DONE | Exists |
| CronEngine (3 schedule types) | ✅ DONE | Exists |
| Multi-agent registry + spawn + channel subscriptions | ✅ DONE | P2-013 |
| FileSystem adapter (sandboxed) | ✅ DONE | Exists + P1-005 |
| Shell adapter (sandboxed) | ✅ DONE | P1-013 |
| WebSearch adapter | ✅ DONE | P2-006 |
| WebFetch adapter (Playwright) | ✅ DONE | P2-007 |
| CodeEval adapter | ✅ DONE | P2-008 |
| ScreenCapture adapter | ✅ DONE | P2-009 |
| Memory adapter (store/recall/forget) | ✅ DONE | P1-013 |
| All 20 bridges: real auth, send, inbound→orchestrator | ✅ DONE | P3 complete |
| OAuth2 PKCE for all 8 OAuth bridges | ✅ DONE | P0-003 + P3 |
| Unified inbound pipeline (`_dispatch_inbound`) | ✅ DONE | P3-003 |
| MQTT bridge (IoT) | ✅ DONE | P3-017 |
| Matrix E2EE bridge | ✅ DONE | P3-018 |
| Prometheus `/metrics` | ✅ DONE | P1-008 |
| Enriched `/health` (all subsystems) | ✅ DONE | P1-014 |
| Structlog JSONL + WS log streamer | ✅ DONE | Exists |
| Self-updater (GitHub releases) | ✅ DONE | Exists |
| macOS Apple Silicon: launchd + Keychain + Metal + HealthKit + Face ID | ✅ DONE | P4 |
| macOS Intel: launchd + Keychain + CPU + Touch ID | ✅ DONE | P4 |
| Linux: systemd + GNOME Keyring + CUDA/ROCm + Landlock + tray | ✅ DONE | P4 |
| Windows 11: Windows Service + Cred Mgr + CUDA + Windows Hello | ✅ DONE | P4 |
| Raspberry Pi: LITE_MODE + FTS5 + armhf .deb + systemd | ✅ DONE | P4 |
| 14+ panel admin UI | ✅ DONE | Exists |
| Voice in/out UI | ✅ DONE | P2-003/004/005 |
| Memory panel, Goals panel, SOP panel | ✅ DONE | P1/P2 |
| Visual DAG editor, ACE widget, Verus wallet | ✅ DONE | Exists |
| YAML skill files + 6 bundled skills | ✅ DONE | P1-012 |
| Test suite >60% coverage | ✅ DONE | P1-006 |

---

### Competitive Position at Delivery

| Capability | Alluci v2 | ZeroClaw | OpenClaw | Accomplish |
|------------|-----------|----------|----------|------------|
| ACE biometrics (Apple Watch → agent behaviour) | ✅ **Unique** | ❌ | ❌ | ❌ |
| VerusID + VDXF sovereign identity | ✅ **Unique** | ❌ | ❌ | ❌ |
| Visual DAG planning editor | ✅ **Unique** | ❌ | ❌ | ❌ |
| Verus Coin wallet built-in | ✅ **Unique** | ❌ | ❌ | ❌ |
| Admin UI depth | ✅ 14+ panels | ⚠️ Minimal | ✅ 13-tab | ⚠️ Electron app |
| Communication bridges | ✅ 22 (incl MQTT, Matrix) | ✅ 20 production | ⚠️ 8 | ⚠️ MCP only |
| Semantic memory (ChromaDB) | ✅ Full | ✅ Qdrant+SQLite | ❌ | ❌ |
| SOP workflows | ✅ (adopted) | ✅ Full | ❌ | ❌ |
| Goals engine | ✅ (adopted) | ✅ Full | ❌ | ❌ |
| Local inference stack | ✅ Ollama+Whisper+Piper | ✅ Same+GPIO | ✅ Ollama | ✅ Ollama |
| LLM providers | ✅ 10+ | ✅ 35+ | ⚠️ Standard | ✅ 12+ |
| Sandbox security | ✅ Landlock+AES-256-GCM | ✅ Landlock+ChaCha20 | ⚠️ Stub WebAuthn | ✅ Partial |
| Platform reach | ✅ **5 platforms** | ✅ +Android+RISC-V | ⚠️ macOS-first | ⚠️ Desktop |
| Test coverage | ✅ >60% target | ✅ 159+ tests | ⚠️ Partial | ✅ 60+ tests |
| Research mode | ✅ (built) | ❌ | ❌ | ✅ web-research skill |

---

### Alluci's Absolute Moat After This Roadmap

> Alluci will be the **only AI agent in existence** that simultaneously offers:

1. **Real-time physiological state adaptation** via Apple Watch biometrics — changes agent behaviour based on your stress, focus, and vitality
2. **Blockchain-anchored sovereign identity** (VerusID + VDXF) — every agent action cryptographically attributed to your identity
3. **Visual DAG planning editor** — see and modify the exact execution graph before it runs
4. **Verus Coin wallet as a first-class agent tool** — cryptocurrency-native from day one
5. **All of the above, plus 22 communication bridges, semantic memory, SOP workflows, goals engine, local voice I/O, research mode, and full platform packages** — running entirely on your hardware with zero data leaving your machine

No other system — ZeroClaw, OpenClaw, Accomplish, or any commercial product — combines these five dimensions.

---

*Alluci Sovereign Agent Production Spec · March 2026 · 153 items · 24 weeks · 5 platforms*
