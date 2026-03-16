# Production Deployment Guide

## Prerequisites

| Component | Version | Purpose |
|-----------|---------|---------|
| Docker | ≥24.0 | Container runtime |
| Docker Compose | ≥2.20 | Multi-service orchestration |
| Python | ≥3.11 | Backend runtime |
| Node.js | ≥20 LTS | Frontend build |
| PostgreSQL | ≥16 | Production database |
| Redis | ≥7 | Rate limiting, WebAuthn challenge store |

---

## Quick Start (Docker Compose)

```bash
# 1. Clone and configure
cp .env.example .env
# Edit .env with your production values

# 2. Generate secure keys
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# → Set POLYTOPE_MASTER_KEY

python -c "import secrets; print(secrets.token_urlsafe(64))"
# → Set JWT_SECRET_KEY

# 3. Set production environment
echo "APP_ENV=production" >> .env
echo "DB_PASSWORD=$(openssl rand -base64 32)" >> .env
echo "PROD_DATABASE_URL=postgresql+asyncpg://alluci:\${DB_PASSWORD}@db:5432/polytope" >> .env

# 4. Launch
docker compose up -d --build

# 5. Run database migrations
docker compose exec backend alembic upgrade head

# 6. Verify
curl http://localhost:8000/health
curl http://localhost:8000/ready
```

---

## Bare-Metal Deployment

### 1. Database Setup

```bash
# PostgreSQL
createdb polytope
psql polytope -c "CREATE USER alluci WITH PASSWORD 'your-secure-password';"
psql polytope -c "GRANT ALL PRIVILEGES ON DATABASE polytope TO alluci;"
```

### 2. Redis Setup

```bash
# Install
brew install redis  # macOS
# or
apt install redis-server  # Ubuntu/Debian

# Verify
redis-cli ping
```

### 3. Backend Deployment

```bash
pip install -r requirements.txt
# Optional TDA deps:
# pip install -r requirements-tda.txt

# Run migrations
cd backend && alembic upgrade head

# Start with uvicorn
uvicorn backend.app:app --host 0.0.0.0 --port 8000 --workers 4
```

### 4. Frontend Build

```bash
npm ci
npm run build
# Serve dist/ with nginx or any static file server
```

---

## Environment Variable Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `POLYTOPE_MASTER_KEY` | **Yes** | — | Fernet-compatible AES-256 key for vault encryption |
| `JWT_SECRET_KEY` | **Yes** | — | JWT signing key (must differ from master key) |
| `APP_ENV` | No | `development` | `development`, `production`, or `local_sovereign` |
| `GEMINI_API_KEY` | No | — | Google Gemini API key for cloud inference |
| `PROD_DATABASE_URL` | **In prod** | — | PostgreSQL connection string |
| `REDIS_URL` | No | — | Redis connection string for rate limiting |
| `WEBAUTHN_RP_ID` | No | `localhost` | WebAuthn Relying Party ID (your domain) |
| `WEBAUTHN_ORIGIN` | No | `http://localhost:5173` | WebAuthn expected origin |
| `ALLOWED_ORIGINS` | No | `["http://localhost:3000", ...]` | CORS allowed origins (JSON array) |

---

## Key Rotation

```bash
# Generate a new master key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Call the rotation API
curl -X POST http://localhost:8000/vault/rotate \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"new_key": "NEW_FERNET_KEY"}'

# Update .env with the new key
# Restart the backend
```

---

## Health Monitoring

| Endpoint | Auth | Purpose |
|----------|------|---------|
| `GET /health` | None | Kubernetes liveness probe |
| `GET /ready` | None | Kubernetes readiness probe (checks DB, Redis) |
| `GET /metrics` | None | Prometheus-compatible metrics |
| `GET /api/system/health` | JWT | Detailed internal health dashboard |

---

## Local Sovereign Stack

For fully offline operation, install Ollama, Whisper.cpp, and Piper:

```bash
bash scripts/setup_sovereign_stack.sh
```

---

## Windows 11 Deployment

Alluci supports native Windows 11 integration including service management and Credential Manager storage.

### 1. Installation
Run the provided PowerShell script as **Administrator**:
```powershell
powershell.exe -ExecutionPolicy Bypass -File install.ps1
```

### 2. Service Management
The backend can be managed as a Windows Service (`AlluciSovereignAgent`):
```powershell
# Start service
Start-Service AlluciSovereignAgent

# Check status
Get-Service AlluciSovereignAgent
```

### 3. MSIX Packaging
For Windows Store or enterprise deployment, use the GitHub Actions workflow to generate an MSIX package. This bundles the backend and frontend into a single installable unit.
