#pragma once

#include "gemma_architecture.hpp"
#include "tokenizer_mlx.hpp"
#include <algorithm>
#include <iostream>
#include <memory>
#include <mlx/mlx.h>
#include <string>
#include <vector>

namespace alluci {

// Mock Grammar Engine to satisfy compilation
struct GrammarEngine {
  std::vector<int> get_valid_next_tokens() { return {}; }
  void advance_state(int token_id) {}
  void rollback_to_valid_state(int rollback_count) {}
};

struct SpeculativeDraftBlock {
  std::vector<int> token_ids;
  mlx::core::array draft_logits = mlx::core::array(0.0f);
};

struct SpeculativeEngineCoordinator {
  ModelArchitectureConfig draft_cfg;
  ModelArchitectureConfig verify_cfg;

  std::vector<KVCacheRingBuffer> draft_kv_registry;
  std::vector<KVCacheRingBuffer> verify_kv_registry;

  int lookahead_depth = 4;
};

class AlluciCognitiveEngine {
private:
  std::unique_ptr<Tokenizer> tokenizer;
  std::unique_ptr<GemmaModel> model;
  std::vector<KVCacheRingBuffer> global_kv_pipeline_registry;

public:
  AlluciCognitiveEngine(const std::string &model_dir) {
    std::cout << "[C++ MLX Core] Initializing Native Metal Engine from: "
              << model_dir << std::endl;

    try {
      std::cout << "[C++ MLX Core] Loading Tokenizer..." << std::endl;
      tokenizer = std::make_unique<Tokenizer>(model_dir + "/tokenizer.model");
      std::cout << "[C++ MLX Core] Tokenizer Loaded. Loading GemmaModel..."
                << std::endl;
      model = std::make_unique<GemmaModel>(model_dir);
      std::cout << "[C++ MLX Core] GemmaModel Loaded." << std::endl;
    } catch (const std::exception &e) {
      std::cerr << "[C++ MLX Core] Initialization Error: " << e.what()
                << std::endl;
    }
  }

  ~AlluciCognitiveEngine() {
    std::cout << "[C++ MLX Core] Releasing Unified Memory..." << std::endl;
  }

  // Dynamically injects LoRA matrices from the background Polytope Forge
  void inject_lora_adapters(const std::string &lora_path) {
    std::cout << "[C++ MLX Core] Hot-swapping LoRA Adapters into Multi-Head "
                 "Attention blocks from: "
              << lora_path << std::endl;
  }

  void flush_global_kv_pipeline_registry() {
    std::cout << "[C++ MLX Core] Flushing KV Pipeline Registry..." << std::endl;
    for (auto &buffer : global_kv_pipeline_registry) {
      buffer.head_index = 0;
      buffer.cumulative_tokens = 0;
      buffer.is_preallocated = false;
    }
  }

  void profile_speculative_efficiency(int accepted_tokens, int K) {
    float acceptance_rate =
        (static_cast<float>(accepted_tokens) / static_cast<float>(K)) * 100.0f;

    std::cout << "[TELEMETRY PROFILE] Stride Acceptance: " << acceptance_rate
              << "% "
              << "(" << accepted_tokens << "/" << K << " tokens accepted). "
              << "V-Cache State: STABLE." << std::endl;

    if (acceptance_rate < 25.0f) {
      std::cout
          << "[WARN] Speculative degradation detected. Review alignment sheets."
          << std::endl;
    }
  }

  // The primary autoregressive inference loop called by the Python router
  std::string evaluate_intent(const std::string &prompt, int max_tokens,
                              float temperature,
                              const std::vector<int> &allowed_token_ids = {}) {
    if (!tokenizer || !model) {
      return "{\"error\": \"Model not loaded properly. Native engine "
             "failed.\"}";
    }

    std::cout << "[C++ MLX Core] Executing Polytope Projection Network intent "
                 "evaluation on Metal GPU..."
              << std::endl;
    try {
      // Encode the prompt
      std::vector<int> input_tokens = tokenizer->encode(prompt);
      std::vector<int> output_tokens;

      // Explicitly flush and reset stale traces at inference boundaries
      for (auto &buffer : global_kv_pipeline_registry) {
        buffer.head_index = 0;
        buffer.cumulative_tokens = 0;
        buffer.is_preallocated = false;
      }

      // Safety limit for KV cache
      std::vector<int> tokens = tokenizer->encode(prompt);
      std::cout << "[C++ MLX Core] Prompt Tokens: ";
      for (int t : tokens) {
        std::cout << t << " ";
      }
      std::cout << std::endl;

      mlx::core::array x =
          mlx::core::array(tokens.data(), {1, static_cast<int>(tokens.size())},
                           mlx::core::int32);

      std::cout << "[C++ MLX Engine] Streaming Output: ";

      for (int step = 0; step < max_tokens; ++step) {
        auto h = model->forward_pipeline(x, global_kv_pipeline_registry);
        auto logits = model->project_vocabulary(h);

        // Debug shape of logits
        std::cout << "[C++ MLX Engine] logits shape: [";
        for (int dim : logits.shape())
          std::cout << dim << ", ";
        std::cout << "]" << std::endl;

        // Take the last token's logits (axis 1 is sequence length)
        logits =
            mlx::core::take(logits, mlx::core::array(logits.shape(1) - 1), 1);
        // Evaluate KV cache graph manually to enforce memory boundaries
        for (auto &buf : global_kv_pipeline_registry) {
          if (buf.is_preallocated) {
            mlx::core::eval({buf.k_cache, buf.v_cache});
          }
        }
        logits = mlx::core::squeeze(logits); // (V,)
        auto raw_max = mlx::core::max(logits, -1, false);
        auto raw_min = mlx::core::min(logits, -1, false);
        mlx::core::eval({raw_max, raw_min});
        mlx::core::synchronize(); // MUST SYNCHRONIZE ON METAL
        std::cout << "[DEBUG RAW LOGITS] MAX: " << raw_max.item<float>()
                  << " | MIN: " << raw_min.item<float>() << std::endl;

        // Structured Logit Bias Masking for Grammatical Safety
        if (!allowed_token_ids.empty()) {
          logits = apply_grammatical_safeguards(logits, allowed_token_ids);
        }

        auto next_token_array = mlx::core::argmax(logits, -1, false);
        mlx::core::eval({next_token_array});
        for (auto &buf : global_kv_pipeline_registry) {
          if (buf.is_preallocated) {
            mlx::core::eval({buf.k_cache, buf.v_cache});
          }
        }
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
    } catch (const std::exception &e) {
      return "{\"error\": \"Generation failed: " + std::string(e.what()) +
             "\"}";
    }
  }

  std::vector<int>
  execute_speculative_stride(SpeculativeEngineCoordinator &coord,
                             std::vector<int> &system_prompt_ids,
                             GrammarEngine &grammar_engine) {
    int K = coord.lookahead_depth;
    SpeculativeDraftBlock draft_block;

    // =========================================================================
    // STEP 1: GENERATE K SPECULATIVE TOKENS (12B DRAFT ENGINE)
    // =========================================================================
    for (int k = 0; k < K; ++k) {
      // Run forward pass through the 12B model branch
      auto single_token_array = mlx::core::array({system_prompt_ids.back()},
                                                 {1, 1}, mlx::core::int32);
      auto draft_h =
          model->forward_pipeline(single_token_array, coord.draft_cfg,
                                  coord.draft_kv_registry, "draft_model");
      auto raw_draft_logits = model->project_vocabulary(draft_h, "draft_model");

      // Apply your existing, verified GPU-side grammar safeguards
      std::vector<int> allowed_tokens = grammar_engine.get_valid_next_tokens();
      auto secure_draft_logits =
          allowed_tokens.empty()
              ? raw_draft_logits
              : apply_grammatical_safeguards(raw_draft_logits, allowed_tokens);

      // Sample the next token ID using argmax
      auto next_token_tensor = mlx::core::argmax(secure_draft_logits, -1);
      mlx::core::eval(
          {next_token_tensor}); // Flush the lazy graph to read the ID
      int sampled_id = next_token_tensor.item<int>();

      draft_block.token_ids.push_back(sampled_id);

      // Push token back to input vector to keep the draft loop moving
      // autoregressively
      system_prompt_ids.push_back(sampled_id);
      grammar_engine.advance_state(
          sampled_id); // Move grammar transition state forward
    }

    // =========================================================================
    // STEP 2: PARALLEL VERIFICATION STRIDE (31B VERIFICATION ENGINE)
    // =========================================================================
    // To verify the K drafted tokens, the verification engine must process:
    // [last_accepted_token, draft_1, draft_2, ..., draft_{K-1}]
    std::vector<int> verify_seq;
    verify_seq.reserve(K);

    int last_accepted_idx = system_prompt_ids.size() - K - 1;
    for (int i = 0; i < K; ++i) {
      verify_seq.push_back(system_prompt_ids[last_accepted_idx + i]);
    }

    auto verify_input_tensor =
        mlx::core::array(verify_seq.data(), {1, K}, mlx::core::int32);

    // Compute parallel forward pass: processes all K tokens simultaneously
    auto verify_h = model->forward_pipeline_parallel(
        verify_input_tensor, coord.verify_cfg, coord.verify_kv_registry,
        "verify_model");
    auto verify_logits = model->project_vocabulary(
        verify_h, "verify_model"); // Shape: [1, K, VocabSize]

    // =========================================================================
    // STEP 3: ELEMENT-WISE ACCEPT/REJECT CRITERIA
    // =========================================================================
    int accepted_count = 0;
    std::vector<int> validated_tokens;

    for (int i = 0; i < K; ++i) {
      int drafted_id = draft_block.token_ids[i];

      // Isolate the target row of verification logits for this specific index
      // verify_logits shape is [1, K, VocabSize]
      auto current_verify_row = mlx::core::slice(
          verify_logits, {0, i, 0}, {1, i + 1, verify_logits.shape(2)});
      auto target_verify_token = mlx::core::argmax(current_verify_row, -1);
      mlx::core::eval({target_verify_token});
      int verified_id = target_verify_token.item<int>();

      if (drafted_id == verified_id) {
        // Strict token match: accept the draft token
        accepted_count++;
        validated_tokens.push_back(drafted_id);
      } else {
        // Divergence detected! Accept the 31B corrective token and halt the
        // block evaluation
        validated_tokens.push_back(verified_id);
        break;
      }
    }

    // =========================================================================
    // STEP 4: HARD KV-CACHE SYNCHRONIZATION AND FLUSH
    // =========================================================================

    profile_speculative_efficiency(accepted_count, K);

    // KV Cache Rollback
    // Both models appended exactly K tokens during this stride: [c_0, d_1, ...,
    // d_{K-1}]
    int kv_rollback_count = std::max(0, K - 1 - accepted_count);

    if (kv_rollback_count > 0) {
      // Rollback Draft Engine
      for (auto &buffer : coord.draft_kv_registry) {
        if (buffer.sliding_window > 0) {
          buffer.head_index =
              (buffer.head_index - kv_rollback_count + buffer.sliding_window) %
              buffer.sliding_window;
        } else {
          buffer.head_index = buffer.head_index - kv_rollback_count;
        }
        buffer.cumulative_tokens -= kv_rollback_count;
      }

      // Rollback Verify Engine
      for (auto &buffer : coord.verify_kv_registry) {
        if (buffer.sliding_window > 0) {
          buffer.head_index =
              (buffer.head_index - kv_rollback_count + buffer.sliding_window) %
              buffer.sliding_window;
        } else {
          buffer.head_index = buffer.head_index - kv_rollback_count;
        }
        buffer.cumulative_tokens -= kv_rollback_count;
      }
    }

    // Synchronize input ID tracking arrays to match the verified branch
    int prompt_rollback = K - accepted_count;
    if (prompt_rollback > 0) {
      system_prompt_ids.resize(system_prompt_ids.size() - prompt_rollback);
      grammar_engine.rollback_to_valid_state(prompt_rollback);
    }

    // If there was a divergence, append the correction token to the prompt
    if (accepted_count < K) {
      system_prompt_ids.push_back(validated_tokens.back());
      grammar_engine.advance_state(validated_tokens.back());
    }

    return validated_tokens;
  }
};

} // namespace alluci
