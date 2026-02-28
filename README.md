<div align="center">
<img width="1200" height="475" alt="GHBanner" src="https://github.com/user-attachments/assets/0aa67016-6eaf-458a-adb2-6e31a0763ed6" />
</div>

# Alluci Sovereign Agent

A multi-modal autonomous AI agent featuring real-time voice interaction via Gemini Live API, DAG-based task execution, an affective computing engine, a heartbeat daemon, and a novel "Polytope" reasoning framework with manifold integrity checks.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Frontend (React/Vite)             │
│  ┌─────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │ App.tsx  │  │ GeminiService│  │  AlluciCore   │   │
│  └────┬─────┘  └──────┬───────┘  └──────────────┘   │
│       │               │                              │
│       └───────┬───────┘                              │
└───────────────┼──────────────────────────────────────┘
                │ REST API / WebSocket
┌───────────────┼──────────────────────────────────────┐
│               ▼       Backend (FastAPI)               │
│  ┌──────────────────────────────────────────────┐    │
│  │             Orchestrator                      │    │
│  │  ┌────────┐  ┌──────────┐  ┌───────┐        │    │
│  │  │Planner │→ │ Executor │→ │Critic │→ Loop  │    │
│  │  └────────┘  └──────────┘  └───────┘        │    │
│  └──────────────────────────────────────────────┘    │
│  ┌───────────┐ ┌─────────┐ ┌────────┐ ┌──────────┐ │
│  │  Security │ │Inference│ │Bridges │ │ Heartbeat│ │
│  │Vault|Auth │ │Router   │ │Email   │ │  Daemon  │ │
│  │DPK|Verus  │ │PPN      │ │Slack   │ │          │ │
│  └───────────┘ └─────────┘ └────────┘ └──────────┘ │
└──────────────────────────────────────────────────────┘
```

## Prerequisites

- **Node.js** ≥ 18 (frontend)
- **Python** ≥ 3.11 (backend)
- **Docker** (optional, for containerized deployment)

## Quick Start

### 1. Clone & Configure

```bash
cp .env.example .env
# Edit .env with your keys (see .env.example for documentation)
```

### 2. Frontend

```bash
npm install
npm run dev        # → http://localhost:3000
```

### 3. Backend

```bash
pip install -r requirements.txt
python -m uvicorn backend.app:app --reload   # → http://localhost:8000
```

### 4. Docker (Production)

```bash
docker compose up --build   # Starts both services
```

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/health` | No | Liveness probe |
| `GET` | `/ready` | No | Readiness probe |
| `POST` | `/auth/login` | No | Get JWT token |
| `GET` | `/status` | Yes | System status |
| `POST` | `/objective/execute` | Yes | Execute autonomous objective |
| `POST` | `/telemetry` | Yes | Ingest biometric telemetry |
| `GET/POST/PUT/DELETE` | `/tasks/*` | Yes | Task management |
| `GET/PUT` | `/soul/manifest` | Yes | Identity configuration |
| `POST` | `/soul/preview` | Yes | Preview personality changes |
| `GET/POST/DELETE` | `/skills/*` | Yes | Cognitive module management |
| `POST` | `/api/gemini/proxy` | Yes | Server-side Gemini API proxy |

## Environment Variables

See [`.env.example`](.env.example) for the full list. Key variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `POLYTOPE_MASTER_KEY` | ✅ | Fernet key for vault encryption |
| `JWT_SECRET_KEY` | ✅ | Separate key for JWT signing |
| `GEMINI_API_KEY` | ✅ | Google Gemini API key |
| `OPENAI_API_KEY` | ❌ | Failover inference provider |
| `ANTHROPIC_API_KEY` | ❌ | Failover inference provider |

## Testing

```bash
# Run backend tests
pip install pytest pytest-asyncio pytest-cov
python -m pytest backend/tests/ -v --tb=short

# With coverage
python -m pytest backend/tests/ -v --cov=backend --cov-report=term-missing
```

## Security

- All API keys are managed server-side; the frontend never stores secrets
- JWT tokens use a dedicated signing key (separate from the vault master key)
- Rate limiting protects all endpoints (configurable via `RATE_LIMIT_PER_MINUTE`)
- Input sanitization blocks prompt injection attempts
- Vault files are encrypted (Fernet) with strict file permissions (0o600)
- Execution manifests are signed with Ed25519 (when VerusID is configured)
- DPK manifold integrity checks block invalid topology states

## Contributing

Contributions are welcome! Please see [`CONTRIBUTING.md`](CONTRIBUTING.md) for guidelines on how to get started.

## License

Alluci Sovereign Agent is released under the [MIT License](LICENSE).
