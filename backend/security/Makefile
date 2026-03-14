# Makefile for Alluci Sovereign Agent Native Kernels

CXX = g++
CXXFLAGS = -O3 -Wall -fPIC -std=c++11
LDFLAGS = -shared

# Target names based on OS
UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Darwin)
	TARGET = libdpk.dylib
else
	TARGET = libdpk.so
endif

SRCS = dpk_kernel.cpp
OBJS = $(SRCS:.cpp=.o)

all: $(TARGET)

$(TARGET): $(OBJS)
	$(CXX) $(LDFLAGS) -o $@ $^

%.o: %.cpp
	$(CXX) $(CXXFLAGS) -c $< -o $@

clean:
	rm -f $(OBJS) $(TARGET)

.PHONY: all clean
