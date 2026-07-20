#include <iostream>
#include <sentencepiece_processor.h>

int main(int argc, char** argv) {
    sentencepiece::SentencePieceProcessor processor;
    auto status = processor.Load("mirror_cache/alluci-polytope-gemma-4-e2b-it-4bit/tokenizer.model");
    if (!status.ok()) {
        std::cout << "Failed to load model" << std::endl;
        return 1;
    }
    
    std::vector<int> tokens = {2, 655, 3041, 236779, 1340, 236779, 887, 236813, 2364, 107, 160315, 127088};
    for (int t : tokens) {
        std::cout << t << ": " << processor.IdToPiece(t) << std::endl;
    }
    
    std::string prompt = "<start_of_turn>user\nHello Alluci, are you back online?<end_of_turn>\n<start_of_turn>model\n";
    std::vector<int> ids;
    auto encode_status = processor.Encode(prompt, &ids);
    if (!encode_status.ok()) {
        std::cout << "Failed to encode prompt" << std::endl;
        return 1;
    }
    std::cout << "Encoded prompt: ";
    for (int t : ids) {
        std::cout << t << " ";
    }
    std::cout << std::endl;
    return 0;
}
