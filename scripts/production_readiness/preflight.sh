#!/usr/bin/env bash
set -euo pipefail

command -v node >/dev/null || { echo "node missing"; exit 1; }
command -v npm >/dev/null || { echo "npm missing"; exit 1; }
command -v python3 >/dev/null || { echo "python3 missing"; exit 1; }
if command -v pip >/dev/null; then
    PIP_CMD="pip"
elif command -v pip3 >/dev/null; then
    PIP_CMD="pip3"
else
    echo "pip missing"; exit 1
fi

echo "Node: $(node -v)"
echo "NPM:  $(npm -v)"
echo "Python: $(python3 --version)"
echo "Pip:    $($PIP_CMD --version)"

echo "Checking npm registry reachability..."
# Some environments might block npm ping, but it's a good test for standard registries
npm ping --timeout=5000 >/dev/null || echo "Warning: npm registry ping failed, but proceeding..."

echo "Checking lockfiles..."
[[ -f package-lock.json ]] || { echo "package-lock.json missing"; exit 1; }
[[ -f requirements.txt ]] || { echo "requirements.txt missing"; exit 1; }

echo "preflight: OK"
