# AGENT.md — Read This First, Every Session
# Last updated: 2026-03-15

## What This Codebase Is
Alluci Sovereign Agent: self-hosted AI executive assistant with biometric-aware autonomy, 
AES-256-GCM encrypted local vault, and 21 messaging bridge adapters.

## Stack Assignment — NEVER Cross These
- **Python** (`backend/`): FastAPI HTTP API, all 21 bridge adapters, vault, auth, AI inference, 
  ChromaDB memory, ACE engine, cron engine, DAG executor. 23,945 lines. DO NOT REWRITE.
- **TypeScript** (`features/`, `components/`, `hooks/`, `store/`): React UI only. 14,098 lines. DO NOT REWRITE.
- **Swift** (`watchos/`): Apple Watch + iOS companion — HealthKit only.
- **Shell** (`scripts/`): Platform installers for macOS, Linux, Windows, Raspberry Pi.

## Golden Rules — Breaking These Creates Production Incidents
1. Never `.unwrap()` or swallow exceptions silently — every error must be handled or propagated
2. Never store credentials in the database — always call `vault.store_connection_secret(bridge_id, account_id, creds)`
3. Every new API endpoint needs: handler function, `app.include_router()`, `RateLimiter` dependency
4. Every new OAuth bridge needs: Redis PKCE state via `oauth_store`, background token refresh loop
5. All WebSocket endpoints must call `authenticate_ws(websocket, token)` before `handle_connection()`
6. Swift session tokens go in Keychain (`SecItemAdd`), not `UserDefaults`
7. Never duplicate router registration in `backend/app.py` — each router appears exactly once
8. All `@router.post()` auth endpoints need `dependencies=[Depends(RateLimiter(times=N, minutes=1))]`

## Current Correct LLM Model IDs
- **Google (flash):** `gemini-2.0-flash`
- **Google (pro):** `gemini-2.5-pro-preview-05-06`  ← still wrong in code, needs fix
- **Anthropic (strong):** `claude-3-7-sonnet-20250219`
- **Anthropic (light):** `claude-3-5-haiku-20241022`
- **OpenAI (strong):** `gpt-4o`
- **OpenAI (light):** `gpt-4o-mini`
- **Local:** `llama3.2` via Ollama at `OLLAMA_URL`

## Where Everything Lives
| What | Where |
|------|-------|
| HTTP route handlers | `backend/routers/{name}.py` |
| Bridge adapters | `backend/bridges/{name}.py` |
| Vault operations | `backend/security/vault.py` → `VaultManager` |
| Auth logic | `backend/security/auth.py` + `backend/routers/auth.py` |
| OAuth PKCE state | `backend/security/oauth_store.py` → `OAuthStateStore` |
| WebAuthn challenges | `backend/security/webauthn_store.py` → `WebAuthnChallengeStore` |
| OTel tracing | `backend/tracing_config.py` |
| Structured logging | `backend/logging_config.py` → `get_logger(__name__)` |
| All Pydantic models | `backend/models.py` |
| Zustand global state | `store/useStore.ts` |
| React features | `features/{name}/` |
| Watch Swift app | `watchos/AlluciWatch/` |
| iOS companion app | `watchos/AlluciCompanion/` (to be created) |

## Verification Commands (Run After Every Change)
```bash
python -m pytest backend/tests/ -x -q                    # all Python tests pass
python -m mypy backend/ --ignore-missing-imports          # no Python type errors  
npx tsc --noEmit                                           # no TypeScript errors
npx vitest run                                             # frontend unit tests pass
curl -s http://localhost:8000/health | python3 -m json.tool  # backend running
```

## What Is Still Missing — Update This List As Items Complete
- [ ] WebAuthn assertion/login endpoints (`backend/routers/auth.py`)
- [ ] Background token refresh loops (all OAuth bridges in `backend/bridges/`)
- [ ] Frontend state hydration on page refresh (`store/useStore.ts`)
- [ ] Android PWA (`vite.config.ts` + `public/manifest.json`)
- [ ] Xcode project file (`watchos/AlluciWatch/AlluciWatch.xcodeproj`)
- [ ] Fix watchOS URL: `/api/bridge/iwatch/biometrics` → `/api/channels/iwatch/biometrics`
- [ ] `WKExtendedRuntimeSession` for background HRV collection
- [ ] iOS companion app (`watchos/AlluciCompanion/`)
- [ ] Fix `gemini_pro` model ID in `backend/inference/router.py` line 67
- [ ] nginx HTTPS/TLS server block + Let's Encrypt
- [ ] CI: add `xcodebuild test` job for Swift
