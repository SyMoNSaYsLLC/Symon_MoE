"""FastAPI router for the planning layer."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..planning.arch_validation import ArchValidator
from ..planning.copilot_prompts import CopilotPromptGenerator
from ..planning.dependency_graph import DependencyGraph
from ..planning.milestones import MilestoneTracker
from ..planning.roadmap import RoadmapGenerator
from ..planning.task_breakdown import TaskBreaker
from ..planning.worker_plans import WorkerPlanGenerator

router = APIRouter(prefix="/api/planning", tags=["planning"])

_roadmap_gen = RoadmapGenerator()
_milestone_tracker = MilestoneTracker()
_task_breaker = TaskBreaker()
_dep_graph = DependencyGraph()
_worker_plan_gen = WorkerPlanGenerator()
_copilot_prompt_gen = CopilotPromptGenerator()
_arch_validator = ArchValidator()


# ── Roadmap ──────────────────────────────────────────────────────────────────

class RoadmapCreateRequest(BaseModel):
    title: str = Field(..., min_length=1)
    description: str = ""
    phases: list[str] = Field(default_factory=list)


class RoadmapPhaseUpdateRequest(BaseModel):
    phase_name: str = Field(..., min_length=1)
    status: str = Field(..., min_length=1)


@router.post("/roadmaps")
def create_roadmap(request: RoadmapCreateRequest) -> dict:
    return _roadmap_gen.create(request.title, request.description, request.phases)


@router.get("/roadmaps")
def list_roadmaps() -> dict:
    return {"roadmaps": _roadmap_gen.list()}


@router.get("/roadmaps/{roadmap_id}")
def get_roadmap(roadmap_id: str) -> dict:
    roadmap = _roadmap_gen.get(roadmap_id)
    if roadmap is None:
        raise HTTPException(status_code=404, detail="Roadmap not found")
    return roadmap


@router.patch("/roadmaps/{roadmap_id}/phase")
def update_roadmap_phase(roadmap_id: str, request: RoadmapPhaseUpdateRequest) -> dict:
    roadmap = _roadmap_gen.update_phase_status(roadmap_id, request.phase_name, request.status)
    if roadmap is None:
        raise HTTPException(status_code=404, detail="Roadmap not found")
    return roadmap


# ── Milestones ────────────────────────────────────────────────────────────────

class MilestoneCreateRequest(BaseModel):
    roadmap_id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    description: str = ""
    target_date: str | None = None


class MilestoneStatusRequest(BaseModel):
    status: str = Field(..., min_length=1)


@router.post("/milestones")
def create_milestone(request: MilestoneCreateRequest) -> dict:
    return _milestone_tracker.create(
        request.roadmap_id, request.name, request.target_date, request.description
    )


@router.get("/milestones")
def list_milestones(roadmap_id: str | None = None) -> dict:
    return {"milestones": _milestone_tracker.list(roadmap_id)}


@router.get("/milestones/{milestone_id}")
def get_milestone(milestone_id: str) -> dict:
    milestone = _milestone_tracker.get(milestone_id)
    if milestone is None:
        raise HTTPException(status_code=404, detail="Milestone not found")
    return milestone


@router.patch("/milestones/{milestone_id}/status")
def update_milestone_status(milestone_id: str, request: MilestoneStatusRequest) -> dict:
    try:
        milestone = _milestone_tracker.update_status(milestone_id, request.status)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if milestone is None:
        raise HTTPException(status_code=404, detail="Milestone not found")
    return milestone


# ── Tasks ─────────────────────────────────────────────────────────────────────

class TaskCreateRequest(BaseModel):
    milestone_id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    description: str = ""
    estimate_hours: float = 0.0
    assignee: str | None = None


class TaskStatusRequest(BaseModel):
    status: str = Field(..., min_length=1)


class SubtaskRequest(BaseModel):
    name: str = Field(..., min_length=1)


@router.post("/tasks")
def create_task(request: TaskCreateRequest) -> dict:
    return _task_breaker.create(
        request.milestone_id,
        request.name,
        request.description,
        request.estimate_hours,
        request.assignee,
    )


@router.get("/tasks")
def list_tasks(milestone_id: str | None = None) -> dict:
    return {"tasks": _task_breaker.list(milestone_id)}


@router.get("/tasks/{task_id}")
def get_task(task_id: str) -> dict:
    task = _task_breaker.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.patch("/tasks/{task_id}/status")
def update_task_status(task_id: str, request: TaskStatusRequest) -> dict:
    task = _task_breaker.update_status(task_id, request.status)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("/tasks/{task_id}/subtasks")
def add_subtask(task_id: str, request: SubtaskRequest) -> dict:
    subtask = _task_breaker.add_subtask(task_id, request.name)
    if subtask is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return subtask


# ── Dependency Graph ──────────────────────────────────────────────────────────

class DependencyRequest(BaseModel):
    node_id: str = Field(..., min_length=1)
    depends_on: str = Field(..., min_length=1)


@router.get("/dependencies")
def get_dependency_graph() -> dict:
    return _dep_graph.as_dict()


@router.post("/dependencies")
def add_dependency(request: DependencyRequest) -> dict:
    try:
        return _dep_graph.add_dependency(request.node_id, request.depends_on)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/dependencies")
def remove_dependency(request: DependencyRequest) -> dict:
    return _dep_graph.remove_dependency(request.node_id, request.depends_on)


@router.get("/dependencies/{node_id}")
def node_dependencies(node_id: str) -> dict:
    return {
        "node": node_id,
        "dependencies": _dep_graph.dependencies(node_id),
        "dependents": _dep_graph.dependents(node_id),
    }


# ── Worker Plans ──────────────────────────────────────────────────────────────

class WorkerPlanRequest(BaseModel):
    worker_type: str = Field(..., min_length=1)
    architecture: str = Field(..., min_length=1)
    capabilities: list[str] = Field(default_factory=list)
    notes: str = ""


@router.post("/worker-plans")
def create_worker_plan(request: WorkerPlanRequest) -> dict:
    return _worker_plan_gen.generate(
        request.worker_type,
        request.architecture,
        request.capabilities,
        request.notes,
    )


@router.get("/worker-plans")
def list_worker_plans() -> dict:
    return {"plans": _worker_plan_gen.list()}


@router.get("/worker-plans/{plan_id}")
def get_worker_plan(plan_id: str) -> dict:
    plan = _worker_plan_gen.get(plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Worker plan not found")
    return plan


@router.post("/worker-plans/{plan_id}/approve")
def approve_worker_plan(plan_id: str) -> dict:
    plan = _worker_plan_gen.approve(plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Worker plan not found")
    return plan


# ── Copilot Prompts ───────────────────────────────────────────────────────────

class PromptGenerateRequest(BaseModel):
    template: str = Field(..., min_length=1)
    variables: dict[str, str] = Field(default_factory=dict)


@router.get("/copilot-prompts/templates")
def list_prompt_templates() -> dict:
    return {"templates": _copilot_prompt_gen.list_templates()}


@router.post("/copilot-prompts/generate")
def generate_copilot_prompt(request: PromptGenerateRequest) -> dict:
    try:
        return _copilot_prompt_gen.generate(request.template, request.variables)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ── Architecture Validation ───────────────────────────────────────────────────

class ValidationStartRequest(BaseModel):
    change_description: str = Field(..., min_length=1)
    custom_items: list[str] = Field(default_factory=list)


class ValidationCheckRequest(BaseModel):
    item_id: str = Field(..., min_length=1)
    checked: bool


@router.post("/validations")
def start_validation(request: ValidationStartRequest) -> dict:
    return _arch_validator.start(
        request.change_description,
        request.custom_items or None,
    )


@router.get("/validations")
def list_validations() -> dict:
    return {"validations": _arch_validator.list()}


@router.get("/validations/{validation_id}")
def get_validation(validation_id: str) -> dict:
    validation = _arch_validator.get(validation_id)
    if validation is None:
        raise HTTPException(status_code=404, detail="Validation not found")
    return validation


@router.patch("/validations/{validation_id}/check")
def check_validation_item(validation_id: str, request: ValidationCheckRequest) -> dict:
    validation = _arch_validator.check_item(validation_id, request.item_id, request.checked)
    if validation is None:
        raise HTTPException(status_code=404, detail="Validation not found")
    return validation
