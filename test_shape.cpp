#include <mlx/mlx.h>
#include <iostream>
int main() {
    auto a = mlx::core::zeros({1, 2, 3});
    try {
        auto mean = mlx::core::mean(a, std::vector<int>{-1});
        std::cout << mean.shape().size() << std::endl;
    } catch (const std::exception& e) {
        std::cout << "Exception: " << e.what() << std::endl;
    }
    return 0;
}
