# Alluci Sovereign Agent beta v1.1.1 — Production Deployment Guide

## 1. Secrets & Root of Trust
The Alluci Sovereign Agent uses a **Sovereign Vault** architecture. 
Only the `POLYTOPE_MASTER_KEY` is required in the environment.

### Production Environment Variables
Set these via your OS, Docker Secrets, or CI/CD Environment:
```bash
POLYTOPE_MASTER_KEY="your-secure-base64-key"
JWT_SECRET_KEY="secure-random-string"
CSRF_SECRET_KEY="secure-random-string"
DB_PASSWORD="your-postgres-password"
APP_ENV="production"
```

## 2. Docker Deployment
Use the included `docker-compose.yml` for containerized environments.
```bash
docker-compose up -d
```
The containers include mandatory healthchecks and resource limits.

## 3. Native macOS/Linux Deployment
1. **Initialize**: `make init`
2. **Start**: `make start`
3. **Verify**: `make doctor`

## 4. Reverse Proxy (NGINX)
It is highly recommended to run Alluci behind NGINX for TLS termination and rate limiting.
Example NGINX fragment:
```nginx
location / {
    proxy_pass http://localhost:3000;
}
location /api {
    proxy_pass http://localhost:8000;
}
```

## 5. Maintenance
- **Key Rotation**: Use the `VaultManager.rotate_keys()` API via CLI (coming soon).
- **Backups**: Periodically backup the `.polytope/vaults/` directory and `polytope_data.db`.
