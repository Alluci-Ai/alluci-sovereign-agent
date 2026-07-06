#!/usr/bin/env python3
import os
import sys

try:
    from huggingface_hub import snapshot_download
except ImportError:
    print("Error: huggingface_hub is not installed. Run 'pip install huggingface_hub'")
    sys.exit(1)

repo_id = "Alluci/alluci-polytope-gemma-4-31b-it-8bit"
# Define the local directory based on the repo name to match mirror_cache structure
local_dir = f"mirror_cache/{repo_id.split('/')[-1]}"

print(f"Starting download of {repo_id}...")
print(f"Destination: {os.path.abspath(local_dir)}\n")

# Ensure the destination directory exists
os.makedirs(local_dir, exist_ok=True)

try:
    snapshot_download(
        repo_id=repo_id,
        local_dir=local_dir
    )
    print(f"\n✅ Successfully downloaded {repo_id} to {local_dir}")
except Exception as e:
    print(f"\n❌ Error during download: {e}")
