#!/usr/bin/env bash
# bootstrap_frontend.sh — Deterministic Frontend Environment Setup
set -euo pipefail

echo "[ BOOTSTRAP ] Initializing frontend environment..."

# 1. Clean node_modules if requested (optional, standard npm ci is usually enough)
# if [ -d "node_modules" ]; then
#   echo "[ BOOTSTRAP ] Removing node_modules..."
#   rm -rf node_modules
# fi

# 2. Run npm ci for deterministic install
if [ -f "package-lock.json" ]; then
  echo "[ BOOTSTRAP ] Running npm ci..."
  npm ci
else
  echo "[ BOOTSTRAP ] package-lock.json not found. Falling back to npm install..."
  npm install
fi

echo "[ BOOTSTRAP ] Frontend environment successfully initialized."
