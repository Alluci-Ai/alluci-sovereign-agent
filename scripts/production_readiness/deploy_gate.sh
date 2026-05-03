#!/usr/bin/env bash
set -euo pipefail

echo "--- Validating Deployment Manifests ---"

if grep -n "PIN_THIS_DIGEST" docker-compose.yml >/dev/null; then
  echo "Found placeholder digest(s) in docker-compose.yml. Please pin to immutable SHA256 digests."
  exit 1
fi

# Verify core services exist in the compose file
for svc in db redis backend frontend; do
  grep -n "^\s*${svc}:" docker-compose.yml >/dev/null || { echo "missing service definition in docker-compose.yml: ${svc}"; exit 1; }
done

echo "deploy gate: OK"
