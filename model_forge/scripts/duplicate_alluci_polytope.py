#!/usr/bin/env python3
import os
import requests
from huggingface_hub import HfApi, login

# ==========================================
# Alluci Sovereign Polytope Duplication Script
# ==========================================
# This script maps the entire Gemma 4 MLX-VLM family (5 sizes x 3 quantizations)
# and performs a server-side duplication to the Alluci-ai organization.

HF_TOKEN = os.environ.get("HF_TOKEN", "your_hf_token_here")
ORG = "Alluci-ai"

# Define the 5 model sizes with their exact upstream casing
SIZES = ["e2b", "e4b", "12B", "26b-a4b", "31b"]
QUANTIZATIONS = ["4bit", "8bit", "bf16"]

models_to_clone = []

# Dynamically build the 15 exact mappings
for size in SIZES:
    for quant in QUANTIZATIONS:
        # The live collection drops the '-it' flag for the source models
        source_repo = f"mlx-community/gemma-4-{size}-{quant}"
        # You requested the target names to perfectly standardize with the '-it' flag
        target_repo = f"{ORG}/alluci-polytope-gemma-4-{size}-it-{quant}"
        models_to_clone.append({"source": source_repo, "target": target_repo})

def duplicate_model_server_side(source: str, target: str, token: str):
    """
    Attempts to trigger a 0-byte server-side duplication using Hugging Face's API.
    This replicates the 'Duplicate Model' button on the HF website.
    """
    print(f"[*] Attempting to duplicate {source} -> {target}")
    
    # The internal API endpoint used by the HF web interface for model cloning
    url = f"https://huggingface.co/api/models/{source}/duplicate"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Hugging Face API recently changed the expected key from 'toRepo' to 'repository'
    payload = {
        "repository": target,
        "private": False # Set to True if you want the models hidden
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 200 or response.status_code == 201:
            print(f"    [SUCCESS] Successfully cloned into {target}")
        else:
            print(f"    [FAILED] HTTP {response.status_code}: {response.text}")
    except Exception as e:
        print(f"    [CRITICAL] Network error: {e}")

if __name__ == "__main__":
    print("==========================================================")
    print("Initiating Alluci Polytope Mass Duplication Protocol")
    print(f"Target Organization: {ORG}")
    print(f"Total Models to Clone: {len(models_to_clone)}")
    print("==========================================================\n")
    
    # Ensure local huggingface_hub is authenticated just in case
    try:
        login(token=HF_TOKEN, add_to_git_credential=True)
    except Exception:
        pass

    for model in models_to_clone:
        duplicate_model_server_side(model["source"], model["target"], HF_TOKEN)
        
    print("\n==========================================================")
    print("Duplication Protocol Complete.")
    print("==========================================================")
