import os
from huggingface_hub import snapshot_download

MLX_FLEET = [
    "Alluci-ai/alluci-polytope-gemma-4-e2b-it-4bit",
    "Alluci-ai/alluci-polytope-gemma-4-e4b-it-OptiQ-4bit",
    "Alluci-ai/alluci-polytope-gemma-4-12B-it-OptiQ-4bit",
    "Alluci-ai/alluci-polytope-gemma-4-26B-A4B-it-OptiQ-4bit",
    "Alluci-ai/alluci-polytope-gemma-4-31b-it-4bit"
]

def cache_fleet():
    print("===========================================================")
    print("ALLUCI SOVEREIGN AGENT: MLX FLEET LOCAL CACHING")
    print("===========================================================")
    print("Downloading the full Sovereign MLX fleet to local Hugging Face cache...")
    
    for repo_id in MLX_FLEET:
        print(f"\\n[*] Caching: {repo_id}")
        try:
            snapshot_download(repo_id=repo_id, allow_patterns=["*.safetensors", "*.json", "*.jinja"])
            print(f"  [✓] Successfully cached {repo_id}")
        except Exception as e:
            print(f"  [!] Failed to cache {repo_id}: {e}")

if __name__ == "__main__":
    cache_fleet()
