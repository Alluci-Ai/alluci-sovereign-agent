#include "tokenizer_mlx.hpp"
#include <sentencepiece_processor.h>
#include <stdexcept>

namespace alluci {

Tokenizer::Tokenizer(const std::string& model_path) {
    processor = std::make_unique<sentencepiece::SentencePieceProcessor>();
    auto status = processor->Load(model_path);
    if (!status.ok()) {
        throw std::runtime_error("Failed to load SentencePiece model: " + model_path + " (" + status.ToString() + ")");
    }
    bos_id = processor->bos_id();
    eos_id = processor->eos_id();
}

Tokenizer::~Tokenizer() = default;

std::vector<int> Tokenizer::encode(const std::string& text) const {
    if (text.empty()) return {};

    // Hack: SentencePiece automatically prepends a dummy space to the start of the string,
    // which encodes "You" as 1599 (" You"). HuggingFace GemmaTokenizer strips this,
    // encoding "You" as 3048. To match Python exactly and bypass the implicit dummy space,
    // we prepend <pad> which absorbs the dummy space, and then strip the resulting 3 tokens.
    std::string processed_text = "<pad>" + text;
    std::vector<int> raw_ids = processor->EncodeAsIds(processed_text);
    
    std::vector<int> ids;
    if (raw_ids.size() >= 3) {
        ids.assign(raw_ids.begin() + 3, raw_ids.end());
    } else {
        ids = raw_ids;
    }

    // Gemma requires BOS token (2) at the start
    std::vector<int> final_ids = {2};
    final_ids.insert(final_ids.end(), ids.begin(), ids.end());
    
    return final_ids;
}

std::string Tokenizer::decode(const std::vector<int>& tokens) const {
    return processor->DecodeIds(tokens);
}

} // namespace alluci
