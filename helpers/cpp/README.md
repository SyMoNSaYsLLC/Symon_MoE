# C++ Helpers Build Instructions

This directory contains the C++ helper sources for the Symon_MoE platform.

## Components

| File | Description |
|------|-------------|
| `gguf_reader.h/.cpp` | Standalone GGUF binary parser (no llama.cpp dependency) |
| `tensor_ops.h/.cpp` | Basic tensor arithmetic (add, mul, dot, reshape, matmul) |
| `llama_bridge.cpp` | Headless LLM inference CLI wrapping `llama_context` |
| `diffusion_bridge.cpp` | Headless txt2img CLI wrapping `stable-diffusion.cpp` |
| `CMakeLists.txt` | CMake build config |

## Prerequisites

- CMake ≥ 3.18
- A C++17 compiler (GCC ≥ 10, Clang ≥ 11, MSVC 2019+)
- Optional: Eigen3 (for optimised tensor_ops)

### Build the submodule dependencies first

**llama.cpp** (required for `llama_bridge`):

```bash
cd ../../converters/llm_engine
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --target llama -j$(nproc)
```

**stable-diffusion.cpp** (required for `diffusion_bridge`):

```bash
cd ../../converters/diffusers_cpp
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j$(nproc)
```

## Build

```bash
# From this directory:
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j$(nproc)
```

Optional Eigen support:

```bash
cmake -B build -DCMAKE_BUILD_TYPE=Release -DUSE_EIGEN=ON
cmake --build build -j$(nproc)
```

Binaries will be placed in `build/` (or `build/bin/` after install).

## Usage

### gguf_reader (library)

```cpp
#include "gguf_reader.h"

gguf::GGUFReader reader("path/to/model.gguf");
auto meta    = reader.metadata();
auto tensors = reader.tensors();
std::string arch = reader.get_string("general.architecture", "unknown");
```

### tensor_ops (library)

```cpp
#include "tensor_ops.h"

auto a = tensor::zeros({3, 4});
auto b = tensor::zeros({4, 2});
auto c = tensor::matmul(a, b);  // 3×2 result
```

### llama_bridge (executable)

```bash
./build/llama_bridge \
  --model path/to/model.gguf \
  --prompt "Explain quantum entanglement in one paragraph" \
  --n-predict 200 \
  --temp 0.7
```

### diffusion_bridge (executable)

```bash
./build/diffusion_bridge \
  --model path/to/model.gguf \
  --prompt "a serene mountain lake at dawn, photorealistic" \
  --output out.png \
  --width 768 --height 512 \
  --steps 30 --cfg 7.5
```

## Install

```bash
cmake --install build --prefix /usr/local
```

This installs:
- `lib/libgguf_reader.a`
- `lib/libtensor_ops.a`
- `include/gguf_reader.h`
- `include/tensor_ops.h`
- `bin/llama_bridge` (if llama.cpp was found)
- `bin/diffusion_bridge` (if stable-diffusion.cpp was found)
