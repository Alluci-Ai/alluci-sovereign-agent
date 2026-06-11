#!/bin/bash
# Enforce strict 80% coverage on critical security components

echo "Running targeted test coverage on security critical paths..."

pytest \
    --cov=backend.security.proxy \
    --cov=backend.security.proxy_stub \
    --cov=backend.security.guardrail \
    --cov=backend.inference.router \
    --cov-fail-under=80 \
    backend/tests/test_proxy_extended.py \
    backend/tests/test_proxy_stub.py \
    backend/tests/test_guardrail.py \
    backend/tests/test_model_router.py \
    backend/tests/test_psi_routing.py \
    backend/tests/test_topological_routing.py

if [ $? -eq 0 ]; then
    echo "✅ Critical paths passed the 80% test coverage requirement."
    exit 0
else
    echo "❌ Critical paths failed to meet the 80% coverage requirement."
    exit 1
fi
