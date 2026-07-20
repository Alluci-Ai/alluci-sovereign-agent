import mlx.core as mx

tensors: dict = mx.load("mirror_cache/alluci-polytope-gemma-4-31b-it-bf16/model-00012-of-00012.safetensors") # type: ignore
for k, v in tensors.items():
    if "norm" in k:
        print(f"{k}: mean={mx.mean(v).item()}, min={mx.min(v).item()}, max={mx.max(v).item()}")
