from __future__ import annotations

from typing import Any

from backend.app.jobs import JOB_MANAGER


def submit_update(artifact_id: str, diff: str, model: str = "llama3", extra: dict[str, Any] | None = None) -> str:
    prompt = (
        f"Apply this diff to artifact {artifact_id}:\n{diff}\n"
        "Return only updated artifact content."
    )
    job = JOB_MANAGER.submit_llm_job(
        operation="update",
        prompt=prompt,
        model=model,
        context={"artifact_id": artifact_id, "diff": diff, **(extra or {})},
    )
    return job["id"]
