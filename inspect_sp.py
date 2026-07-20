import sentencepiece.sentencepiece_model_pb2 as sp_model # type: ignore
from typing import Any
model: Any = sp_model
m = model.ModelProto()
m.ParseFromString(open("base_tokenizer.model", "rb").read())

print("Searching for start_of_turn in pieces...")
for i, piece in enumerate(m.pieces):
    if "start_of_turn" in piece.piece or "end_of_turn" in piece.piece:
        print(f"ID {i}: '{piece.piece}' type: {piece.type}")
