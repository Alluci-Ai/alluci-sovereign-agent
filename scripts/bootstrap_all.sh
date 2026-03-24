#!/usr/bin/env bash
# bootstrap_all.sh — Global Deterministic Setup
set -euo pipefail

# 1. Project root check
echo "[ BOOTSTRAP ] Starting Alluci Sovereign Agent Global Bootstrap..."

# 2. Call backend setup
if [ -f "scripts/bootstrap_backend.sh" ]; then
  chmod +x scripts/bootstrap_backend.sh
  ./scripts/bootstrap_backend.sh
else
  echo "[ FAILED ] scripts/bootstrap_backend.sh not found."
  exit 1
fi

# 3. Call frontend setup
if [ -f "scripts/bootstrap_frontend.sh" ]; then
  chmod +x scripts/bootstrap_frontend.sh
  ./scripts/bootstrap_frontend.sh
else
  echo "[ FAILED ] scripts/bootstrap_frontend.sh not found."
  exit 1
fi

# 4. Verify system configuration
echo "[ BOOTSTRAP ] Checking system configuration..."
if [ ! -f ".env" ]; then
  echo "[ INFO ] .env file not found. Copying from .env.example..."
  cp .env.example .env
fi

echo -e "\n[ BOOTSTRAP ] FINISHED: System is ready for 'make quality' and development."
