import os
from huggingface_hub import snapshot_download

models = [
    "Alluci/alluci-polytope-gemma-4-31b-it-bf16",
    "Alluci/alluci-polytope-gemma-4-31b-it-4bit",
    "Alluci/alluci-polytope-gemma-4-26b-a4b-it-4bit"
]

for repo_id in models:
    local_dir = f"mirror_cache/{repo_id.split('/')[-1]}"
    os.makedirs(local_dir, exist_ok=True)
    snapshot_download(repo_id=repo_id, local_dir=local_dir)
print("Downloads completed.")
