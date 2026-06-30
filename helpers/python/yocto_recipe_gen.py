from __future__ import annotations

from backend.app.jobs import JOB_MANAGER


def generate_recipe(description: str, model: str = "llama3") -> str:
    prompt = (
        "Generate a Yocto .bb recipe for the following component. "
        "Return recipe text only.\n"
        f"Description: {description}"
    )
    job = JOB_MANAGER.submit_llm_job(operation="yocto_recipe", prompt=prompt, model=model)
    return job["id"]
