#!/usr/bin/env bash
# bootstrap_backend.sh — Deterministic Backend Environment Setup
set -euo pipefail

echo "[ BOOTSTRAP ] Initializing backend environment..."

# 1. Clean old virtual environment if it exists
if [ -d ".venv" ]; then
  echo "[ BOOTSTRAP ] Removing existing .venv..."
  rm -rf .venv
fi

# 2. Create virtual environment
echo "[ BOOTSTRAP ] Creating new .venv..."
if command -v python3.12 >/dev/null 2>&1; then
  python3.12 -m venv .venv
else
  python3 -m venv .venv
fi

# 3. Upgrade pip and install requirements
echo "[ BOOTSTRAP ] Installing dependencies from requirements-dev.txt..."
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements-dev.txt

echo "[ BOOTSTRAP ] Backend environment successfully initialized."
