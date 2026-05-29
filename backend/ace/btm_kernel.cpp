#include <algorithm>
#include <cstdlib>

extern "C" {
    struct BTMHandle {
        float* hrv_history;
        float* gsr_history;
        int hrv_window;
        int hrv_count;
        int hrv_head;
        int gsr_count;
        int gsr_head;
        float max_hrv_observed;
    };

    BTMHandle* btm_new(int hrv_window) {
        BTMHandle* handle = new BTMHandle();
        handle->hrv_window = hrv_window;
        handle->hrv_history = new float[hrv_window]();
        handle->gsr_history = new float[hrv_window]();
        handle->hrv_count = 0;
        handle->hrv_head = 0;
        handle->gsr_count = 0;
        handle->gsr_head = 0;
        handle->max_hrv_observed = 100.0f;
        return handle;
    }

    void btm_free(BTMHandle* handle) {
        if (handle) {
            delete[] handle->hrv_history;
            delete[] handle->gsr_history;
            delete handle;
        }
    }

    void btm_map(BTMHandle* handle, 
                 float hrv, int has_hrv,
                 float gsr, int has_gsr,
                 float stress_score, int has_stress_score,
                 float hr, int has_hr,
                 float respiratory_rate, int has_respiratory_rate,
                 float in_valence, int has_valence,
                 float* out_valence, float* out_arousal, float* out_tension) {
        
        // A. AROUSAL: inverse HRV stability + GSR gradient
        float arousal = 512.0f;
        if (has_hrv && hrv > 0.0f) {
            handle->hrv_history[handle->hrv_head] = hrv;
            handle->hrv_head = (handle->hrv_head + 1) % handle->hrv_window;
            if (handle->hrv_count < handle->hrv_window) {
                handle->hrv_count++;
            }
            
            if (hrv > handle->max_hrv_observed) {
                handle->max_hrv_observed = hrv;
            }
            
            float hrv_stability = hrv / handle->max_hrv_observed;
            float raw_arousal = 1.0f / (hrv_stability + 0.1f);
            arousal = std::max(0.0f, std::min(1024.0f, raw_arousal * 256.0f));
        }

        if (has_gsr) {
            handle->gsr_history[handle->gsr_head] = gsr;
            int prev_head = handle->gsr_head;
            handle->gsr_head = (handle->gsr_head + 1) % handle->hrv_window;
            if (handle->gsr_count < handle->hrv_window) {
                handle->gsr_count++;
            }
            
            if (handle->gsr_count >= 2) {
                int latest_idx = prev_head;
                int second_latest_idx = (prev_head - 1 + handle->hrv_window) % handle->hrv_window;
                float gsr_gradient = handle->gsr_history[latest_idx] - handle->gsr_history[second_latest_idx];
                
                float gsr_arousal = std::max(0.0f, std::min(1024.0f, gsr_gradient * 4.0f * 256.0f));
                arousal = std::max(0.0f, std::min(1024.0f, (arousal + gsr_arousal) / 2.0f));
            }
        }

        // B. TENSION: torsion mapping
        float tension = 0.0f;
        if (has_stress_score) {
            float torsion = std::min(1.0f, stress_score / 100.0f);
            tension = std::min(1024.0f, torsion * 1024.0f);
        } else if (has_hr && has_hrv) {
            float rr = has_respiratory_rate ? (respiratory_rate / 15.0f) : 1.0f;
            float max_hrv = hrv > 1.0f ? hrv : 1.0f;
            float torsion = std::min(1.0f, (hr / max_hrv) * 10.0f * rr / 100.0f);
            tension = std::min(1024.0f, torsion * 1024.0f);
        }

        // C. VALENCE: symmetry mapping
        float valence = 512.0f;
        if (has_valence) {
            valence = std::max(0.0f, std::min(1024.0f, in_valence * 1024.0f));
        }

        *out_valence = valence;
        *out_arousal = arousal;
        *out_tension = tension;
    }

    int32_t btm_compute_psi(int32_t hrv_raw, int32_t gsr_raw) {
        int32_t arousal = gsr_raw ? (gsr_raw << 2) : 512;
        int32_t valence = hrv_raw >> 1;
        int32_t psi = (arousal - valence) + 512;
        return std::max(0, std::min(1024, psi));
    }
    
    void btm_get_state(BTMHandle* handle, float* out_hrv_history, float* out_gsr_history, int* out_hrv_count, int* out_gsr_count, float* out_max_hrv) {
        if (handle) {
            int hrv_idx = (handle->hrv_head - handle->hrv_count + handle->hrv_window) % handle->hrv_window;
            for (int i = 0; i < handle->hrv_count; ++i) {
                out_hrv_history[i] = handle->hrv_history[(hrv_idx + i) % handle->hrv_window];
            }
            int gsr_idx = (handle->gsr_head - handle->gsr_count + handle->hrv_window) % handle->hrv_window;
            for (int i = 0; i < handle->gsr_count; ++i) {
                out_gsr_history[i] = handle->gsr_history[(gsr_idx + i) % handle->hrv_window];
            }
            *out_hrv_count = handle->hrv_count;
            *out_gsr_count = handle->gsr_count;
            *out_max_hrv = handle->max_hrv_observed;
        }
    }
}
