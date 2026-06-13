#!/usr/bin/env bash
set -euo pipefail

echo "--- Frontend Quality Gate ---"
npm install --legacy-peer-deps
npm run lint
npm run typecheck
npm run test

echo "--- Backend Quality Gate ---"
if [[ -d .venv ]]; then
    source .venv/bin/activate
fi

python3 -m pip install -r requirements.txt -r requirements-dev.txt

echo "Running production-readiness check..."
# Ensure no mocks are left in core logic
grep -r "SIMULATION" backend/engine | grep -v "logger" && { echo "ERROR: Simulated logic found in backend/engine"; exit 1; } || true

echo "Running tests with coverage (Threshold: 76%)..."
python3 -m pytest backend/tests --cov=backend --cov-fail-under=76 -q

echo "SUCCESS: Quality Gate Passed."
