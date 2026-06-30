from __future__ import annotations

from .schemas import RouteRequest


def select_converter(request: RouteRequest) -> str | None:
    if request.task == "conversion":
        return request.inspection.suggested_converter
    if request.task == "deployment":
        return None
    # TODO: Add converter policy by target runtime and quantization constraints.
    return request.inspection.suggested_converter
