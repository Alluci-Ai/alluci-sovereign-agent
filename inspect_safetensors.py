import mlx.core as mx

# Load one of the safetensors files
weights = mx.load("mirror_cache/alluci-polytope-gemma-4-31b-it-bf16/model-00001-of-00012.safetensors")

# Print keys
for k in weights.keys():
    if "layers.0" in k:
        print(k)
