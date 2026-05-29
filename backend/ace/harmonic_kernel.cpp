#include <cmath>
#include <algorithm>
#include <vector>
#include <cstdlib>

extern "C" {
    int lattice_analyze(const float* series, int n, float* out_strength, int* out_cycle_length) {
        if (n < 5) {
            *out_strength = 0.0f;
            *out_cycle_length = 0;
            return 0;
        }

        float sum = 0.0f;
        for (int i = 0; i < n; ++i) {
            sum += series[i];
        }
        float mean = sum / n;

        float sum_sq = 0.0f;
        for (int i = 0; i < n; ++i) {
            float diff = series[i] - mean;
            sum_sq += diff * diff;
        }
        float std_val = std::sqrt(sum_sq / n);
        float std_epsilon = std_val + 1e-6f;

        std::vector<float> norm_arr(n);
        for (int i = 0; i < n; ++i) {
            norm_arr[i] = (series[i] - mean) / std_epsilon;
        }

        std::vector<float> result(n, 0.0f);
        for (int k = 0; k < n; ++k) {
            float accum = 0.0f;
            for (int i = 0; i < n - k; ++i) {
                accum += norm_arr[i] * norm_arr[i + k];
            }
            result[k] = accum;
        }

        float best_strength = -1.0f;
        int best_lag = 0;
        bool found = false;

        for (int i = 1; i < n - 1; ++i) {
            if (result[i - 1] < result[i] && result[i] > result[i + 1]) {
                if (result[i] > best_strength) {
                    best_strength = result[i];
                    best_lag = i;
                    found = true;
                }
            }
        }

        if (found) {
            float norm_strength = std::min(1.0f, best_strength / n);
            *out_strength = norm_strength;
            *out_cycle_length = best_lag;
            return 1;
        } else {
            *out_strength = 0.0f;
            *out_cycle_length = 0;
            return 0;
        }
    }

    struct TopologyMapperHandle {
        float* valence_history;
        float* arousal_history;
        int max_history;
        int count;
        int head;
    };

    TopologyMapperHandle* topology_mapper_new(int max_history) {
        TopologyMapperHandle* handle = new TopologyMapperHandle();
        handle->max_history = max_history;
        handle->valence_history = new float[max_history]();
        handle->arousal_history = new float[max_history]();
        handle->count = 0;
        handle->head = 0;
        return handle;
    }

    void topology_mapper_free(TopologyMapperHandle* handle) {
        if (handle) {
            delete[] handle->valence_history;
            delete[] handle->arousal_history;
            delete handle;
        }
    }

    void topology_mapper_update(TopologyMapperHandle* handle, float valence, float arousal, float* out_c_val, float* out_c_ar, int* out_stress) {
        if (!handle) return;

        handle->valence_history[handle->head] = valence;
        handle->arousal_history[handle->head] = arousal;
        handle->head = (handle->head + 1) % handle->max_history;
        if (handle->count < handle->max_history) {
            handle->count++;
        }

        float val_sum = 0.0f;
        float ar_sum = 0.0f;
        for (int i = 0; i < handle->count; ++i) {
            val_sum += handle->valence_history[i];
            ar_sum += handle->arousal_history[i];
        }

        float c_val = val_sum / handle->count;
        float c_ar = ar_sum / handle->count;

        *out_c_val = c_val;
        *out_c_ar = c_ar;
        *out_stress = (c_ar > 0.7f && c_val < 0.3f) ? 1 : 0;
    }

    void topology_mapper_get_state(TopologyMapperHandle* handle, float* out_valence, float* out_arousal, int* out_count) {
        if (handle) {
            int idx = (handle->head - handle->count + handle->max_history) % handle->max_history;
            for (int i = 0; i < handle->count; ++i) {
                out_valence[i] = handle->valence_history[(idx + i) % handle->max_history];
                out_arousal[i] = handle->arousal_history[(idx + i) % handle->max_history];
            }
            *out_count = handle->count;
        }
    }
}
