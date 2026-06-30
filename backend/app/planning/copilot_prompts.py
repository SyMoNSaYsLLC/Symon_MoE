"""Copilot prompt generation for the planning layer."""
from __future__ import annotations

from typing import Any

PROMPT_TEMPLATES: dict[str, str] = {
    "new_worker": (
        "You are an expert Python/FastAPI developer.\n"
        "Implement a new {worker_type} worker for the Symon_MoE backend.\n"
        "Architecture: {architecture}\n"
        "Required capabilities: {capabilities}\n"
        "Follow the existing worker patterns in backend/app/workers/.\n"
        "The worker must integrate hardware throttle checks and register itself in "
        "backend/app/model_runtime/registry.py.\n"
        "Additional notes: {notes}"
    ),
    "new_router": (
        "You are an expert Python/FastAPI developer.\n"
        "Add a new FastAPI router for the '{feature}' feature.\n"
        "Place it in backend/app/routers/{feature}.py.\n"
        "Use prefix /api/{feature} and tag '{feature}'.\n"
        "Endpoints needed: {endpoints}\n"
        "Follow the existing router patterns in backend/app/routers/.\n"
        "Additional notes: {notes}"
    ),
    "refactor": (
        "You are an expert Python developer.\n"
        "Refactor the following module: {module}\n"
        "Goals: {goals}\n"
        "Constraints: {constraints}\n"
        "Ensure backward compatibility with existing API contracts.\n"
        "Additional notes: {notes}"
    ),
    "test_suite": (
        "You are an expert Python/pytest developer.\n"
        "Write a comprehensive test suite for: {target}\n"
        "Cover: {coverage_goals}\n"
        "Use pytest with fixtures. Mock external services.\n"
        "Additional notes: {notes}"
    ),
    "custom": "{prompt}",
}


class CopilotPromptGenerator:
    """Generate structured Copilot prompts for common development tasks."""

    def generate(self, template: str, variables: dict[str, str]) -> dict[str, Any]:
        if template not in PROMPT_TEMPLATES:
            raise ValueError(
                f"Unknown template {template!r}. Available: {sorted(PROMPT_TEMPLATES)}"
            )
        try:
            prompt_text = PROMPT_TEMPLATES[template].format_map(variables)
        except KeyError as exc:
            raise ValueError(f"Missing template variable: {exc}") from exc
        return {
            "template": template,
            "variables": variables,
            "prompt": prompt_text,
        }

    def list_templates(self) -> list[str]:
        return sorted(PROMPT_TEMPLATES)
