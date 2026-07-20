import sentencepiece as spm # type: ignore

sp = spm.SentencePieceProcessor()
sp.Load("mirror_cache/alluci-polytope-gemma-4-e2b-it-4bit/tokenizer.model")
tokens = [2, 655, 3041, 236779, 1340, 236779, 887, 236813, 2364, 107, 160315, 127088]
print("Tokens decode:")
for t in tokens:
    print(f"{t}: {sp.IdToPiece(t)}")

test_string = "<start_of_turn>user\nHello<end_of_turn>\n<start_of_turn>model\n"
print("Tokens for test string:", sp.EncodeAsIds(test_string))
