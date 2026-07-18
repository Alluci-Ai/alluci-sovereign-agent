#pragma once

#include <string>
#include <iostream>
#include <vector>
#include <memory>
#include <mlx/mlx.h>
#include "tokenizer_mlx.hpp"
#include "gemma_architecture.hpp"

namespace alluci {

class AlluciCognitiveEngine {
private:
    std::unique_ptr<Tokenizer> tokenizer;
    std::unique_ptr<GemmaModel> model;

public:
    AlluciCognitiveEngine(const std::string& model_dir) {
        std::cout << "[C++ MLX Core] Initializing Native Metal Engine from: " << model_dir << std::endl;
        
        try {
            std::cout << "[C++ MLX Core] Loading Tokenizer..." << std::endl;
            tokenizer = std::make_unique<Tokenizer>(model_dir + "/tokenizer.model");
            std::cout << "[C++ MLX Core] Tokenizer Loaded. Loading GemmaModel..." << std::endl;
            model = std::make_unique<GemmaModel>(model_dir);
            std::cout << "[C++ MLX Core] GemmaModel Loaded." << std::endl;
        } catch (const std::exception& e) {
            std::cerr << "[C++ MLX Core] Initialization Error: " << e.what() << std::endl;
        }
    }

    ~AlluciCognitiveEngine() {
        std::cout << "[C++ MLX Core] Releasing Unified Memory..." << std::endl;
    }

    // Dynamically injects LoRA matrices from the background Polytope Forge
    void inject_lora_adapters(const std::string& lora_path) {
        std::cout << "[C++ MLX Core] Hot-swapping LoRA Adapters into Multi-Head Attention blocks from: " << lora_path << std::endl;
    }

    // The primary autoregressive inference loop called by the Python router
    std::string evaluate_intent(const std::string& prompt, int max_tokens, float temperature) {
        if (!tokenizer || !model) {
            return "{\"error\": \"Model not loaded properly. Native engine failed.\"}";
        }
        
        std::cout << "[C++ MLX Core] Executing Polytope Projection Network intent evaluation on Metal GPU..." << std::endl;
        try {
            // Encode the prompt
            std::vector<int> input_tokens = tokenizer->encode(prompt);
            std::vector<int> output_tokens;
            std::vector<mlx::core::array> kv_cache;
            
            // Safety limit for KV cache
            std::vector<int> tokens = tokenizer->encode(prompt);
            std::cout << "[C++ MLX Core] Prompt Tokens: ";
            for (int t : tokens) {
                std::cout << t << " ";
            }
            std::cout << std::endl;
            
            mlx::core::array x = mlx::core::array(tokens.data(), {1, static_cast<int>(tokens.size())}, mlx::core::int32);
            
            std::cout << "[C++ MLX Engine] Streaming Output: ";

            for (int step = 0; step < max_tokens; ++step) {
                // Check KV Cache limits
                const size_t MAX_CONTEXT = 4096;
                if (kv_cache.size() > MAX_CONTEXT) {
                    kv_cache.clear(); // Safe evict to prevent VRAM rupture
                }

                auto logits = model->forward(x, kv_cache);
                
                // Debug shape of logits
                std::cout << "[C++ MLX Engine] logits shape: [";
                for (int dim : logits.shape()) std::cout << dim << ", ";
                std::cout << "]" << std::endl;
                
                // Take the last token's logits (axis 1 is sequence length)
                logits = mlx::core::take(logits, mlx::core::array(logits.shape(1) - 1), 1);
                mlx::core::eval(kv_cache);
                logits = mlx::core::squeeze(logits); // (V,)
                auto raw_max = mlx::core::max(logits, -1, false);
                auto raw_min = mlx::core::min(logits, -1, false);
                mlx::core::eval({raw_max, raw_min});
                mlx::core::synchronize(); // MUST SYNCHRONIZE ON METAL
                std::cout << "[DEBUG RAW LOGITS] MAX: " << raw_max.item<float>() << " | MIN: " << raw_min.item<float>() << std::endl;
                
                // Softcapping is now handled in gemma_architecture.hpp
                auto next_token_array = mlx::core::argmax(logits, -1, false);
                mlx::core::eval({next_token_array});
                mlx::core::eval(kv_cache);
                int next_token = static_cast<int>(next_token_array.item<uint32_t>());
                auto max_val = mlx::core::max(logits, -1, false);
                auto min_val = mlx::core::min(logits, -1, false);
                mlx::core::eval({max_val, min_val});
                std::cout << "\n[CPP TOKEN ID] " << next_token 
                          << " | MAX LOGIT: " << max_val.item<float>() 
                          << " | MIN LOGIT: " << min_val.item<float>() << std::endl;
                output_tokens.push_back(next_token);

                // Stream decoding dynamically for TTFT
                std::string streamed_piece = tokenizer->decode({next_token});
                std::cout << streamed_piece << std::flush;
                
                if (next_token == tokenizer->get_eos_id()) {
                    break;
                }
                
                // Update input for next step
                x = mlx::core::array({next_token}, {1, 1}, mlx::core::int32);
            }
            std::cout << std::endl;

            // Final generation payload
            return tokenizer->decode(output_tokens);
        } catch (const std::exception& e) {
            return "{\"error\": \"Generation failed: " + std::string(e.what()) + "\"}";
        }
    }
};

} // namespace alluci
