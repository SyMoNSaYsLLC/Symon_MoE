# C++ Helpers Reference

See also: [`helpers/cpp/README.md`](../helpers/cpp/README.md) for full build instructions.

## Build

```bash
cmake -B helpers/cpp/build -S helpers/cpp -DCMAKE_BUILD_TYPE=Release
cmake --build helpers/cpp/build -j$(nproc)
```

---

## gguf_reader — GGUF Binary Parser

**Files:** `gguf_reader.h`, `gguf_reader.cpp`

A standalone, zero-dependency GGUF file parser.  Reads metadata key-value pairs and tensor descriptors from any GGUF v1/v2/v3 file without requiring the full llama.cpp library.

### Key classes

| Class / Function | Description |
|---|---|
| `gguf::GGUFReader(path)` | Open a GGUF file |
| `reader.metadata()` | Return all KV metadata as `map<string, GGUFValue>` |
| `reader.tensors()` | Return tensor descriptors (name, shape, type) |
| `reader.get_string(key, default)` | Read a string metadata value |
| `reader.get_uint32(key, default)` | Read a uint32 metadata value |

### Example

```cpp
#include "gguf_reader.h"

gguf::GGUFReader reader("model.gguf");
auto arch = reader.get_string("general.architecture", "unknown");
for (auto& t : reader.tensors()) {
    printf("%s  shape=[%zu x %zu]\n", t.name.c_str(), t.shape[0], t.shape[1]);
}
```

---

## tensor_ops — Tensor Arithmetic

**Files:** `tensor_ops.h`, `tensor_ops.cpp`

Provides basic CPU tensor operations over contiguous float32 buffers.

### API

| Function | Signature | Description |
|---|---|---|
| `tensor::zeros` | `(shape) → Tensor` | Create zero-filled tensor |
| `tensor::ones` | `(shape) → Tensor` | Create ones tensor |
| `tensor::add` | `(a, b) → Tensor` | Element-wise addition |
| `tensor::mul` | `(a, b) → Tensor` | Element-wise multiplication |
| `tensor::matmul` | `(a, b) → Tensor` | Matrix multiplication |
| `tensor::reshape` | `(t, new_shape) → Tensor` | Reshape without copying |
| `tensor::transpose` | `(t) → Tensor` | Transpose last two dims |

Compile with `-DUSE_EIGEN=ON` to use Eigen3-accelerated BLAS paths.

---

## llama_bridge — Headless LLM Inference CLI

**File:** `llama_bridge.cpp`  
**Requires:** `converters/llm_engine` (llama.cpp) built first.

```
Usage: llama_bridge [OPTIONS]

Options:
  --model PATH        Path to GGUF model file (required)
  --prompt TEXT       Input prompt (required)
  --n-predict N       Max tokens to generate (default: 128)
  --temp FLOAT        Sampling temperature (default: 0.8)
  --top-k INT         Top-K sampling (default: 40)
  --top-p FLOAT       Top-P sampling (default: 0.95)
  --ctx-size N        Context window size (default: 2048)
  --threads N         CPU threads (default: system core count)
  --no-newline        Suppress trailing newline
```

**Example**

```bash
./helpers/cpp/build/llama_bridge \
  --model frontend/models/converted/llama.gguf \
  --prompt "What is a tensor?" \
  --n-predict 200 --temp 0.7
```

---

## diffusion_bridge — Headless Text-to-Image CLI

**File:** `diffusion_bridge.cpp`  
**Requires:** `converters/diffusers_cpp` (stable-diffusion.cpp) built first.

```
Usage: diffusion_bridge [OPTIONS]

Options:
  --model PATH        Path to GGUF diffusion model (required)
  --prompt TEXT       Positive prompt (required)
  --negative TEXT     Negative prompt
  --output PATH       Output PNG path (default: output.png)
  --width INT         Image width in pixels (default: 512)
  --height INT        Image height in pixels (default: 512)
  --steps INT         Diffusion steps (default: 20)
  --cfg FLOAT         Classifier-free guidance scale (default: 7.0)
  --seed INT          RNG seed (-1 = random)
```

**Example**

```bash
./helpers/cpp/build/diffusion_bridge \
  --model frontend/models/converted/sd-v1-5.gguf \
  --prompt "a red fox in a snowy forest, oil painting" \
  --output fox.png --width 768 --height 512 --steps 30
```
