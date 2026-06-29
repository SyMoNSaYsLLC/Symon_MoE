# Python Helper Scripts Reference

All scripts live under `helpers/python/`.

Install dependencies:
```bash
pip install gguf safetensors sympy httpx numpy
```

---

## tensor_utils.py

**Purpose:** safetensors/GGUF tensor inspection, slicing, and dtype casting.

### Public API

#### `list_safetensors(path) → list[dict]`
Return a list of tensor descriptors from a `.safetensors` file.

Each descriptor contains:
- `name` — tensor name
- `shape` — list of dimensions
- `dtype` — numpy dtype string
- `nbytes` — memory size in bytes

#### `load_safetensors_tensor(path, name) → np.ndarray`
Load a single named tensor from a `.safetensors` file as a numpy array.

#### `slice_tensor(tensor, *slices) → np.ndarray`
Return a view/copy of *tensor* for the given index slices.

#### `cast_tensor(tensor, target_dtype) → np.ndarray`
Cast a numpy tensor to a target dtype string (e.g. `'fp16'`, `'float32'`).

#### `dtype_name_to_np(name) → np.dtype`
Convert a dtype name string to a numpy dtype.  Recognises `fp32`, `fp16`, `bf16`, `int8`, `uint8` plus any numpy-native string.

#### `gguf_dtype_name(gguf_type) → str`
Return a human-readable name for a GGUF tensor type integer (e.g. `8 → "Q8_0"`).

#### `nbytes_gguf_block(gguf_type, n_elements) → int`
Estimate byte size for a quantised GGUF block.

### CLI Usage

```bash
# List all tensors in a safetensors file
python helpers/python/tensor_utils.py model.safetensors

# Inspect a specific tensor
python helpers/python/tensor_utils.py model.safetensors --tensor model.embed_tokens.weight
```

---

## gguf_inspect.py

**Purpose:** GGUF file metadata reader/writer.

### Public API

#### `read_metadata(path) → dict`
Return all metadata KV pairs from a GGUF file as a plain dict.

#### `list_tensors(path) → list[dict]`
Return a list of tensor descriptors (`name`, `shape`, `type`, `type_name`, `n_elements`, `data_offset`).

#### `read_key(path, key) → object`
Read a single metadata value by key. Raises `KeyError` if not found.

#### `patch_metadata(src_path, dst_path, patches)`
Write a copy of `src_path` to `dst_path` with `patches` applied.

### CLI Usage

```bash
# Read all metadata
python helpers/python/gguf_inspect.py read model.gguf

# Read a specific key
python helpers/python/gguf_inspect.py read model.gguf --key general.name

# List tensors
python helpers/python/gguf_inspect.py read model.gguf --tensors

# Patch metadata
python helpers/python/gguf_inspect.py patch model.gguf patched.gguf '{"general.name":"MyModel"}'
```

---

## diffusion_convert.py

**Purpose:** `.safetensors` → GGUF pipeline helper via stable-diffusion.cpp.

### Public API

#### `find_convert_bin(custom_bin=None) → Path`
Locate the `sd` binary (stable-diffusion.cpp), checking the default build path and `PATH`.

#### `convert_safetensors_to_gguf(src, dst, quant_type, convert_bin, extra_args) → int`
Convert a `.safetensors` diffusion checkpoint to GGUF.  Returns the process exit code.

#### `batch_convert(src_dir, dst_dir, quant_type, convert_bin) → dict[str, int]`
Convert all `.safetensors` files in `src_dir` to GGUF in `dst_dir`.

### CLI Usage

```bash
# Single conversion
python helpers/python/diffusion_convert.py convert sd-v1-5.safetensors sd-v1-5.gguf --type f16

# Batch conversion
python helpers/python/diffusion_convert.py batch ./raw_diffusion/ ./converted/ --type q8_0
```

---

## ollama_compat.py

**Purpose:** Modelfile generator and push/pull wrappers for Ollama REST API.

### Public API

#### `generate_modelfile(gguf_path, system_prompt, template, parameters) → str`
Generate an Ollama Modelfile string for a local GGUF file.

#### `write_modelfile(path, gguf_path, system_prompt, template, parameters) → Path`
Write a Modelfile to `path` and return the resolved path.

#### `list_models(base_url) → list[dict]`
Return the list of models available in an Ollama instance.

#### `create_model(name, modelfile_content, base_url, stream)`
Create (register) a model in Ollama via the `/api/create` endpoint.

#### `pull_model(name, base_url) → list[dict]`
Pull a model from the Ollama registry.

#### `delete_model(name, base_url)`
Delete a model from an Ollama instance.

### CLI Usage

```bash
# Generate a Modelfile
python helpers/python/ollama_compat.py modelfile my-model.gguf --system "You are a helpful assistant."

# Write Modelfile to disk
python helpers/python/ollama_compat.py modelfile my-model.gguf --out Modelfile --temperature 0.7

# List loaded models
python helpers/python/ollama_compat.py list

# Pull a model from registry
python helpers/python/ollama_compat.py pull llama3:8b

# Delete a model
python helpers/python/ollama_compat.py delete my-model:latest
```

---

## lora_merge.py

**Purpose:** LoRA weight merging for LLM and diffusion checkpoints.

Supports PEFT-style (`lora_A` / `lora_B`) and Kohya-style (`lora_down` / `lora_up`) LoRA formats.

### Public API

#### `load_tensors(path) → dict[str, np.ndarray]`
Load all tensors from a `.safetensors` file.

#### `merge_lora_peft(base_tensors, lora_tensors, alpha) → dict`
Merge PEFT-style LoRA tensors.  Formula: `W_merged = W_base + alpha * (lora_B @ lora_A)`.

#### `merge_lora_kohya(base_tensors, lora_tensors, alpha) → dict`
Merge Kohya-style LoRA tensors.  Formula: `W_merged = W_base + alpha * (lora_up @ lora_down)`.

### CLI Usage

```bash
# Merge PEFT LoRA
python helpers/python/lora_merge.py base.safetensors adapter.safetensors merged.safetensors --alpha 1.0 --style peft

# Merge Kohya LoRA
python helpers/python/lora_merge.py base.safetensors kohya_adapter.safetensors merged.safetensors --style kohya
```

---

## quant_utils.py

**Purpose:** Quantisation preset helper for GGUF models.

### Public API

#### `resolve_preset(name) → QuantPreset`
Resolve a preset name or alias to a `QuantPreset` object.

#### `llama_cpp_flag(name) → str`
Return the `llama.cpp` `--outtype` flag value for a given preset name.

#### `estimate_model_size_gb(n_parameters, preset, overhead_gb) → float`
Estimate on-disk size in GB for a quantised model.

#### `list_presets(suitable_for=None) → list[QuantPreset]`
Return all presets, optionally filtered by tag.

Available presets: `fp32`, `fp16`, `bf16`, `q8_0`, `q5_k_s`, `q5_k_m`, `q4_k_s`, `q4_k_m`, `q4_0`, `q4_1`, `q3_k_s`, `q3_k_m`, `q2_k`.

### CLI Usage

```bash
# List all presets
python helpers/python/quant_utils.py list

# Show preset details
python helpers/python/quant_utils.py info q4_k_m

# Estimate model size
python helpers/python/quant_utils.py estimate 7e9 q4_k_m
```

---

## sympy_calc.py

**Purpose:** SymPy-based calculus engine for the AI calculator app.

### Public API

#### `calc_derivative(expr_str, variable, order) → dict`
Compute `d^n/dx^n f(x)`.  Returns `{latex, numeric, expr}`.

#### `calc_integral(expr_str, variable, lower, upper) → dict`
Compute indefinite or definite integral.

#### `calc_limit(expr_str, variable, point, direction) → dict`
Compute `lim_{x→point} f(x)`.  `direction` is `"+"`, `"-"`, or `"+-"`.

#### `solve_ode(ode_str, func_name, variable, ics) → dict`
Solve an ODE.  `ics` is a dict of initial conditions, e.g. `{"y(0)": "1"}`.

#### `numeric_evaluate(expr_str, variable_values, precision) → dict`
Numerically evaluate an expression with variable substitutions.

#### `evaluate(request) → dict`
Unified dispatcher used by the `/api/calc` backend endpoint.

### CLI Usage

```bash
python helpers/python/sympy_calc.py derivative "x**3 + 2*x" --var x --order 2
python helpers/python/sympy_calc.py integral "sin(x)" --var x --lower 0 --upper pi
python helpers/python/sympy_calc.py limit "sin(x)/x" --var x --point 0 --direction +-
python helpers/python/sympy_calc.py ode "y(x).diff(x) + y(x)" --var x --func y
python helpers/python/sympy_calc.py numeric "sqrt(2) + pi" --precision 20
```
