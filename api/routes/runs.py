"""API routes for workflow runs."""

import os
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from api.auth.dependencies import CurrentUser, get_current_user
from api.models.api_models import (
    RunSummary,
    StateLogEntry,
    TokenBreakdown,
    ArtifactInfo,
)
from api.services.run_service import RunService
from runner.config import WORKING_DIR

router = APIRouter()
# Use correct runs directory matching where WorkflowRunner saves runs
run_service = RunService(runs_dir=os.path.join(WORKING_DIR, "runs"))


@router.get("", response_model=list[RunSummary])
async def list_runs(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """List all workflow runs for the current user."""
    return run_service.list_runs(str(current_user.user_id))


@router.get("/{run_id}", response_model=RunSummary)
async def get_run(
    run_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """Get a specific run by ID."""
    run = run_service.get_run_for_user(run_id, str(current_user.user_id))
    if not run:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    return run


@router.get("/{run_id}/states", response_model=list[StateLogEntry])
async def get_state_log(
    run_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """Get state log entries for a run."""
    run = run_service.get_run_for_user(run_id, str(current_user.user_id))
    if not run:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    return run_service.get_state_log(run_id)


@router.get("/{run_id}/summary")
async def get_summary(
    run_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """Get run summary markdown."""
    run = run_service.get_run_for_user(run_id, str(current_user.user_id))
    if not run:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    summary = run_service.get_summary(run_id)
    if summary is None:
        raise HTTPException(status_code=404, detail=f"Summary not found for: {run_id}")
    return {"summary": summary}


@router.get("/{run_id}/tokens", response_model=TokenBreakdown)
async def get_token_breakdown(
    run_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """Get token usage breakdown for a run."""
    run = run_service.get_run_for_user(run_id, str(current_user.user_id))
    if not run:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    breakdown = run_service.get_token_breakdown(run_id)
    if not breakdown:
        raise HTTPException(status_code=404, detail=f"Token data not found: {run_id}")
    return breakdown


@router.get("/{run_id}/artifacts", response_model=list[ArtifactInfo])
async def list_artifacts(
    run_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """List all artifacts for a run."""
    run = run_service.get_run_for_user(run_id, str(current_user.user_id))
    if not run:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    return run_service.list_artifacts(run_id)


@router.get("/{run_id}/artifacts/{path:path}")
async def get_artifact(
    run_id: str,
    path: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """Get content of an artifact file within the specified run."""
    run = run_service.get_run_for_user(run_id, str(current_user.user_id))
    if not run:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    content = run_service.get_artifact_content(run_id, path)
    if content is None:
        raise HTTPException(status_code=404, detail=f"Artifact not found: {path}")
    return {"content": content, "path": path}
