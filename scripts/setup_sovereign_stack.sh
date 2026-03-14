#!/usr/bin/env bash
# scripts/setup_sovereign_stack.sh
# Installs local sovereign inference stack: Ollama, Whisper.cpp, Piper TTS
set -euo pipefail

echo "═══════════════════════════════════════════════════════"
echo "  Alluci Sovereign Stack Setup"
echo "═══════════════════════════════════════════════════════"

OS=$(uname -s)
ARCH=$(uname -m)

# ── 1. Ollama ──────────────────────────────────────────────
echo "[1/4] Installing Ollama..."
if command -v ollama &>/dev/null; then
    echo "  Ollama already installed: $(ollama --version)"
else
    if [[ "$OS" == "Darwin" ]]; then
        if command -v brew &>/dev/null; then
            brew install ollama
        else
            curl -fsSL https://ollama.ai/install.sh | sh
        fi
    else
        curl -fsSL https://ollama.ai/install.sh | sh
    fi
fi

echo "[2/4] Pulling Llama 3.2 model (default sovereign model)..."
ollama pull llama3.2

# ── 2. Whisper.cpp ─────────────────────────────────────────
echo "[3/4] Setting up Whisper.cpp for local ASR..."
if [[ ! -d "$HOME/.polytope/whisper.cpp" ]]; then
    git clone https://github.com/ggerganov/whisper.cpp "$HOME/.polytope/whisper.cpp"
    cd "$HOME/.polytope/whisper.cpp"
    if [[ "$ARCH" == "arm64" ]] && [[ "$OS" == "Darwin" ]]; then
        make -j$(sysctl -n hw.physicalcpu) WHISPER_METAL=1
    else
        make -j$(nproc 2>/dev/null || echo 4)
    fi
    bash ./models/download-ggml-model.sh base.en
    cd -
else
    echo "  Whisper.cpp already installed at ~/.polytope/whisper.cpp"
fi

# ── 3. Piper TTS ───────────────────────────────────────────
echo "[4/4] Setting up Piper TTS..."
PIPER_DIR="$HOME/.polytope/piper"
mkdir -p "$PIPER_DIR"

if [[ "$OS" == "Darwin" ]]; then
    if [[ "$ARCH" == "arm64" ]]; then
        PIPER_URL="https://github.com/rhasspy/piper/releases/latest/download/piper_macos_aarch64.tar.gz"
    else
        PIPER_URL="https://github.com/rhasspy/piper/releases/latest/download/piper_macos_x64.tar.gz"
    fi
elif [[ "$OS" == "Linux" ]]; then
    PIPER_URL="https://github.com/rhasspy/piper/releases/latest/download/piper_linux_x86_64.tar.gz"
fi

if [[ ! -f "$PIPER_DIR/piper" ]]; then
    curl -L "$PIPER_URL" | tar xz -C "$PIPER_DIR" --strip-components=1
    curl -L "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx" \
         -o "$PIPER_DIR/en_US-amy-medium.onnx"
    curl -L "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx.json" \
         -o "$PIPER_DIR/en_US-amy-medium.onnx.json"
else
    echo "  Piper already installed at ~/.polytope/piper"
fi
# ── 4. Native Security Kernels ─────────────────────────────
echo "[5/5] Compiling Native Security Kernels (DPK)..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
make -C "$SCRIPT_DIR/../backend/security"

# ── Summary ────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════"
echo "  Setup complete! Add these to your .env:"
echo ""
echo "  OLLAMA_URL=http://localhost:11434"
echo "  WHISPER_CPP_PATH=$HOME/.polytope/whisper.cpp/main"
echo "  PIPER_PATH=$HOME/.polytope/piper/piper"
echo "  PIPER_MODEL=$HOME/.polytope/piper/en_US-amy-medium.onnx"
echo "═══════════════════════════════════════════════════════"
