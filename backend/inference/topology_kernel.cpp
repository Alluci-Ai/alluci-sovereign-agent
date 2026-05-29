#include <cmath>
#include <cstdint>
#include <vector>
#include <numeric>

extern "C" {
    void topology_compute(const float* points, int n_points, int dim, float* betti_out) {
        if (n_points == 0) {
            betti_out[0] = 0.0f; betti_out[1] = 0.0f; betti_out[2] = 0.0f; betti_out[3] = 0.0f;
            return;
        }
        if (n_points == 1) {
            betti_out[0] = 1.0f; betti_out[1] = 0.0f; betti_out[2] = 0.0f; betti_out[3] = 0.0f;
            return;
        }

        const float epsilon = 0.5f;
        int edges = 0;
        
        std::vector<int> parent(n_points);
        std::iota(parent.begin(), parent.end(), 0);

        auto find = [&](int i, auto& find_ref) -> int {
            if (parent[i] == i) return i;
            return parent[i] = find_ref(parent[i], find_ref);
        };

        auto unite = [&](int i, int j, auto& find_ref) {
            int root_i = find_ref(i, find_ref);
            int root_j = find_ref(j, find_ref);
            if (root_i != root_j) parent[root_i] = root_j;
        };

        for (int i = 0; i < n_points; ++i) {
            for (int j = i + 1; j < n_points; ++j) {
                float dist_sq = 0.0f;
                for (int d = 0; d < dim; ++d) {
                    float diff = points[i * dim + d] - points[j * dim + d];
                    dist_sq += diff * diff;
                }
                if (std::sqrt(dist_sq) < epsilon) {
                    edges++;
                    unite(i, j, find);
                }
            }
        }

        int b0 = 0;
        for (int i = 0; i < n_points; ++i) {
            if (parent[i] == i) b0++;
        }

        betti_out[0] = static_cast<float>(b0);
        betti_out[1] = static_cast<float>(edges - n_points + b0);
        betti_out[2] = 0.0f;
        betti_out[3] = 0.0f;
    }

    void simplex_counts(const float* points, int n_points, int dim, float epsilon, int32_t* V, int32_t* E, int32_t* F) {
        if (n_points < 3) {
            *V = n_points;
            *E = 0;
            *F = 0;
            return;
        }

        *V = n_points;
        int edges = 0;
        int faces = 0;

        std::vector<std::vector<bool>> adj(n_points, std::vector<bool>(n_points, false));

        for (int i = 0; i < n_points; ++i) {
            for (int j = i + 1; j < n_points; ++j) {
                float dist_sq = 0.0f;
                for (int d = 0; d < dim; ++d) {
                    float diff = points[i * dim + d] - points[j * dim + d];
                    dist_sq += diff * diff;
                }
                if (std::sqrt(dist_sq) < epsilon) {
                    adj[i][j] = true;
                    adj[j][i] = true;
                    edges++;
                }
            }
        }
        *E = edges;

        for (int i = 0; i < n_points; ++i) {
            for (int j = i + 1; j < n_points; ++j) {
                if (adj[i][j]) {
                    for (int k = j + 1; k < n_points; ++k) {
                        if (adj[i][k] && adj[j][k]) {
                            faces++;
                        }
                    }
                }
            }
        }
        *F = faces;
    }

    float kcm_geodesic_cost(const float* betti_current, const float* betti_goal, float psi, int n) {
        float sum = 0.0f;
        for (int i = 0; i < n; ++i) {
            sum += std::abs(betti_current[i] - betti_goal[i]);
        }
        return sum * (1.0f + psi);
    }
}
