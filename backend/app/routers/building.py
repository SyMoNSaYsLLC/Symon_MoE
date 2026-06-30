"""FastAPI router for the building layer."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..building.code_gen import CodeGenOrchestrator
from ..building.embedded_builds import EmbeddedBuildManager
from ..building.packager import Packager
from ..building.release_artifacts import ReleaseArtifactCreator
from ..building.runtime_builds import RuntimeBuildManager
from ..building.scaffolder import RepoScaffolder
from ..building.test_runner import TestRunner

router = APIRouter(prefix="/api/building", tags=["building"])

_scaffolder = RepoScaffolder()
_code_gen = CodeGenOrchestrator()
_test_runner = TestRunner()
_packager = Packager()
_runtime_builds = RuntimeBuildManager()
_embedded_builds = EmbeddedBuildManager()
_release_creator = ReleaseArtifactCreator()


# ── Scaffolding ───────────────────────────────────────────────────────────────

class ScaffoldRequest(BaseModel):
    name: str = Field(..., min_length=1)
    description: str = ""
    extra_dirs: list[str] = Field(default_factory=list)


@router.post("/scaffold")
def scaffold_repo(request: ScaffoldRequest) -> dict:
    return _scaffolder.scaffold(
        request.name,
        request.description,
        request.extra_dirs or None,
    )


@router.get("/scaffold")
def list_scaffolds() -> dict:
    return {"jobs": _scaffolder.list()}


@router.get("/scaffold/{job_id}")
def get_scaffold(job_id: str) -> dict:
    job = _scaffolder.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Scaffold job not found")
    return job


# ── Code Generation ───────────────────────────────────────────────────────────

class CodeGenSubmitRequest(BaseModel):
    target: str = Field(..., min_length=1)
    template: str = Field(..., min_length=1)
    variables: dict[str, str] = Field(default_factory=dict)
    output_path: str | None = None


class CodeGenCompleteRequest(BaseModel):
    result: str = Field(..., min_length=1)


class CodeGenFailRequest(BaseModel):
    error: str = Field(..., min_length=1)


@router.post("/code-gen")
def submit_code_gen(request: CodeGenSubmitRequest) -> dict:
    try:
        return _code_gen.submit(
            request.target, request.template, request.variables, request.output_path
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid code-gen target") from exc


@router.get("/code-gen")
def list_code_gen_jobs() -> dict:
    return {"jobs": _code_gen.list()}


@router.get("/code-gen/{job_id}")
def get_code_gen_job(job_id: str) -> dict:
    job = _code_gen.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Code-gen job not found")
    return job


@router.post("/code-gen/{job_id}/complete")
def complete_code_gen(job_id: str, request: CodeGenCompleteRequest) -> dict:
    job = _code_gen.complete(job_id, request.result)
    if job is None:
        raise HTTPException(status_code=404, detail="Code-gen job not found")
    return job


@router.post("/code-gen/{job_id}/fail")
def fail_code_gen(job_id: str, request: CodeGenFailRequest) -> dict:
    job = _code_gen.fail(job_id, request.error)
    if job is None:
        raise HTTPException(status_code=404, detail="Code-gen job not found")
    return job


# ── Test Runner ───────────────────────────────────────────────────────────────

class TestRunRequest(BaseModel):
    extra_args: list[str] = Field(default_factory=list)


@router.post("/tests/run")
def run_tests(request: TestRunRequest) -> dict:
    result = _test_runner.run(request.extra_args or None)
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail="Invalid test arguments")
    # Return only metadata; retrieve full output (stdout/stderr) via GET /tests/runs/{run_id}
    return {
        "id": result.get("id"),
        "status": result.get("status"),
        "return_code": result.get("return_code"),
        "test_path": result.get("test_path"),
        "created_at": result.get("created_at"),
        "updated_at": result.get("updated_at"),
    }


@router.get("/tests/runs")
def list_test_runs() -> dict:
    return {"runs": _test_runner.list()}


@router.get("/tests/runs/{run_id}")
def get_test_run(run_id: str) -> dict:
    run = _test_runner.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Test run not found")
    return run


# ── Packager ──────────────────────────────────────────────────────────────────

class PackageCreateRequest(BaseModel):
    package_name: str = Field(..., min_length=1)
    fmt: str = "wheel"
    dry_run: bool = True


@router.post("/packages")
def create_package(request: PackageCreateRequest) -> dict:
    try:
        return _packager.create(
            request.package_name,
            request.fmt,
            request.dry_run,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid package format") from exc


@router.get("/packages")
def list_packages() -> dict:
    return {"jobs": _packager.list()}


@router.get("/packages/{job_id}")
def get_package_job(job_id: str) -> dict:
    job = _packager.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Package job not found")
    return job


# ── Runtime Builds ────────────────────────────────────────────────────────────

class RuntimeBuildSubmitRequest(BaseModel):
    runtime: str = Field(..., min_length=1)
    model_name: str = Field(..., min_length=1)
    source_path: str = Field(..., min_length=1)
    options: dict = Field(default_factory=dict)


@router.post("/runtime-builds")
def submit_runtime_build(request: RuntimeBuildSubmitRequest) -> dict:
    try:
        return _runtime_builds.submit(
            request.runtime,
            request.model_name,
            request.source_path,
            request.options or None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid runtime type") from exc


@router.get("/runtime-builds")
def list_runtime_builds(runtime: str | None = None) -> dict:
    return {"jobs": _runtime_builds.list(runtime)}


@router.get("/runtime-builds/{job_id}")
def get_runtime_build(job_id: str) -> dict:
    job = _runtime_builds.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Runtime build job not found")
    return job


# ── Embedded Image Builds ─────────────────────────────────────────────────────

class EmbeddedBuildSubmitRequest(BaseModel):
    machine: str = Field(..., min_length=1)
    recipe: str = Field(..., min_length=1)
    distro: str = "poky"
    layers: list[str] = Field(default_factory=list)
    extra_vars: dict[str, str] = Field(default_factory=dict)


class EmbeddedBuildUpdateRequest(BaseModel):
    status: str = Field(..., min_length=1)
    log_line: str | None = None


@router.post("/embedded-builds")
def submit_embedded_build(request: EmbeddedBuildSubmitRequest) -> dict:
    return _embedded_builds.submit(
        request.machine,
        request.recipe,
        request.distro,
        request.layers or None,
        request.extra_vars or None,
    )


@router.get("/embedded-builds")
def list_embedded_builds(machine: str | None = None) -> dict:
    return {"jobs": _embedded_builds.list(machine)}


@router.get("/embedded-builds/{job_id}")
def get_embedded_build(job_id: str) -> dict:
    job = _embedded_builds.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Embedded build job not found")
    return job


@router.patch("/embedded-builds/{job_id}/status")
def update_embedded_build_status(job_id: str, request: EmbeddedBuildUpdateRequest) -> dict:
    job = _embedded_builds.update_status(job_id, request.status, request.log_line)
    if job is None:
        raise HTTPException(status_code=404, detail="Embedded build job not found")
    return job


# ── Release Artifacts ─────────────────────────────────────────────────────────

class ReleaseCreateRequest(BaseModel):
    version: str = Field(..., min_length=1)
    release_type: str = "stable"
    notes: str = ""


class ReleaseArtifactAttachRequest(BaseModel):
    name: str = Field(..., min_length=1)
    path: str = Field(..., min_length=1)
    artifact_type: str = "binary"


@router.post("/releases")
def create_release(request: ReleaseCreateRequest) -> dict:
    try:
        return _release_creator.create(request.version, request.release_type, notes=request.notes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid release type") from exc


@router.get("/releases")
def list_releases(release_type: str | None = None) -> dict:
    return {"releases": _release_creator.list(release_type)}


@router.get("/releases/{release_id}")
def get_release(release_id: str) -> dict:
    release = _release_creator.get(release_id)
    if release is None:
        raise HTTPException(status_code=404, detail="Release not found")
    return release


@router.post("/releases/{release_id}/artifacts")
def attach_release_artifact(release_id: str, request: ReleaseArtifactAttachRequest) -> dict:
    release = _release_creator.attach_artifact(
        release_id, request.name, request.path, request.artifact_type
    )
    if release is None:
        raise HTTPException(status_code=404, detail="Release not found")
    return release


@router.post("/releases/{release_id}/publish")
def publish_release(release_id: str) -> dict:
    release = _release_creator.publish(release_id)
    if release is None:
        raise HTTPException(status_code=404, detail="Release not found")
    return release
