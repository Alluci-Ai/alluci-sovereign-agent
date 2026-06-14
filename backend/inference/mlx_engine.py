import asyncio
import logging
import sys
import os
from typing import AsyncGenerator, Optional, Dict, Any

# Dynamically append the CMake build path to load the native C++ PyBind11 module
# Removed C++ PyBind11 module import; will use mlx_lm for inference.


from backend.inference.profiler import HardwareProfiler

logger = logging.getLogger("MLXEngine")

class MLXEngine:
    """
    [ PPN-021 ] Native MLX Inference Singleton.
    Wraps the highly optimized C++ AlluciCognitiveEngine via PyBind11.
    """
    engine: Optional[Any] = None
    model: Optional[Any] = None
    tokenizer: Optional[Any] = None
    current_lora: Optional[str] = None
    is_loading: bool = False
    hardware_profile: Optional[Dict[str, Any]] = None
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(MLXEngine, cls).__new__(cls)
            cls._instance.engine = None
            cls._instance.model = None
            cls._instance.tokenizer = None
            cls._instance.current_lora = None
            cls._instance.is_loading = False
            cls._instance.hardware_profile = HardwareProfiler.get_system_profile()
        return cls._instance

    def load_model_sync(self):
        """Synchronously loads the MLX model and tokenizer using mlx_lm."""
        if self.model is not None:
            return

        self.is_loading = True
        try:
            if not self.hardware_profile:
                raise RuntimeError("Hardware profile not initialized.")

            # ── Alluci Polytope Local Model Routing MOAT ──
            tier = self.hardware_profile.get("tier", "TIER_4_EDGE")
            local_mapping = {
                "TIER_1_MAX": "mirror_cache/gemma-4-31b-it-4bit",
                "TIER_2_PRO": "mirror_cache/gemma-4-26B-A4B-it-OptiQ-4bit",
                "TIER_3_BASE": "mirror_cache/gemma-4-12B-it-OptiQ-4bit",
                "TIER_4_EDGE": "mirror_cache/gemma-4-e2b-it-4bit"
            }

            target_model_path = self.hardware_profile["recommended_model"]

            # Resolve absolute path to the local model folder in the project workspace
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            local_path = os.path.join(base_dir, local_mapping.get(tier, ""))

            if local_path and os.path.exists(local_path):
                target_model_path = local_path
                logger.info(f"MLXEngine: Native Alluci Polytope local model detected in cache. Routing to: {target_model_path}")
            else:
                logger.info(f"MLXEngine: Local cache not found. Fallback to HF repository: {target_model_path}")

            logger.info(f"MLXEngine: Loading MLX model from {target_model_path}...")
            # Register gemma4 to map to gemma3n and load with strict=False to ignore audio/vision weights
            import sys
            import mlx.core as mx
            import mlx.nn as nn
            import mlx_lm.models.gemma3n as gemma3n
            from mlx.utils import tree_flatten, tree_unflatten

            # --- Gemma 4 to Gemma 3n alignment monkeypatches ---

            # 1. Patch TextConfig.from_dict to preserve global_head_dim, num_global_key_value_heads, and attention_k_eq_v
            original_from_dict = gemma3n.TextConfig.from_dict
            def custom_from_dict(cls, params):
                obj = original_from_dict(params)
                setattr(obj, "global_head_dim", params.get("global_head_dim", 512))
                setattr(obj, "num_global_key_value_heads", params.get("num_global_key_value_heads", None))
                setattr(obj, "attention_k_eq_v", params.get("attention_k_eq_v", False))
                return obj
            setattr(gemma3n.TextConfig, "from_dict", classmethod(custom_from_dict))

            # 2. Laurel block initialization bypass to avoid ZeroDivisionError
            def laurel_init(self, config):
                nn.Module.__init__(self)
                self.config = config
                if config.laurel_rank > 0:
                    self.linear_left = nn.Linear(config.hidden_size, config.laurel_rank, bias=False)
                    self.linear_right = nn.Linear(config.laurel_rank, config.hidden_size, bias=False)
                    self.post_laurel_norm = nn.RMSNorm(dims=config.hidden_size, eps=config.rms_norm_eps)
            def laurel_call(self, x):
                if self.config.laurel_rank == 0:
                    return x
                laurel_x = self.linear_left(x)
                laurel_x = self.linear_right(laurel_x)
                normed_laurel_x = self.post_laurel_norm(laurel_x)
                return x + normed_laurel_x
            gemma3n.Gemma3nLaurelBlock.__init__ = laurel_init
            gemma3n.Gemma3nLaurelBlock.__call__ = laurel_call

            # 3. Proportional RoPE (p-RoPE) implementation for global layers
            class PartialRoPE:
                def __init__(self, rope_dim, head_dim, traditional, base):
                    self.rope_dim = rope_dim
                    self.head_dim = head_dim
                    self.base = base
                    i = mx.arange(0, rope_dim, 2, dtype=mx.float32)
                    inv_freq_rotated = 1.0 / (base ** (i / head_dim))
                    nope_angles = (head_dim - rope_dim) // 2
                    zeros = mx.zeros((nope_angles,), dtype=mx.float32)
                    self.inv_freq = mx.concatenate([inv_freq_rotated, zeros])
                def __call__(self, x, offset=0):
                    B, H, L, D = x.shape
                    pos = mx.arange(offset, offset + L, dtype=mx.float32)
                    angles = pos[:, None] * self.inv_freq[None, :]
                    cos = mx.cos(angles)
                    sin = mx.sin(angles)
                    cos_full = mx.concatenate([cos, cos], axis=-1)[None, None, :, :]
                    sin_full = mx.concatenate([sin, sin], axis=-1)[None, None, :, :]
                    x1, x2 = x[..., :D//2], x[..., D//2:]
                    x_rot = mx.concatenate([-x2, x1], axis=-1)
                    return x * cos_full + x_rot * sin_full

            # 4. Custom attention init mapping global layers to p-RoPE & attention_k_eq_v
            def custom_attention_init(self, config, layer_idx, is_kv_shared_layer):
                nn.Module.__init__(self)
                self.config = config
                self.is_sliding = config.layer_types[layer_idx] == "sliding_attention"
                dim = config.hidden_size
                self.n_heads = n_heads = config.num_attention_heads
                if self.is_sliding:
                    self.n_kv_heads = n_kv_heads = config.num_key_value_heads
                else:
                    self.n_kv_heads = n_kv_heads = int(getattr(config, "num_global_key_value_heads", None) or config.num_key_value_heads or 8)
                self.repeats = n_heads // n_kv_heads
                head_dim_val = config.head_dim if self.is_sliding else getattr(config, "global_head_dim", None) or config.head_dim or 256
                self.head_dim = head_dim = int(head_dim_val)
                self.layer_idx = layer_idx
                self.scale = 1.0
                self.q_proj = nn.Linear(dim, n_heads * head_dim, bias=False)
                self.k_proj = nn.Linear(dim, n_kv_heads * head_dim, bias=False)
                if getattr(config, "attention_k_eq_v", False) and not self.is_sliding:
                    self.v_proj = None
                else:
                    self.v_proj = nn.Linear(dim, n_kv_heads * head_dim, bias=False)
                self.o_proj = nn.Linear(n_heads * head_dim, dim, bias=False)
                self.q_norm = nn.RMSNorm(dims=head_dim, eps=config.rms_norm_eps)
                self.k_norm = nn.RMSNorm(dims=head_dim, eps=config.rms_norm_eps)
                self.v_norm = gemma3n.RMSNoScale(eps=config.rms_norm_eps)
                self.is_kv_shared_layer = is_kv_shared_layer
                if self.is_sliding:
                    self.rope = nn.RoPE(head_dim, traditional=False, base=config.rope_local_base_freq)
                else:
                    self.rope = PartialRoPE(rope_dim=128, head_dim=512, traditional=False, base=config.rope_theta)

            def custom_attention_call(self, x, mask=None, cache=None):
                B, L, _ = x.shape
                queries = self.q_proj(x)
                queries = queries.reshape(B, L, -1, self.head_dim)
                queries = self.q_norm(queries)
                offset = 0
                if self.is_kv_shared_layer and cache is not None:
                    keys, values = cache.state
                    offset = cache.offset
                else:
                    if cache is not None:
                        offset = cache.offset
                    if self.v_proj is None:
                        keys_proj = self.k_proj(x).reshape(B, L, -1, self.head_dim)
                        keys = self.k_norm(keys_proj)
                        keys = keys.transpose(0, 2, 1, 3)
                        keys = self.rope(keys, offset=offset)
                        values = self.v_norm(keys_proj)
                        values = values.transpose(0, 2, 1, 3)
                    else:
                        keys = self.k_proj(x).reshape(B, L, -1, self.head_dim)
                        keys = self.k_norm(keys)
                        keys = keys.transpose(0, 2, 1, 3)
                        keys = self.rope(keys, offset=offset)
                        values = self.v_proj(x).reshape(B, L, -1, self.head_dim)
                        values = self.v_norm(values)
                        values = values.transpose(0, 2, 1, 3)
                    if cache is not None:
                        keys, values = cache.update_and_fetch(keys, values)
                queries = queries.transpose(0, 2, 1, 3)
                queries = self.rope(queries, offset=offset)
                output = gemma3n.scaled_dot_product_attention(  # type: ignore
                    queries, keys, values, cache=cache, scale=self.scale, mask=mask
                )
                output = output.transpose(0, 2, 1, 3).reshape(B, L, -1)
                return self.o_proj(output)

            gemma3n.Gemma3nAttention.__init__ = custom_attention_init
            gemma3n.Gemma3nAttention.__call__ = custom_attention_call

            # 5. AltUp predict and correct bypass for altup_num_inputs == 1
            original_predict = gemma3n.Gemma3nAltUp.predict
            original_correct = gemma3n.Gemma3nAltUp.correct
            def custom_predict(self, x):
                if self.config.altup_num_inputs == 1:
                    return x
                return original_predict(self, x)
            def custom_correct(self, predictions, activated):
                if self.config.altup_num_inputs == 1:
                    return activated[None]
                return original_correct(self, predictions, activated)
            gemma3n.Gemma3nAltUp.predict = custom_predict
            gemma3n.Gemma3nAltUp.correct = custom_correct

            # 6. Gemma3nDecoderLayer monkeypatch for conditional PLE, layer_scalar, and single-stream PLE
            def custom_decoder_init(self, config, layer_idx, is_kv_shared_layer):
                nn.Module.__init__(self)
                self.config = config
                self.hidden_size = config.hidden_size
                self.layer_idx = layer_idx
                self.self_attn = gemma3n.Gemma3nAttention(config, layer_idx, is_kv_shared_layer)
                self.mlp = gemma3n.MLP(config, layer_idx=layer_idx)
                self.input_layernorm = nn.RMSNorm(self.hidden_size, eps=config.rms_norm_eps)
                self.post_attention_layernorm = nn.RMSNorm(self.hidden_size, eps=config.rms_norm_eps)
                self.pre_feedforward_layernorm = nn.RMSNorm(self.hidden_size, eps=config.rms_norm_eps)
                self.post_feedforward_layernorm = nn.RMSNorm(self.hidden_size, eps=config.rms_norm_eps)
                self.is_sliding = self.self_attn.is_sliding
                self.hidden_size_per_layer_input = config.hidden_size_per_layer_input
                self.altup = gemma3n.Gemma3nAltUp(config)
                self.laurel = gemma3n.Gemma3nLaurelBlock(config)
                if self.hidden_size_per_layer_input > 0:
                    self.per_layer_input_gate = nn.Linear(self.hidden_size, self.hidden_size_per_layer_input, bias=False)
                    self.per_layer_projection = nn.Linear(self.hidden_size_per_layer_input, self.hidden_size, bias=False)
                    self.post_per_layer_input_norm = nn.RMSNorm(self.hidden_size, eps=config.rms_norm_eps)
                else:
                    self.per_layer_input_gate = None
                    self.per_layer_projection = None
                    self.post_per_layer_input_norm = None
                self.layer_scalar = mx.ones((1,))

            def custom_decoder_call(self, x, mask=None, cache=None, per_layer_input=None):
                predictions = self.altup.predict(x)
                active_prediction = predictions[self.config.altup_active_idx]
                active_prediction_normed = self.input_layernorm(active_prediction)
                laurel_output = self.laurel(active_prediction_normed)
                attn = self.self_attn(active_prediction_normed, mask, cache)
                attn = self.post_attention_layernorm(attn)
                attn_gated = active_prediction + attn
                if self.config.laurel_rank > 0:
                    attn_laurel = (attn_gated + laurel_output) * (2.0**-0.5)
                else:
                    attn_laurel = attn_gated
                attn_norm = self.pre_feedforward_layernorm(attn_laurel)
                attn_ffw = self.mlp(attn_norm)
                attn_ffw_norm = self.post_feedforward_layernorm(attn_ffw)
                attn_ffw_laurel_gated = attn_laurel + attn_ffw_norm
                corrected_predictions = self.altup.correct(predictions, attn_ffw_laurel_gated)
                if self.hidden_size_per_layer_input > 0 and per_layer_input is not None:
                    first_prediction = corrected_predictions[self.config.altup_active_idx]
                    if self.config.altup_correct_scale:
                        first_prediction = first_prediction * self.altup.correct_output_scale
                    first_prediction = self.per_layer_input_gate(first_prediction)
                    first_prediction = nn.gelu_approx(first_prediction)
                    first_prediction = mx.multiply(first_prediction, per_layer_input)
                    first_prediction = self.per_layer_projection(first_prediction)
                    first_prediction = self.post_per_layer_input_norm(first_prediction)
                    if self.config.altup_num_inputs == 1:
                        corrected_predictions = corrected_predictions + first_prediction[None]
                    else:
                        corrected_predictions[1:] = corrected_predictions[1:] + first_prediction
                if hasattr(self, "layer_scalar"):
                    corrected_predictions = corrected_predictions * self.layer_scalar
                return corrected_predictions
            gemma3n.Gemma3nDecoderLayer.__init__ = custom_decoder_init
            gemma3n.Gemma3nDecoderLayer.__call__ = custom_decoder_call

            # 7. Model sanitize weight sanitizer
            def custom_sanitize(self, weights):
                new_weights = {}
                for k, v in weights.items():
                    if k.startswith("language_model.model."):
                        new_key = "model.language_model." + k[len("language_model.model."):]
                        new_weights[new_key] = v
                    else:
                        new_weights[k] = v
                weights_unflattened = tree_unflatten(list(new_weights.items()))
                for k in ["vision_tower", "audio_tower", "embed_audio", "embed_vision"]:
                    if "model" in weights_unflattened:
                        weights_unflattened["model"].pop(k, None)
                return dict(tree_flatten(weights_unflattened))
            gemma3n.Model.sanitize = custom_sanitize

            # 8. LanguageModel monkeypatch to conditionally initialize PLE embedding/projection layers
            def custom_lm_init(self, config):
                nn.Module.__init__(self)
                self.config = config
                self.hidden_size = config.hidden_size
                self.hidden_size_per_layer_input = config.hidden_size_per_layer_input
                self.vocab_size = config.vocab_size
                self.vocab_size_per_layer_input = config.vocab_size_per_layer_input
                self.num_hidden_layers = config.num_hidden_layers
                self.final_logit_softcapping = config.final_logit_softcapping
                self.first_kv_shared_layer_idx = config.num_hidden_layers - config.num_kv_shared_layers

                self.embed_tokens = nn.Embedding(config.vocab_size, config.hidden_size)
                self.layers = [
                    gemma3n.Gemma3nDecoderLayer(
                        config=config,
                        layer_idx=layer_idx,
                        is_kv_shared_layer=layer_idx >= self.first_kv_shared_layer_idx,
                    )
                    for layer_idx in range(config.num_hidden_layers)
                ]

                if self.hidden_size_per_layer_input > 0:
                    self.embed_tokens_per_layer = nn.Embedding(
                        config.vocab_size_per_layer_input,
                        config.num_hidden_layers * config.hidden_size_per_layer_input,
                    )
                    self.per_layer_model_projection = nn.Linear(
                        config.hidden_size,
                        config.num_hidden_layers * config.hidden_size_per_layer_input,
                        bias=False,
                    )
                    self.per_layer_projection_norm = nn.RMSNorm(
                        dims=config.hidden_size_per_layer_input,
                        eps=config.rms_norm_eps,
                    )

                self.altup_projections = [
                    nn.Linear(config.hidden_size, config.hidden_size, bias=False)
                    for _ in range(1, self.config.altup_num_inputs)
                ]

                self.altup_unembed_projections = [
                    nn.Linear(config.hidden_size, config.hidden_size, bias=False)
                    for _ in range(1, self.config.altup_num_inputs)
                ]

                self.norm = nn.RMSNorm(
                    config.hidden_size,
                    eps=config.rms_norm_eps,
                )

                self.first_sliding_idx = config.layer_types.index("sliding_attention")
                self.first_full_idx = config.layer_types.index("full_attention")
                self.sliding_window = config.sliding_window

                concrete_layers = config.layer_types[: self.first_kv_shared_layer_idx]
                shared_full_idx = (
                    len(concrete_layers) - 1 - concrete_layers[::-1].index("full_attention")
                )
                shared_sliding_idx = (
                    len(concrete_layers) - 1 - concrete_layers[::-1].index("sliding_attention")
                )

                self.layer_idx_to_cache_idx = []
                for i, layer_type in enumerate(self.config.layer_types):
                    if i < self.first_kv_shared_layer_idx:
                        self.layer_idx_to_cache_idx.append(i)
                    else:
                        if layer_type == "full_attention":
                            self.layer_idx_to_cache_idx.append(shared_full_idx)
                        elif layer_type == "sliding_attention":
                            self.layer_idx_to_cache_idx.append(shared_sliding_idx)
                        else:
                            raise NotImplementedError(f"Unknown layer type: {layer_type}")

            def custom_lm_call(self, inputs: Optional[mx.array] = None, cache=None, input_embeddings: Optional[mx.array] = None):
                if input_embeddings is None:
                    h = self.embed_tokens(inputs) * (self.hidden_size**0.5)
                else:
                    h = input_embeddings

                if self.hidden_size_per_layer_input > 0:
                    per_layer_inputs = self.get_per_layer_inputs(inputs)
                    per_layer_inputs = self.project_per_layer_inputs(h, per_layer_inputs)
                else:
                    per_layer_inputs = None

                if cache is None:
                    cache = [None] * len(self.layers)

                global_mask = gemma3n.create_attention_mask(h, cache[self.first_full_idx])  # type: ignore
                sliding_window_mask = gemma3n.create_attention_mask(h, cache[self.first_sliding_idx], window_size=self.sliding_window)  # type: ignore
                h0 = h

                target_magnitude = mx.mean(h0**2, axis=-1, keepdims=True) ** 0.5

                h_list = [h0]
                h_list.extend([proj(h0) for proj in self.altup_projections])
                h = mx.stack(h_list, axis=0)
                mags = mx.mean(h[1:] ** 2, axis=-1, keepdims=True) ** 0.5
                h[1:] = h[1:] * (target_magnitude / mx.maximum(mags, mx.finfo(h0.dtype).min))
                for i, layer in enumerate(self.layers):
                    per_layer_input = per_layer_inputs[:, :, i, :] if per_layer_inputs is not None else None
                    is_global = self.config.layer_types[i] == "full_attention"
                    if is_global:
                        mask = global_mask
                    else:
                        mask = sliding_window_mask
                    h = layer(h, mask, cache[self.layer_idx_to_cache_idx[i]], per_layer_input)

                target_magnitude = mx.mean(h[0] ** 2, axis=-1, keepdims=True) ** 0.5
                for i, proj in enumerate(self.altup_unembed_projections):
                    h[i + 1] = proj(h[i + 1])
                mags = mx.mean(h[1:] ** 2, axis=-1, keepdims=True) ** 0.5
                h[1:] = h[1:] * (target_magnitude / mx.maximum(mags, mx.finfo(h0.dtype).min))

                h = mx.mean(h, axis=0)
                out = self.norm(h)
                out = self.embed_tokens.as_linear(out)
                if self.final_logit_softcapping is not None:
                    out = gemma3n.logit_softcap(self.final_logit_softcapping, out)
                return out

            gemma3n.LanguageModel.__init__ = custom_lm_init
            gemma3n.LanguageModel.__call__ = custom_lm_call

            sys.modules['mlx_lm.models.gemma4'] = gemma3n
            
            from mlx_lm.utils import load_model, load_tokenizer
            from pathlib import Path

            # Custom get_model_classes to inject defaults and double-wide MLP array
            from mlx_lm.utils import _get_classes
            def custom_get_classes(config):
                text_config = config.get("text_config", {})
                num_layers = text_config.get("num_hidden_layers", 35)
                if text_config.get("use_double_wide_mlp", False):
                    base_size = text_config["intermediate_size"]
                    if not isinstance(base_size, list):
                        num_kv_shared_layers = text_config.get("num_kv_shared_layers", 20)
                        first_shared_idx = num_layers - num_kv_shared_layers
                        text_config["intermediate_size"] = [
                            base_size if i < first_shared_idx else base_size * 2
                            for i in range(num_layers)
                        ]
                defaults = {
                    "rope_local_base_freq": 10000.0,
                    "rope_theta": 1000000.0,
                    "activation_sparsity_pattern": [0.0] * num_layers,
                    "altup_num_inputs": 1,
                    "altup_coef_clip": 0.0,
                    "altup_correct_scale": False,
                    "altup_active_idx": 0,
                    "laurel_rank": 0,
                    "attention_k_eq_v": False
                }
                if "global_head_dim" in config and "global_head_dim" not in text_config:
                    text_config["global_head_dim"] = config["global_head_dim"]
                for k, v in defaults.items():
                    if k not in text_config:
                        text_config[k] = v
                config["text_config"] = text_config
                return _get_classes(config)

            self.model, _ = load_model(Path(target_model_path), strict=False, get_model_classes=custom_get_classes)
            
            import json
            with open(Path(target_model_path) / "config.json", "r") as f:
                config_data = json.load(f)
            eos_ids = config_data.get("eos_token_id", [1])
            if isinstance(eos_ids, int):
                eos_ids = [eos_ids]
            from mlx_lm.tokenizer_utils import TokenizerWrapper
            raw_tokenizer = load_tokenizer(Path(target_model_path))
            self.tokenizer = TokenizerWrapper(raw_tokenizer, eos_token_ids=eos_ids)
            logger.info("MLXEngine: Model and tokenizer loaded successfully.")
        except Exception as e:
            logger.error(f"MLXEngine load error: {e}")
            raise
        finally:
            self.is_loading = False

    async def ensure_loaded(self):
        """Asynchronously ensures the model is loaded."""
        if self.model is None and not self.is_loading:
            await asyncio.to_thread(self.load_model_sync)
        while self.is_loading:
            await asyncio.sleep(0.1)

    def _apply_ace_logic(self, prompt: str, system_instruction: str, temperature: float) -> tuple[str, str, float]:
        """Injects ACE logic into the system instructions and adjusts temperature."""
        from .. import services
        if services.ace:
            state = services.ace.current_state
            ace_state = state.get("ace_state", "<ACE_STATE_0>")
            
            ace_system_inject = f"\n[ AFFECTIVE COMPUTING GATE: {ace_state} ]"
            if system_instruction:
                system_instruction = system_instruction + ace_system_inject
            else:
                system_instruction = ace_system_inject.strip()
            
            if ace_state in ["<ACE_STATE_4>", "<ACE_STATE_5>"]:
                temperature = min(0.35, temperature)
            elif ace_state in ["<ACE_STATE_2>", "<ACE_STATE_3>"]:
                temperature = min(0.55, temperature)
            elif ace_state == "<ACE_STATE_1>":
                temperature = max(0.70, temperature)
                
        return prompt, system_instruction, temperature

    async def generate(self, prompt: str, system_instruction: str = "", max_tokens: int = 1024, temperature: float = 0.7) -> str:
        """Generates a complete response via the native MLX model."""
        await self.ensure_loaded()
        model = self.model
        tokenizer = self.tokenizer
        if model is None or tokenizer is None:
            raise RuntimeError("Model or tokenizer not loaded.")
        prompt, system_instruction, temperature = self._apply_ace_logic(prompt, system_instruction, temperature)
        # Prepare input using tokenizer's chat template
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})
        formatted_prompt = tokenizer.apply_chat_template(messages, add_generation_prompt=True)
        from mlx_lm import generate
        from mlx_lm.sample_utils import make_sampler
        sampler = make_sampler(temp=temperature)
        def _sync_gen():
            return generate(model, tokenizer, prompt=formatted_prompt, max_tokens=max_tokens, sampler=sampler)
        return await asyncio.to_thread(_sync_gen)

    async def generate_stream(self, prompt: str, max_tokens: int = 1024, temperature: float = 0.7) -> AsyncGenerator[str, None]:
        """Streams response by chunking the generated text for UI consumption."""
        response = await self.generate(prompt, max_tokens=max_tokens, temperature=temperature)
        chunk_size = 20
        for i in range(0, len(response), chunk_size):
            yield response[i:i+chunk_size]
            await asyncio.sleep(0.01)

    async def apply_context_moat(self, agent_id: str):
        """Loads LoRA adapters if present. Currently a no-op for pure MLX models."""
        await self.ensure_loaded()
        # Placeholder: MLX models can load adapters via tokenizer or model method if supported.
        # For now, simply log if an adapter path exists.
        import re, os
        safe_agent_id = re.sub(r'[^a-zA-Z0-9_-]', '_', agent_id)
        lora_path = os.path.abspath(os.path.join("models", "loras", f"agent_{safe_agent_id}_lora.safetensors"))
        if os.path.exists(lora_path) and self.current_lora != lora_path:
            logger.info(f"LoRA adapter found at {lora_path}, but loading not implemented for MLX. Skipping.")
            self.current_lora = lora_path

engine = MLXEngine()
