import typing
import sentencepiece.sentencepiece_model_pb2 as _model # type: ignore
model: typing.Any = _model

m = model.ModelProto()
with open("mirror_cache/alluci-polytope-gemma-4-e2b-it-4bit/tokenizer.model", "rb") as f:
    m.ParseFromString(f.read())

m.pieces[106].piece = "<start_of_turn>"
m.pieces[106].type = model.ModelProto.SentencePiece.USER_DEFINED

m.pieces[107].piece = "<end_of_turn>"
m.pieces[107].type = model.ModelProto.SentencePiece.USER_DEFINED

with open("mirror_cache/alluci-polytope-gemma-4-e2b-it-4bit/tokenizer.model", "wb") as f:
    f.write(m.SerializeToString())

print("Successfully injected <start_of_turn> and <end_of_turn> into tokenizer.model")
