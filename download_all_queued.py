#!/usr/bin/env python3
import os
import sys

try:
    from huggingface_hub import snapshot_download
except ImportError:
    print("Error: huggingface_hub is not installed. Run 'pip install huggingface_hub'")
    sys.exit(1)

models = [
    "Alluci/alluci-polytope-gemma-4-31b-it-bf16",
    "Alluci/alluci-polytope-gemma-4-31b-it-4bit",
    "Alluci/alluci-polytope-gemma-4-26b-a4b-it-4bit",
    "Alluci/alluci-polytope-gemma-4-26b-a4b-it-8bit"
]

for repo_id in models:
    local_dir = f"mirror_cache/{repo_id.split('/')[-1]}"
    print(f"\n==============================================")
    print(f"Starting download of {repo_id}...")
    print(f"Destination: {os.path.abspath(local_dir)}")
    print(f"==============================================\n")
    
    os.makedirs(local_dir, exist_ok=True)
    
    try:
        snapshot_download(
            repo_id=repo_id,
            local_dir=local_dir
        )
        print(f"\n✅ Successfully downloaded {repo_id}")
    except Exception as e:
        print(f"\n❌ Error during download of {repo_id}: {e}")
