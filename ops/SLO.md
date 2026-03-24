# Alluci Sovereign Agent — Service Level Objectives (SLO)

This document defines the reliability and performance targets for the Alluci Sovereign Agent.

## 1. Core API Availability
*   **Target**: 99.9% monthly availability for all standard API endpoints.
*   **Measurement**: Proportion of all non-client-error response codes (excluding 4xx) that are NOT 5xx.
*   **Critical path**: Authentication, Vault secret retrieval, Objective management.

## 2. API Latency (p95)
*   **Target**: < 400ms for p95 latency on standard non-inference API calls.
*   **Measurement**: Response time as measured by Prometheus metrics at the ingress.
*   **Inclusions**: `GET /api/v1/objectives`, `POST /api/v1/auth/login`.
*   **Exclusions**: Long-running inference tasks (LLM generation).

## 3. Task Execution Success Rate
*   **Target**: > 99% task execution success rate for deterministic tasks.
*   **Measurement**: Ratio of `COMPLETED` tasks vs `FAILED` tasks where the failure was internal-to-engine.
*   **Critical path**: Exec Approval, Engine/Adapter interface.

## 4. Model Response Reliability
*   **Target**: < 5% failure rate for model routing (fallback rate).
*   **Measurement**: Proportion of requests that require a fallback to a secondary model due to primary model error or timeout.

## 5. Deployment Health
*   **Target**: 100% success rate for CI/CD pipeline deployments.
*   **Rollback condition**: Any failure of post-deploy synthetic monitors should trigger an automatic rollback within 5 minutes.
