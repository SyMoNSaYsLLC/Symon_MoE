# Tensors in Machine Learning — A Practical Guide

A **tensor** is the fundamental data structure of machine learning.
Every piece of data and every model weight in a neural network lives inside a tensor.

---

## What Is a Tensor?

A tensor is a generalisation of scalars, vectors, and matrices to *any* number of dimensions.

| Rank | Name | Example |
|---|---|---|
| 0 | Scalar | `3.14` |
| 1 | Vector | `[1, 2, 3]` |
| 2 | Matrix | `[[1, 2], [3, 4]]` |
| 3 | 3-D Tensor | Image batch `[batch, height, width]` |
| 4 | 4-D Tensor | Colour image batch `[batch, channels, height, width]` |
| N | N-D Tensor | Arbitrary-rank data |

The *rank* (also called *ndim*) is the number of axes.
The *shape* describes the size along each axis.

---

## Tensors in a Neural Network

When a large language model (LLM) like Llama 3 runs, it stores:

- **Embedding weights** — shape `[vocab_size, hidden_dim]`
- **Attention Q/K/V weights** — shape `[hidden_dim, head_dim * n_heads]`
- **Feed-forward weights** — shape `[hidden_dim, ffn_dim]`
- **Layer-norm parameters** — shape `[hidden_dim]`

During inference each input token is looked up in the embedding table to get a vector of shape `[hidden_dim]`.
The network then repeatedly multiplies and transforms that vector through dozens of layers.
Every one of those operations is a tensor operation.

---

## Data Types (dtypes)

Tensor values are stored in a *dtype*.  Smaller dtypes save memory and speed up inference at a small accuracy cost.

| Dtype | Bits | Notes |
|---|---|---|
| `float32` (FP32) | 32 | Full precision reference |
| `bfloat16` (BF16) | 16 | Good dynamic range; preferred for training |
| `float16` (FP16) | 16 | GPU inference standard |
| `int8` / `Q8_0` | 8 | Near-lossless for inference |
| `Q4_K_M` | ~4.6 | Recommended GGUF 4-bit quant |
| `Q2_K` | ~2.6 | Extreme compression; visible quality loss |

The Symoneural `quant_utils.py` helper manages these presets.
The `tensor_utils.py` helper can cast tensors between dtypes.

---

## Common Tensor Operations

### Element-wise Operations

Applied to every element independently.  Both tensors must share the same shape.

```
C[i,j] = A[i,j] + B[i,j]   (addition)
C[i,j] = A[i,j] * B[i,j]   (Hadamard product)
```

### Matrix Multiplication (Matmul)

The core operation behind attention, feed-forward layers, and embeddings.

```
C[i,j] = Σ_k  A[i,k] * B[k,j]
```

For shapes: `(M×K) @ (K×N) → (M×N)`

### Reshape

Change the shape without copying data.

```
A shape [6]  → reshape →  B shape [2, 3]
```

### Transpose

Swap two axes.

```
A shape [M, N]  → transpose →  B shape [N, M]
```

### Softmax

Converts logit scores into a probability distribution.

```
softmax(x)_i = exp(x_i) / Σ_j exp(x_j)
```

Used in the attention mechanism and output projection of LLMs.

---

## Tensors in GGUF Models

GGUF is the binary format used by llama.cpp.
Each tensor inside a GGUF file has:

- **name** — e.g. `blk.0.attn_q.weight`
- **shape** — e.g. `[4096, 4096]`
- **type** — quantisation type (F32, F16, Q8_0, Q4_K, …)
- **data_offset** — byte offset in the file

Use `helpers/python/gguf_inspect.py` to inspect these tensors:

```bash
python helpers/python/gguf_inspect.py read model.gguf --tensors
```

Use `helpers/python/tensor_utils.py` to inspect `.safetensors` checkpoints:

```bash
python helpers/python/tensor_utils.py model.safetensors
```

---

## Tensor Lab (Frontend)

The **Tensor Lab** page (`/apps/tensor_lab.html`) lets you:

1. **Create tensors** — specify shape and dtype, fill with zeros / ones / range / random
2. **Visualise** — see shape, dtype, memory footprint, and flat value preview
3. **Apply operations** — add, subtract, multiply, matmul between two tensors
4. **Connect to a model** — enter an API key and pick an Ollama model to customise parameters (temperature, top-p, top-k, repeat-penalty, context length) and test inference directly

All tensor operations are performed by the backend `helpers/python/tensor_utils.py` module and exposed through the `/api/tensor/` endpoints.

---

## LoRA: Low-Rank Adaptation

LoRA is an efficient fine-tuning technique.  Instead of updating all model weights it adds a low-rank decomposition:

```
W_adapted = W_base + alpha * (B @ A)
```

where `A` has shape `[r, d_in]` and `B` has shape `[d_out, r]` with `r ≪ d_in, d_out`.

The `helpers/python/lora_merge.py` script merges LoRA adapters back into the base model:

```bash
python helpers/python/lora_merge.py base.safetensors adapter.safetensors merged.safetensors --alpha 1.0
```

---

## Further Reading

- [What is a Tensor? (Medium)](https://medium.com/@stephenc211/what-is-a-tensor-f28d10162832)
- [GGUF format spec](https://github.com/ggml-org/llama.cpp/blob/master/docs/gguf.md)
- [Safetensors format](https://github.com/huggingface/safetensors)
- [LoRA paper (Hu et al. 2021)](https://arxiv.org/abs/2106.09685)
- [llama.cpp quantisation guide](https://github.com/ggml-org/llama.cpp/blob/master/docs/quantization.md)
