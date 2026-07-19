#pragma once

#include <mlx/mlx.h>
#include <mlx/fast.h>
#include <string>
#include <unordered_map>
#include <filesystem>
#include <vector>
#include <optional>
#include <fstream>
#include <iostream>
#include <algorithm>
#include <cmath>
#include <utility>
#include <nlohmann/json.hpp>

using json = nlohmann::json;

namespace fs = std::filesystem;

namespace alluci {

struct ModelArchitectureConfig {
    int num_hidden_layers = 0;
    int sliding_window = 4096;
    float rope_theta_global = 1000000.0f;
    float rope_theta_local = 10000.0f;
    
    // Quantization Specs
    int global_group_size = 64;
    int global_bits = 4;
    bool is_quantized = false;
    bool enable_moe = false;
    int num_experts = 128;
    int num_experts_per_tok = 2;
};

struct QuantizedWeightDescriptor {
    mlx::core::array weight;
    mlx::core::array scales;
    mlx::core::array biases;
    int group_size = 64;  
    int bits = 4;         
    bool has_bias = false;
    
    QuantizedWeightDescriptor(mlx::core::array w, mlx::core::array s) 
        : weight(w), scales(s), biases(mlx::core::zeros({1}, mlx::core::float32)) {}
};

struct KVCacheRingBuffer {
    mlx::core::array k_cache = mlx::core::zeros({1}, mlx::core::float32);
    mlx::core::array v_cache = mlx::core::zeros({1}, mlx::core::float32);
    
    int head_index = 0;
    int cumulative_tokens = 0;
    int sliding_window = 0;
    bool is_preallocated = false;
};

inline std::pair<mlx::core::array, mlx::core::array> orchestrate_kv_allocation(
    KVCacheRingBuffer& layer_buffer,
    const mlx::core::array& new_k,
    const mlx::core::array& new_v,
    bool is_global_layer,
    const ModelArchitectureConfig& model_cfg
) {
    int batch = new_k.shape(0);
    int kv_heads = new_k.shape(1);
    int incoming_len = new_k.shape(2);
    int head_dim = new_k.shape(3);

    if (is_global_layer) {
        if (!layer_buffer.is_preallocated) {
            layer_buffer.k_cache = new_k;
            layer_buffer.v_cache = new_v;
            layer_buffer.is_preallocated = true;
        } else {
            layer_buffer.k_cache = mlx::core::concatenate({layer_buffer.k_cache, new_k}, /*axis=*/2);
            layer_buffer.v_cache = mlx::core::concatenate({layer_buffer.v_cache, new_v}, /*axis=*/2);
        }
        layer_buffer.cumulative_tokens += incoming_len;
        return {layer_buffer.k_cache, layer_buffer.v_cache};
    }

    int window = model_cfg.sliding_window;

    if (!layer_buffer.is_preallocated) {
        layer_buffer.k_cache = mlx::core::zeros({batch, kv_heads, window, head_dim}, new_k.dtype());
        layer_buffer.v_cache = mlx::core::zeros({batch, kv_heads, window, head_dim}, new_v.dtype());
        layer_buffer.sliding_window = window;
        layer_buffer.is_preallocated = true;
    }

    std::vector<int> indices_raw(incoming_len);
    for (int i = 0; i < incoming_len; ++i) {
        indices_raw[i] = (layer_buffer.head_index + i) % window;
    }
    
    auto scatter_indices = mlx::core::array(indices_raw.data(), {incoming_len}, mlx::core::int32);

    layer_buffer.k_cache = mlx::core::scatter(layer_buffer.k_cache, scatter_indices, new_k, /*axis=*/2);
    layer_buffer.v_cache = mlx::core::scatter(layer_buffer.v_cache, scatter_indices, new_v, /*axis=*/2);

    layer_buffer.head_index = (layer_buffer.head_index + incoming_len) % window;
    layer_buffer.cumulative_tokens += incoming_len;

    if (layer_buffer.cumulative_tokens < window) {
        auto valid_k = mlx::core::slice(layer_buffer.k_cache, {0, 0, 0, 0}, {batch, kv_heads, layer_buffer.cumulative_tokens, head_dim});
        auto valid_v = mlx::core::slice(layer_buffer.v_cache, {0, 0, 0, 0}, {batch, kv_heads, layer_buffer.cumulative_tokens, head_dim});
        return {valid_k, valid_v};
    }

    return {layer_buffer.k_cache, layer_buffer.v_cache};
}

// =========================================================================
// STRUCTURED LOGIT MASKING (CFG / AUTOMATED TOOL SAFEGUARD)
// =========================================================================
inline mlx::core::array apply_grammatical_safeguards(
    const mlx::core::array& final_logits,       
    const std::vector<int>& allowed_token_ids 
) {
    auto penalty_mask = mlx::core::full(
        final_logits.shape(), 
        -10000.0f, 
        final_logits.dtype()
    );

    int valid_count = allowed_token_ids.size();
    auto valid_indices = mlx::core::array(allowed_token_ids.data(), {valid_count}, mlx::core::int32);
    auto zero_modifiers = mlx::core::zeros({valid_count}, final_logits.dtype());

    // Use the last axis for scattering
    int target_axis = final_logits.ndim() - 1;
    penalty_mask = mlx::core::scatter(penalty_mask, valid_indices, zero_modifiers, target_axis);

    return mlx::core::add(final_logits, penalty_mask);
}

class GemmaModel {
private:
    std::unordered_map<std::string, mlx::core::array> weights;
    std::unordered_map<std::string, QuantizedWeightDescriptor> model_weight_registry;
    ModelArchitectureConfig model_cfg;
    int vocab_size = 262144;
    int hidden_size = 5376;
    int num_layers = 60;

    void parse_model_config(const std::string& config_path) {
        std::ifstream file(config_path);
        if (!file.is_open()) {
            std::cout << "[WARNING] config.json not found at " << config_path << ", using defaults." << std::endl;
            return;
        }

        json cfg;
        try {
            file >> cfg;
            json actual_cfg = cfg.contains("text_config") ? cfg["text_config"] : cfg;

            model_cfg.num_hidden_layers = actual_cfg.value("num_hidden_layers", 60);
            model_cfg.sliding_window = actual_cfg.value("sliding_window_size", 4096);
            
            if (actual_cfg.contains("num_experts")) {
                model_cfg.enable_moe = true;
                model_cfg.num_experts = actual_cfg.value("num_experts", 128);
                model_cfg.num_experts_per_tok = actual_cfg.value("num_experts_per_tok", 2);
            } else {
                model_cfg.enable_moe = actual_cfg.value("enable_moe_block", false);
            }

            if (actual_cfg.contains("rope_parameters")) {
                auto rope = actual_cfg["rope_parameters"];
                if (rope.contains("full_attention")) {
                    model_cfg.rope_theta_global = rope["full_attention"].value("rope_theta", 1000000.0f);
                }
                if (rope.contains("sliding_attention")) {
                    model_cfg.rope_theta_local = rope["sliding_attention"].value("rope_theta", 10000.0f);
                }
            } else if (actual_cfg.contains("rope_theta")) {
                model_cfg.rope_theta_global = actual_cfg.value("rope_theta", 10000.0f);
                model_cfg.rope_theta_local = actual_cfg.value("rope_theta", 10000.0f);
            }

            // Quantization is usually at the top level
            if (cfg.contains("quantization")) {
                model_cfg.is_quantized = true;
                auto quant = cfg["quantization"];
                model_cfg.global_bits = quant.value("bits", 4);
                model_cfg.global_group_size = quant.value("group_size", 64);
            }
        } catch (const std::exception& e) {
            std::cerr << "[WARNING] Error parsing config.json: " << e.what() << std::endl;
        }
    }

    mlx::core::array adaptive_quantized_matmul(
        const mlx::core::array& x, 
        const std::string& weight_key,
        bool transpose = true
    ) {
        auto it = model_weight_registry.find(weight_key);
        if (it != model_weight_registry.end()) {
            const auto& desc = it->second;
            if (desc.has_bias) {
                return mlx::core::quantized_matmul(
                    x, desc.weight, desc.scales, desc.biases, transpose, desc.group_size, desc.bits
                );
            } else {
                return mlx::core::quantized_matmul(
                    x, desc.weight, desc.scales, mlx::core::zeros({1}, mlx::core::float32), transpose, desc.group_size, desc.bits
                );
            }
        }
        
        // Dense fallback
        if (weights.find(weight_key + ".weight") == weights.end()) {
            return x; // Identity fallback
        }
        auto w = weights.at(weight_key + ".weight");
        return mlx::core::matmul(x, transpose ? mlx::core::transpose(w) : w);
    }

    mlx::core::array sparse_moe_routing(
        const mlx::core::array& h,
        const std::string& moe_prefix,
        int layer_idx,
        const ModelArchitectureConfig& cfg
    ) {
        int num_experts = cfg.num_experts;
        int top_k = cfg.num_experts_per_tok;
        
        int batch_size = h.shape(0);
        int seq_len = h.shape(1);
        int hidden_dim = h.shape(2);

        auto flat_h = mlx::core::reshape(h, {batch_size * seq_len, hidden_dim});
        auto router_logits = adaptive_quantized_matmul(flat_h, moe_prefix + ".gate");
        auto routing_probs = mlx::core::softmax(router_logits, -1);

        auto neg_probs = mlx::core::negative(routing_probs);
        auto partitioned = mlx::core::argpartition(neg_probs, top_k - 1, -1);
        auto topk_indices = mlx::core::slice(partitioned, {0, 0}, {batch_size * seq_len, top_k});
        auto topk_weights = mlx::core::take_along_axis(routing_probs, topk_indices, -1);

        auto weight_sum = mlx::core::sum(topk_weights, -1, /* keepdims = */ true);
        topk_weights = mlx::core::divide(topk_weights, weight_sum);

        auto output_flat = mlx::core::zeros_like(flat_h);

        for (int k = 0; k < top_k; ++k) {
            auto current_expert_indices = mlx::core::slice(topk_indices, {0, k}, {batch_size * seq_len, k + 1});
            auto current_weights = mlx::core::slice(topk_weights, {0, k}, {batch_size * seq_len, k + 1});

            for (int ex_idx = 0; ex_idx < num_experts; ++ex_idx) {
                auto expert_match_mask = mlx::core::equal(current_expert_indices, mlx::core::array(ex_idx));
                
                auto match_count = mlx::core::sum(expert_match_mask).item<int>();
                if (match_count == 0) continue; 

                auto mask_int = mlx::core::astype(expert_match_mask, mlx::core::int32);
                auto sorted_idx = mlx::core::argsort(mask_int);
                auto token_indices = mlx::core::slice(sorted_idx, {batch_size * seq_len - match_count}, {batch_size * seq_len});
                
                auto gathered_tokens = mlx::core::take(flat_h, token_indices, 0);

                std::string expert_prefix = moe_prefix + ".experts." + std::to_string(ex_idx);

                auto gate_out = adaptive_quantized_matmul(gathered_tokens, expert_prefix + ".gate_proj");
                auto up_out   = adaptive_quantized_matmul(gathered_tokens, expert_prefix + ".up_proj");
                
                auto gated_activated = mlx_native_gelu(gate_out);
                auto intermediate    = mlx::core::multiply(gated_activated, up_out);
                
                auto expert_down_out = adaptive_quantized_matmul(intermediate, expert_prefix + ".down_proj");

                auto expert_weights = mlx::core::take(current_weights, token_indices, 0);
                auto scaled_expert_out = mlx::core::multiply(expert_down_out, expert_weights);

                output_flat = mlx::core::scatter_add(output_flat, token_indices, scaled_expert_out, 0);
            }
        }
        return mlx::core::reshape(output_flat, {batch_size, seq_len, hidden_dim});
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
        
        mlx::core::array attention(
        const mlx::core::array& x, 
        int layer_idx, 
        std::vector<KVCacheRingBuffer>& global_kv_pipeline_registry,
        const ModelArchitectureConfig& cfg,
        const std::string& layer_prefix = ""
    ) {
        std::string prefix = layer_prefix.empty() ? "language_model.model.layers." + std::to_string(layer_idx) + ".self_attn" : layer_prefix + ".self_attn";
        bool is_full_attention = (layer_idx % 6 == 5);
        auto q = adaptive_quantized_matmul(x, prefix + ".q_proj");
        auto k = adaptive_quantized_matmul(x, prefix + ".k_proj");
        mlx::core::array v = mlx::core::zeros({1}, mlx::core::float32); // dummy init
        if (is_full_attention) {
            v = k; 
        } else {
            v = adaptive_quantized_matmul(x, prefix + ".v_proj");
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
        if (global_kv_pipeline_registry.size() <= static_cast<size_t>(layer_idx)) {
            global_kv_pipeline_registry.resize(num_layers);
        }
        offset = global_kv_pipeline_registry[layer_idx].cumulative_tokens;

        // RoPE Schedule for Polytope Gemma 4
        // 1. Establish the explicit Gemma 4 dynamic layer stride (5:1 ratio)
        bool is_global_layer = ((layer_idx + 1) % 6 == 0);
        
        // Dynamically parse properties out of the verified JSON config struct
        float current_rope_theta = is_global_layer ? cfg.rope_theta_global : cfg.rope_theta_local;
        int current_sliding_window = is_global_layer ? -1 : cfg.sliding_window;

        int current_seq_len = x.shape(1); // Extract sequence layout dimension

        int rope_dims = head_dim;
        if (is_global_layer) {
            rope_dims = static_cast<int>(head_dim * 0.25f);
        }

        std::optional<float> base = current_rope_theta;
        std::optional<mlx::core::array> freqs = std::nullopt;
        
        q = mlx::core::fast::rope(q, rope_dims, false, base, 1.0f, offset, freqs);
        k = mlx::core::fast::rope(k, rope_dims, false, base, 1.0f, offset, freqs);
        
        mlx::core::eval({q, k});
        q = mlx::core::contiguous(q);
        k = mlx::core::contiguous(k);
        
        auto kv_pair = orchestrate_kv_allocation(
            global_kv_pipeline_registry[layer_idx],
            k, v,
            is_global_layer,
            cfg
        );
        k = kv_pair.first;
        v = kv_pair.second;
        
        int num_kv_groups = q_heads / kv_heads;
        std::optional<mlx::core::array> layer_mask = std::nullopt;
        int L_q = q.shape(2);
        int L_k = k.shape(2);
        if (L_q > 1) {
            auto mask = mlx::core::triu(mlx::core::ones({L_q, L_k}, q.dtype()), 1);
            auto inf_mask = mlx::core::multiply(mask, mlx::core::array(-10000.0f, q.dtype()));

            // Enforce the banded local sliding limit if this layer is not global
            if (!is_global_layer && current_sliding_window > 0 && L_q > current_sliding_window) {
                auto local_band = mlx::core::triu(mlx::core::ones({L_q, L_k}, q.dtype()), -(current_sliding_window - 1));
                auto outside_window = mlx::core::subtract(mlx::core::array(1.0f, q.dtype()), local_band);
                auto outside_inf = mlx::core::multiply(outside_window, mlx::core::array(-10000.0f, q.dtype()));
                
                inf_mask = mlx::core::minimum(inf_mask, outside_inf);
            }
            layer_mask = inf_mask;
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
        
        mlx::core::array attn_out = mlx::core::zeros({1}, mlx::core::float32);
        if (layer_mask.has_value()) {
            attn_out = mlx::core::fast::scaled_dot_product_attention(
                q_per_head, k_per_head, v_per_head, 0.0625f, "", layer_mask.value());
        } else {
            attn_out = mlx::core::fast::scaled_dot_product_attention(
                q_per_head, k_per_head, v_per_head, 0.0625f);
        }
        attn_out = mlx::core::transpose(attn_out, {0, 2, 1, 3});
        attn_out = mlx::core::reshape(attn_out, {B, L, q_heads * head_dim});
        
        return adaptive_quantized_matmul(attn_out, prefix + ".o_proj");
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

    mlx::core::array mlp(const mlx::core::array& x, int layer_idx, const std::string& layer_prefix = "") {
        std::string prefix = layer_prefix.empty() ? "language_model.model.layers." + std::to_string(layer_idx) + ".mlp" : layer_prefix + ".mlp";
        auto gate = adaptive_quantized_matmul(x, prefix + ".gate_proj");
        auto up = adaptive_quantized_matmul(x, prefix + ".up_proj");
        
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
        
        return adaptive_quantized_matmul(intermediate, prefix + ".down_proj");
    }

public:
    GemmaModel(const std::string& model_dir) {
        std::cout << "[C++ MLX Core] Initializing Polytope Gemma architecture from " << model_dir << "..." << std::endl;
        
        std::string config_path = (fs::path(model_dir) / "config.json").string();
        parse_model_config(config_path);
        
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
        
        // Populate model_weight_registry for quantized models
        if (model_cfg.is_quantized) {
            for (const auto& [name, array] : weights) {
                if (name.find(".weight") != std::string::npos) {
                    std::string key = name.substr(0, name.length() - 7);
                    if (weights.find(key + ".scales") != weights.end()) {
                        QuantizedWeightDescriptor desc(array, weights.at(key + ".scales"));
                        if (weights.find(key + ".biases") != weights.end()) {
                            desc.biases = weights.at(key + ".biases");
                            desc.has_bias = true;
                        }
                        desc.bits = model_cfg.global_bits;
                        desc.group_size = model_cfg.global_group_size;
                        
                        // Handle the explicit 26B MoE mixed precision override exception:
                        if (key.find(".router.proj") != std::string::npos) {
                            desc.bits = 8;
                            desc.group_size = 64; 
                        }
                        
                        model_weight_registry.insert_or_assign(key, desc);
                    }
                }
            }
        }
        
        std::cout << "[C++ MLX Core] Successfully loaded " << weights.size() << " Text tensors." << std::endl;
        std::cout << "[C++ MLX Core] Inferred Layer Count: " << num_layers << std::endl;
        std::cout << "[C++ MLX Core] Configured layers: " << model_cfg.num_hidden_layers << std::endl;
        
        if (model_cfg.num_hidden_layers > 0) {
            num_layers = model_cfg.num_hidden_layers;
        } else if (num_layers == 0) {
            num_layers = 2; // Safe fallback
        }
    }

    mlx::core::array forward_pipeline(
        const mlx::core::array& x, 
        std::vector<KVCacheRingBuffer>& global_kv_pipeline_registry,
        const std::string& prefix = ""
    ) {
        return forward_pipeline(x, this->model_cfg, global_kv_pipeline_registry, prefix);
    }

    mlx::core::array forward_pipeline(
        const mlx::core::array& x, 
        const ModelArchitectureConfig& cfg,
        std::vector<KVCacheRingBuffer>& global_kv_pipeline_registry,
        const std::string& prefix = ""
    ) {
        std::string embed_key = prefix.empty() ? "language_model.model.embed_tokens.weight" : prefix + ".model.embed_tokens.weight";
        auto it = weights.find(embed_key);
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

        int active_layers = cfg.num_hidden_layers > 0 ? cfg.num_hidden_layers : num_layers;
        for (int i = 0; i < active_layers; ++i) {
            std::string layer_prefix = prefix.empty() ? "language_model.model.layers." + std::to_string(i) : prefix + ".model.layers." + std::to_string(i);
            
            // =========================================================================
            // SUB-LAYER 1: ATTENTION PIPELINE (SEQUENTIAL)
            // =========================================================================
            // 1. Pre-Attention Input Normalization (Using raw baked weights, NO +1.0f)
            auto h_attn_norm = rms_norm(h, layer_prefix + ".input_layernorm.weight"); 
            
            auto attn_raw = attention(h_attn_norm, i, global_kv_pipeline_registry, cfg, layer_prefix);
            
            // 3. Post-Attention Scaling Bottleneck
            auto attn_scaled = rms_norm(attn_raw, layer_prefix + ".post_attention_layernorm.weight");
            
            // 4. Update the Residual Stream sequentially
            h = mlx::core::add(h, attn_scaled);
            
            // =========================================================================
            // SUB-LAYER 2: FEED-FORWARD NETWORK PIPELINE (SEQUENTIAL)
            // =========================================================================
            // 5. Pre-FFN Normalization using the newly updated 'h' state
            auto h_ffn_norm = rms_norm(h, layer_prefix + ".pre_feedforward_layernorm.weight");
            
            mlx::core::array mlp_raw = mlx::core::zeros({1}, mlx::core::float32);
            if (cfg.enable_moe && model_weight_registry.find(layer_prefix + ".moe.gate") != model_weight_registry.end()) {
                mlp_raw = sparse_moe_routing(h_ffn_norm, layer_prefix + ".moe", i, cfg);
            } else {
                mlp_raw = mlp(h_ffn_norm, i, layer_prefix);
            }
            
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
        std::string norm_key = prefix.empty() ? "language_model.model.norm.weight" : prefix + ".model.norm.weight";
        auto w = weights.at(norm_key);
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
        return h;
    }

    mlx::core::array project_vocabulary(const mlx::core::array& h, const std::string& prefix = "") {
        mlx::core::array raw_logits = mlx::core::array(0.0f);
        mlx::core::array embed_weights = mlx::core::array(0.0f);
        
        std::string lm_head_key = prefix.empty() ? "language_model.lm_head.weight" : prefix + ".lm_head.weight";
        std::string embed_tokens_key = prefix.empty() ? "language_model.model.embed_tokens.weight" : prefix + ".model.embed_tokens.weight";
        
        if (weights.find(lm_head_key) != weights.end()) {
            embed_weights = weights.at(lm_head_key);
        } else if (weights.find(embed_tokens_key) != weights.end()) {
            embed_weights = weights.at(embed_tokens_key);
        } else {
            return mlx::core::zeros({h.shape(0), 1, 262144}, mlx::core::float32);
        }
        
        auto serialized_weights = mlx::core::contiguous(mlx::core::transpose(embed_weights, {1, 0}));
        auto h_bf16 = mlx::core::astype(h, mlx::core::bfloat16);
        auto serialized_w_bf16 = mlx::core::astype(serialized_weights, mlx::core::bfloat16);
        
        raw_logits = mlx::core::matmul(h_bf16, serialized_w_bf16);
        
        float native_logit_scale = 1.0f; 
        auto scaled_logits = mlx::core::multiply(raw_logits, mlx::core::array(native_logit_scale, raw_logits.dtype()));
        
        float softcap_val = 30.0f; 
        auto final_logits = mlx::core::multiply(
            mlx::core::array(softcap_val), 
            mlx::core::tanh(mlx::core::divide(scaled_logits, mlx::core::array(softcap_val)))
        );
        
        return mlx::core::astype(final_logits, mlx::core::float32);
    }

    mlx::core::array forward_pipeline_parallel(
        const mlx::core::array& x, 
        const ModelArchitectureConfig& cfg,
        std::vector<KVCacheRingBuffer>& global_kv_pipeline_registry,
        const std::string& prefix = ""
    ) {
        return forward_pipeline(x, cfg, global_kv_pipeline_registry, prefix);
    }
};

} // namespace alluci
