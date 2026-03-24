# Alluci Sovereign Agent — Standard Operations Runbook

This document contains standardized procedures for common incidents and operational tasks.

## 1. Bridge Outages (Telegram, Discord, Slack)
*   **Symptoms**: Telegram/Discord messages are not being received or sent. Logs show 401 Unauthorized or 404.
*   **Resolution**: 
    1. Check API token validity in the bridge provider's portal.
    2. Rotate the connection secret using the Vault: `make rotate_keys` (if master key compromised) or manually update via Vault UI/API.
    3. Restart the specific bridge instance.

## 2. Redis Cache Connection Loss
*   **Symptoms**: `RedisConnectionLost` alert triggered. Rate limiting is degraded.
*   **Resolution**: 
    1. Check Redis pod/service health: `kubectl get pods -l app=redis`.
    2. Check `REDIS_URL` in `.env` or secrets.
    3. If Redis is unrecoverable, the application will fallback to in-memory caching.

## 3. Vault Integrity Failure
*   **Symptoms**: `VaultIntegrityFailure` alert triggered. `ACCESS DENIED` in logs.
*   **Resolution**:
    1. **WARNING**: This indicates possible unauthorized file tampering.
    2. Audit file system logs for unauthorized access to `~/.polytope/vaults`.
    3. Restore vault from the latest known-good backup.
    4. Immediately rotate the `POLYTOPE_MASTER_KEY` using `scripts/rotate_keys.py`.

## 4. Database Failover / Recovery
*   **Symptoms**: 5xx errors on all DB-backed routes.
*   **Resolution**:
    1. Verify DB connectivity via `pg_isready` (if Postgres).
    2. Check `DATABASE_URL` connectivity.
    3. Restore from nightly snapshot if the data is corrupted.

## 5. Key Rotation
*   **Procedure**:
    1. Generate a new 64-character master key.
    2. Run `scripts/rotate_keys.py <new_key>`.
    3. Update the production `.env` and restart the daemon.
    4. Verify JWT signing still works by logging in.

## 6. Rollback Procedure
*   **Manual Rollback**:
    ```bash
    kubectl rollout undo deployment/alluci-backend
    ```
*   **Verification**: Check `/api/v1/health` on the previous version.
