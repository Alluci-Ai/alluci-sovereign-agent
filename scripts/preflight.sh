#!/bin/bash
# scripts/preflight.sh - PRODUCTION READINESS VERIFIER

set -e

echo "--- [ ALLUCI_PREFLIGHT ] Validation Started ---"

# 1. Check Node.js & Dependencies
if ! command -v node >/dev/null 2>&1; then
    echo "[ FAIL ] Node.js not found."
    exit 1
fi
echo "[ OK ] Node.js: $(node -v)"

if [ ! -d "node_modules" ]; then
    echo "[ FAIL ] node_modules missing. Run 'npm install'."
    exit 1
fi
echo "[ OK ] Frontend Dependencies installed."

# 2. Check Python & Virtual Env
if [ ! -d ".venv" ]; then
    echo "[ FAIL ] .venv missing. Run 'make init'."
    exit 1
fi

PYTHON=.venv/bin/python3
if ! $PYTHON -c "import pytest_asyncio" >/dev/null 2>&1; then
    echo "[ FAIL ] pytest-asyncio missing in .venv. Run 'pip install -r requirements-dev.txt'."
    exit 1
fi
echo "[ OK ] Backend Dependencies (Dev) installed."

# 3. Check for .env
if [ ! -f ".env" ]; then
    echo "[ FAIL ] .env file missing."
    exit 1
fi
echo "[ OK ] Environment configuration (.env) exists."

# 4. Toolchain Version Check
VITE_VER=$(npx vite --version 2>/dev/null | head -n 1)
echo "[ OK ] Vite Toolchain: $VITE_VER"

echo "--- [ ALLUCI_PREFLIGHT ] PASS ---"
