"""Workspace-scoped content routes.

All content operations are scoped to a workspace via /api/v1/w/{workspace_id}/...
This ensures multi-tenancy by requiring workspace context for all queries.
"""

from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session, select

from api.auth.scopes import Scope
from api.routes.v1.dependencies import (
    WorkspaceCtx,
    WorkspaceContext,
    require_workspace_scope,
)
from runner.db.engine import get_session_dependency
from runner.db.models import (
    Goal,
    Chapter,
    Post,
)
from runner.content.repository import WorkflowRunRepository, WorkflowOutputRepository


router = APIRouter(prefix="/v1/w/{workspace_id}", tags=["workspace-content"])


# =============================================================================
# Request/Response Models
# =============================================================================


class GoalResponse(BaseModel):
    """Goal data for API responses."""

    id: UUID
    workspace_id: Optional[UUID]
    positioning: Optional[str]
    signature_thesis: Optional[str]
    target_audience: Optional[str]
    content_style: Optional[str]
    strategy_type: Optional[str]
    voice_profile_id: Optional[UUID]
    image_config_set_id: Optional[UUID]


class CreateGoalRequest(BaseModel):
    """Request to create a new goal."""

    positioning: Optional[str] = None
    signature_thesis: Optional[str] = None
    target_audience: Optional[str] = None
    content_style: Optional[str] = None
    strategy_type: str = "series"


class UpdateGoalRequest(BaseModel):
    """Request to update goal fields."""

    positioning: Optional[str] = None
    signature_thesis: Optional[str] = None
    target_audience: Optional[str] = None
    content_style: Optional[str] = None
    strategy_type: Optional[str] = None
    voice_profile_id: Optional[UUID] = None
    image_config_set_id: Optional[UUID] = None


class ChapterResponse(BaseModel):
    """Chapter data for API responses."""

    id: UUID
    workspace_id: Optional[UUID]
    chapter_number: int
    title: str
    description: Optional[str]
    theme: Optional[str]
    theme_description: Optional[str]
    weeks_start: Optional[int]
    weeks_end: Optional[int]
    post_count: int = 0
    completed_count: int = 0


class CreateChapterRequest(BaseModel):
    """Request to create a new chapter."""

    chapter_number: int
    title: str
    description: Optional[str] = None
    theme: Optional[str] = None
    theme_description: Optional[str] = None
    weeks_start: Optional[int] = None
    weeks_end: Optional[int] = None


class PostResponse(BaseModel):
    """Post data for API responses."""

    id: UUID
    workspace_id: Optional[UUID]
    chapter_id: UUID
    post_number: int
    topic: Optional[str]
    shape: Optional[str]
    cadence: Optional[str]
    entry_point: Optional[str]
    status: str
    guidance: Optional[str]
    story_used: Optional[str]
    published_url: Optional[str]
    # Assignment fields (Phase 6)
    assignee_id: Optional[UUID] = None
    due_date: Optional[str] = None
    priority: Optional[str] = None
    estimated_hours: Optional[float] = None


class CreatePostRequest(BaseModel):
    """Request to create a new post."""

    chapter_id: UUID
    post_number: int
    topic: Optional[str] = None
    shape: Optional[str] = None
    cadence: Optional[str] = None
    entry_point: Optional[str] = None
    status: str = "not_started"
    guidance: Optional[str] = None
    # Assignment fields (Phase 6)
    assignee_id: Optional[UUID] = None
    due_date: Optional[str] = None
    priority: Optional[str] = None
    estimated_hours: Optional[float] = None


class UpdatePostRequest(BaseModel):
    """Request to update post fields."""

    topic: Optional[str] = None
    shape: Optional[str] = None
    cadence: Optional[str] = None
    entry_point: Optional[str] = None
    status: Optional[str] = None
    guidance: Optional[str] = None
    story_used: Optional[str] = None
    published_url: Optional[str] = None
    # Assignment fields (Phase 6)
    assignee_id: Optional[UUID] = None
    due_date: Optional[str] = None
    priority: Optional[str] = None
    estimated_hours: Optional[float] = None


# =============================================================================
# Goal Endpoints
# =============================================================================


@router.get("/goals", response_model=list[GoalResponse])
async def list_goals(
    ctx: WorkspaceCtx,
    session: Annotated[Session, Depends(get_session_dependency)],
):
    """List all goals in the workspace."""
    statement = select(Goal).where(Goal.workspace_id == ctx.workspace_id)
    goals = session.exec(statement).all()

    return [
        GoalResponse(
            id=g.id,
            workspace_id=g.workspace_id,
            positioning=g.positioning,
            signature_thesis=g.signature_thesis,
            target_audience=g.target_audience,
            content_style=g.content_style,
            strategy_type=g.strategy_type,
            voice_profile_id=g.voice_profile_id,
            image_config_set_id=g.image_config_set_id,
        )
        for g in goals
    ]


@router.post("/goals", response_model=GoalResponse, status_code=status.HTTP_201_CREATED)
async def create_goal(
    request: CreateGoalRequest,
    ctx: Annotated[
        WorkspaceContext, Depends(require_workspace_scope(Scope.STRATEGY_WRITE))
    ],
    session: Annotated[Session, Depends(get_session_dependency)],
):
    """Create a new goal in the workspace.

    Requires strategy:write scope.
    """
    goal = Goal(
        workspace_id=ctx.workspace_id,
        user_id=ctx.user_id,
        positioning=request.positioning,
        signature_thesis=request.signature_thesis,
        target_audience=request.target_audience,
        content_style=request.content_style,
        strategy_type=request.strategy_type,
    )
    session.add(goal)
    session.commit()
    session.refresh(goal)

    return GoalResponse(
        id=goal.id,
        workspace_id=goal.workspace_id,
        positioning=goal.positioning,
        signature_thesis=goal.signature_thesis,
        target_audience=goal.target_audience,
        content_style=goal.content_style,
        strategy_type=goal.strategy_type,
        voice_profile_id=goal.voice_profile_id,
        image_config_set_id=goal.image_config_set_id,
    )


@router.get("/goals/{goal_id}", response_model=GoalResponse)
async def get_goal(
    goal_id: UUID,
    ctx: WorkspaceCtx,
    session: Annotated[Session, Depends(get_session_dependency)],
):
    """Get a specific goal."""
    goal = session.get(Goal, goal_id)

    if not goal or goal.workspace_id != ctx.workspace_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Goal not found",
        )

    return GoalResponse(
        id=goal.id,
        workspace_id=goal.workspace_id,
        positioning=goal.positioning,
        signature_thesis=goal.signature_thesis,
        target_audience=goal.target_audience,
        content_style=goal.content_style,
        strategy_type=goal.strategy_type,
        voice_profile_id=goal.voice_profile_id,
        image_config_set_id=goal.image_config_set_id,
    )


@router.patch("/goals/{goal_id}", response_model=GoalResponse)
async def update_goal(
    goal_id: UUID,
    request: UpdateGoalRequest,
    ctx: Annotated[
        WorkspaceContext, Depends(require_workspace_scope(Scope.STRATEGY_WRITE))
    ],
    session: Annotated[Session, Depends(get_session_dependency)],
):
    """Update a goal.

    Requires strategy:write scope.
    """
    goal = session.get(Goal, goal_id)

    if not goal or goal.workspace_id != ctx.workspace_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Goal not found",
        )

    # Apply updates
    updates = request.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(goal, field, value)

    session.add(goal)
    session.commit()
    session.refresh(goal)

    return GoalResponse(
        id=goal.id,
        workspace_id=goal.workspace_id,
        positioning=goal.positioning,
        signature_thesis=goal.signature_thesis,
        target_audience=goal.target_audience,
        content_style=goal.content_style,
        strategy_type=goal.strategy_type,
        voice_profile_id=goal.voice_profile_id,
        image_config_set_id=goal.image_config_set_id,
    )


@router.delete("/goals/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_goal(
    goal_id: UUID,
    ctx: Annotated[
        WorkspaceContext, Depends(require_workspace_scope(Scope.STRATEGY_WRITE))
    ],
    session: Annotated[Session, Depends(get_session_dependency)],
):
    """Delete a goal.

    Requires strategy:write scope.
    """
    goal = session.get(Goal, goal_id)

    if not goal or goal.workspace_id != ctx.workspace_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Goal not found",
        )

    session.delete(goal)
    session.commit()


# =============================================================================
# Chapter Endpoints
# =============================================================================


@router.get("/chapters", response_model=list[ChapterResponse])
async def list_chapters(
    ctx: WorkspaceCtx,
    session: Annotated[Session, Depends(get_session_dependency)],
):
    """List all chapters in the workspace."""
    statement = select(Chapter).where(Chapter.workspace_id == ctx.workspace_id)
    chapters = session.exec(statement).all()

    result = []
    for chapter in chapters:
        # Count posts
        post_stmt = select(Post).where(
            Post.chapter_id == chapter.id,
            Post.workspace_id == ctx.workspace_id,
        )
        posts = session.exec(post_stmt).all()
        completed = [p for p in posts if p.status in ("ready", "published")]

        result.append(
            ChapterResponse(
                id=chapter.id,
                workspace_id=chapter.workspace_id,
                chapter_number=chapter.chapter_number,
                title=chapter.title,
                description=chapter.description,
                theme=chapter.theme,
                theme_description=chapter.theme_description,
                weeks_start=chapter.weeks_start,
                weeks_end=chapter.weeks_end,
                post_count=len(posts),
                completed_count=len(completed),
            )
        )

    return result


@router.post(
    "/chapters", response_model=ChapterResponse, status_code=status.HTTP_201_CREATED
)
async def create_chapter(
    request: CreateChapterRequest,
    ctx: Annotated[
        WorkspaceContext, Depends(require_workspace_scope(Scope.CONTENT_WRITE))
    ],
    session: Annotated[Session, Depends(get_session_dependency)],
):
    """Create a new chapter.

    Requires content:write scope.
    """
    chapter = Chapter(
        workspace_id=ctx.workspace_id,
        user_id=ctx.user_id,
        chapter_number=request.chapter_number,
        title=request.title,
        description=request.description,
        theme=request.theme,
        theme_description=request.theme_description,
        weeks_start=request.weeks_start,
        weeks_end=request.weeks_end,
    )
    session.add(chapter)
    session.commit()
    session.refresh(chapter)

    return ChapterResponse(
        id=chapter.id,
        workspace_id=chapter.workspace_id,
        chapter_number=chapter.chapter_number,
        title=chapter.title,
        description=chapter.description,
        theme=chapter.theme,
        theme_description=chapter.theme_description,
        weeks_start=chapter.weeks_start,
        weeks_end=chapter.weeks_end,
        post_count=0,
        completed_count=0,
    )


@router.get("/chapters/{chapter_id}", response_model=ChapterResponse)
async def get_chapter(
    chapter_id: UUID,
    ctx: WorkspaceCtx,
    session: Annotated[Session, Depends(get_session_dependency)],
):
    """Get a specific chapter with post counts."""
    chapter = session.get(Chapter, chapter_id)

    if not chapter or chapter.workspace_id != ctx.workspace_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chapter not found",
        )

    # Count posts
    post_stmt = select(Post).where(
        Post.chapter_id == chapter.id,
        Post.workspace_id == ctx.workspace_id,
    )
    posts = session.exec(post_stmt).all()
    completed = [p for p in posts if p.status in ("ready", "published")]

    return ChapterResponse(
        id=chapter.id,
        workspace_id=chapter.workspace_id,
        chapter_number=chapter.chapter_number,
        title=chapter.title,
        description=chapter.description,
        theme=chapter.theme,
        theme_description=chapter.theme_description,
        weeks_start=chapter.weeks_start,
        weeks_end=chapter.weeks_end,
        post_count=len(posts),
        completed_count=len(completed),
    )


# =============================================================================
# Post Endpoints
# =============================================================================


@router.get("/posts", response_model=list[PostResponse])
async def list_posts(
    ctx: WorkspaceCtx,
    session: Annotated[Session, Depends(get_session_dependency)],
    chapter_id: Optional[UUID] = None,
    status_filter: Optional[str] = None,
):
    """List posts in the workspace.

    Optional filters:
    - chapter_id: Filter by chapter
    - status_filter: Filter by status (not_started, draft, ready, published)
    """
    statement = select(Post).where(Post.workspace_id == ctx.workspace_id)

    if chapter_id:
        statement = statement.where(Post.chapter_id == chapter_id)
    if status_filter:
        statement = statement.where(Post.status == status_filter)

    posts = session.exec(statement).all()

    return [
        PostResponse(
            id=p.id,
            workspace_id=p.workspace_id,
            chapter_id=p.chapter_id,
            post_number=p.post_number,
            topic=p.topic,
            shape=p.shape,
            cadence=p.cadence,
            entry_point=p.entry_point,
            status=p.status,
            guidance=p.guidance,
            story_used=p.story_used,
            published_url=p.published_url,
            assignee_id=p.assignee_id,
            due_date=p.due_date.isoformat() if p.due_date else None,
            priority=p.priority,
            estimated_hours=p.estimated_hours,
        )
        for p in posts
    ]


@router.post("/posts", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(
    request: CreatePostRequest,
    ctx: Annotated[
        WorkspaceContext, Depends(require_workspace_scope(Scope.CONTENT_WRITE))
    ],
    session: Annotated[Session, Depends(get_session_dependency)],
):
    """Create a new post.

    Requires content:write scope.
    """
    # Verify chapter belongs to workspace
    chapter = session.get(Chapter, request.chapter_id)
    if not chapter or chapter.workspace_id != ctx.workspace_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chapter not found in this workspace",
        )

    post = Post(
        workspace_id=ctx.workspace_id,
        user_id=ctx.user_id,
        chapter_id=request.chapter_id,
        post_number=request.post_number,
        topic=request.topic,
        shape=request.shape,
        cadence=request.cadence,
        entry_point=request.entry_point,
        status=request.status,
        guidance=request.guidance,
        assignee_id=request.assignee_id,
        priority=request.priority,
        estimated_hours=request.estimated_hours,
    )
    session.add(post)
    session.commit()
    session.refresh(post)

    return PostResponse(
        id=post.id,
        workspace_id=post.workspace_id,
        chapter_id=post.chapter_id,
        post_number=post.post_number,
        topic=post.topic,
        shape=post.shape,
        cadence=post.cadence,
        entry_point=post.entry_point,
        status=post.status,
        guidance=post.guidance,
        story_used=post.story_used,
        published_url=post.published_url,
        assignee_id=post.assignee_id,
        due_date=post.due_date.isoformat() if post.due_date else None,
        priority=post.priority,
        estimated_hours=post.estimated_hours,
    )


@router.get("/posts/{post_id}", response_model=PostResponse)
async def get_post(
    post_id: UUID,
    ctx: WorkspaceCtx,
    session: Annotated[Session, Depends(get_session_dependency)],
):
    """Get a specific post."""
    post = session.get(Post, post_id)

    if not post or post.workspace_id != ctx.workspace_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )

    return PostResponse(
        id=post.id,
        workspace_id=post.workspace_id,
        chapter_id=post.chapter_id,
        post_number=post.post_number,
        topic=post.topic,
        shape=post.shape,
        cadence=post.cadence,
        entry_point=post.entry_point,
        status=post.status,
        guidance=post.guidance,
        story_used=post.story_used,
        published_url=post.published_url,
        assignee_id=post.assignee_id,
        due_date=post.due_date.isoformat() if post.due_date else None,
        priority=post.priority,
        estimated_hours=post.estimated_hours,
    )


@router.patch("/posts/{post_id}", response_model=PostResponse)
async def update_post(
    post_id: UUID,
    request: UpdatePostRequest,
    ctx: Annotated[
        WorkspaceContext, Depends(require_workspace_scope(Scope.CONTENT_WRITE))
    ],
    session: Annotated[Session, Depends(get_session_dependency)],
):
    """Update a post.

    Requires content:write scope.
    """
    post = session.get(Post, post_id)

    if not post or post.workspace_id != ctx.workspace_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )

    # Apply updates
    updates = request.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(post, field, value)

    session.add(post)
    session.commit()
    session.refresh(post)

    return PostResponse(
        id=post.id,
        workspace_id=post.workspace_id,
        chapter_id=post.chapter_id,
        post_number=post.post_number,
        topic=post.topic,
        shape=post.shape,
        cadence=post.cadence,
        entry_point=post.entry_point,
        status=post.status,
        guidance=post.guidance,
        story_used=post.story_used,
        published_url=post.published_url,
        assignee_id=post.assignee_id,
        due_date=post.due_date.isoformat() if post.due_date else None,
        priority=post.priority,
        estimated_hours=post.estimated_hours,
    )


@router.delete("/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post_id: UUID,
    ctx: Annotated[
        WorkspaceContext, Depends(require_workspace_scope(Scope.CONTENT_WRITE))
    ],
    session: Annotated[Session, Depends(get_session_dependency)],
):
    """Delete a post.

    Requires content:write scope.
    """
    post = session.get(Post, post_id)

    if not post or post.workspace_id != ctx.workspace_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )

    session.delete(post)
    session.commit()


class ResetPostResponse(BaseModel):
    """Response for post reset."""

    status: str
    post_id: UUID
    post_number: int
    deleted_workflow_outputs: int


@router.post("/posts/{post_id}/reset", response_model=ResetPostResponse)
async def reset_post(
    post_id: str,
    ctx: Annotated[
        WorkspaceContext, Depends(require_workspace_scope(Scope.CONTENT_WRITE))
    ],
    session: Annotated[Session, Depends(get_session_dependency)],
):
    """Reset a post to 'not started' state.

    Accepts post_id in formats: UUID, c1p1, post_04

    This will:
    - Set status to 'not_started'
    - Delete workflow outputs for this post

    Requires content:write scope.
    """

    # Parse post_id to find the post
    post = None
    post_number = None

    # Try UUID first
    try:
        from uuid import UUID as UUIDType

        post_uuid = UUIDType(post_id)
        post = session.get(Post, post_uuid)
        if post:
            post_number = post.post_number
    except ValueError:
        pass

    # Try c1p1 format
    if not post and post_id.startswith("c") and "p" in post_id:
        try:
            post_number = int(post_id.split("p")[1])
        except (ValueError, IndexError):
            pass

    # Try post_04 format
    if not post and post_id.startswith("post_"):
        try:
            post_number = int(post_id.replace("post_", "").lstrip("0") or "0")
        except ValueError:
            pass

    # Find post by number if we parsed one
    if not post and post_number:
        statement = select(Post).where(
            Post.workspace_id == ctx.workspace_id,
            Post.post_number == post_number,
        )
        post = session.exec(statement).first()

    if not post or post.workspace_id != ctx.workspace_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post {post_id} not found in workspace",
        )

    # Reset status
    post.status = "not_started"
    session.add(post)

    # Delete workflow outputs for this post
    story_id = f"post_{post.post_number:02d}"
    deleted_outputs = 0

    workflow_repo = WorkflowRunRepository(session)
    output_repo = WorkflowOutputRepository(session)

    # Find workflow runs for this story
    runs = workflow_repo.list_by_workspace(ctx.workspace_id, limit=100)
    for run in runs:
        if run.story == story_id:
            # Delete outputs for this run
            outputs = output_repo.list_by_run(run.run_id)
            for output in outputs:
                session.delete(output)
                deleted_outputs += 1

    session.commit()

    return ResetPostResponse(
        status="reset",
        post_id=post.id,
        post_number=post.post_number,
        deleted_workflow_outputs=deleted_outputs,
    )
