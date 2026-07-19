# Alluci Sovereign Agent beta v1.1.1 — Production Deployment Guide

## 1. The Air-Gap Boundary
End users need to understand the lifecycle of the setup for absolute data sovereignty.
Step 1 (`install.sh` or `install.ps1`) requires a **high-bandwidth internet connection** to pull the multi-gigabyte models and embedding `.safetensors` from HuggingFace into your local `mirror_cache/`. 

Once the terminal outputs `[ INFO ]: Setup Complete.`, the setup is finalized. You can now **physically sever the ethernet cable or disable Wi-Fi**, and the Sovereign Agent will run indefinitely offline without ever pinging an external server again.

## 2. Secrets & Root of Trust
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

## 3. Docker Deployment
Use the included `docker-compose.yml` for containerized environments.
```bash
docker-compose up -d
```
The containers include mandatory healthchecks and resource limits.

## 4. Native macOS/Linux Deployment
1. **Initialize**: `make init`
2. **Start**: `make start`
3. **Verify**: `make doctor`

## 5. Reverse Proxy (NGINX)
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

## 6. Maintenance
- **Key Rotation**: Use the `VaultManager.rotate_keys()` API via CLI (coming soon).
- **Backups**: Periodically backup the `.polytope/vaults/` directory, `db.sqlite3` (Control Plane), and the `polytope_data.kuzu/` directory (Cognitive Plane).
