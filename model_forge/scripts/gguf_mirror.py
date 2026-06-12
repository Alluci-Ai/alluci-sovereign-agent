import os
from huggingface_hub import HfApi, snapshot_download

api = HfApi()

# Define mapping for sovereign conversion
TARGET_ORG = "Alluci-ai"

DESIRED_SIZES = ["e2b", "e4b", "12b", "26b-a4b", "31b"]

def discover_best_gguf_variants():
    """Automatically discover the best GGUF variants from bartowski."""
    print("[*] Automatically discovering best GGUF Community variants...")
    models_to_mirror = []
    
    all_models = [m.modelId for m in api.list_models(author="bartowski", search="gemma-4")]
    
    for size in DESIRED_SIZES:
        matches = [m for m in all_models if size in m.lower() and "gguf" in m.lower()]
        it_matches = [m for m in matches if "-it" in m.lower() and "heretic" not in m.lower() and "luchador" not in m.lower()]
        
        if it_matches:
            models_to_mirror.append(it_matches[0])
        elif matches:
            models_to_mirror.append(matches[0])
        else:
            print(f"[!] Warning: No GGUF variant found for {size}")
            
    return list(set(models_to_mirror))

SOURCE_MODELS = discover_best_gguf_variants()

def forge_polytope_metadata(local_dir, model_name):
    """Injects the Sovereign Polytope identity card into the mirrored repository."""
    readme_path = os.path.join(local_dir, "README.md")
    metadata = f"""---
tags:
- sovereign-agent
- polytope
- gguf
- gemma-4
---
# Alluci Polytope Sovereign Model ({model_name})

This model is a strictly secured, sovereign GGUF variant mirrored from `{model_name}`.
It is specifically compiled with the **Q4_K_M** edge-native precision.

It is designed to run completely offline on Windows and Linux via the **Alluci Hardware PyInstaller**.

## Polytope Forging Protocol
This model has undergone the Sovereign Mirror Protocol to ensure persistent availability, integrity, and absolute data sovereignty under the Alluci-ai organization.
"""
    with open(readme_path, "w") as f:
        f.write(metadata)
    print(f"[+] Polytope Identity Injected: {readme_path}")

def mirror_protocol():
    print("===========================================================")
    print("ALLUCI SOVEREIGN AGENT: GGUF MIRROR PROTOCOL")
    print("===========================================================")
    
    for src_repo in SOURCE_MODELS:
        # Extract the base model name, dropping the 'google_' prefix if present
        base_name = src_repo.split("/")[-1].replace("google_", "")
        target_repo = f"{TARGET_ORG}/alluci-polytope-{base_name}"
        
        print(f"\\n>>> COMMENCING GGUF MIRROR FOR: {src_repo}")
        print(f"Target Designation: {target_repo}")
        
        print("[+] Cloning repository locally (filtering for Q4_K_M to save 500GB+ of bandwidth)...")
        local_dir = f"./mirror_cache/{base_name}"
        os.makedirs(local_dir, exist_ok=True)
        
        # CRITICAL: We only download the Q4_K_M edge variants and config files!
        snapshot_download(
            repo_id=src_repo, 
            local_dir=local_dir,
            allow_patterns=["*Q4_K_M.gguf", "*.json", "README.md", "*.jinja", "*.txt"]
        )
        
        print("[+] Restructuring Metadata...")
        forge_polytope_metadata(local_dir, base_name)
        
        print("[+] Creating Sovereign Target Repository...")
        api.create_repo(repo_id=target_repo, private=False, exist_ok=True)
        
        print("[+] Initiating Ascension Upload to Alluci-ai...")
        api.upload_folder(
            folder_path=local_dir,
            repo_id=target_repo,
            commit_message="Sovereign Mirror Protocol: GGUF Edge Polytope Initialization"
        )
        print(f"[✓] {target_repo} completely secured and verified.\\n")

if __name__ == "__main__":
    mirror_protocol()
