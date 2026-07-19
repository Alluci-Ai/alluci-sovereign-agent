#include <iostream>
#include <mlx/mlx.h>
#include <vector>

int main() {
    auto x = mlx::core::ones({1, 1, 1, 4}, mlx::core::float32);
    x = mlx::core::multiply(x, mlx::core::array({1.0f, 2.0f, 3.0f, 4.0f}, {1, 1, 1, 4}));
    
    std::optional<float> no_base = std::nullopt;
    auto exponents = mlx::core::divide(mlx::core::array({0.0f, 2.0f}), mlx::core::array(4.0f));
    auto freqs = mlx::core::divide(mlx::core::array(1.0f), mlx::core::power(mlx::core::array(10000.0f), exponents));
    
    auto out_trad = mlx::core::fast::rope(x, 4, true, no_base, 1.0f, 1, freqs);
    auto out_notrad = mlx::core::fast::rope(x, 4, false, no_base, 1.0f, 1, freqs);
    
    mlx::core::eval({out_trad, out_notrad});
    
    std::cout << "Original: " << x << std::endl;
    std::cout << "Traditional: " << out_trad << std::endl;
    std::cout << "Non-Traditional: " << out_notrad << std::endl;
    return 0;
}
