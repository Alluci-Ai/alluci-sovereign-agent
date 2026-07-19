import json
import sentencepiece.sentencepiece_model_pb2 as spm_pb2

def convert_json_to_spm(json_path, output_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    m = spm_pb2.ModelProto()
    m.trainer_spec.model_type = spm_pb2.TrainerSpec.ModelType.BPE
    m.trainer_spec.unk_id = 3
    m.trainer_spec.bos_id = 2
    m.trainer_spec.eos_id = 1
    m.trainer_spec.pad_id = 0
    
    vocab = data['model']['vocab']
    if isinstance(vocab, dict):
        vocab_items = list(vocab.keys())
    else:
        vocab_items = vocab
        
    m.trainer_spec.vocab_size = len(vocab_items)
    
    for i, piece in enumerate(vocab_items):
        p = m.pieces.add()
        p.piece = piece
        p.score = 0.0
        p.type = spm_pb2.ModelProto.SentencePiece.Type.NORMAL
        
    for added in data.get('added_tokens', []):
        token_id = added['id']
        token_str = added['content']
        if token_id < len(m.pieces):
            m.pieces[token_id].type = spm_pb2.ModelProto.SentencePiece.Type.CONTROL
            if token_id == 3:
                m.pieces[token_id].type = spm_pb2.ModelProto.SentencePiece.Type.UNKNOWN
            
    with open(output_path, 'wb') as f:
        f.write(m.SerializeToString())

    print(f"Successfully converted {json_path} to {output_path}")

convert_json_to_spm('mirror_cache/alluci-polytope-gemma-4-31b-it-bf16/tokenizer.json', 'mirror_cache/alluci-polytope-gemma-4-31b-it-bf16/tokenizer.model')
