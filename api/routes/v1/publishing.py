"""Publishing routes for social media platforms.

Handles immediate and scheduled publishing to LinkedIn, X, and Threads.
"""

from datetime import datetime, timezone
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from api.routes.v1.dependencies import WorkspaceContext, get_workspace_context
from runner.db.engine import get_session_dependency
from runner.db.models import (
    Post,
    SocialConnection,
    SocialPlatform,
    ScheduledPost,
    ScheduledPostStatus,
    ScheduledPostRead,
    PublishResult,
)
from runner.db.crypto import decrypt_token
from api.services.social_service import (
    linkedin_service,
    x_service,
    threads_service,
)

router = APIRouter(prefix="/publish", tags=["publishing"])


# =============================================================================
# Request/Response Models
# =============================================================================


class PublishRequest(BaseModel):
    """Request to publish content."""

    post_id: UUID = Field(..., description="ID of the post to publish")
    content: Optional[str] = Field(
        None,
        description="Optional content override (uses post content if not provided)",
    )


class ScheduleRequest(BaseModel):
    """Request to schedule a post."""

    post_id: UUID = Field(..., description="ID of the post to schedule")
    connection_id: UUID = Field(..., description="ID of the social connection to use")
    scheduled_for: datetime = Field(..., description="When to publish (UTC)")
    timezone: str = Field(default="UTC", description="User's timezone")


class PublishResponse(BaseModel):
    """Response from publish operation."""

    success: bool
    platform: str
    post_url: Optional[str] = None
    platform_post_id: Optional[str] = None
    error: Optional[str] = None


# =============================================================================
# Helper Functions
# =============================================================================


async def _get_connection(
    session: Session, connection_id: UUID, workspace_id: UUID, user_id: UUID
) -> SocialConnection:
    """Get and validate a social connection."""
    connection = session.get(SocialConnection, connection_id)
    if not connection:
        raise HTTPException(status_code=404, detail="Social connection not found")
    if connection.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Connection not in this workspace")
    if connection.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not your connection")
    return connection


async def _get_post_content(session: Session, post_id: UUID, workspace_id: UUID) -> str:
    """Get post content for publishing."""
    post = session.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Post not in this workspace")
    return post.linkedin_post or post.content or ""


async def _publish_to_platform(
    session: Session, connection: SocialConnection, content: str
) -> PublishResult:
    """Publish content to the appropriate platform."""
    try:
        # Decrypt tokens
        access_token = decrypt_token(session, connection.access_token)
        token_secret = decrypt_token(session, connection.token_secret)

        if connection.platform == SocialPlatform.linkedin:
            result = await linkedin_service.publish(
                access_token=access_token,
                person_id=connection.platform_user_id,
                text=content,
            )
        elif connection.platform == SocialPlatform.x:
            # Check character limit for X
            if len(content) > 280:
                return PublishResult(
                    success=False,
                    platform=connection.platform,
                    error="Content exceeds X's 280 character limit",
                )
            result = await x_service.publish(
                access_token=access_token,
                access_token_secret=token_secret or "",
                text=content,
            )
        elif connection.platform == SocialPlatform.threads:
            result = await threads_service.publish(
                access_token=access_token,
                user_id=connection.platform_user_id,
                text=content,
            )
        else:
            return PublishResult(
                success=False,
                platform=connection.platform,
                error=f"Unsupported platform: {connection.platform}",
            )

        return PublishResult(
            success=True,
            platform=connection.platform,
            post_url=result.get("post_url"),
            platform_post_id=result.get("post_id"),
        )

    except Exception as e:
        return PublishResult(
            success=False,
            platform=connection.platform,
            error=str(e),
        )


# =============================================================================
# Immediate Publishing
# =============================================================================


@router.post(
    "/w/{workspace_id}/linkedin/{connection_id}",
    response_model=PublishResponse,
)
async def publish_to_linkedin(
    connection_id: UUID,
    request: PublishRequest,
    ctx: Annotated[WorkspaceContext, Depends(get_workspace_context)],
    session: Annotated[Session, Depends(get_session_dependency)],
) -> PublishResponse:
    """Publish content to LinkedIn immediately."""
    connection = await _get_connection(
        session, connection_id, ctx.workspace_id, ctx.user_id
    )
    if connection.platform != SocialPlatform.linkedin:
        raise HTTPException(status_code=400, detail="Not a LinkedIn connection")

    content = request.content or await _get_post_content(
        session, request.post_id, ctx.workspace_id
    )
    result = await _publish_to_platform(session, connection, content)

    return PublishResponse(
        success=result.success,
        platform=result.platform.value,
        post_url=result.post_url,
        platform_post_id=result.platform_post_id,
        error=result.error,
    )


@router.post(
    "/w/{workspace_id}/x/{connection_id}",
    response_model=PublishResponse,
)
async def publish_to_x(
    connection_id: UUID,
    request: PublishRequest,
    ctx: Annotated[WorkspaceContext, Depends(get_workspace_context)],
    session: Annotated[Session, Depends(get_session_dependency)],
) -> PublishResponse:
    """Publish content to X immediately."""
    connection = await _get_connection(
        session, connection_id, ctx.workspace_id, ctx.user_id
    )
    if connection.platform != SocialPlatform.x:
        raise HTTPException(status_code=400, detail="Not an X connection")

    content = request.content or await _get_post_content(
        session, request.post_id, ctx.workspace_id
    )
    result = await _publish_to_platform(session, connection, content)

    return PublishResponse(
        success=result.success,
        platform=result.platform.value,
        post_url=result.post_url,
        platform_post_id=result.platform_post_id,
        error=result.error,
    )


@router.post(
    "/w/{workspace_id}/threads/{connection_id}",
    response_model=PublishResponse,
)
async def publish_to_threads(
    connection_id: UUID,
    request: PublishRequest,
    ctx: Annotated[WorkspaceContext, Depends(get_workspace_context)],
    session: Annotated[Session, Depends(get_session_dependency)],
) -> PublishResponse:
    """Publish content to Threads immediately."""
    connection = await _get_connection(
        session, connection_id, ctx.workspace_id, ctx.user_id
    )
    if connection.platform != SocialPlatform.threads:
        raise HTTPException(status_code=400, detail="Not a Threads connection")

    content = request.content or await _get_post_content(
        session, request.post_id, ctx.workspace_id
    )
    result = await _publish_to_platform(session, connection, content)

    return PublishResponse(
        success=result.success,
        platform=result.platform.value,
        post_url=result.post_url,
        platform_post_id=result.platform_post_id,
        error=result.error,
    )


# =============================================================================
# Scheduled Publishing
# =============================================================================


@router.post(
    "/w/{workspace_id}/schedule",
    response_model=ScheduledPostRead,
)
async def schedule_post(
    request: ScheduleRequest,
    ctx: Annotated[WorkspaceContext, Depends(get_workspace_context)],
    session: Annotated[Session, Depends(get_session_dependency)],
) -> ScheduledPostRead:
    """Schedule a post for future publishing."""
    # Validate connection
    await _get_connection(session, request.connection_id, ctx.workspace_id, ctx.user_id)

    # Validate post
    post = session.get(Post, request.post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.workspace_id != ctx.workspace_id:
        raise HTTPException(status_code=403, detail="Post not in this workspace")

    # Ensure scheduled time is in the future
    now = datetime.now(timezone.utc)
    scheduled_for = request.scheduled_for
    if scheduled_for.tzinfo is None:
        scheduled_for = scheduled_for.replace(tzinfo=timezone.utc)
    if scheduled_for <= now:
        raise HTTPException(
            status_code=400, detail="Scheduled time must be in the future"
        )

    # Create scheduled post
    scheduled = ScheduledPost(
        workspace_id=ctx.workspace_id,
        post_id=request.post_id,
        connection_id=request.connection_id,
        scheduled_for=scheduled_for,
        timezone=request.timezone,
        status=ScheduledPostStatus.pending,
    )
    session.add(scheduled)
    session.commit()
    session.refresh(scheduled)

    return ScheduledPostRead.model_validate(scheduled)


@router.get(
    "/w/{workspace_id}/scheduled",
    response_model=list[ScheduledPostRead],
)
async def list_scheduled_posts(
    ctx: Annotated[WorkspaceContext, Depends(get_workspace_context)],
    session: Annotated[Session, Depends(get_session_dependency)],
    status_filter: Optional[ScheduledPostStatus] = None,
) -> list[ScheduledPostRead]:
    """List scheduled posts for the workspace."""
    statement = select(ScheduledPost).where(
        ScheduledPost.workspace_id == ctx.workspace_id
    )
    if status_filter:
        statement = statement.where(ScheduledPost.status == status_filter)
    statement = statement.order_by(ScheduledPost.scheduled_for)

    scheduled = session.exec(statement).all()
    return [ScheduledPostRead.model_validate(s) for s in scheduled]


@router.get(
    "/w/{workspace_id}/scheduled/{scheduled_id}",
    response_model=ScheduledPostRead,
)
async def get_scheduled_post(
    scheduled_id: UUID,
    ctx: Annotated[WorkspaceContext, Depends(get_workspace_context)],
    session: Annotated[Session, Depends(get_session_dependency)],
) -> ScheduledPostRead:
    """Get a specific scheduled post."""
    scheduled = session.get(ScheduledPost, scheduled_id)
    if not scheduled:
        raise HTTPException(status_code=404, detail="Scheduled post not found")
    if scheduled.workspace_id != ctx.workspace_id:
        raise HTTPException(status_code=403, detail="Not in this workspace")

    return ScheduledPostRead.model_validate(scheduled)


@router.delete("/w/{workspace_id}/scheduled/{scheduled_id}")
async def cancel_scheduled_post(
    scheduled_id: UUID,
    ctx: Annotated[WorkspaceContext, Depends(get_workspace_context)],
    session: Annotated[Session, Depends(get_session_dependency)],
) -> dict:
    """Cancel a scheduled post."""
    scheduled = session.get(ScheduledPost, scheduled_id)
    if not scheduled:
        raise HTTPException(status_code=404, detail="Scheduled post not found")
    if scheduled.workspace_id != ctx.workspace_id:
        raise HTTPException(status_code=403, detail="Not in this workspace")

    if scheduled.status not in [
        ScheduledPostStatus.pending,
        ScheduledPostStatus.failed,
    ]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel post with status: {scheduled.status}",
        )

    scheduled.status = ScheduledPostStatus.cancelled
    scheduled.updated_at = datetime.utcnow()
    session.commit()

    return {"status": "cancelled"}


@router.post("/w/{workspace_id}/scheduled/{scheduled_id}/retry")
async def retry_scheduled_post(
    scheduled_id: UUID,
    ctx: Annotated[WorkspaceContext, Depends(get_workspace_context)],
    session: Annotated[Session, Depends(get_session_dependency)],
) -> ScheduledPostRead:
    """Retry a failed scheduled post."""
    scheduled = session.get(ScheduledPost, scheduled_id)
    if not scheduled:
        raise HTTPException(status_code=404, detail="Scheduled post not found")
    if scheduled.workspace_id != ctx.workspace_id:
        raise HTTPException(status_code=403, detail="Not in this workspace")

    if scheduled.status != ScheduledPostStatus.failed:
        raise HTTPException(
            status_code=400,
            detail="Can only retry failed posts",
        )

    scheduled.status = ScheduledPostStatus.pending
    scheduled.error_message = None
    scheduled.scheduled_for = datetime.now(timezone.utc)  # Publish now
    scheduled.updated_at = datetime.utcnow()
    session.commit()
    session.refresh(scheduled)

    return ScheduledPostRead.model_validate(scheduled)
