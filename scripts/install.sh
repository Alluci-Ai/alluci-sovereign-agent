#!/bin/bash
set -e

echo "============================================================"
echo "    Alluci Sovereign Agent: Native Bare-Metal Installer     "
echo "============================================================"

if [[ $(uname -m) != "arm64" ]]; then
    echo "ERROR: Alluci Sovereign Agent requires Apple Silicon (M1/M2/M3) for Native MLX hardware acceleration."
    exit 1
fi

echo "[*] Checking dependencies..."
if ! command -v brew &> /dev/null; then
    echo "ERROR: Homebrew not found. Please install Homebrew."
    exit 1
fi

echo "[*] Installing required system libraries..."
brew install python@3.11 node postgresql@15 redis

echo "[*] Setting up Python virtual environment..."
python3.11 -m venv .venv
source .venv/bin/activate

echo "[*] Installing Python backend dependencies..."
# Use pip to install the requirements, pulling in mlx for Apple Silicon
pip install -r requirements.txt
pip install mlx mlx-lm

echo "[*] Installing Frontend Node dependencies..."
npm install

echo "[*] Running Database Migrations..."
# Start postgresql/redis locally if not running
brew services start postgresql@15 || true
brew services start redis || true

sleep 2
# Initialize the polytope database
alembic upgrade head || echo "Alembic setup pending..."

echo "============================================================"
echo " Installation Complete. "
echo " Run 'make start' to launch the Native Sovereign Execution."
echo "============================================================"
