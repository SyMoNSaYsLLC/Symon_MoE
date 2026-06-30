# Symon_MoE / Symoneural Platform

This repository separates orchestration, backend API, and frontend UI while
preserving existing converter/interface submodules.

## Product Structure

```
.
├── orchestration/          # Conversion & inference pipeline scripts
├── converters/             # Git submodules: llama.cpp, ComfyUI-GGUF, stable-diffusion.cpp, Ollama, AUTOMATIC1111
├── interfaces/             # Git submodules: opencode-cli, llama_cpp_server, ComfyUI, Open WebUI
├── backend/app/            # FastAPI system-of-record for model operations + new feature APIs
├── frontend/               # Static Symoneural UI shell
│   ├── index.html          # Home / Model Manager (with sidebar nav)
│   ├── apps/               # Individual app pages (chatbot, calculator, code_assist, iptv, …)
│   ├── js/apps/            # Per-app JavaScript modules
│   └── css/                # Shared styles (styles.css, apps.css)
└── helpers/                # Language-specific helper libraries
    ├── python/             # Python helpers (tensor_utils, gguf_inspect, sympy_calc, …)
    ├── cpp/                # C++ helpers (gguf_reader, tensor_ops, llama_bridge, …)
    ├── rust/               # Rust workspace (gguf_parser, ollama_client, m3u_parser)
    └── java/               # Java helpers (GGUFMetaReader, OllamaClient, SymPyBridge)
```

## Submodules

| Path | Repository |
|------|-----------|
| `converters/llm_engine`      | [ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp) |
| `converters/diff_engine`     | [city96/ComfyUI-GGUF](https://github.com/city96/ComfyUI-GGUF) |
| `converters/stable_diffusion`| [AUTOMATIC1111/stable-diffusion-webui](https://github.com/AUTOMATIC1111/stable-diffusion-webui) (dev) |
| `converters/diffusers_cpp`   | [leejet/stable-diffusion.cpp](https://github.com/leejet/stable-diffusion.cpp) |
| `converters/ollama`          | [ollama/ollama](https://github.com/ollama/ollama) |
| `interfaces/opencode_cli`    | [anomalyco/opencode](https://github.com/anomalyco/opencode) |
| `interfaces/llama_cpp_server`| [ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp) |
| `interfaces/comfyui`         | [comfyanonymous/ComfyUI](https://github.com/comfyanonymous/ComfyUI) |
| `interfaces/open_webui`      | [open-webui/open-webui](https://github.com/open-webui/open-webui) |

Initialise all submodules after cloning:

```bash
git submodule update --init --recursive
```

## Scope Decisions (explicit)

1. **Migration v1 architectures:** `llama + qwen2 + mistral` (3→1 GGUF).
2. **Frontend location:** inside this repository at `frontend/`.
3. **Cloudflare auth in v1:** no (Cloudflare used for edge proxy/CDN/CORS posture first).

## Documentation

Full reference documentation lives under `docs/`:

| File | Content |
|------|---------|
| [`docs/backend-api.md`](docs/backend-api.md) | Complete REST API reference for all endpoints |
| [`docs/helpers-python.md`](docs/helpers-python.md) | Python helper scripts API + CLI reference |
| [`docs/helpers-cpp.md`](docs/helpers-cpp.md) | C++ helper library API + CLI reference |
| [`docs/helpers-rust.md`](docs/helpers-rust.md) | Rust crate API + CLI reference |
| [`docs/helpers-java.md`](docs/helpers-java.md) | Java class API + CLI reference |
| [`docs/tensor-guide.md`](docs/tensor-guide.md) | Tensor concepts, dtypes, LoRA, and GGUF guide |
| [`docs/mining.md`](docs/mining.md) | Mining setup and APIs |
| [`docs/embedded.md`](docs/embedded.md) | Embedded build setup and workflow |
| [`docs/terminal.md`](docs/terminal.md) | Web terminal usage and security |
| [`docs/workers.md`](docs/workers.md) | Worker queues and throttling |

## Man Pages

Unix-style man pages for every Python CLI tool live under `man/man1/`:

```bash
man -l man/man1/tensor_utils.1
man -l man/man1/gguf_inspect.1
man -l man/man1/quant_utils.1
man -l man/man1/lora_merge.1
man -l man/man1/diffusion_convert.1
man -l man/man1/ollama_compat.1
man -l man/man1/sympy_calc.1
```

To install system-wide (Linux/macOS):

```bash
sudo cp man/man1/*.1 /usr/local/share/man/man1/
sudo mandb       # Linux
sudo makewhatis  # macOS
```



```bash
pip install -r requirements.txt
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

### Core endpoints (model management)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/models/discover` | Scan model storage |
| POST | `/api/jobs/conversion` | Submit conversion job |
| POST | `/api/jobs/migration` | Submit 3→1 migration job |
| GET | `/api/jobs` | List all jobs |
| GET | `/api/jobs/{job_id}` | Get job status/logs |
| GET | `/api/workers/status` | Worker queue status |
| GET | `/api/migration/supported` | Supported migration combos |
| GET | `/api/artifacts/{type}/{filename}` | Download artifact |

### New app endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/chat` | Stream chat from Ollama |
| GET | `/api/chat/models` | List Ollama models |
| POST | `/api/code` | Code explain/complete/refactor/debug |
| POST | `/api/image` | Queue txt2img job |
| GET | `/api/image/models` | List diffusion GGUF models |
| GET | `/api/image/jobs/{id}` | Image job status |
| POST | `/api/video` | Queue text-to-video job |
| GET | `/api/video/jobs/{id}` | Video job status |
| POST | `/api/calc` | SymPy expression evaluation |
| GET | `/api/calc/modes` | List calculator modes |
| POST | `/api/iptv/parse` | Parse M3U playlist from URL |
| POST | `/api/iptv/parse/text` | Parse M3U from raw text |
| GET | `/api/tensor/dtypes` | List tensor dtypes |
| POST | `/api/tensor/create` | Create a tensor (zeros/ones/range/random) |
| POST | `/api/tensor/op` | Apply binary op to two tensors |
| GET | `/api/tensor/model/info` | Fetch Ollama model parameters |
| POST | `/api/tensor/chat` | Chat with full parameter control + API key |

## Frontend Apps

Open `http://localhost:8000` to access the Symoneural UI.  The sidebar
provides navigation to:

| App | Path | Description |
|-----|------|-------------|
| Model Manager | `/` | Existing model conversion/migration UI |
| Chatbot | `/apps/chatbot.html` | Streaming chat with any Ollama model |
| Code Assistant | `/apps/code_assist.html` | Monaco editor + LLM code actions |
| Calculator | `/apps/calculator.html` | SymPy symbolic calculator (KaTeX output) |
| Text to Image | `/apps/text_to_image.html` | Diffusion GGUF image generation |
| Text to Video | `/apps/text_to_video.html` | CogVideoX / ModelScope video generation |
| IPTV | `/apps/iptv.html` | M3U playlist loader + HLS player |
| Tensor Lab | `/apps/tensor_lab.html` | Tensor creation/ops, model param customisation, API-key chat |
| Mining | `/apps/mining.html` | Miner pool discovery, controls, and status dashboard |
| Embedded | `/apps/embedded.html` | Yocto/PetaLinux build queue and layer management |
| LLM Ops | `/apps/llm_ops.html` | LLM create/update job queue UI |
| Terminal | `/apps/terminal.html` | Browser VT100 terminal over WebSocket |

## Helper Libraries

### Python (`helpers/python/`)

```bash
pip install gguf safetensors sympy httpx numpy
```

| Script | Purpose |
|--------|---------|
| `tensor_utils.py` | safetensors inspection, slicing, dtype casting |
| `gguf_inspect.py` | GGUF metadata reader/writer |
| `diffusion_convert.py` | .safetensors → GGUF via stable-diffusion.cpp |
| `ollama_compat.py` | Modelfile generator + Ollama REST wrappers |
| `lora_merge.py` | LoRA weight merging (PEFT and Kohya styles) |
| `quant_utils.py` | Quantisation preset helper |
| `sympy_calc.py` | SymPy calculus engine (derivatives, integrals, ODE, …) |

### C++ (`helpers/cpp/`)

See [`helpers/cpp/README.md`](helpers/cpp/README.md) for full build instructions.

```bash
cmake -B helpers/cpp/build -S helpers/cpp -DCMAKE_BUILD_TYPE=Release
cmake --build helpers/cpp/build -j$(nproc)
```

| File | Purpose |
|------|---------|
| `gguf_reader.h/.cpp` | Standalone GGUF binary parser |
| `tensor_ops.h/.cpp` | Tensor arithmetic (add, mul, matmul, reshape) |
| `llama_bridge.cpp` | Headless LLM inference CLI |
| `diffusion_bridge.cpp` | Headless txt2img CLI |

### Rust (`helpers/rust/`)

Requires Rust ≥ 1.75 (`rustup`).

```bash
cd helpers/rust
cargo build --release
```

| Crate | Purpose |
|-------|---------|
| `gguf_parser` | Async GGUF file parser |
| `ollama_client` | Async Ollama REST client |
| `m3u_parser` | M3U/M3U8 playlist parser and fetcher |

### Java (`helpers/java/`)

Requires Java 17+ and Maven 3.8+.

```bash
cd helpers/java
mvn package
java -cp target/symoneural-helpers-0.1.0-jar-with-dependencies.jar com.symoneural.GGUFMetaReader model.gguf
```

| Class | Purpose |
|-------|---------|
| `GGUFMetaReader` | JVM GGUF metadata reader |
| `OllamaClient` | Java HTTP client for Ollama API (OkHttp) |
| `SymPyBridge` | Subprocess bridge to run Python SymPy from JVM |

## Model Storage Contract

Backend-visible and frontend-visible model root:

`frontend/models/`

```text
frontend/models/
  raw/        # input model folders
  converted/  # GGUF conversion outputs
  migrated/   # 3->1 migration outputs
  images/     # text-to-image outputs
  videos/     # text-to-video outputs
  metadata.json
```

## Orchestration

| Script | Purpose |
|--------|---------|
| `orchestration/convert.py` | Auto-detect and dispatch LLM or diffusion conversion |
| `orchestration/image_pipeline.py` | txt2img / img2img via stable-diffusion.cpp |
| `orchestration/video_pipeline.py` | Text-to-video via CogVideoX or ModelScope |

## Migration Rules

- Accepts exactly 3 sources.
- Supports only the v1 architecture combination (`llama`, `qwen2`, `mistral`).
- Verifies source artifacts exist in `frontend/models/converted`.
- Returns actionable `400` errors for unsupported or incomplete requests.

## Cloudflare Integration (post API/UI contract)

Recommended rollout after API/UI stability:

1. Put `frontend/` behind Cloudflare.
2. Proxy `/api/*` to FastAPI origin.
3. Restrict origin access and tighten CORS to trusted domain(s).
4. Start with CDN/proxy/bot controls; evaluate auth later as a separate decision.

## Milestones

1. backend skeleton ✅
2. frontend shell ✅
3. model-folder onboarding ✅
4. worker execution queues ✅
5. GGUF migration flow ✅
6. Cloudflare integration plan ✅
7. New submodules (stable-diffusion.cpp, Ollama, ComfyUI, Open WebUI) ✅
8. Helper libraries (Python, C++, Rust, Java) ✅
9. New backend API routers (chat, code, image, video, calculator, iptv) ✅
10. Frontend app pages + sidebar nav ✅
11. Orchestration pipeline scripts (image, video) ✅
12. Documentation and man pages (docs/, man/man1/) ✅
13. Tensor Lab: frontend app + backend router with API-key support ✅



## Expansion Environment Variables

- `DB_PATH` (default: `frontend/models/symoneural.db`)
- `MINING_ENABLED`
- `EMBEDDED_BUILD_ROOT`
- `TERMINAL_SHELL`
- `HARDWARE_THROTTLE_CPU_LIMIT` / `HARDWARE_THROTTLE_GPU_LIMIT`
