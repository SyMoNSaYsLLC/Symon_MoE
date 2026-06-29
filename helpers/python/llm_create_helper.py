from __future__ import annotations

from typing import Any

from backend.app.jobs import JOB_MANAGER


def submit_create(prompt: str, model: str = "llama3", context: dict[str, Any] | None = None) -> str:
    formatted = f"Create artifact from request:\n{prompt}\nReturn only final artifact content."
    job = JOB_MANAGER.submit_llm_job(
        operation="create",
        prompt=formatted,
        model=model,
        context=context or {},
    )
    return job["id"]
