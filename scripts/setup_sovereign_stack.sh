#!/bin/bash

# Alluci Sovereign Stack Setup Script (Cross-Platform)
# Installs Ollama, Whisper.cpp, and Piper TTS for Mac, Linux, and RPi

echo "--- Initializing Alluci Sovereign Architecture Setup ---"

# Detect Architecture
OS="$(uname -s)"
ARCH="$(uname -m)"
echo "[ INFO ]: Detected Platform: $OS ($ARCH)"

# 1. Ollama
if ! command -v ollama &> /dev/null; then
    echo "[ INFO ]: Ollama not found. Installing..."
    if [[ "$OS" == "Darwin" ]]; then
        brew install --cask ollama
    elif [[ "$OS" == "Linux" ]]; then
        curl -fsSL https://ollama.com/install.sh | sh
    fi
else
    echo "[ OK ]: Ollama already installed."
fi

# 2. Whisper.cpp
WHISPER_DIR="$HOME/whisper.cpp"
if [ ! -d "$WHISPER_DIR" ]; then
    echo "[ INFO ]: Cloning and building Whisper.cpp..."
    git clone https://github.com/ggerganov/whisper.cpp.git "$WHISPER_DIR"
    cd "$WHISPER_DIR"
    
    if [[ "$OS" == "Darwin" ]]; then
        echo "[ INFO ]: macOS detected. Enabling Metal GPU inference for Whisper..."
        WHISPER_METAL=1 make
    elif [[ "$OS" == "Linux" ]]; then
        # Check for CUDA
        if command -v nvidia-smi &> /dev/null; then
            echo "[ INFO ]: CUDA detected. Enabling GPU offload..."
            GGML_CUDA=1 make
        elif command -v rocminfo &> /dev/null; then
            echo "[ INFO ]: ROCm detected. Enabling AMD GPU offload..."
            GGML_HIPBLAS=1 make
        else
            make
        fi
    fi
    
    # Download models based on ARCH
    if [[ "$ARCH" == "aarch64" || "$ARCH" == "arm"* ]]; then
        if [[ "$OS" == "Darwin" ]]; then
            echo "[ INFO ]: Apple Silicon detected. Transcribing with 'small' model (Metal optimized)..."
            bash ./models/download-ggml-model.sh small.en
        else
            echo "[ INFO ]: ARM Linux (RPi) detected. Downloading 'tiny' model..."
            bash ./models/download-ggml-model.sh tiny.en
        fi
    elif [[ "$ARCH" == "x86_64" && "$OS" == "Darwin" ]]; then
        echo "[ INFO ]: Intel Mac detected. Downloading 'tiny' model for CPU efficiency..."
        bash ./models/download-ggml-model.sh tiny.en
    else
        echo "[ INFO ]: Standard x86_64 (Linux/Windows) detected. Downloading 'small' model..."
        bash ./models/download-ggml-model.sh small.en
    fi
    cd -
else
    echo "[ OK ]: Whisper.cpp found at $WHISPER_DIR."
fi

# 3. Piper TTS
if ! command -v piper &> /dev/null; then
    echo "[ INFO ]: Downloading Piper TTS..."
    PIPER_VERSION="1.2.0"
    if [[ "$OS" == "Darwin" ]]; then
        curl -L "https://github.com/rhasspy/piper/releases/download/v${PIPER_VERSION}/piper_macos_x64.tar.gz" -o piper.tar.gz
    elif [[ "$ARCH" == "aarch64" || "$ARCH" == "arm"* ]]; then
        curl -L "https://github.com/rhasspy/piper/releases/download/v${PIPER_VERSION}/piper_linux_aarch64.tar.gz" -o piper.tar.gz
    else
        curl -L "https://github.com/rhasspy/piper/releases/download/v${PIPER_VERSION}/piper_linux_x86_64.tar.gz" -o piper.tar.gz
    fi
    
    mkdir -p piper_tmp && tar -xzf piper.tar.gz -C piper_tmp
    sudo mv piper_tmp/piper/piper /usr/local/bin/
    rm -rf piper_tmp piper.tar.gz
else
    echo "[ OK ]: Piper already installed."
fi

echo "--- Setup Complete ---"
echo "[ ACTION ]: Ensure Ollama is running ('ollama serve') and has models pulled."
echo "[ ACTION ]: Suggested: 'ollama pull mistral' (Desktop) or 'ollama pull phi3:mini' (RPi)."
