from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

MODEL_ID = "./models/gemma-4-e2b"

print(f"Loading tokenizer for {MODEL_ID}...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True, use_fast=False)

print(f"Loading model {MODEL_ID} with device_map='auto'...")
# Note: On a 31B model, this will require significant VRAM. 
# Added load_in_4bit=True for safety if bitsandbytes is available.
try:
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True
    )
    print("✅ Model loaded successfully!")
    
    prompt = "The philosophy of a Sovereign AI is based on"
    print(f"\n--- Testing Inference ---\nPrompt: {prompt}")
    
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    with torch.no_grad():
        outputs = model.generate(**inputs, max_new_tokens=50)
    
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    print(f"Response: {response}")
    print("\n--- Dry Run Complete ---")
except Exception as e:
    print(f"❌ Failed to load or run model: {e}")
