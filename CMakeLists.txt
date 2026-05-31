cmake_minimum_required(VERSION 3.24)
project(AlluciSovereignCore VERSION 1.0)

# We are building a Python Extension module via PyBind11
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find MLX
# Assumes MLX C++ headers are installed locally or pulled via FetchContent
# For this scaffolding, we link against the frameworks
find_library(ACCELERATE_FRAMEWORK Accelerate REQUIRED)
find_library(METAL_FRAMEWORK Metal REQUIRED)
find_library(FOUNDATION_FRAMEWORK Foundation REQUIRED)

# Fetch PyBind11
include(FetchContent)
FetchContent_Declare(
  pybind11
  GIT_REPOSITORY https://github.com/pybind/pybind11.git
  GIT_TAG        v2.11.1
)
FetchContent_MakeAvailable(pybind11)

# Include directories (Placeholder for mlx/c/mlx.h)
include_directories(${CMAKE_SOURCE_DIR}/src)

# Define the Python extension module
pybind11_add_module(alluci_core src/pybind_module.cpp)

# Link Apple Silicon Frameworks
target_link_libraries(alluci_core PRIVATE 
    ${ACCELERATE_FRAMEWORK} 
    ${METAL_FRAMEWORK} 
    ${FOUNDATION_FRAMEWORK}
)

# Compiler flags for maximum Apple Silicon optimization
target_compile_options(alluci_core PRIVATE -O3 -flto -ffast-math -mcpu=apple-m1)
