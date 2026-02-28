#!/bin/bash

# Alluci Sovereign Stack Setup Script (macOS)
# Installs Ollama, Whisper.cpp, and Piper TTS

echo "--- Initializing Sovereign Architecture Setup ---"

# 1. Ollama
if ! command -v ollama &> /dev/null; then
    echo "[ INFO ]: Ollama not found. Installing via Homebrew..."
    brew install --cask ollama
else
    echo "[ OK ]: Ollama already installed."
fi

# 2. Whisper.cpp (GGML)
WHISPER_DIR="$HOME/whisper.cpp"
if [ ! -d "$WHISPER_DIR" ]; then
    echo "[ INFO ]: Cloning Whisper.cpp..."
    git clone https://github.com/ggerganov/whisper.cpp.git "$WHISPER_DIR"
    cd "$WHISPER_DIR"
    make
    # Download small model
    bash ./models/download-ggml-model.sh small.en
    cd -
else
    echo "[ OK ]: Whisper.cpp found at $WHISPER_DIR."
fi

# 3. Piper TTS
if ! command -v piper &> /dev/null; then
    echo "[ INFO ]: Downloading Piper TTS..."
    # macOS binary URL (example, verify latest)
    PIPER_VERSION="1.2.0"
    curl -L "https://github.com/rhasspy/piper/releases/download/v${PIPER_VERSION}/piper_macos_x64.tar.gz" -o piper.tar.gz
    tar -xzf piper.tar.gz
    sudo mv piper/piper /usr/local/bin/
    rm -rf piper piper.tar.gz
else
    echo "[ OK ]: Piper already installed."
fi

echo "--- Setup Complete ---"
echo "Please ensure Ollama is running ('ollama serve') and has 'mistral' pulled ('ollama pull mistral')."
