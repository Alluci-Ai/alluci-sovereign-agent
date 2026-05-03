import os
import argparse
from huggingface_hub import snapshot_download

def download_gemma(model_id: str, local_dir: str):
    print(f"Starting download for {model_id}...")
    print(f"Target directory: {local_dir}")
    print("Note: The Gemma family of models is gated. You must have accepted the license on HuggingFace and have your HF_TOKEN set in your environment.")
    
    try:
        # Download the model weights and tokenizer
        path = snapshot_download(
            repo_id=model_id,
            local_dir=local_dir,
            local_dir_use_symlinks=False,
            ignore_patterns=["*.msgpack", "*.h5", "coreml/*"] # Ignore unnecessary formats
        )
        print(f"✅ Successfully downloaded {model_id} to {path}")
    except Exception as e:
        print(f"❌ Failed to download {model_id}: {e}")
        print("\nPlease ensure you have:")
        print("1. Accepted the Gemma license at https://huggingface.co/google")
        print("2. Set your HuggingFace token: export HF_TOKEN='hf_...'")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download Gemma 4 models directly for local execution.")
    parser.add_argument("--model", type=str, default="google/gemma-2-9b-it", help="The HuggingFace model ID (e.g., google/gemma-4-e2b)")
    parser.add_argument("--dir", type=str, default="./models/gemma", help="Local directory to save the weights")
    
    args = parser.parse_args()
    
    os.makedirs(args.dir, exist_ok=True)
    download_gemma(args.model, args.dir)
