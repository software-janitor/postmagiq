"""Audit log routes for viewing activity history.

Provides endpoints for:
- Listing audit logs with filtering and pagination
- Viewing individual audit log entries

Admin-only access for security compliance.
"""

from datetime import datetime
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlmodel import Session

from api.auth.scopes import Scope
from api.routes.v1.dependencies import (
    WorkspaceContext,
    require_workspace_scope,
)
from api.services.audit_service import (
    AuditService,
    AuditNotFoundError,
)
from runner.db.engine import get_session_dependency
from runner.db.models.audit import AuditAction


router = APIRouter(prefix="/v1/w/{workspace_id}/audit-logs", tags=["audit"])

audit_service = AuditService()


# =============================================================================
# Response Models
# =============================================================================


class AuditLogResponse(BaseModel):
    """Response model for audit log entries."""

    id: UUID
    workspace_id: UUID
    user_id: UUID
    action: str
    resource_type: str
    resource_id: Optional[UUID]
    old_value: Optional[dict]
    new_value: Optional[dict]
    description: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    created_at: datetime


class AuditLogListResponse(BaseModel):
    """Response model for paginated audit log list."""

    items: list[AuditLogResponse]
    total: int
    limit: int
    offset: int


# =============================================================================
# Audit Log Routes
# =============================================================================


@router.get("", response_model=AuditLogListResponse)
async def list_audit_logs(
    ctx: Annotated[WorkspaceContext, Depends(require_workspace_scope(Scope.ADMIN))],
    session: Annotated[Session, Depends(get_session_dependency)],
    user_id: Optional[UUID] = Query(default=None, description="Filter by user"),
    action: Optional[str] = Query(default=None, description="Filter by action type"),
    resource_type: Optional[str] = Query(
        default=None, description="Filter by resource type"
    ),
    resource_id: Optional[UUID] = Query(
        default=None, description="Filter by specific resource"
    ),
    start_date: Optional[datetime] = Query(
        default=None, description="Start of date range"
    ),
    end_date: Optional[datetime] = Query(default=None, description="End of date range"),
    limit: int = Query(default=50, ge=1, le=100, description="Max results"),
    offset: int = Query(default=0, ge=0, description="Results to skip"),
):
    """List audit logs for the workspace.

    Requires admin scope. Returns paginated results with optional filtering.
    """
    # Validate action if provided
    action_enum = None
    if action:
        try:
            action_enum = AuditAction(action)
        except ValueError:
            valid_actions = [a.value for a in AuditAction]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid action. Must be one of: {', '.join(valid_actions)}",
            )

    logs, total = audit_service.get_audit_logs(
        session=session,
        workspace_id=ctx.workspace_id,
        user_id=user_id,
        action=action_enum,
        resource_type=resource_type,
        resource_id=resource_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )

    return AuditLogListResponse(
        items=[
            AuditLogResponse(
                id=log.id,
                workspace_id=log.workspace_id,
                user_id=log.user_id,
                action=log.action.value
                if isinstance(log.action, AuditAction)
                else log.action,
                resource_type=log.resource_type,
                resource_id=log.resource_id,
                old_value=log.old_value,
                new_value=log.new_value,
                description=log.description,
                ip_address=log.ip_address,
                user_agent=log.user_agent,
                created_at=log.created_at,
            )
            for log in logs
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{audit_id}", response_model=AuditLogResponse)
async def get_audit_log(
    audit_id: UUID,
    ctx: Annotated[WorkspaceContext, Depends(require_workspace_scope(Scope.ADMIN))],
    session: Annotated[Session, Depends(get_session_dependency)],
):
    """Get a specific audit log entry.

    Requires admin scope.
    """
    try:
        log = audit_service.get_audit_log(session, audit_id, ctx.workspace_id)
        return AuditLogResponse(
            id=log.id,
            workspace_id=log.workspace_id,
            user_id=log.user_id,
            action=log.action.value
            if isinstance(log.action, AuditAction)
            else log.action,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            old_value=log.old_value,
            new_value=log.new_value,
            description=log.description,
            ip_address=log.ip_address,
            user_agent=log.user_agent,
            created_at=log.created_at,
        )
    except AuditNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit log entry not found",
        )


@router.get(
    "/resource/{resource_type}/{resource_id}", response_model=list[AuditLogResponse]
)
async def get_resource_history(
    resource_type: str,
    resource_id: UUID,
    ctx: Annotated[WorkspaceContext, Depends(require_workspace_scope(Scope.ADMIN))],
    session: Annotated[Session, Depends(get_session_dependency)],
    limit: int = Query(default=100, ge=1, le=500, description="Max results"),
):
    """Get audit history for a specific resource.

    Returns all audit log entries for the specified resource,
    ordered by most recent first.
    """
    logs = audit_service.get_resource_history(
        session=session,
        workspace_id=ctx.workspace_id,
        resource_type=resource_type,
        resource_id=resource_id,
        limit=limit,
    )

    return [
        AuditLogResponse(
            id=log.id,
            workspace_id=log.workspace_id,
            user_id=log.user_id,
            action=log.action.value
            if isinstance(log.action, AuditAction)
            else log.action,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            old_value=log.old_value,
            new_value=log.new_value,
            description=log.description,
            ip_address=log.ip_address,
            user_agent=log.user_agent,
            created_at=log.created_at,
        )
        for log in logs
    ]


@router.get("/user/{user_id}/activity", response_model=list[AuditLogResponse])
async def get_user_activity(
    user_id: UUID,
    ctx: Annotated[WorkspaceContext, Depends(require_workspace_scope(Scope.ADMIN))],
    session: Annotated[Session, Depends(get_session_dependency)],
    limit: int = Query(default=50, ge=1, le=200, description="Max results"),
):
    """Get recent activity for a specific user in the workspace.

    Returns all audit log entries for the specified user,
    ordered by most recent first.
    """
    logs = audit_service.get_user_activity(
        session=session,
        workspace_id=ctx.workspace_id,
        user_id=user_id,
        limit=limit,
    )

    return [
        AuditLogResponse(
            id=log.id,
            workspace_id=log.workspace_id,
            user_id=log.user_id,
            action=log.action.value
            if isinstance(log.action, AuditAction)
            else log.action,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            old_value=log.old_value,
            new_value=log.new_value,
            description=log.description,
            ip_address=log.ip_address,
            user_agent=log.user_agent,
            created_at=log.created_at,
        )
        for log in logs
    ]
