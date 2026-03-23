# Security Operations Guide

## Secret Management

The Alluci Sovereign Agent uses a tiered secret retrieval strategy to ensure maximum security and sovereignty.

### Secret Priority Chain
1. **Environment Variables**: Highest priority. Overrides everything.
2. **OS Keychain (keyring)**: Recommended for local sovereign deployments. Uses the system's native secure storage (macOS Keychain, GNOME Keyring, Windows Credential Manager).
3. **Defaults**: Lowest priority.

### Configuration
- `SECRETS_PROVIDER`: Set to `keyring` (default) to use the OS keychain.
- `KEYRING_SERVICE`: The name of the service in the keychain (default: `alluci-sovereign`).

### Purge Incident Response (v6.3)
Committed TLS private material (`certs/privkey.pem`) was identified and purged from the repository.
**Action Required**:
1. All instances must rotate their TLS certificates immediately.
2. Ensure `certs/` and `*.pem` are ignored via `.gitignore` (implemented).
3. Do not commit `.env` or keychain export files.

## Certificate Rotation
To rotate certificates in a production environment:
1. Generate new keys locally or via Let's Encrypt.
2. Mount the new `certs/` directory into the NGINX container.
3. Reload NGINX: `docker exec alluci-nginx nginx -s reload`.
