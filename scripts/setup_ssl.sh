#!/bin/bash
# Alluci Sovereign Agent — Local SSL Setup Utility
# Resolves: "Your connection to this site is not secure" warnings on localhost.

set -e

echo "🔒 Starting Local SSL Setup..."

# 1. Detect OS and install mkcert
if [[ "$OSTYPE" == "darwin"* ]]; then
    if ! command -v brew &> /dev/null; then
        echo "❌ Homebrew not found. Please install Homebrew first: https://brew.sh"
        exit 1
    fi
    echo "📦 Installing mkcert via Homebrew..."
    brew install mkcert
    brew install NSS # For Firefox support
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "📦 Installing mkcert via apt..."
    sudo apt update && sudo apt install -y mkcert libnss3-tools
else
    echo "❌ Unsupported OS for this script. Please install mkcert manually."
    exit 1
fi

# 2. Setup Local CA Trust (Requires Sudo)
echo "🔑 Requesting permission to trust the local Certificate Authority..."
mkcert -install

# 3. Generate Certificates
mkdir -p certs
echo "🎫 Generating Certificates for localhost, 127.0.0.1, and ::1..."
mkcert -key-file certs/privkey.pem -cert-file certs/fullchain.pem localhost 127.0.0.1 ::1

echo ""
echo "✅ SUCCESS: Local SSL Setup Complete."
echo "--------------------------------------------------------"
echo "1. Restart your dev services (Vite and Uvicorn)."
echo "2. Access the agent at: https://localhost:3000"
echo "3. Or via NGINX at: https://localhost:8443"
echo "--------------------------------------------------------"
