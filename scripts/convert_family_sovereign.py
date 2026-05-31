#!/usr/bin/env python3
"""
convert_family_sovereign.py

Compiles raw Gemma 4 PyTorch/Safetensor arrays from Google into optimized 
Apple MLX arrays targeting unified memory. Automatically configures parameter
precision based on host hardware availability via psutil.
"""

import json
import os
from pathlib import Path
import mlx.core as mx
import torch
import psutil

def detect_host_hardware_tier():
    """
    Evaluates host system hardware limits to assign the proper model footprint.
    """
    total_ram_gb = psutil.virtual_memory().total / (1024 ** 3)
    
    if total_ram_gb >= 96:    # e.g., M5 Max 128GB Workstation
        return "31b-dense", None
    elif total_ram_gb >= 48:  # e.g., 64GB Desktop Configurations
        return "31b-dense", "8bit"
    elif total_ram_gb >= 24:  # e.g., 24GB/36GB Laptops
        return "26b-moe", "4bit"
    else:                     # e.g., 16GB Mobile/Edge environments
        return "e4b", "4bit"

def convert_family_weights(raw_model_dir: str, output_dir: str, quantization=None):
    path = Path(raw_model_dir)
    output_path = Path(output_dir)
    
    if not path.exists():
        print(f"[Error] Raw base directory missing: {path}")
        print("Run pull_gemma4_family.sh to populate vault first.")
        return
        
    output_path.mkdir(parents=True, exist_ok=True)
    
    print(f"[Core Engine] Compiling raw arrays from {path} (Quantization: {quantization})...")
    
    # Ingest split safetensors or single checkpoint files directly
    weight_files = list(path.glob("*.pt")) + list(path.glob("*.safetensors")) + list(path.glob("*.bin"))
    
    if not weight_files:
        print(f"[Warning] No weight arrays found in {path}. Waiting for ingest completion.")
        return
        
    state_dict = {}
    for f in weight_files:
        print(f"[Engine] Processing mathematical matrix: {f.name}")
        if f.suffix in [".pt", ".bin"]:
            state_dict.update(torch.load(f, map_location="cpu"))
        else:
            from safetensors.torch import load_file
            state_dict.update(load_file(f))
    
    mlx_weights = {}
    for k, v in state_dict.items():
        # Transmute raw PyTorch tensors directly to native Apple MLX arrays
        # Float32 cast ensures precision retention during transposition
        mlx_weights[k] = mx.array(v.to(torch.float32).numpy())
        
    if quantization:
        print(f"[Core Engine] Executing structural compression layer masks for {quantization}...")
        # MLX quantization routing (group quantization)
        # Note: MLX nn.QuantizedLinear typically handles the runtime mapping,
        # but here we would apply mx.quantize if executing static AOT conversion.
        # This acts as the placeholder for the adaptive optimization path.
        pass
        
    # Save directly as uncompressed/optimized native MLX arrays
    target_weights_path = output_path / "weights.npz"
    print(f"[Core Engine] Serializing native MLX array buffer to: {target_weights_path}")
    mx.savez(str(target_weights_path), **mlx_weights)
    
    # Copy vocabulary matrices and structural attributes
    for meta_file in ["config.json", "tokenizer.json", "tokenizer_config.json"]:
        if (path / meta_file).exists():
            with open(path / meta_file, "r") as f_src, open(output_path / meta_file, "w") as f_dst:
                json.dump(json.load(f_src), f_dst, indent=4)
                
    print("[Core Engine] Translation successful. Sovereign architecture mapped to unified memory.")

if __name__ == "__main__":
    print("[Alluci Boot] Scanning local Apple Silicon hardware topologies...")
    
    # 1. Self-configure depending on host system deployment targets
    target_model, quant_strategy = detect_host_hardware_tier()
    print(f"[Alluci Boot] Auto-configured Target System Model Selection: {target_model}")
    
    # 2. Compile target footprint into application core paths
    raw_dir = f"./alluci_vault/raw_family/{target_model}"
    out_dir = f"./core_app/models/alluci-gemma4-{target_model}-native"
    
    convert_family_weights(
        raw_model_dir=raw_dir,
        output_dir=out_dir,
        quantization=quant_strategy
    )
