#!/bin/bash
# Preflight dependency connectivity diagnostic

echo "--- 1. Checking NPM Registry Connectivity ---"
if curl -s -o /dev/null -w "%{http_code}" https://registry.npmjs.org/vitest > /tmp/npm_check; then
  NPM_CODE=$(cat /tmp/npm_check)
  if [[ "$NPM_CODE" == "200" ]]; then
    echo "✅ NPM Registry Reachable (200 OK)"
  else
    echo "❌ NPM Registry check failed with status: $NPM_CODE"
    exit 1
  fi
else
  echo "❌ NPM Registry UNREACHABLE"
  exit 1
fi

echo "--- 2. Checking PyPI Connectivity ---"
if curl -s -o /dev/null -w "%{http_code}" https://pypi.org/simple/fastapi/ > /tmp/pypi_check; then
  PYPI_CODE=$(cat /tmp/pypi_check)
  if [[ "$PYPI_CODE" == "200" ]]; then
    echo "✅ PyPI Reachable (200 OK)"
  else
    echo "❌ PyPI check failed with status: $PYPI_CODE"
    exit 1
  fi
else
  echo "❌ PyPI UNREACHABLE"
  exit 1
fi

echo "✅ Preflight completed successfully."
exit 0
