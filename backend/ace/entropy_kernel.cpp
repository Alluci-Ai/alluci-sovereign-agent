#include <cmath>
#include <algorithm>
#include <cstdlib>

extern "C" {
    struct EntropyState {
        float* history;
        int window_size;
        int count;
        int head;
        float spike_threshold;
    };

    EntropyState* entropy_new(int window_size, float threshold) {
        EntropyState* state = new EntropyState();
        state->window_size = window_size;
        state->history = new float[window_size]();
        state->count = 0;
        state->head = 0;
        state->spike_threshold = threshold;
        return state;
    }

    void entropy_free(EntropyState* state) {
        if (state) {
            delete[] state->history;
            delete state;
        }
    }

    int entropy_push(EntropyState* state, float h_norm) {
        if (!state) return 0;
        
        if (state->count < 5) {
            state->history[state->head] = h_norm;
            state->head = (state->head + 1) % state->window_size;
            state->count++;
            return 0;
        }
        
        float sum = 0.0f;
        for (int i = 0; i < state->count; ++i) {
            sum += state->history[i];
        }
        float mean = sum / state->count;
        
        float sum_sq_diff = 0.0f;
        for (int i = 0; i < state->count; ++i) {
            float diff = state->history[i] - mean;
            sum_sq_diff += diff * diff;
        }
        float variance = sum_sq_diff / state->count;
        float std = std::sqrt(variance);
        if (std < 0.1f) {
            std = 0.1f;
        }
        
        float z_score = std::abs(h_norm - mean) / std;
        
        state->history[state->head] = h_norm;
        state->head = (state->head + 1) % state->window_size;
        
        if (z_score > state->spike_threshold) {
            return 1;
        }
        return 0;
    }

    void entropy_get_state(EntropyState* state, float* out_history, int* out_count, float* out_threshold) {
        if (state) {
            int idx = (state->head - state->count + state->window_size) % state->window_size;
            for (int i = 0; i < state->count; ++i) {
                out_history[i] = state->history[(idx + i) % state->window_size];
            }
            *out_count = state->count;
            *out_threshold = state->spike_threshold;
        }
    }
}
