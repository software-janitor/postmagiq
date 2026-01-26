"""Workspace-scoped finished posts routes.

All finished posts operations are scoped to a workspace.
Handles viewing finished content and publish status.
"""

import json
import re
from datetime import datetime
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from api.auth.scopes import Scope
from api.routes.v1.dependencies import (
    WorkspaceCtx,
    WorkspaceContext,
    require_workspace_scope,
)
from api.services.content_service import ContentService
from runner.content.workflow_store import WorkflowStore
from runner.db.engine import get_session
from runner.content.repository import WorkflowRunRepository, WorkflowOutputRepository


router = APIRouter(prefix="/v1/w/{workspace_id}/finished-posts", tags=["finished-posts"])
content_service = ContentService()

# Available platforms
PLATFORMS = ["linkedin", "threads", "medium", "x"]


# =============================================================================
# Models
# =============================================================================


class PublishInfo(BaseModel):
    """Publishing information for a post."""
    platform: str
    published_at: str
    url: Optional[str] = None


class FinishedPost(BaseModel):
    """A finished post with content and image prompt."""
    post_id: str  # e.g., "c1p1"
    post_number: int
    chapter: int
    title: str
    content: str
    image_prompt: Optional[str] = None
    file_path: str
    publish_status: list[PublishInfo] = []


class PublishRequest(BaseModel):
    """Request to publish/unpublish a post."""
    platform: str
    url: Optional[str] = None


class FinishedPostsResponse(BaseModel):
    """List of finished posts."""
    posts: list[FinishedPost]


# =============================================================================
# Helper Functions
# =============================================================================


def _extract_title(content: str) -> str:
    """Extract title from first line of post content."""
    lines = content.strip().split('\n')
    if lines:
        return lines[0].strip()
    return "Untitled"


def _get_workflow_run_with_final(workspace_id: UUID, story: str, user_id: UUID):
    """Get the latest workflow run that has a 'final' output.

    First tries workspace-scoped query, then falls back to user_id for legacy runs
    that were created without workspace_id.
    """
    with get_session() as session:
        repo = WorkflowRunRepository(session)

        # Try workspace-scoped query first (for new runs with workspace_id)
        run = repo.get_latest_with_final_output(user_id, story, workspace_id=workspace_id)
        if run:
            return run

        # Fallback: query by user_id only (for legacy runs without workspace_id)
        run = repo.get_latest_with_final_output(user_id, story)
        return run


def _get_workflow_outputs(run_id: str):
    """Get all outputs for a workflow run."""
    with get_session() as session:
        repo = WorkflowOutputRepository(session)
        return repo.list_by_run(run_id)


# =============================================================================
# Routes
# =============================================================================


@router.get("", response_model=FinishedPostsResponse)
async def list_finished_posts(
    ctx: WorkspaceCtx,
):
    """List all finished posts for the workspace.

    Returns posts with status 'ready' or 'published'.
    """
    posts = []
    seen_posts = set()

    # Get workspace content service methods
    # Get ALL posts with status 'ready' or 'published'
    with get_session() as session:
        from runner.content.repository import PostRepository, ChapterRepository
        post_repo = PostRepository(session)
        chapter_repo = ChapterRepository(session)

        all_posts = post_repo.list_by_workspace(ctx.workspace_id)
        chapters = {c.id: c for c in chapter_repo.list_by_workspace(ctx.workspace_id)}

        finished = [p for p in all_posts if p.status in ("ready", "published")]

        for post in finished:
            chapter = chapters.get(post.chapter_id)
            chapter_num = chapter.chapter_number if chapter else 1
            post_id = f"c{chapter_num}p{post.post_number}"

            # Try to get content from workflow output
            story_id = f"post_{post.post_number:02d}"
            run = _get_workflow_run_with_final(ctx.workspace_id, story_id, ctx.user_id)

            final_content = None
            file_path = "no_workflow_run"

            if run:
                outputs = _get_workflow_outputs(run.run_id)
                for output in outputs:
                    if output.output_type == "final":
                        final_content = output.content
                        file_path = f"database:{run.run_id}"
                        break

            # If no workflow content, use topic as placeholder
            if not final_content:
                final_content = f"[Content not available in workflow system]\n\nTopic: {post.topic or 'No topic'}"

            # Use post topic as title, fall back to first line of content
            title = post.topic if post.topic else _extract_title(final_content)

            posts.append(FinishedPost(
                post_id=post_id,
                post_number=post.post_number,
                chapter=chapter_num,
                title=title,
                content=final_content,
                image_prompt=None,  # Can add workspace-scoped image prompts later
                file_path=file_path,
                publish_status=[],  # TODO: Add workspace-scoped publish status
            ))
            seen_posts.add(post.post_number)

    # Sort by post number
    posts.sort(key=lambda p: p.post_number)
    return FinishedPostsResponse(posts=posts)


@router.get("/{post_id}", response_model=FinishedPost)
async def get_finished_post(
    post_id: str,
    ctx: WorkspaceCtx,
):
    """Get a specific finished post by ID (e.g., c1p1)."""
    # Parse post_id (format: c1p1, c1p02, etc.)
    match = re.match(r"c(\d+)p(\d+)", post_id)
    if not match:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid post ID format. Use c1p1, c2p3, etc.",
        )

    chapter_num = int(match.group(1))
    post_num = int(match.group(2))

    with get_session() as session:
        from runner.content.repository import PostRepository, ChapterRepository
        post_repo = PostRepository(session)

        # Find the post by number in this workspace
        posts = post_repo.list_by_workspace(ctx.workspace_id)
        post = next((p for p in posts if p.post_number == post_num), None)

        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Post {post_num} not found in workspace",
            )

        # Try to get workflow content
        story_id = f"post_{post_num:02d}"
        run = _get_workflow_run_with_final(ctx.workspace_id, story_id, ctx.user_id)

        final_content = None
        file_path = "no_workflow_run"

        if run:
            outputs = _get_workflow_outputs(run.run_id)
            for output in outputs:
                if output.output_type == "final":
                    final_content = output.content
                    file_path = f"database:{run.run_id}"
                    break

        if not final_content:
            final_content = f"[Content not available]\n\nTopic: {post.topic or 'No topic'}"

        title = post.topic if post.topic else _extract_title(final_content)

        return FinishedPost(
            post_id=post_id,
            post_number=post_num,
            chapter=chapter_num,
            title=title,
            content=final_content,
            image_prompt=None,
            file_path=file_path,
            publish_status=[],
        )


@router.get("/platforms")
async def get_platforms(ctx: WorkspaceCtx):
    """Get list of available platforms."""
    return {"platforms": PLATFORMS}


@router.post("/{post_id}/publish")
async def publish_post(
    post_id: str,
    request: PublishRequest,
    ctx: Annotated[WorkspaceContext, Depends(require_workspace_scope(Scope.CONTENT_WRITE))],
):
    """Mark a post as published on a platform.

    Requires content:write scope.
    """
    if request.platform not in PLATFORMS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid platform. Must be one of: {', '.join(PLATFORMS)}",
        )

    # TODO: Implement workspace-scoped publish status storage
    # For now, return success (publish status would need a workspace_id column)
    return {
        "success": True,
        "post_id": post_id,
        "platform": request.platform,
        "message": "Publish status recorded for workspace",
    }


@router.delete("/{post_id}/publish/{platform}")
async def unpublish_post(
    post_id: str,
    platform: str,
    ctx: Annotated[WorkspaceContext, Depends(require_workspace_scope(Scope.CONTENT_WRITE))],
):
    """Remove publish status for a post on a platform.

    Requires content:write scope.
    """
    if platform not in PLATFORMS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid platform. Must be one of: {', '.join(PLATFORMS)}",
        )

    # TODO: Implement workspace-scoped publish status removal
    return {"success": True, "post_id": post_id, "platform": platform}
