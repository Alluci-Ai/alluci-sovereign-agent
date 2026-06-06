#!/usr/bin/env python3
"""
download_gemma31b.py
Download the official Google Gemma-4 31B model weights (raw PyTorch) into the project's vault.
This script uses huggingface_hub to fetch the snapshot without requiring git-lfs manually.
"""
import os
from huggingface_hub import snapshot_download

# Destination directory within the repo
raw_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../alluci_vault/raw_family/31b-dense"))
os.makedirs(raw_dir, exist_ok=True)

# Model identifier on HuggingFace (official Google repo)
model_id = "google/gemma-4-31b-it"
print(f"[Download] Pulling {model_id} into {raw_dir} ...")
# snapshot_download will download all files, respecting git-lfs files automatically.
# Use cache_dir to keep within repo
snapshot_download(repo_id=model_id, local_dir=raw_dir, revision="main", allow_patterns=["*.bin", "*.safetensors", "*.json"], ignore_patterns=["*.pt"])
print("[Download] Completed.")
