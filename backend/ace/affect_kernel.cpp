#include <cmath>
#include <cstdint>
#include <algorithm>

extern "C" {
    void affect_apply_batch(float* out, const float* in, int n, int32_t tension, int32_t arousal, int32_t valence) {
        int32_t SCALE = 2048;
        int32_t NEUTRAL_TENSION = 1024;
        int32_t MAX_VAL = 32767;

        int32_t tension_coeff = NEUTRAL_TENSION + (tension * 8);
        int32_t tension_clamped = std::max(tension_coeff, 1);
        int32_t arousal_term = NEUTRAL_TENSION + arousal;
        int32_t valence_shear = (valence * 512) >> 2;

        for (int i = 0; i < n; ++i) {
            int32_t raw_int = static_cast<int32_t>(in[i] * SCALE);
            int32_t dilated = (raw_int * arousal_term) >> 10;
            dilated += valence_shear;
            
            int32_t final_val = (dilated * NEUTRAL_TENSION) / tension_clamped;
            
            if (final_val > MAX_VAL) final_val = MAX_VAL;
            if (final_val < -MAX_VAL) final_val = -MAX_VAL;
            
            out[i] = static_cast<float>(final_val) / static_cast<float>(SCALE);
        }
    }

    void decay_retention_batch(float* out, const float* delta_t, const float* topo_imp, const float* betti_1, int n, float half_life) {
        float decay_constant = 0.693147f / half_life;
        for (int i = 0; i < n; ++i) {
            float imp = topo_imp[i] > 1.0f ? topo_imp[i] : 1.0f;
            float lambda_adj = decay_constant / imp;
            
            if (betti_1[i] > 0.0f) {
                float b_boost = betti_1[i] < 5.0f ? betti_1[i] : 5.0f;
                lambda_adj /= (1.0f + b_boost);
            }
            
            out[i] = std::exp(-lambda_adj * delta_t[i]);
        }
    }
}
