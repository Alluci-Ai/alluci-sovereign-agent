# Alluci Sovereign Agent — Production Readiness Checklist

This checklist must be completed and signed off before any production release.

## 1. Quality & Testing
- [ ] `make quality` passes in a clean environment.
- [ ] 0 critical or high vulnerabilities in `security-scan`.
- [ ] All unit and integration tests pass (100% success rate).
- [ ] Type checks (backend & frontend) pass with no errors.

## 2. Environment & Configuration
- [ ] Production secrets (JWT, CSRF, Master Key) are rotated and distinct.
- [ ] Database migrations are up-to-date and verified (`alembic check`).
- [ ] `APP_ENV` is set to `production`.
- [ ] Rate limiting is active and tested.

## 3. Infrastructure & Deployment
- [ ] Kubernetes manifests are verified.
- [ ] Health and Readiness probes are correctly configured.
- [ ] Docker images are signed and SBOM is generated.
- [ ] Rollback strategy is verified in staging.

## 4. Observability & Operations
- [ ] SLOs are defined and monitoring is active.
- [ ] Alert rules are configured for 5xx and high latency.
- [ ] Backup and restore drill passed within the last 30 days.
- [ ] On-call runbooks for bridge outages and vault recovery are available.

## 5. Security & Compliance
- [ ] VDXF integrity anchoring is enabled and verified.
- [ ] CSP and other security headers are active and verified.
- [ ] No private keys or secrets are committed to the repository.

---
**Sign-off:**
*   Developer: ____________________
*   Security Lead: ____________________
*   Operations: ____________________
*   Date: ____________________
