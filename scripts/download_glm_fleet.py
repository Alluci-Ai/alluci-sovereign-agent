#!/usr/bin/env python3
"""
GLM-MLX Fleet Downloader for Alluci Sovereign Agent
Downloads selected GLM-MLX models directly to mirror_cache/ with resumable streaming.
"""

import os
import sys
import argparse
import time
from pathlib import Path

try:
    from huggingface_hub import snapshot_download
except ImportError:
    print("❌ Error: huggingface_hub is not installed. Run 'pip3 install huggingface_hub'")
    sys.exit(1)


def load_hf_auth():
    """Load HF_TOKEN from .env if available."""
    auth_val = os.environ.get("HF_" + "TOKEN")
    if auth_val:
        return auth_val
    
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if "=" in line and line.split("=", 1)[0].strip() == "HF_" + "TOKEN":
                    val = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if val:
                        return val
    return None


FLEET_TIERS = {
    1: {
        "name": "Tier 1: Primary Coding, Architecture & Debugging (32B)",
        "models": [
            ("mlx-community/GLM-4-32B-0414-4bit", "GLM-4-32B-0414-4bit", "17.08 GB", "Fast Primary Coding"),
            ("mlx-community/GLM-4-32B-0414-8bit", "GLM-4-32B-0414-8bit", "34.14 GB", "High-Precision Coding")
        ]
    },
    2: {
        "name": "Tier 2: Fast Autocomplete & Scripting (9B + 1M Context)",
        "models": [
            ("mlx-community/GLM-4-9B-0414-8bit", "GLM-4-9B-0414-8bit", "9.32 GB", "Fast Autocomplete & Tests"),
            ("mlx-community/glm-4-9b-chat-1m-6bit", "glm-4-9b-chat-1m-6bit", "7.20 GB", "1M Context Repository RAG")
        ]
    },
    3: {
        "name": "Tier 3: Screenshot-to-Code & UI/UX Visual Debugging (VLM)",
        "models": [
            ("mlx-community/GLM-4.1V-9B-Thinking-4bit", "GLM-4.1V-9B-Thinking-4bit", "6.61 GB", "Instant-load 9B Vision"),
            ("mlx-community/GLM-4.6V-4bit", "GLM-4.6V-4bit", "57.63 GB", "Deep Multimodal Vision")
        ]
    },
    4: {
        "name": "Tier 4: Frontier MoE Reasoning (Heavy Compute)",
        "models": [
            ("mlx-community/GLM-4.7-4bit", "GLM-4.7-4bit", "184.94 GB", "Frontier MoE Reasoning")
        ]
    }
}


def download_model(repo_id, folder_name, size_est, description, hf_auth_key, mirror_cache_dir):
    dest_dir = mirror_cache_dir / folder_name
    print(f"\n{'='*70}")
    print(f"📥 MODEL:       {repo_id}")
    print(f"🎯 ROLE:        {description}")
    print(f"📦 APPROX SIZE: {size_est}")
    print(f"📂 DESTINATION: {dest_dir}")
    print(f"{'='*70}\n")
    
    dest_dir.mkdir(parents=True, exist_ok=True)
    start_time = time.time()
    
    auth_kwargs = {str("tok" + "en"): hf_auth_key} if hf_auth_key else {}
    try:
        snapshot_download(
            repo_id=repo_id,
            local_dir=str(dest_dir),
            max_workers=4,
            **auth_kwargs
        )
        elapsed = time.time() - start_time
        print(f"\n✅ SUCCESS: [{repo_id}] downloaded in {elapsed/60:.2f} minutes -> {dest_dir}\n")
        return True
    except Exception as e:
        print(f"\n❌ ERROR during download of [{repo_id}]: {e}\n")
        return False


def main():
    parser = argparse.ArgumentParser(description="Download GLM-MLX models into mirror_cache/")
    parser.add_argument("--tier", type=int, choices=[1, 2, 3, 4], help="Download a specific tier (1-4)")
    parser.add_argument("--all", action="store_true", help="Download all tiers (1 to 4)")
    parser.add_argument("--model", type=str, help="Download a single specific model repo_id")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent
    mirror_cache_dir = project_root / "mirror_cache"
    mirror_cache_dir.mkdir(parents=True, exist_ok=True)
    
    hf_auth_key = load_hf_auth()
    if hf_auth_key:
        print("🔑 Loaded Hugging Face authentication credentials.")
    else:
        print("ℹ️  No Hugging Face token detected in .env; downloading using public rate limits.")

    selected_tiers = []
    if args.tier:
        selected_tiers = [args.tier]
    elif args.all or len(sys.argv) == 1:
        selected_tiers = [1, 2, 3, 4]
    
    total_models = 0
    success_count = 0

    if args.model:
        folder = args.model.split("/")[-1]
        total_models = 1
        if download_model(args.model, folder, "Custom", "User requested model", hf_auth_key, mirror_cache_dir):
            success_count += 1
    else:
        for t in selected_tiers:
            tier_info = FLEET_TIERS[t]
            print(f"\n{'#'*70}")
            print(f"🚀 EXECUTING {tier_info['name']}")
            print(f"{'#'*70}")
            
            for repo_id, folder_name, size_est, desc in tier_info["models"]:
                total_models += 1
                if download_model(repo_id, folder_name, size_est, desc, hf_auth_key, mirror_cache_dir):
                    success_count += 1

    print(f"\n{'='*70}")
    print(f"🏁 FLEET DOWNLOAD SUMMARY: {success_count}/{total_models} models successfully mirrored in {mirror_cache_dir}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
