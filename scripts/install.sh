#!/bin/bash

# Alluci Sovereign Agent - Universal Installer
# Targets: macOS (Intel/M1), Linux (x86/ARM/RPi)

set -e

echo "--- Alluci Sovereign Agent Installer ---"

# Detect OS and Arch
OS="$(uname -s)"
ARCH="$(uname -m)"
echo "[ INFO ]: Platform: $OS ($ARCH)"

# 0. Self-Update Check
echo "[ INFO ]: Checking for installer updates..."
if command -v git &> /dev/null && [ -d .git ]; then
    git fetch --quiet
    LOCAL=$(git rev-parse @)
    REMOTE=$(git rev-parse @{u})
    if [ "$LOCAL" != "$REMOTE" ]; then
        echo "[ WARN ]: Installer is out of date. Please 'git pull' and re-run."
    fi
fi

# 1. Prerequisite Checks
if [[ "$OS" == "Darwin" ]]; then
    if ! command -v brew &> /dev/null; then
        echo "[ WARN ]: Homebrew not found. Please install Homebrew first."
        exit 1
    fi
elif [[ "$OS" == "Linux" ]]; then
    if ! command -v apt-get &> /dev/null; then
        echo "[ WARN ]: This installer currently supports Debian-based systems (apt)."
    fi
fi

# 2. Local Inference Stack (Ollama, Whisper, Piper)
echo "[ INFO ]: Setting up local inference stack..."
if [ -f scripts/setup_sovereign_stack.sh ]; then
    bash scripts/setup_sovereign_stack.sh
else
    echo "[ WARN ]: setup_sovereign_stack.sh not found. Skipping local LLM setup."
fi

# 3. Environment Setup
echo "[ INFO ]: Initializing environment..."
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "[ OK ]: Created .env from example."
    else
        echo "LITE_MODE=false" > .env
        echo "POLYTOPE_MASTER_KEY=sovereign-development-key" >> .env
    fi
fi

# RAM Check and LITE_MODE auto-enable
if [[ "$OS" == "Linux" ]]; then
    TOTAL_RAM=$(free -m | awk '/^Mem:/{print $2}')
    if [ "$TOTAL_RAM" -lt 3000 ]; then
        echo "[ INFO ]: Low RAM detected ($TOTAL_RAM MB). Enabling LITE_MODE."
        sed -i 's/LITE_MODE=false/LITE_MODE=true/' .env
    fi
fi

# 4. Service Installation
echo "[ INFO ]: Installing background service..."
WORKING_DIR=$(pwd)
if [[ "$OS" == "Darwin" ]]; then
    PLIST_PATH="$HOME/Library/LaunchAgents/com.polytope.agent.plist"
    if [ -f service_templates/com.polytope.agent.plist ]; then
        cp service_templates/com.polytope.agent.plist "$PLIST_PATH"
        sed -i '' "s|{{WORKING_DIR}}|$WORKING_DIR|g" "$PLIST_PATH"
        launchctl unload "$PLIST_PATH" 2>/dev/null || true
        launchctl load "$PLIST_PATH"
        echo "[ OK ]: Service loaded via launchd."
    fi
elif [[ "$OS" == "Linux" ]]; then
    USER_SERVICE_DIR="$HOME/.config/systemd/user"
    mkdir -p "$USER_SERVICE_DIR"
    if [ -f service_templates/polytope.service ]; then
        cp service_templates/polytope.service "$USER_SERVICE_DIR/alluci.service"
        sed -i "s|{{WORKING_DIR}}|$WORKING_DIR|g" "$USER_SERVICE_DIR/alluci.service"
        systemctl --user daemon-reload
        systemctl --user enable alluci
        systemctl --user start alluci
        echo "[ OK ]: Service enabled and started via systemd."
    fi
fi

# 5. Success Verification
echo "[ INFO ]: Verifying installation..."
sleep 2
if curl -s http://localhost:8000/health > /dev/null; then
    echo "[ OK ]: Backend Manifold is ONLINE."
else
    echo "[ WARN ]: Backend not responding yet. It may still be booting. Check backend.log."
fi

echo "--- Installation Complete ---"
echo "[ ACTION ]: Open http://localhost:3000 to access the UI."
