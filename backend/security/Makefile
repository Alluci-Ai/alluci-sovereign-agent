# backend/security/Makefile
BUILD_DIR := build
TARGET_DYLIB := $(BUILD_DIR)/libdpk.dylib
TARGET_SO := $(BUILD_DIR)/libdpk.so
TARGET_OBJ := $(BUILD_DIR)/dpk_kernel.o
SRC := dpk_kernel.cpp

CXX := g++
CXXFLAGS := -O2 -std=c++17 -fPIC -Wall

.PHONY: all clean macos linux

all: $(shell uname -s | tr '[:upper:]' '[:lower:]')

$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

macos: $(BUILD_DIR)
	$(CXX) $(CXXFLAGS) -dynamiclib -o $(TARGET_DYLIB) $(SRC)
	@echo "Built macOS dylib: $(TARGET_DYLIB)"

linux: $(BUILD_DIR)
	$(CXX) $(CXXFLAGS) -shared -o $(TARGET_SO) $(SRC)
	@echo "Built Linux .so: $(TARGET_SO)"

clean:
	rm -rf $(BUILD_DIR)
