#!/usr/bin/env bash
# High-Fidelity VLM Compiler Script for Alluci Sovereign Agent
# This script pulls the Google Gemma 4 Dense 31B weights, compiles them
# into an MLX-VLM native tensor graph, and pushes them to Alluci-ai.

# Requires: pip install mlx-vlm huggingface_hub

set -e

# Replace with the token provided by the user
HF_TOKEN="${HF_TOKEN:-your_hf_token_here}"

echo "[Phase A] Authenticating with Hugging Face..."
huggingface-cli login --token "$HF_TOKEN" --add-to-git-credential

# Target repositories
# Note: In production 2026, replace with the exact Google repo if different
SOURCE_REPO="google/gemma-4-31b-it"
TARGET_REPO="Alluci-ai/alluci-gemma-4-31b-vlm-4bit"
LOCAL_DIR="./models/alluci-gemma-4-31b-vlm-4bit"

mkdir -p "$LOCAL_DIR"

echo "[Phase A] Initiating MLX-VLM Unified Compilation for $SOURCE_REPO..."
echo "This will download ~62GB of base weights. This may take several hours."

# The mlx_vlm.convert tool natively pulls the weights, isolates the SigLIP2 vision encoder,
# and packs it alongside the K-eq-V attention blocks into a quantized 4-bit safetensor directory.
python3 -m mlx_vlm.convert \
    --hf-path "$SOURCE_REPO" \
    --mlx-path "$LOCAL_DIR" \
    -q --q-bits 4

echo "[Phase A] Compilation Complete. Uploading Unified Tensor Graph to $TARGET_REPO..."

# Upload the finalized VLM directory to the Alluci-ai organization
huggingface-cli upload \
    "$TARGET_REPO" \
    "$LOCAL_DIR" \
    . \
    --repo-type model

echo "[Phase A] Success. The local model router can now be pointed to $TARGET_REPO."
