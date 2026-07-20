import mlx.core as mx

# The model safetensors
weights = mx.load("mirror_cache/alluci-polytope-gemma-4-e2b-it-4bit/model.safetensors")

if not isinstance(weights, dict):
    raise TypeError(f"Expected dict, got {type(weights)}")

for k in ["language_model.model.layers.0.input_layernorm.weight", 
          "language_model.model.layers.0.post_attention_layernorm.weight",
          "language_model.model.norm.weight"]:
    if k in weights:
        w = weights[k]
        print(f"{k}: mean={float(mx.mean(w).item()):.4f}, min={float(mx.min(w).item()):.4f}, max={float(mx.max(w).item()):.4f}") # type: ignore
    else:
        print(f"{k} not found in safetensors!")
