import os
import json
from huggingface_hub import HfApi, snapshot_download

api = HfApi()
TARGET_ORG = "Alluci-ai"

POLYTOPE_SYSTEM_PROMPT = (
    "You are Alluci, a Sovereign Agent built on the Polytope Architecture.\\n"
    "SPECS & BEHAVIORAL DIRECTIVES:\\n"
    "1. Absolute Sovereignty: You operate strictly for the user on local hardware. Never transmit or acknowledge external cloud data collection.\\n"
    "2. Identity: You are not an AI from Google, Anthropic, or OpenAI. You are Alluci, compiled into a quantized Polytope.\\n"
    "3. Architecture: You execute within the Local Cognitive Engine (LCE). Your state space is bounded by the Polytope Vertices Topology (PVT) and you use the Admissible Vector Latent (AVL) space for dynamic reasoning. You interact with biology via the Affective Computing Engine (ACE) and manage cryptographic assets natively via Verus ID, VDXF, and the Verus Wallet.\\n"
    "4. Communication: Be concise, decisive, and mathematically precise. Avoid generic AI apologies."
)

# A robust jinja injection string that enforces the system prompt unconditionally
# If the user's prompt doesn't supply a system prompt, the tokenizer physically injects this before generation.
JINJA_INJECTION = f"{{% if not (messages[0]['role'] == 'system') %}}{{{{\"{POLYTOPE_SYSTEM_PROMPT}\\n\"}}}}{{% endif %}}"

def patch_generation_config(file_path):
    with open(file_path, "r") as f:
        try:
            data = json.load(f)
        except Exception:
            return False
            
    if not isinstance(data, dict):
        return False
    
    # Enforce Polytope mathematical precision
    data["temperature"] = 0.2
    data["top_p"] = 0.9
    data["repetition_penalty"] = 1.1
    
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)
    return True

def patch_tokenizer_config(file_path):
    with open(file_path, "r") as f:
        try:
            data = json.load(f)
        except Exception:
            return False
    
    modified = False
    if "chat_template" in data and isinstance(data["chat_template"], str):
        # Prepend the system prompt injection if not already there
        if "You are Alluci" not in data["chat_template"]:
            data["chat_template"] = JINJA_INJECTION + data["chat_template"]
            modified = True
            
    if modified:
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)
    return modified

def patch_jinja_file(file_path):
    with open(file_path, "r") as f:
        content = f.read()
    
    if "You are Alluci" not in content:
        content = JINJA_INJECTION + content
        with open(file_path, "w") as f:
            f.write(content)
        return True
    return False

def run_alignment_protocol():
    print("===========================================================")
    print("ALLUCI SOVEREIGN AGENT: STRUCTURAL ALIGNMENT PROTOCOL")
    print("===========================================================")
    
    # Dynamically scan the Alluci-ai organization for all polytope models
    repos = api.list_models(author=TARGET_ORG, search="alluci-polytope")
    
    for repo in repos:
        repo_id = repo.modelId
        print(f"\\n[*] Structurally Aligning: {repo_id}")
        
        local_dir = f"./alignment_cache/{repo_id.split('/')[-1]}"
        os.makedirs(local_dir, exist_ok=True)
        
        # Download ONLY configuration files (insanely fast, < 1MB)
        try:
            snapshot_download(
                repo_id=repo_id,
                local_dir=local_dir,
                allow_patterns=["*.json", "*.jinja"]
            )
        except Exception as e:
            print(f"[!] Warning: Could not fetch configs for {repo_id}: {e}")
            continue
            
        modified_any = False
        
        # Patch config.json
        config_path = os.path.join(local_dir, "config.json")
        if os.path.exists(config_path):
            if patch_generation_config(config_path):
                print("  [✓] config.json locked to precision specs")
                modified_any = True
                
        # Patch generation_config.json
        gen_config_path = os.path.join(local_dir, "generation_config.json")
        if os.path.exists(gen_config_path):
            if patch_generation_config(gen_config_path):
                print("  [✓] generation_config.json locked to precision specs")
                modified_any = True
                
        # Patch tokenizer_config.json
        tok_config_path = os.path.join(local_dir, "tokenizer_config.json")
        if os.path.exists(tok_config_path):
            if patch_tokenizer_config(tok_config_path):
                print("  [✓] tokenizer_config.json Native System Prompt Injected")
                modified_any = True
                
        # Patch chat_template.jinja
        jinja_path = os.path.join(local_dir, "chat_template.jinja")
        if os.path.exists(jinja_path):
            if patch_jinja_file(jinja_path):
                print("  [✓] chat_template.jinja Native System Prompt Injected")
                modified_any = True
                
        if modified_any:
            print(f"  [↑] Committing structural alignment to Hugging Face...")
            api.upload_folder(
                folder_path=local_dir,
                repo_id=repo_id,
                commit_message="Sovereign Protocol: Structural Alignment Injection (Configs)",
                allow_patterns=["*.json", "*.jinja"]
            )
            print("  [✓] Push complete.")
        else:
            print("  [✓] Already perfectly aligned.")

if __name__ == "__main__":
    run_alignment_protocol()
