# Symon_MoE / Symoneural Platform

This repository now separates orchestration, backend API, and frontend UI while preserving existing converter/interface submodules.

## Product Structure

- `orchestration/convert.py` — retained as the conversion orchestrator.
- `converters/*` and `interfaces/*` — retained submodule structure.
- `backend/` — FastAPI system-of-record for model operations.
- `frontend/` — static Symoneural UI shell (`index.html`, `css/`, `js/`).

## Scope Decisions (explicit)

1. **Migration v1 architectures:** `llama + qwen2 + mistral` (3→1 GGUF).
2. **Frontend location:** inside this repository at `frontend/`.
3. **Cloudflare auth in v1:** no (Cloudflare used for edge proxy/CDN/CORS posture first).

## Backend API

Run:

```bash
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

Core endpoints:

- `GET /api/health`
- `GET /api/models/discover`
- `POST /api/jobs/conversion`
- `POST /api/jobs/migration`
- `GET /api/jobs`
- `GET /api/jobs/{job_id}`
- `GET /api/jobs/{job_id}/logs`
- `GET /api/workers/status`
- `GET /api/migration/supported`
- `GET /api/artifacts/{artifact_type}/{filename}`

## Model Storage Contract

Backend-visible and frontend-visible model root:

`/home/runner/work/Symon_MoE/Symon_MoE/frontend/models`

Contracted folders/files:

```text
frontend/models/
  raw/        # input model folders
  converted/  # GGUF conversion outputs
  migrated/   # 3->1 migration outputs
  metadata.json
```

## Frontend

`frontend/index.html` provides:

- Symoneural-branded dashboard shell
- guided model onboarding text and required file guidance
- conversion and migration submission forms
- API-driven scan/job/worker polling and logs

## Migration Rules

Migration is a first-class backend feature with validation:

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
7. branding language and hardening in follow-up deployment pass
