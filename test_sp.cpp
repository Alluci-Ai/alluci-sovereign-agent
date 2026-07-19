#include <iostream>
#include <sentencepiece_processor.h>

int main(int argc, char** argv) {
    sentencepiece::SentencePieceProcessor processor;
    auto status = processor.Load(argv[1]);
    if (!status.ok()) {
        std::cout << "Failed to load model" << std::endl;
    }
    return 0;
}
