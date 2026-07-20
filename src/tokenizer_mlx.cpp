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

    std::vector<int> unified_ids;
    
    // Deleting the custom chunking loop entirely.
    // SentencePiece now parses the pristine string in a single GPU-optimized stride.
    auto status = processor->Encode(text, &unified_ids);
    
    if (!status.ok()) {
        throw std::runtime_error("Tokenizer Core Failure: " + status.ToString());
    }

    // Gemma requires BOS token (2) at the start
    std::vector<int> final_ids = {2};
    final_ids.insert(final_ids.end(), unified_ids.begin(), unified_ids.end());

    return final_ids;
}

std::string Tokenizer::decode(const std::vector<int>& tokens) const {
    return processor->DecodeIds(tokens);
}

} // namespace alluci
