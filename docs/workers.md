# Worker Architecture

## Workers

- `database:sqlite` serialises persistence operations.
- `conversion:*` handles conversion jobs.
- `migration:v1` handles migration jobs.
- `llm:ollama` handles create/update and recipe generation jobs.
- `mining` and `embedded` workers stream operational stats.

## Queue and Status

Use `GET /api/workers/status` for queue depth and active jobs.
Use `GET /api/db/events` for persisted worker events.

## Throttling

`helpers/python/hardware_throttle.py` provides `throttle_check()`.
Workers pause intake when CPU/GPU usage exceeds configured limits.
