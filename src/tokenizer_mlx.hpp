#pragma once

#include <string>
#include <vector>
#include <memory>

// Forward declaration for SentencePiece
namespace sentencepiece {
    class SentencePieceProcessor;
}

namespace alluci {

class Tokenizer {
private:
    std::unique_ptr<sentencepiece::SentencePieceProcessor> processor;
    int bos_id;
    int eos_id;

public:
    Tokenizer(const std::string& model_path);
    ~Tokenizer();

    std::vector<int> encode(const std::string& text) const;
    std::string decode(const std::vector<int>& tokens) const;
    
    int get_bos_id() const { return bos_id; }
    int get_eos_id() const { return eos_id; }
};

} // namespace alluci
