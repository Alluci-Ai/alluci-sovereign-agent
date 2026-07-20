import mlx.core as mx

tensors: dict = mx.load("mirror_cache/alluci-polytope-gemma-4-31b-it-bf16/model-00012-of-00012.safetensors") # type: ignore
print([k for k in tensors.keys() if "q_proj" in k or "q_norm" in k])
