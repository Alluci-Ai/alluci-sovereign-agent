import os
from huggingface_hub import snapshot_download

# Define the full Gemma 4 family
MODELS = [
    "google/gemma-4-E2B-it",
    "google/gemma-4-E4B-it",
    "google/gemma-4-12B-it",
    "google/gemma-4-26B-A4B-it",
    "google/gemma-4-31B-it"
]

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "base_models"))

def main():
    print("Initiating Alluci Model Forge: Base Model Download sequence...")
    os.makedirs(BASE_DIR, exist_ok=True)
    
    for repo_id in MODELS:
        print(f"\\n--- Downloading {repo_id} ---")
        try:
            # We ignore safe tensor files if we specifically want pytorch bins, but for modern
            # pipelines safetensors are preferred. We'll download everything except standard git noise.
            local_dir = os.path.join(BASE_DIR, repo_id.split("/")[-1])
            path = snapshot_download(
                repo_id=repo_id,
                local_dir=local_dir
            )
            print(f"✅ Successfully downloaded {repo_id} to {path}")
        except Exception as e:
            print(f"❌ Failed to download {repo_id}. Ensure you have accepted the Google license agreement on Hugging Face. Error: {e}")

if __name__ == "__main__":
    main()
