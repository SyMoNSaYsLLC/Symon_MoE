# Symoneural Backend API Reference

The FastAPI backend runs at `http://localhost:8000` by default.

Start the server:

```bash
pip install -r requirements.txt
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

Interactive Swagger UI: `http://localhost:8000/docs`
ReDoc UI: `http://localhost:8000/redoc`

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `SYMON_MODELS_ROOT` | `frontend/models` | Root directory for model storage |
| `SYMON_ALLOWED_ORIGINS` | `http://localhost:8000,…` | Comma-separated CORS allowed origins |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama instance base URL |
| `CODE_MODEL` | `codellama` | Default model for code-assist router |
| `SD_CPP_BIN` | `converters/diffusers_cpp/build/bin/sd` | Path to stable-diffusion.cpp binary |

---

## Health & Discovery

### `GET /api/health`

Returns service health status, models root, and scope decisions.

**Response**
```json
{
  "status": "ok",
  "service": "symoneural-backend",
  "models_root": "/path/to/frontend/models",
  "scope_decisions": { ... }
}
```

### `GET /api/models/discover`

Scans `frontend/models` and returns available models grouped by category.

**Response**
```json
{
  "raw": ["my-llm-model"],
  "converted": ["llama.gguf"],
  "migrated": ["symoneural-migrated.gguf"]
}
```

---

## Job Management

### `POST /api/jobs/conversion`

Submit a model conversion job (HuggingFace → GGUF).

**Request body**
```json
{
  "model_name": "my-llm-model",
  "architecture": "llama",
  "outtype": "q8_0",
  "output_name": "my-model.gguf",
  "source_file": null
}
```

Supported architectures: `llama`, `qwen2`, `mistral`, `diffusion`.

### `POST /api/jobs/migration`

Submit a 3→1 GGUF migration job (llama + qwen2 + mistral → one merged GGUF).

**Request body**
```json
{
  "sources": [
    {"architecture": "llama",   "artifact_name": "llama.gguf"},
    {"architecture": "qwen2",   "artifact_name": "qwen2.gguf"},
    {"architecture": "mistral", "artifact_name": "mistral.gguf"}
  ],
  "target_name": "symoneural-migrated.gguf"
}
```

### `GET /api/jobs`

List all submitted jobs with their status.

### `GET /api/jobs/{job_id}`

Get full status, logs, and result of a specific job.

### `GET /api/jobs/{job_id}/logs`

Get only the log lines for a job.

### `GET /api/workers/status`

Return the current state of all background worker threads.

### `GET /api/migration/supported`

Return supported migration architecture combinations.

---

## Artifact Download

### `GET /api/artifacts/{artifact_type}/{filename}`

Download a converted or migrated model file.

- `artifact_type`: `converted` or `migrated`
- `filename`: Base filename only (no path traversal allowed)

---

## Chat (`/api/chat`)

Routes to an Ollama instance.

### `GET /api/chat/models`

List models currently available in the connected Ollama instance.

### `POST /api/chat`

Send a chat request and stream or collect the response.

**Request body**
```json
{
  "model": "llama3",
  "messages": [
    {"role": "user", "content": "Hello!"}
  ],
  "stream": true,
  "temperature": 0.8,
  "system": "You are a helpful assistant."
}
```

When `stream: true`, returns `text/plain` SSE-style streamed tokens.
When `stream: false`, returns `{"response": "..."}`.

---

## Code Assistant (`/api/code`)

### `POST /api/code`

Submit a code snippet for LLM-assisted analysis.

**Request body**
```json
{
  "code": "def add(a, b):\n    return a + b",
  "action": "explain",
  "language": "python",
  "model": "codellama",
  "stream": true
}
```

`action` values: `explain`, `complete`, `refactor`, `debug`.

---

## Calculator (`/api/calc`)

Powered by SymPy.

### `GET /api/calc/modes`

List supported calculator modes.

### `POST /api/calc`

Evaluate a mathematical expression.

**Request body — derivative**
```json
{"mode": "derivative", "expr": "x**3 + 2*x", "var": "x", "order": 1}
```

**Request body — definite integral**
```json
{"mode": "integral", "expr": "sin(x)", "var": "x", "lower": "0", "upper": "pi"}
```

**Request body — limit**
```json
{"mode": "limit", "expr": "sin(x)/x", "var": "x", "point": "0", "direction": "+-"}
```

**Request body — ODE**
```json
{"mode": "ode", "expr": "y(x).diff(x) + y(x) - x", "var": "x", "func": "y"}
```

**Request body — numeric**
```json
{"mode": "numeric", "expr": "sqrt(2) + pi", "values": {}, "precision": 15}
```

**Response**
```json
{"latex": "...", "numeric": "...", "expr": "..."}
```

---

## Text-to-Image (`/api/image`)

Requires `stable-diffusion.cpp` built under `converters/diffusers_cpp`.

### `GET /api/image/models`

List GGUF diffusion model files.

### `POST /api/image`

Queue an image generation job.

**Request body**
```json
{
  "prompt": "a red panda in a forest",
  "negative_prompt": "blurry, low quality",
  "model": "sd-v1-5.gguf",
  "width": 512,
  "height": 512,
  "steps": 20,
  "cfg_scale": 7.0,
  "seed": -1
}
```

### `GET /api/image/jobs`

List all image generation jobs.

### `GET /api/image/jobs/{job_id}`

Get the status and output path of a specific image job.

---

## Text-to-Video (`/api/video`)

Routes to `orchestration/video_pipeline.py` (CogVideoX / ModelScope).

### `POST /api/video`

Queue a text-to-video job.

**Request body**
```json
{
  "prompt": "a butterfly landing on a flower",
  "frame_count": 16,
  "fps": 8,
  "width": 512,
  "height": 320
}
```

### `GET /api/video/jobs`

List all video generation jobs.

### `GET /api/video/jobs/{job_id}`

Get the status and output path of a specific video job.

---

## IPTV (`/api/iptv`)

### `POST /api/iptv/parse`

Fetch and parse an M3U playlist from a URL.

**Request body**
```json
{"url": "https://example.com/playlist.m3u"}
```

**Response**
```json
{
  "source": "https://example.com/playlist.m3u",
  "total": 120,
  "groups": ["News", "Sports"],
  "channels": [{"name": "BBC News", "group": "News", "url": "https://..."}]
}
```

### `POST /api/iptv/parse/text`

Parse a raw M3U string.

**Request body**
```json
{"content": "#EXTM3U\n#EXTINF:-1,Channel Name\nhttps://stream.url/live"}
```

---

## Tensor Lab (`/api/tensor`)

Tensor inspection and API-key-based model proxy.

### `GET /api/tensor/dtypes`

List supported tensor data types and their descriptions.

### `POST /api/tensor/create`

Create a tensor (zeros, ones, range, or random) and return its metadata and flat values.

**Request body**
```json
{
  "shape": [3, 4],
  "dtype": "float32",
  "fill": "zeros"
}
```

`fill` values: `zeros`, `ones`, `range`, `random`.

### `POST /api/tensor/op`

Apply a binary operation to two same-shape tensors.

**Request body**
```json
{
  "a": [[1, 2], [3, 4]],
  "b": [[5, 6], [7, 8]],
  "op": "add"
}
```

`op` values: `add`, `sub`, `mul`, `matmul`.

### `GET /api/tensor/model/info`

Query an Ollama model's parameter list via the Ollama `/api/show` endpoint.
Pass the model name as a query parameter: `?model=llama3`.

### `POST /api/tensor/chat`

Send a chat completion to an Ollama-compatible endpoint, optionally overriding
the `base_url` and supplying an `api_key` (passed as a ******

**Request body**
```json
{
  "model": "llama3",
  "messages": [{"role": "user", "content": "Hi"}],
  "temperature": 0.7,
  "top_p": 0.9,
  "top_k": 40,
  "repeat_penalty": 1.1,
  "num_predict": 512,
  "stream": true,
  "base_url": "http://localhost:11434",
  "api_key": ""
}
```
