#!/usr/bin/env bash
set -euo pipefail

echo "--- Frontend Quality Gate ---"
npm ci
npm run lint
npm run typecheck
npm run test

echo "--- Backend Quality Gate ---"
if [[ -d .venv ]]; then
    source .venv/bin/activate
fi

python3 -m pip install -r requirements.txt -r requirements-dev.txt
python3 -m pytest backend/tests -q
