import os, json, glob

for p in glob.glob("mirror_cache/*/config.json"):
    with open(p, "r") as f:
        data = json.load(f)
    
    if "text_config" in data:
        data["model_type"] = "paligemma"
        data["architectures"] = ["PaliGemmaForConditionalGeneration"]
        data["text_config"]["model_type"] = "gemma"
        if "vision_config" in data:
            data["vision_config"]["model_type"] = "siglip_vision_model"
    else:
        # Standard LLM (non-VLM)
        data["model_type"] = "gemma2"
        data["architectures"] = ["Gemma2ForCausalLM"]

    with open(p, "w") as f:
        json.dump(data, f, indent=4)
    print(f"Fixed {p}")
