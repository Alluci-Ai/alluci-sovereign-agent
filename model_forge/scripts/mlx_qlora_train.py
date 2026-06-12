import os
import subprocess
import argparse

# The models we will fine-tune
MODELS = {
    "E2B": "google/gemma-4-E2B-it",
    "E4B": "google/gemma-4-E4B-it",
    "12B": "google/gemma-4-12B-it",
    "26B-A4B": "google/gemma-4-26B-A4B-it",
    "31B": "google/gemma-4-31B-it"
}

BASE_MODELS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "base_models"))
FINETUNED_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "finetuned"))
DATASET_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dataset"))

def run_mlx_lora(model_name: str, repo_id: str, iters: int = 1000):
    print(f"\\n{'='*50}\\nStarting QLoRA Fine-tuning for: {model_name}\\n{'='*50}")
    
    model_path = os.path.join(BASE_MODELS_DIR, repo_id.split('/')[-1])
    adapter_path = os.path.join(FINETUNED_DIR, f"{model_name}_adapters")
    
    if not os.path.exists(model_path):
        print(f"❌ Error: Base model {model_name} not found at {model_path}.")
        print(f"Skipping {model_name}...")
        return

    os.makedirs(adapter_path, exist_ok=True)
    
    # We use Apple MLX-LM for hardware-native Silicon training
    # - fine_tune=True runs the training
    # - lora-layers=16 (targets attention layers)
    # - batch-size=2 for large models, up to 4 for smaller ones
    command = [
        "python", "-m", "mlx_lm.lora",
        "--model", model_path,
        "--train",
        "--data", DATASET_DIR,
        "--iters", str(iters),
        "--batch-size", "2",
        "--num-layers", "16",
        "--adapter-path", adapter_path,
        "--save-every", "200"
    ]
    
    print(f"Executing command: {' '.join(command)}\\n")
    subprocess.run(command)
    print(f"\\n✅ Finished fine-tuning {model_name}. Adapters saved to {adapter_path}")

def main():
    parser = argparse.ArgumentParser(description="Alluci Polytope MLX QLoRA Fine-Tuner")
    parser.add_argument("--model", type=str, help="Specific model variant to train (e.g. 12B). If blank, trains all.")
    parser.add_argument("--iters", type=int, default=1000, help="Number of iterations per model.")
    args = parser.parse_args()

    os.makedirs(FINETUNED_DIR, exist_ok=True)
    os.makedirs(DATASET_DIR, exist_ok=True)
    
    # Check if dataset exists (train.jsonl, valid.jsonl)
    if not os.path.exists(os.path.join(DATASET_DIR, "train.jsonl")):
        print("⚠️ Warning: No train.jsonl found in model_forge/dataset/.")
        print("Please populate the dataset directory with Alluci formatting examples before proceeding.")
        return

    if args.model:
        if args.model in MODELS:
            run_mlx_lora(args.model, MODELS[args.model], iters=args.iters)
        else:
            print(f"❌ Unknown model variant: {args.model}")
    else:
        for name, repo in MODELS.items():
            run_mlx_lora(name, repo, iters=args.iters)

if __name__ == "__main__":
    main()
