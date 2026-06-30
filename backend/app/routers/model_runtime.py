from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..model_runtime.detector import inspect_model
from ..model_runtime.runtime_router import route_runtime, runtime_capabilities
from ..model_runtime.schemas import InspectRequest, InspectResponse, RouteRequest, RuntimeDecision
from ..model_runtime.worker_loader import list_workers

router = APIRouter(prefix="/model-runtime", tags=["model-runtime"])


@router.post("/inspect", response_model=InspectResponse)
def inspect(request: InspectRequest) -> InspectResponse:
    return inspect_model(request.path, request.files)


@router.post("/route", response_model=RuntimeDecision)
def route(request: RouteRequest) -> RuntimeDecision:
    try:
        return route_runtime(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/capabilities")
def capabilities() -> dict:
    return runtime_capabilities().model_dump()


@router.get("/workers")
def workers() -> dict:
    return {"workers": [worker.model_dump() for worker in list_workers()]}
