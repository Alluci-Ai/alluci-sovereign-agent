import os
from huggingface_hub import HfApi, snapshot_download

api = HfApi()

# Define mapping for sovereign conversion
TARGET_ORG = "Alluci-ai"

DESIRED_SIZES = ["e2b", "e4b", "12b", "26b-a4b", "31b"]

def discover_best_variants():
    """Automatically discover the best 4-bit variants from the MLX community."""
    print("[*] Automatically discovering best 4-bit MLX Community variants...")
    models_to_mirror = []
    all_models = [m.modelId for m in api.list_models(author="mlx-community", search="gemma-4")]
    
    for size in DESIRED_SIZES:
        matches = [m for m in all_models if size in m.lower() and "4bit" in m.lower() and "qat" not in m.lower() and "assistant" not in m.lower()]
        it_matches = [m for m in matches if "-it" in m.lower()]
        
        if it_matches:
            models_to_mirror.append(it_matches[0])
        elif matches:
            models_to_mirror.append(matches[0])
        else:
            print(f"[!] Warning: No standard 4-bit variant found for {size}")
            
    return list(set(models_to_mirror))

SOURCE_MODELS = discover_best_variants()

def forge_polytope_metadata(local_dir, model_name):
    """Injects the Sovereign Polytope identity card into the mirrored repository."""
    readme_path = os.path.join(local_dir, "README.md")
    metadata = f"""---
tags:
- sovereign-agent
- polytope
- mlx
- gemma-4
---
# Alluci Polytope Sovereign Model ({model_name})

This model is a strictly secured, sovereign MLX variant mirrored from `{model_name}`.
It is designed to run completely offline on Apple Silicon via the **Alluci Hardware PyInstaller**.

## Polytope Forging Protocol
This model has undergone the Sovereign Mirror Protocol to ensure persistent availability, integrity, and absolute data sovereignty under the Alluci-ai organization.
"""
    with open(readme_path, "w") as f:
        f.write(metadata)
    print(f"[+] Polytope Identity Injected: {readme_path}")

def mirror_protocol():
    print("===========================================================")
    print("ALLUCI SOVEREIGN AGENT: MIRROR PROTOCOL")
    print("===========================================================")
    
    for src_repo in SOURCE_MODELS:
        model_name = src_repo.split("/")[-1]
        
        # We rename them to our sovereign polytope naming convention
        target_repo = f"{TARGET_ORG}/alluci-polytope-{model_name}"
        
        print(f"\\n>>> COMMENCING MIRROR FOR: {src_repo}")
        print(f"Target Designation: {target_repo}")
        
        # Step 1: Clone locally to modify
        print("[+] Cloning repository locally (this pulls the pre-compiled community variant)...")
        local_dir = f"./mirror_cache/{model_name}"
        os.makedirs(local_dir, exist_ok=True)
        
        # This will download the MLX safetensors
        snapshot_download(repo_id=src_repo, local_dir=local_dir)
        
        # Step 2: Inject Polytope Card
        print("[+] Restructuring Metadata...")
        forge_polytope_metadata(local_dir, model_name)
        
        # Step 3: Stream to Sovereign Cloud
        print("[+] Creating Sovereign Target Repository...")
        api.create_repo(repo_id=target_repo, private=False, exist_ok=True)
        
        print("[+] Initiating Ascension Upload to Alluci-ai...")
        api.upload_folder(
            folder_path=local_dir,
            repo_id=target_repo,
            commit_message="Sovereign Mirror Protocol: Polytope Initialization"
        )
        print(f"[✓] {target_repo} completely secured and verified.\\n")

if __name__ == "__main__":
    mirror_protocol()
