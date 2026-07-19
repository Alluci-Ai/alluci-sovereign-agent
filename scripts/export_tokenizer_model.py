import os
import json
import urllib.request
import sentencepiece.sentencepiece_model_pb2 as spm_pb2

def convert_tokenizer(cache_dir):
    tokenizer_json_path = os.path.join(cache_dir, "tokenizer.json")
    output_model_path = os.path.join(cache_dir, "tokenizer.model")
    
    if not os.path.exists(tokenizer_json_path):
        return
        
    print(f"\nProcessing {cache_dir}...")
    
    print("1. Downloading base Gemma 2 tokenizer.model from HuggingFace...")
    # Using unsloth's base Gemma 2 tokenizer as the structural template
    base_url = "https://huggingface.co/unsloth/gemma-2-9b-it/resolve/main/tokenizer.model"
    base_model_path = "base_tokenizer.model"
    if not os.path.exists(base_model_path):
        urllib.request.urlretrieve(base_url, base_model_path)
    print("   Downloaded base template.")

    print("2. Parsing base tokenizer protobuf...")
    m = spm_pb2.ModelProto()
    with open(base_model_path, "rb") as f:
        m.ParseFromString(f.read())
    
    print("3. Loading custom tokenizer.json...")
    with open(tokenizer_json_path, "r", encoding="utf-8") as f:
        tok_json = json.load(f)
        
    vocab_dict = tok_json["model"]["vocab"]
    # Invert vocab from {token: id} to {id: token}
    id_to_token = {v: k for k, v in vocab_dict.items()}
    max_id = max(id_to_token.keys())
    
    added_tokens = {t["id"]: t for t in tok_json.get("added_tokens", [])}
    
    print(f"   Found {len(vocab_dict)} total tokens and {len(added_tokens)} custom added/special tokens.")

    print("4. Injecting custom vocabulary into binary protobuf...")
    # Clear existing pieces to prevent leftover base model tokens
    del m.pieces[:]
    
    # Resize pieces array
    while len(m.pieces) <= max_id:
        m.pieces.add()
        
    for i in range(max_id + 1):
        if i not in id_to_token:
            continue
            
        piece_str = id_to_token[i]
        
        # We retain the score from the base model if available, otherwise 0
        
        # Determine token type
        if i in added_tokens:
            content = added_tokens[i]["content"]
            m.pieces[i].piece = content
            if content == "<unk>":
                m.pieces[i].type = 2
            elif content in ["<pad>", "<eos>", "<bos>"]:
                m.pieces[i].type = 3
            else:
                m.pieces[i].type = 4 # USER_DEFINED
        else:
            m.pieces[i].piece = piece_str
            if piece_str.startswith("<0x") and piece_str.endswith(">"):
                m.pieces[i].type = 6 # BYTE
            elif piece_str in ["<pad>", "<eos>", "<bos>", "<unk>"]:
                if piece_str == "<unk>": m.pieces[i].type = 2
                else: m.pieces[i].type = 3 # CONTROL
            else:
                m.pieces[i].type = 1 # NORMAL

    print("5. Serializing and saving new tokenizer.model...")
    with open(output_model_path, "wb") as f:
        f.write(m.SerializeToString())
        
    print(f"SUCCESS: Wrote valid SentencePiece binary to {output_model_path}")

if __name__ == "__main__":
    mirror_cache = "mirror_cache"
    for d in os.listdir(mirror_cache):
        full_path = os.path.join(mirror_cache, d)
        if os.path.isdir(full_path):
            convert_tokenizer(full_path)
