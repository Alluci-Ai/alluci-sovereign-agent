#pragma once

#include <mlx/mlx.h>
#include <mlx/fast.h>
#include <string>
#include <unordered_map>
#include <filesystem>
#include <vector>
#include <optional>

namespace fs = std::filesystem;

namespace alluci {

class GemmaModel {
private:
    std::unordered_map<std::string, mlx::core::array> weights;
    int vocab_size = 262144;
    int hidden_size = 5376;
    int num_layers = 60;

    mlx::core::array flexible_matmul(const mlx::core::array& x, const std::string& prefix) {
        if (weights.find(prefix + ".weight") == weights.end()) {
            return x; // Identity fallback
        }
        
        auto w = weights.at(prefix + ".weight");
        
        if (weights.find(prefix + ".scales") != weights.end()) {
            auto scales = weights.at(prefix + ".scales");
            auto biases = weights.at(prefix + ".biases");
            return mlx::core::quantized_matmul(x, w, scales, biases, true, 128, 4);
        }

        // Unquantized (dense FP16/BF16) safetensors weights are stored as (Out, In)
        // mlx::core::matmul(X, W) expects W to be (In, Out), so we must transpose it.
        return mlx::core::matmul(x, mlx::core::transpose(w));
    }

        mlx::core::array rms_norm(const mlx::core::array& x, const std::string& weight_key) {
        if (weights.find(weight_key) != weights.end()) {
            auto w = weights.at(weight_key);
            auto x_fp32 = mlx::core::astype(x, mlx::core::float32);
            
            auto orig_shape = x.shape();
            auto flat_x = mlx::core::reshape(x_fp32, {-1, orig_shape.back()});
            
            auto var = mlx::core::mean(mlx::core::square(flat_x), std::vector<int>{-1}, /*keepdims=*/true);
            auto x_norm = mlx::core::multiply(flat_x, mlx::core::rsqrt(mlx::core::add(var, mlx::core::array(1e-6f))));
            
            // Explicit Type Casting: Ensure bfloat16
            auto w_shifted = mlx::core::astype(w, mlx::core::bfloat16);
            
            // Apply weight directly (Weights are already statically shifted in the checkpoint!)
            auto res = mlx::core::multiply(mlx::core::astype(x_norm, mlx::core::bfloat16), w_shifted);
            res = mlx::core::reshape(res, orig_shape);
            return mlx::core::astype(res, x.dtype());
        }
        return x;
    } // Fallback if weight not found
        
        mlx::core::array rms_norm_no_weight(const mlx::core::array& x, int head_dim) {
            auto x_fp32 = mlx::core::astype(x, mlx::core::float32);
            
            auto orig_shape = x.shape();
            int num_heads = orig_shape.back() / head_dim;
            auto new_shape = orig_shape;
            new_shape.back() = num_heads;
            new_shape.push_back(head_dim);
            x_fp32 = mlx::core::reshape(x_fp32, new_shape);
            
            auto var = mlx::core::mean(mlx::core::square(x_fp32), std::vector<int>{-1}, /*keepdims=*/true);
            auto x_norm = mlx::core::multiply(x_fp32, mlx::core::rsqrt(mlx::core::add(var, mlx::core::array(1e-6f))));
            
            auto res = mlx::core::astype(x_norm, x.dtype());
            return mlx::core::reshape(res, orig_shape);
        };
        
        mlx::core::array attention(const mlx::core::array& x, int layer_idx, std::vector<mlx::core::array>& kv_cache) {
        std::string prefix = "language_model.model.layers." + std::to_string(layer_idx) + ".self_attn";
        bool is_full_attention = (layer_idx % 6 == 5);
        auto q = flexible_matmul(x, prefix + ".q_proj");
        auto k = flexible_matmul(x, prefix + ".k_proj");
        mlx::core::array v = mlx::core::zeros({1}, mlx::core::float32); // dummy init
        if (is_full_attention) {
            v = k; 
        } else {
            v = flexible_matmul(x, prefix + ".v_proj");
        }
        
        int q_heads = 32;
        int kv_heads = 16;
        int head_dim = 256;
        
        if (weights.find(prefix + ".q_proj.weight") != weights.end() && 
            weights.find(prefix + ".q_norm.weight") != weights.end() &&
            weights.find(prefix + ".k_proj.weight") != weights.end()) {
            
            auto q_norm_w = weights.at(prefix + ".q_norm.weight");
            head_dim = q_norm_w.shape(0);
            auto q_proj_w = weights.at(prefix + ".q_proj.weight");
            q_heads = q_proj_w.shape(0) / head_dim;
            auto k_proj_w = weights.at(prefix + ".k_proj.weight");
            kv_heads = k_proj_w.shape(0) / head_dim;
        }

        int B = x.shape(0);
        int L = x.shape(1);
        q = mlx::core::reshape(q, {B, L, q_heads, head_dim});
        k = mlx::core::reshape(k, {B, L, kv_heads, head_dim});
        v = mlx::core::reshape(v, {B, L, kv_heads, head_dim});
        
        if (weights.find(prefix + ".q_norm.weight") != weights.end()) {
            q = rms_norm_no_weight(q, head_dim);
            auto w = mlx::core::reshape(mlx::core::astype(weights.at(prefix + ".q_norm.weight"), mlx::core::bfloat16), {1, 1, 1, -1});
            q = mlx::core::multiply(mlx::core::astype(q, mlx::core::bfloat16), w);
        }
        if (weights.find(prefix + ".k_norm.weight") != weights.end()) {
            k = rms_norm_no_weight(k, head_dim);
            auto w = mlx::core::reshape(mlx::core::astype(weights.at(prefix + ".k_norm.weight"), mlx::core::bfloat16), {1, 1, 1, -1});
            k = mlx::core::multiply(mlx::core::astype(k, mlx::core::bfloat16), w);
        }
        v = rms_norm_no_weight(v, head_dim);
        
        q = mlx::core::transpose(q, {0, 2, 1, 3});
        k = mlx::core::transpose(k, {0, 2, 1, 3});
        v = mlx::core::transpose(v, {0, 2, 1, 3});
        
        int offset = 0;
        if (kv_cache.size() <= static_cast<size_t>(layer_idx)) {
            kv_cache.resize(num_layers, mlx::core::array(0.0f));
        }
        if (kv_cache[layer_idx].size() > 1) {
            offset = kv_cache[layer_idx].shape(2);
        }

        // RoPE Schedule for Polytope Gemma 4
        if (is_full_attention) {
            // Proportional RoPE for full attention layers
            // Gemma 2/4 uses head_dim = 256, partial_rotary_factor = 0.25
            int rope_dim = static_cast<int>(head_dim * 0.25f); // 64
            int rope_theta = 1000000;
            
            auto exponents = mlx::core::divide(mlx::core::arange(0.0f, static_cast<float>(rope_dim), 2.0f, mlx::core::float32), mlx::core::array(static_cast<float>(head_dim)));
            
            auto freqs_base = mlx::core::power(mlx::core::array(static_cast<float>(rope_theta)), exponents);
            
            auto pad_size = (head_dim - rope_dim) / 2;
            auto pad = mlx::core::full({pad_size}, std::numeric_limits<float>::infinity(), mlx::core::float32);
            
            auto freqs = mlx::core::concatenate({freqs_base, pad});
            
            std::optional<float> no_base = std::nullopt;
            
            q = mlx::core::fast::rope(q, head_dim, false, no_base, 1.0f, offset, freqs);
            k = mlx::core::fast::rope(k, head_dim, false, no_base, 1.0f, offset, freqs);
        } else { // sliding_attention
            std::optional<float> base = 10000.0f;
            std::optional<mlx::core::array> freqs = std::nullopt;
            
            q = mlx::core::fast::rope(q, head_dim, false, base, 1.0f, offset, freqs);
            k = mlx::core::fast::rope(k, head_dim, false, base, 1.0f, offset, freqs);
        }
        
        mlx::core::eval({q, k});
        q = mlx::core::contiguous(q);
        k = mlx::core::contiguous(k);
        
        if (kv_cache[layer_idx].size() == 1) {
            auto kv_combined = mlx::core::concatenate({k, v}, /*axis=*/-1);
            kv_cache[layer_idx] = kv_combined;
        } else {
            auto prev_kv = kv_cache[layer_idx];
            auto kv_combined = mlx::core::concatenate({k, v}, /*axis=*/-1);
            kv_cache[layer_idx] = mlx::core::concatenate({prev_kv, kv_combined}, /*axis=*/2);
            auto full_kv = kv_cache[layer_idx];
            k = mlx::core::slice(full_kv, {0, 0, 0, 0}, {full_kv.shape(0), full_kv.shape(1), full_kv.shape(2), head_dim});
            v = mlx::core::slice(full_kv, {0, 0, 0, head_dim}, {full_kv.shape(0), full_kv.shape(1), full_kv.shape(2), full_kv.shape(3)});
        }
        
        int num_kv_groups = q_heads / kv_heads;
        std::optional<mlx::core::array> mask = std::nullopt;
        int L_q = q.shape(2);
        int L_k = k.shape(2);
        if (L_q > 1) {
            auto causal = mlx::core::full({L_q, L_k}, -1e9f, mlx::core::float32);
            causal = mlx::core::triu(causal, 1);
            if ((layer_idx + 1) % 6 != 0) {
                int sliding_window = 4096;
                auto banded = mlx::core::full({L_q, L_k}, -1e9f, mlx::core::float32);
                banded = mlx::core::tril(banded, -sliding_window);
                causal = mlx::core::add(causal, banded);
            }
            mask = mlx::core::astype(causal, q.dtype());
        }
        
        auto q_per_head = mlx::core::contiguous(q); // q is already [B, q_heads, L_q, head_dim]
        auto k_per_head = mlx::core::contiguous(k); // k is already [B, kv_heads, L_k, head_dim]
        auto v_per_head = mlx::core::contiguous(v); // v is already [B, kv_heads, L_k, head_dim]
        
        if (layer_idx == 0) {
            auto q_var = mlx::core::astype(mlx::core::var(q_per_head), mlx::core::float32);
            auto k_var = mlx::core::astype(mlx::core::var(k_per_head), mlx::core::float32);
            auto v_var = mlx::core::astype(mlx::core::var(v_per_head), mlx::core::float32);
            
            auto q_sum = mlx::core::astype(mlx::core::sum(q_per_head), mlx::core::float32);
            auto k_sum = mlx::core::astype(mlx::core::sum(k_per_head), mlx::core::float32);
            auto v_sum = mlx::core::astype(mlx::core::sum(v_per_head), mlx::core::float32);
            
            auto q_max = mlx::core::astype(mlx::core::max(q_per_head), mlx::core::float32);
            auto k_max = mlx::core::astype(mlx::core::max(k_per_head), mlx::core::float32);
            auto v_max = mlx::core::astype(mlx::core::max(v_per_head), mlx::core::float32);
            
            mlx::core::eval({q_var, k_var, v_var, q_sum, k_sum, v_sum, q_max, k_max, v_max});
            std::cout << "[DEBUG] Layer 0 q var: " << q_var.item<float>() << " sum: " << q_sum.item<float>() << " max: " << q_max.item<float>() << std::endl;
            std::cout << "[DEBUG] Layer 0 k var: " << k_var.item<float>() << " sum: " << k_sum.item<float>() << " max: " << k_max.item<float>() << std::endl;
            std::cout << "[DEBUG] Layer 0 v var: " << v_var.item<float>() << " sum: " << v_sum.item<float>() << " max: " << v_max.item<float>() << std::endl;
        }
        
        auto out = mlx::core::fast::scaled_dot_product_attention(q_per_head, k_per_head, v_per_head, 1.0f, "", mask);
        out = mlx::core::transpose(out, {0, 2, 1, 3});
        out = mlx::core::reshape(out, {B, L, q_heads * head_dim});
        
        return flexible_matmul(out, prefix + ".o_proj");
    }

    mlx::core::array mlx_native_gelu(const mlx::core::array& x) {
        // Exact GELU: 0.5 * x * (1 + erf(x / sqrt(2)))
        auto constant_half = mlx::core::array(0.5f, x.dtype());
        auto constant_one  = mlx::core::array(1.0f, x.dtype());
        
        // 1 / sqrt(2) ≈ 0.7071067811865476
        auto inv_sqrt_2    = mlx::core::array(0.7071067811865476f, x.dtype()); 
        
        auto inner = mlx::core::multiply(x, inv_sqrt_2);
        auto erf_calculated = mlx::core::erf(inner); // Native MLX C++ API support
        
        auto bracket = mlx::core::add(constant_one, erf_calculated);
        auto half_x = mlx::core::multiply(x, constant_half);
        
        return mlx::core::multiply(half_x, bracket);
    }

    mlx::core::array gelu_pytorch_tanh(const mlx::core::array& x) {
        // 0.5 * x * (1 + tanh(sqrt(2/pi) * (x + 0.044715 * x^3)))
        auto x3 = mlx::core::multiply(x, mlx::core::square(x));
        auto scaled_x3 = mlx::core::multiply(x3, mlx::core::array(0.044715f));
        auto inner = mlx::core::add(x, scaled_x3);
        auto sqrt_2_over_pi = mlx::core::array(0.7978845608028654f);
        auto tanh_arg = mlx::core::multiply(sqrt_2_over_pi, inner);
        auto tanh_val = mlx::core::tanh(tanh_arg);
        auto one_plus_tanh = mlx::core::add(mlx::core::array(1.0f), tanh_val);
        auto half_x = mlx::core::multiply(x, mlx::core::array(0.5f));
        return mlx::core::multiply(half_x, one_plus_tanh);
    }

    mlx::core::array mlp(const mlx::core::array& x, int layer_idx) {
        std::string prefix = "language_model.model.layers." + std::to_string(layer_idx) + ".mlp";
        auto gate = flexible_matmul(x, prefix + ".gate_proj");
        auto up = flexible_matmul(x, prefix + ".up_proj");
        
        auto activated = gelu_pytorch_tanh(gate); 
        auto intermediate = mlx::core::multiply(activated, up);
        
        if (layer_idx == 0) {
            mlx::core::eval({gate, up, activated, intermediate});
            auto gate_var = mlx::core::astype(mlx::core::var(gate, std::vector<int>{-1}), mlx::core::float32);
            auto up_var = mlx::core::astype(mlx::core::var(up, std::vector<int>{-1}), mlx::core::float32);
            auto act_var = mlx::core::astype(mlx::core::var(activated, std::vector<int>{-1}), mlx::core::float32);
            auto int_var = mlx::core::astype(mlx::core::var(intermediate, std::vector<int>{-1}), mlx::core::float32);
            mlx::core::eval({gate_var, up_var, act_var, int_var});
            std::cout << "[DEBUG] Layer 0 gate var: " << mlx::core::mean(gate_var).item<float>() << std::endl;
            std::cout << "[DEBUG] Layer 0 up var: " << mlx::core::mean(up_var).item<float>() << std::endl;
            std::cout << "[DEBUG] Layer 0 activated var: " << mlx::core::mean(act_var).item<float>() << std::endl;
            std::cout << "[DEBUG] Layer 0 intermediate var: " << mlx::core::mean(int_var).item<float>() << std::endl;
        }
        
        return flexible_matmul(intermediate, prefix + ".down_proj");
    }

public:
    GemmaModel(const std::string& model_dir) {
        std::cout << "[C++ MLX Core] Initializing Polytope Gemma architecture from " << model_dir << "..." << std::endl;
        
        if (fs::exists(model_dir)) {
            for (const auto& entry : fs::directory_iterator(model_dir)) {
                if (entry.path().extension() == ".safetensors") {
                    std::cout << "[C++ MLX Core] Loading shard: " << entry.path().filename().string() << std::endl;
                    
                    try {
                        auto loaded = mlx::core::load_safetensors(entry.path().string());
                        for (const auto& [name, array] : loaded.first) {
                            // Modality Bypassing for Text Phase 3
                            if (name.find("audio_tower") == 0 || name.find("embed_vision") == 0 || name.find("optiq_vision") == 0) {
                                continue;
                            }
                            
                            weights.insert_or_assign(name, array);
                            
                            if (name.find("language_model.model.layers.") == 0) {
                                size_t dot_pos = name.find(".", 28);
                                if (dot_pos != std::string::npos) {
                                    int layer_id = std::stoi(name.substr(28, dot_pos - 28));
                                    num_layers = std::max(num_layers, layer_id + 1);
                                }
                            }
                        }
                    } catch (const std::exception& e) {
                        std::cerr << "[C++ MLX Core] Error loading shard: " << e.what() << std::endl;
                    }
                }
            }
        }
        
        std::cout << "[C++ MLX Core] Successfully loaded " << weights.size() << " Text tensors." << std::endl;
        std::cout << "[C++ MLX Core] Inferred Layer Count: " << num_layers << std::endl;
        
        if (num_layers == 0) {
            num_layers = 2; // Safe fallback
        }
    }

    mlx::core::array forward(const mlx::core::array& x, std::vector<mlx::core::array>& kv_cache) {
        auto it = weights.find("language_model.model.embed_tokens.weight");
        if (it == weights.end()) {
            std::cout << "[FATAL] EMBED WEIGHTS NOT FOUND IN MAP!" << std::endl;
        } else {
            auto w_var = mlx::core::astype(mlx::core::mean(mlx::core::var(it->second, std::vector<int>{-1})), mlx::core::float32);
            mlx::core::eval({w_var});
            std::cout << "[DEBUG] Full Embed weight variance: " << w_var.item<float>() << std::endl;
            
            auto w_max = mlx::core::astype(mlx::core::max(it->second), mlx::core::float32);
            auto w_min = mlx::core::astype(mlx::core::min(it->second), mlx::core::float32);
            mlx::core::eval({w_max, w_min});
            std::cout << "[DEBUG] Full Embed weight max: " << w_max.item<float>() << ", min: " << w_min.item<float>() << std::endl;
        }
        
        mlx::core::array h = (it != weights.end()) 
            ? mlx::core::take(it->second, x, 0)
            : mlx::core::zeros({x.shape(0), 1, 2048}, mlx::core::float32);
            
        // Ensure h has shape (B, L, D) -> (1, L, D)
        h = mlx::core::reshape(h, {x.shape(0), x.shape(1), -1});
        
        // Scale embeddings by sqrt(hidden_dim) for ALL passes
        // We removed the in-memory scaling, so we MUST dynamically scale here!
        h = mlx::core::multiply(h, mlx::core::array(std::sqrt(5376.0f), h.dtype()));
        
        h = mlx::core::astype(h, mlx::core::bfloat16);
        
        mlx::core::eval({h});
        auto h_f32_init = mlx::core::astype(h, mlx::core::float32);
        auto h_var_init = mlx::core::astype(mlx::core::mean(mlx::core::var(h_f32_init, std::vector<int>{-1})), mlx::core::float32);
        mlx::core::eval({h_var_init});
        std::cout << "[DEBUG] Embed raw variance entering Layer 0: " << h_var_init.item<float>() << std::endl;

        for (int i = 0; i < num_layers; ++i) {
            std::string layer_prefix = "language_model.model.layers." + std::to_string(i);
            
            // =========================================================================
            // SUB-LAYER 1: ATTENTION PIPELINE (SEQUENTIAL)
            // =========================================================================
            // 1. Pre-Attention Input Normalization (Using raw baked weights, NO +1.0f)
            auto h_attn_norm = rms_norm(h, layer_prefix + ".input_layernorm.weight"); 
            
            // 2. Multi-Head Attention Kernels
            auto attn_raw = attention(h_attn_norm, i, kv_cache);
            
            // 3. Post-Attention Scaling Bottleneck
            auto attn_scaled = rms_norm(attn_raw, layer_prefix + ".post_attention_layernorm.weight");
            
            // 4. Update the Residual Stream sequentially
            h = mlx::core::add(h, attn_scaled);
            
            // =========================================================================
            // SUB-LAYER 2: FEED-FORWARD NETWORK PIPELINE (SEQUENTIAL)
            // =========================================================================
            // 5. Pre-FFN Normalization using the newly updated 'h' state
            auto h_ffn_norm = rms_norm(h, layer_prefix + ".pre_feedforward_layernorm.weight");
            
            // 6. Execute MLP blocks
            auto mlp_raw = mlp(h_ffn_norm, i);
            
            // 7. Post-FFN Scaling Bottleneck
            auto mlp_scaled = rms_norm(mlp_raw, layer_prefix + ".post_feedforward_layernorm.weight");
            
            // 8. Final Block Update to the Residual Stream
            h = mlx::core::add(h, mlp_scaled);
            
            if (weights.find(layer_prefix + ".layer_scalar") != weights.end()) {
                auto l_scalar = mlx::core::reshape(mlx::core::astype(weights.at(layer_prefix + ".layer_scalar"), mlx::core::bfloat16), {1, 1, 1});
                h = mlx::core::multiply(mlx::core::astype(h, mlx::core::bfloat16), l_scalar);
            }
            
            if (i == 0) {
                mlx::core::eval({h, attn_scaled, mlp_scaled, mlp_raw, attn_raw});
                auto h_var = mlx::core::astype(mlx::core::var(h, std::vector<int>{-1}), mlx::core::float32);
            }
        }
        
        // Preserve batch dimension for final output: (1, L, D)
        
        // Final norm WITH NO +1.0f (Weights are already shifted in checkpoint)
        auto w = weights.at("language_model.model.norm.weight");
        auto w_bf16 = mlx::core::astype(w, mlx::core::bfloat16);
        
        h = mlx::core::fast::rms_norm(h, w_bf16, 1e-6f);
        
        mlx::core::eval({h});
        mlx::core::synchronize();
        
        auto h_f32_final = mlx::core::astype(h, mlx::core::float32);
        auto mean_h_final = mlx::core::mean(h_f32_final);
        auto variance_h_final = mlx::core::mean(mlx::core::square(mlx::core::subtract(h_f32_final, mean_h_final)));
        auto h_max = mlx::core::max(h_f32_final);
        auto h_min = mlx::core::min(h_f32_final);
        mlx::core::eval({variance_h_final, h_max, h_min});
        mlx::core::synchronize();
        std::cout << "[DEBUG] final h var: " << variance_h_final.item<float>() 
                  << " | max: " << h_max.item<float>() 
                  << " | min: " << h_min.item<float>() << std::endl;
        
        mlx::core::array raw_logits = mlx::core::array(0.0f);
        // Check if lm_head exists or if we use tied embeddings
        mlx::core::array embed_weights = mlx::core::array(0.0f);
        if (weights.find("language_model.lm_head.weight") != weights.end()) {
            embed_weights = weights.at("language_model.lm_head.weight");
        } else if (weights.find("language_model.model.embed_tokens.weight") != weights.end()) {
            embed_weights = weights.at("language_model.model.embed_tokens.weight");
        } else {
            return mlx::core::zeros({h.shape(0), 1, 262144}, mlx::core::float32);
        }
        
        // The weight matrix is [vocab_size, hidden_dim].
        // To project [batch, seq, hidden_dim] -> [batch, seq, vocab_size],
        // we transpose the weight matrix to [hidden_dim, vocab_size].
        auto serialized_weights = mlx::core::contiguous(mlx::core::transpose(embed_weights, {1, 0}));
        
        // Cast to matching types
        auto h_bf16 = mlx::core::astype(h, mlx::core::bfloat16);
        auto serialized_w_bf16 = mlx::core::astype(serialized_weights, mlx::core::bfloat16);
        
        raw_logits = mlx::core::matmul(h_bf16, serialized_w_bf16);
        
        // 3. THE FIX: Remove the manual 1.0f / sqrt(5376.0f) scaler entirely!
        // Gemma 2/4 architectures do not scale by inverse hidden dimension at the output.
        // Instead, verify if your config targets a specific 'logit_scale' float (often 1.0f or raw).
        float native_logit_scale = 1.0f; 
        auto scaled_logits = mlx::core::multiply(raw_logits, mlx::core::array(native_logit_scale, raw_logits.dtype()));
        
        // 4. Force Tanh Softcapping Clamp using the standard 30.0f configuration
        // With raw_logits allowed to naturally scale to its true bounds, 
        // a Max Logit of 15.9375 will seamlessly map through the Tanh activation:
        // tanh(15.9375 / 30.0) = tanh(0.53125) = 0.486
        // 30.0f * 0.486 = 14.58 (Perfect structural dynamic resolution!)
        float softcap_val = 30.0f; 
        auto final_logits = mlx::core::multiply(
            mlx::core::array(softcap_val), 
            mlx::core::tanh(mlx::core::divide(scaled_logits, mlx::core::array(softcap_val)))
        );
        
        return mlx::core::astype(final_logits, mlx::core::float32);
    }
};

} // namespace alluci
