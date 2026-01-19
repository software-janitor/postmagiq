"""Notification routes for managing notifications and preferences.

Provides endpoints for:
- Listing and managing notifications
- Managing notification preferences
- Marking notifications as read
"""

from datetime import datetime
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlmodel import Session

from api.auth.scopes import Scope
from api.routes.v1.dependencies import (
    WorkspaceContext,
    require_workspace_scope,
)
from api.services.notification_service import (
    NotificationService,
    NotificationServiceError,
    NotificationNotFoundError,
    ChannelNotFoundError,
)
from runner.db.engine import get_session_dependency


router = APIRouter(prefix="/v1/w/{workspace_id}/notifications", tags=["notifications"])

notification_service = NotificationService()


# =============================================================================
# Request/Response Models
# =============================================================================


class NotificationChannelResponse(BaseModel):
    """Response model for notification channels."""
    id: UUID
    channel_type: str
    name: str
    description: Optional[str]
    is_enabled: bool
    created_at: datetime


class NotificationPreferenceResponse(BaseModel):
    """Response model for notification preferences."""
    id: UUID
    channel_id: UUID
    notification_type: str
    is_enabled: bool


class UpdatePreferenceRequest(BaseModel):
    """Request to update a notification preference."""
    channel_id: UUID
    notification_type: str
    is_enabled: bool


class BulkUpdatePreferencesRequest(BaseModel):
    """Request to update multiple notification preferences."""
    preferences: list[UpdatePreferenceRequest]


class NotificationResponse(BaseModel):
    """Response model for notifications."""
    id: UUID
    notification_type: str
    title: str
    message: str
    priority: str
    resource_type: Optional[str]
    resource_id: Optional[UUID]
    actor_id: Optional[UUID]
    is_read: bool
    read_at: Optional[datetime]
    is_dismissed: bool
    dismissed_at: Optional[datetime]
    created_at: datetime


class NotificationListResponse(BaseModel):
    """Response for listing notifications with metadata."""
    notifications: list[NotificationResponse]
    unread_count: int
    total: int


class MarkReadRequest(BaseModel):
    """Request to mark notification(s) as read."""
    notification_ids: list[UUID] = Field(default_factory=list)
    mark_all: bool = False


class UnreadCountResponse(BaseModel):
    """Response for unread notification count."""
    count: int


class MarkReadResponse(BaseModel):
    """Response after marking notifications as read."""
    marked_count: int


# =============================================================================
# Notification Channels
# =============================================================================


@router.get("/channels", response_model=list[NotificationChannelResponse])
async def list_channels(
    ctx: Annotated[WorkspaceContext, Depends(require_workspace_scope(Scope.CONTENT_READ))],
    session: Annotated[Session, Depends(get_session_dependency)],
):
    """List all available notification channels."""
    channels = notification_service.ensure_default_channels(session)
    return [
        NotificationChannelResponse(
            id=c.id,
            channel_type=c.channel_type,
            name=c.name,
            description=c.description,
            is_enabled=c.is_enabled,
            created_at=c.created_at,
        )
        for c in channels
    ]


# =============================================================================
# Notification Preferences
# =============================================================================


@router.get("/preferences", response_model=list[NotificationPreferenceResponse])
async def get_preferences(
    ctx: Annotated[WorkspaceContext, Depends(require_workspace_scope(Scope.CONTENT_READ))],
    session: Annotated[Session, Depends(get_session_dependency)],
):
    """Get notification preferences for the current user."""
    preferences = notification_service.get_user_preferences(
        session, ctx.user_id, ctx.workspace_id
    )
    return [
        NotificationPreferenceResponse(
            id=p.id,
            channel_id=p.channel_id,
            notification_type=p.notification_type,
            is_enabled=p.is_enabled,
        )
        for p in preferences
    ]


@router.patch("/preferences", response_model=list[NotificationPreferenceResponse])
async def update_preferences(
    request: BulkUpdatePreferencesRequest,
    ctx: Annotated[WorkspaceContext, Depends(require_workspace_scope(Scope.CONTENT_READ))],
    session: Annotated[Session, Depends(get_session_dependency)],
):
    """Update notification preferences for the current user."""
    try:
        preferences_data = [
            {
                "channel_id": p.channel_id,
                "notification_type": p.notification_type,
                "is_enabled": p.is_enabled,
            }
            for p in request.preferences
        ]
        preferences = notification_service.set_bulk_preferences(
            session, ctx.user_id, ctx.workspace_id, preferences_data
        )
        return [
            NotificationPreferenceResponse(
                id=p.id,
                channel_id=p.channel_id,
                notification_type=p.notification_type,
                is_enabled=p.is_enabled,
            )
            for p in preferences
        ]
    except ChannelNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put("/preferences/{channel_id}/{notification_type}", response_model=NotificationPreferenceResponse)
async def set_preference(
    channel_id: UUID,
    notification_type: str,
    is_enabled: bool,
    ctx: Annotated[WorkspaceContext, Depends(require_workspace_scope(Scope.CONTENT_READ))],
    session: Annotated[Session, Depends(get_session_dependency)],
):
    """Set a specific notification preference."""
    try:
        pref = notification_service.set_preference(
            session, ctx.user_id, ctx.workspace_id, channel_id, notification_type, is_enabled
        )
        return NotificationPreferenceResponse(
            id=pref.id,
            channel_id=pref.channel_id,
            notification_type=pref.notification_type,
            is_enabled=pref.is_enabled,
        )
    except ChannelNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# =============================================================================
# Notifications
# =============================================================================


@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    ctx: Annotated[WorkspaceContext, Depends(require_workspace_scope(Scope.CONTENT_READ))],
    session: Annotated[Session, Depends(get_session_dependency)],
    unread_only: bool = Query(False, description="Only return unread notifications"),
    include_dismissed: bool = Query(False, description="Include dismissed notifications"),
    limit: int = Query(50, ge=1, le=100, description="Maximum notifications to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    """Get notifications for the current user."""
    notifications = notification_service.get_notifications(
        session,
        ctx.user_id,
        ctx.workspace_id,
        unread_only=unread_only,
        include_dismissed=include_dismissed,
        limit=limit,
        offset=offset,
    )

    unread_count = notification_service.get_unread_count(
        session, ctx.user_id, ctx.workspace_id
    )

    return NotificationListResponse(
        notifications=[
            NotificationResponse(
                id=n.id,
                notification_type=n.notification_type,
                title=n.title,
                message=n.message,
                priority=n.priority,
                resource_type=n.resource_type,
                resource_id=n.resource_id,
                actor_id=n.actor_id,
                is_read=n.is_read,
                read_at=n.read_at,
                is_dismissed=n.is_dismissed,
                dismissed_at=n.dismissed_at,
                created_at=n.created_at,
            )
            for n in notifications
        ],
        unread_count=unread_count,
        total=len(notifications),
    )


@router.get("/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(
    ctx: Annotated[WorkspaceContext, Depends(require_workspace_scope(Scope.CONTENT_READ))],
    session: Annotated[Session, Depends(get_session_dependency)],
):
    """Get count of unread notifications."""
    count = notification_service.get_unread_count(
        session, ctx.user_id, ctx.workspace_id
    )
    return UnreadCountResponse(count=count)


@router.get("/{notification_id}", response_model=NotificationResponse)
async def get_notification(
    notification_id: UUID,
    ctx: Annotated[WorkspaceContext, Depends(require_workspace_scope(Scope.CONTENT_READ))],
    session: Annotated[Session, Depends(get_session_dependency)],
):
    """Get a specific notification."""
    try:
        n = notification_service.get_notification(session, notification_id, ctx.user_id)
        return NotificationResponse(
            id=n.id,
            notification_type=n.notification_type,
            title=n.title,
            message=n.message,
            priority=n.priority,
            resource_type=n.resource_type,
            resource_id=n.resource_id,
            actor_id=n.actor_id,
            is_read=n.is_read,
            read_at=n.read_at,
            is_dismissed=n.is_dismissed,
            dismissed_at=n.dismissed_at,
            created_at=n.created_at,
        )
    except NotificationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )


@router.post("/mark-read", response_model=MarkReadResponse)
async def mark_notifications_read(
    request: MarkReadRequest,
    ctx: Annotated[WorkspaceContext, Depends(require_workspace_scope(Scope.CONTENT_READ))],
    session: Annotated[Session, Depends(get_session_dependency)],
):
    """Mark notifications as read.

    Either provide specific notification_ids or set mark_all=True to mark all.
    """
    if request.mark_all:
        count = notification_service.mark_all_as_read(
            session, ctx.user_id, ctx.workspace_id
        )
        return MarkReadResponse(marked_count=count)
    elif request.notification_ids:
        notifications = notification_service.mark_multiple_as_read(
            session, request.notification_ids, ctx.user_id
        )
        return MarkReadResponse(marked_count=len(notifications))
    else:
        return MarkReadResponse(marked_count=0)


@router.post("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: UUID,
    ctx: Annotated[WorkspaceContext, Depends(require_workspace_scope(Scope.CONTENT_READ))],
    session: Annotated[Session, Depends(get_session_dependency)],
):
    """Mark a specific notification as read."""
    try:
        n = notification_service.mark_as_read(session, notification_id, ctx.user_id)
        return NotificationResponse(
            id=n.id,
            notification_type=n.notification_type,
            title=n.title,
            message=n.message,
            priority=n.priority,
            resource_type=n.resource_type,
            resource_id=n.resource_id,
            actor_id=n.actor_id,
            is_read=n.is_read,
            read_at=n.read_at,
            is_dismissed=n.is_dismissed,
            dismissed_at=n.dismissed_at,
            created_at=n.created_at,
        )
    except NotificationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )


@router.post("/{notification_id}/dismiss", response_model=NotificationResponse)
async def dismiss_notification(
    notification_id: UUID,
    ctx: Annotated[WorkspaceContext, Depends(require_workspace_scope(Scope.CONTENT_READ))],
    session: Annotated[Session, Depends(get_session_dependency)],
):
    """Dismiss a notification (hide from list)."""
    try:
        n = notification_service.dismiss(session, notification_id, ctx.user_id)
        return NotificationResponse(
            id=n.id,
            notification_type=n.notification_type,
            title=n.title,
            message=n.message,
            priority=n.priority,
            resource_type=n.resource_type,
            resource_id=n.resource_id,
            actor_id=n.actor_id,
            is_read=n.is_read,
            read_at=n.read_at,
            is_dismissed=n.is_dismissed,
            dismissed_at=n.dismissed_at,
            created_at=n.created_at,
        )
    except NotificationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )


@router.post("/dismiss-all", response_model=MarkReadResponse)
async def dismiss_all_notifications(
    ctx: Annotated[WorkspaceContext, Depends(require_workspace_scope(Scope.CONTENT_READ))],
    session: Annotated[Session, Depends(get_session_dependency)],
):
    """Dismiss all notifications."""
    count = notification_service.dismiss_all(session, ctx.user_id, ctx.workspace_id)
    return MarkReadResponse(marked_count=count)
