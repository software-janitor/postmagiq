"""API routes for workflow execution."""

from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from api.auth.dependencies import CurrentUser, get_current_user
from api.models.api_models import (
    WorkflowExecuteRequest,
    WorkflowStepRequest,
    ApprovalRequest,
    WorkflowStatus,
)
from api.services.workflow_service import workflow_service
from runner.content.ids import normalize_user_id
from runner.content.workflow_store import WorkflowStore

router = APIRouter()


@router.get("/status", response_model=WorkflowStatus)
async def get_status(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """Get current workflow execution status."""
    return workflow_service.get_status()


@router.post("/execute")
async def execute_workflow(
    request: WorkflowExecuteRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """Start a new workflow execution."""
    return await workflow_service.execute(
        story=request.story,
        user_id=str(current_user.user_id),
        input_path=request.input_path,
        content=request.content,
        config=request.config,
    )


@router.post("/step")
async def execute_step(
    request: WorkflowStepRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """Execute a single workflow step. If run_id is provided, continues an existing run."""
    return await workflow_service.execute_step(
        request.story,
        request.step,
        run_id=request.run_id,
        user_id=str(current_user.user_id),
    )


@router.post("/abort")
async def abort_workflow(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """Abort the currently running workflow."""
    return await workflow_service.abort()


@router.post("/approve")
async def submit_approval(
    request: ApprovalRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """Submit human approval decision."""
    return await workflow_service.submit_approval(
        request.decision,
        feedback=request.feedback,
    )


@router.post("/pause")
async def pause_workflow(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """Pause the running workflow at the next checkpoint."""
    return await workflow_service.pause()


@router.post("/resume")
async def resume_workflow(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """Resume a paused workflow."""
    return await workflow_service.resume()


@router.get("/runs")
async def get_workflow_runs(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    limit: int = 20,
):
    """Get recent workflow runs for the current user."""
    store = WorkflowStore(current_user.user_id)
    runs = store.get_workflow_runs_for_user(current_user.user_id, limit)
    return [run.model_dump() for run in runs]


@router.get("/runs/{run_id}")
async def get_workflow_run(
    run_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """Get a specific workflow run."""
    store = WorkflowStore(current_user.user_id)
    run = store.get_workflow_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    # Verify ownership - return 404 to prevent enumeration
    if str(run.user_id) != str(current_user.user_id):
        raise HTTPException(status_code=404, detail="Run not found")

    return run.model_dump()


@router.get("/runs/{run_id}/outputs")
async def get_workflow_outputs(
    run_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """Get all outputs for a workflow run."""
    store = WorkflowStore(current_user.user_id)

    # First verify run ownership
    run = store.get_workflow_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if str(run.user_id) != str(current_user.user_id):
        raise HTTPException(status_code=404, detail="Run not found")

    outputs = store.get_workflow_outputs(run_id)
    return [output.model_dump() for output in outputs]


@router.get("/story/{story}/latest")
async def get_latest_run_for_story(
    story: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """Get the latest workflow run for a story and its outputs."""
    store = WorkflowStore(current_user.user_id)
    run = store.get_latest_workflow_run_for_story(current_user.user_id, story)
    if not run:
        return {"run": None, "outputs": []}

    outputs = store.get_workflow_outputs(run.run_id)

    # Organize outputs by type for easier frontend consumption
    outputs_by_type = {}
    for output in outputs:
        output_type = output.output_type
        if output_type in ("draft", "audit", "final_audit"):
            # Group drafts/audits by agent
            if output_type not in outputs_by_type:
                outputs_by_type[output_type] = {}
            outputs_by_type[output_type][output.agent or "unknown"] = output.content
        else:
            outputs_by_type[output_type] = output.content

    return {
        "run": run.model_dump(),
        "outputs": outputs_by_type,
    }


@router.post("/story/{story}/finalize")
async def finalize_story(
    story: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """Finalize a story: save final post to posts directory and update status to 'ready'."""
    import re
    from pathlib import Path
    from api.services.content_service import ContentService

    content_service = ContentService()
    store = WorkflowStore(current_user.user_id)

    # Parse post number from story ID
    match = re.search(r"post_(\d+)", story)
    if not match:
        raise HTTPException(status_code=400, detail="Invalid story ID format")

    post_number = int(match.group(1))

    # Get the post from content database to find chapter
    uid = current_user.user_id
    post = content_service.get_post_by_number(uid, post_number)
    if not post:
        raise HTTPException(status_code=404, detail=f"Post {post_number} not found")

    # Get the latest run and final post content
    run = store.get_latest_workflow_run_for_story(uid, story)
    if not run:
        raise HTTPException(status_code=404, detail="No workflow run found for this story")

    outputs = store.get_workflow_outputs(run.run_id)
    final_content = None
    for output in outputs:
        if output.output_type == "final":
            final_content = output.content
            break

    if not final_content:
        raise HTTPException(status_code=404, detail="No final post content found")

    # Determine posts directory
    posts_dir = Path(__file__).parent.parent.parent.parent / "posts"
    chapter_dir = posts_dir / f"chapter_{post.chapter_number}"
    chapter_dir.mkdir(parents=True, exist_ok=True)

    # Write the final post
    post_file = chapter_dir / f"post_{post_number:02d}.md"
    post_file.write_text(final_content)

    # Update post status to 'ready'
    content_service.update_post(post.id, status="ready")

    return {
        "status": "finalized",
        "post_number": post_number,
        "chapter": post.chapter_number,
        "file_path": str(post_file),
    }
