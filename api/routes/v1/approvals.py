"""Approval routes for managing content approval workflows.

Provides endpoints for:
- Approval stage management
- Post assignment
- Submitting/approving/rejecting content
- Approval comments
"""

from datetime import datetime
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel import Session

from api.auth.scopes import Scope
from api.routes.v1.dependencies import (
    WorkspaceContext,
    require_workspace_scope,
)
from api.services import (
    ApprovalService,
    ApprovalServiceError,
    StageNotFoundError,
    RequestNotFoundError,
    InvalidTransitionError,
)
from runner.db.engine import get_session_dependency


router = APIRouter(prefix="/v1/w/{workspace_id}/approvals", tags=["approvals"])

approval_service = ApprovalService()


# =============================================================================
# Request/Response Models
# =============================================================================


class ApprovalStageResponse(BaseModel):
    """Response model for approval stages."""

    id: UUID
    workspace_id: UUID
    name: str
    description: Optional[str]
    order: int
    is_required: bool
    is_active: bool
    auto_approve_role: Optional[str]
    created_at: datetime


class CreateStageRequest(BaseModel):
    """Request to create an approval stage."""

    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = None
    order: int = Field(default=0, ge=0)
    is_required: bool = True
    auto_approve_role: Optional[str] = None


class UpdateStageRequest(BaseModel):
    """Request to update an approval stage."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = None
    order: Optional[int] = Field(default=None, ge=0)
    is_required: Optional[bool] = None
    auto_approve_role: Optional[str] = None


class AssignPostRequest(BaseModel):
    """Request to assign a post to a user."""

    post_id: UUID
    assignee_id: Optional[UUID] = None  # None to unassign
    notes: Optional[str] = None


class AssignmentHistoryResponse(BaseModel):
    """Response model for assignment history."""

    id: UUID
    post_id: UUID
    action: str
    previous_assignee_id: Optional[UUID]
    new_assignee_id: Optional[UUID]
    assigned_by_id: UUID
    notes: Optional[str]
    created_at: datetime


class SubmitForApprovalRequest(BaseModel):
    """Request to submit a post for approval."""

    post_id: UUID
    stage_id: Optional[UUID] = None  # Auto-select first stage if not provided
    assigned_approver_id: Optional[UUID] = None


class ApprovalRequestResponse(BaseModel):
    """Response model for approval requests."""

    id: UUID
    post_id: UUID
    workspace_id: UUID
    stage_id: UUID
    submitted_by_id: UUID
    assigned_approver_id: Optional[UUID]
    decided_by_id: Optional[UUID]
    status: str
    submitted_at: datetime
    decided_at: Optional[datetime]
    decision_notes: Optional[str]
    content_version: Optional[int]
    created_at: datetime


class ApprovalDecisionRequest(BaseModel):
    """Request for approval decisions (approve/reject/request changes)."""

    notes: Optional[str] = None


class AddCommentRequest(BaseModel):
    """Request to add a comment to an approval request."""

    content: str = Field(min_length=1)
    is_internal: bool = False
    line_reference: Optional[str] = None


class CommentResponse(BaseModel):
    """Response model for approval comments."""

    id: UUID
    approval_request_id: UUID
    author_id: UUID
    content: str
    is_internal: bool
    line_reference: Optional[str]
    created_at: datetime


# =============================================================================
# Approval Stages
# =============================================================================


@router.get("/stages", response_model=list[ApprovalStageResponse])
async def list_stages(
    ctx: Annotated[
        WorkspaceContext, Depends(require_workspace_scope(Scope.CONTENT_READ))
    ],
    session: Annotated[Session, Depends(get_session_dependency)],
    include_inactive: bool = False,
):
    """List approval stages for the workspace."""
    stages = approval_service.get_workspace_stages(
        session, ctx.workspace_id, include_inactive
    )
    return [
        ApprovalStageResponse(
            id=s.id,
            workspace_id=s.workspace_id,
            name=s.name,
            description=s.description,
            order=s.order,
            is_required=s.is_required,
            is_active=s.is_active,
            auto_approve_role=s.auto_approve_role,
            created_at=s.created_at,
        )
        for s in stages
    ]


@router.post(
    "/stages", response_model=ApprovalStageResponse, status_code=status.HTTP_201_CREATED
)
async def create_stage(
    request: CreateStageRequest,
    ctx: Annotated[WorkspaceContext, Depends(require_workspace_scope(Scope.ADMIN))],
    session: Annotated[Session, Depends(get_session_dependency)],
):
    """Create a new approval stage. Requires admin scope."""
    stage = approval_service.create_stage(
        session,
        ctx.workspace_id,
        ctx.user_id,
        name=request.name,
        description=request.description,
        order=request.order,
        is_required=request.is_required,
        auto_approve_role=request.auto_approve_role,
    )
    return ApprovalStageResponse(
        id=stage.id,
        workspace_id=stage.workspace_id,
        name=stage.name,
        description=stage.description,
        order=stage.order,
        is_required=stage.is_required,
        is_active=stage.is_active,
        auto_approve_role=stage.auto_approve_role,
        created_at=stage.created_at,
    )


@router.patch("/stages/{stage_id}", response_model=ApprovalStageResponse)
async def update_stage(
    stage_id: UUID,
    request: UpdateStageRequest,
    ctx: Annotated[WorkspaceContext, Depends(require_workspace_scope(Scope.ADMIN))],
    session: Annotated[Session, Depends(get_session_dependency)],
):
    """Update an approval stage. Requires admin scope."""
    try:
        stage = approval_service.update_stage(
            session,
            stage_id,
            ctx.workspace_id,
            **request.model_dump(exclude_unset=True),
        )
        return ApprovalStageResponse(
            id=stage.id,
            workspace_id=stage.workspace_id,
            name=stage.name,
            description=stage.description,
            order=stage.order,
            is_required=stage.is_required,
            is_active=stage.is_active,
            auto_approve_role=stage.auto_approve_role,
            created_at=stage.created_at,
        )
    except StageNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Stage not found"
        )


@router.delete("/stages/{stage_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_stage(
    stage_id: UUID,
    ctx: Annotated[WorkspaceContext, Depends(require_workspace_scope(Scope.ADMIN))],
    session: Annotated[Session, Depends(get_session_dependency)],
):
    """Delete (deactivate) an approval stage. Requires admin scope."""
    try:
        approval_service.delete_stage(session, stage_id, ctx.workspace_id)
    except StageNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Stage not found"
        )


# =============================================================================
# Post Assignment
# =============================================================================


@router.post("/assign", response_model=AssignmentHistoryResponse)
async def assign_post(
    request: AssignPostRequest,
    ctx: Annotated[
        WorkspaceContext, Depends(require_workspace_scope(Scope.CONTENT_WRITE))
    ],
    session: Annotated[Session, Depends(get_session_dependency)],
):
    """Assign or reassign a post to a user."""
    try:
        history = approval_service.assign_post(
            session,
            request.post_id,
            ctx.workspace_id,
            ctx.user_id,
            request.assignee_id,
            request.notes,
        )
        return AssignmentHistoryResponse(
            id=history.id,
            post_id=history.post_id,
            action=history.action,
            previous_assignee_id=history.previous_assignee_id,
            new_assignee_id=history.new_assignee_id,
            assigned_by_id=history.assigned_by_id,
            notes=history.notes,
            created_at=history.created_at,
        )
    except ApprovalServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/posts/{post_id}/assignments", response_model=list[AssignmentHistoryResponse]
)
async def get_assignment_history(
    post_id: UUID,
    ctx: Annotated[
        WorkspaceContext, Depends(require_workspace_scope(Scope.CONTENT_READ))
    ],
    session: Annotated[Session, Depends(get_session_dependency)],
):
    """Get assignment history for a post."""
    history = approval_service.get_assignment_history(
        session, post_id, ctx.workspace_id
    )
    return [
        AssignmentHistoryResponse(
            id=h.id,
            post_id=h.post_id,
            action=h.action,
            previous_assignee_id=h.previous_assignee_id,
            new_assignee_id=h.new_assignee_id,
            assigned_by_id=h.assigned_by_id,
            notes=h.notes,
            created_at=h.created_at,
        )
        for h in history
    ]


# =============================================================================
# Approval Requests
# =============================================================================


@router.post(
    "/submit",
    response_model=ApprovalRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_for_approval(
    request: SubmitForApprovalRequest,
    ctx: Annotated[
        WorkspaceContext, Depends(require_workspace_scope(Scope.CONTENT_WRITE))
    ],
    session: Annotated[Session, Depends(get_session_dependency)],
):
    """Submit a post for approval."""
    try:
        approval_request = approval_service.submit_for_approval(
            session,
            request.post_id,
            ctx.workspace_id,
            ctx.user_id,
            request.stage_id,
            request.assigned_approver_id,
        )
        return ApprovalRequestResponse(
            id=approval_request.id,
            post_id=approval_request.post_id,
            workspace_id=approval_request.workspace_id,
            stage_id=approval_request.stage_id,
            submitted_by_id=approval_request.submitted_by_id,
            assigned_approver_id=approval_request.assigned_approver_id,
            decided_by_id=approval_request.decided_by_id,
            status=approval_request.status,
            submitted_at=approval_request.submitted_at,
            decided_at=approval_request.decided_at,
            decision_notes=approval_request.decision_notes,
            content_version=approval_request.content_version,
            created_at=approval_request.created_at,
        )
    except StageNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Stage not found"
        )
    except ApprovalServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/pending", response_model=list[ApprovalRequestResponse])
async def get_pending_approvals(
    ctx: Annotated[
        WorkspaceContext, Depends(require_workspace_scope(Scope.CONTENT_READ))
    ],
    session: Annotated[Session, Depends(get_session_dependency)],
    mine_only: bool = False,
):
    """Get pending approval requests.

    If mine_only=True, only returns requests assigned to the current user.
    """
    approver_id = ctx.user_id if mine_only else None
    requests = approval_service.get_pending_approvals(
        session, ctx.workspace_id, approver_id
    )
    return [
        ApprovalRequestResponse(
            id=r.id,
            post_id=r.post_id,
            workspace_id=r.workspace_id,
            stage_id=r.stage_id,
            submitted_by_id=r.submitted_by_id,
            assigned_approver_id=r.assigned_approver_id,
            decided_by_id=r.decided_by_id,
            status=r.status,
            submitted_at=r.submitted_at,
            decided_at=r.decided_at,
            decision_notes=r.decision_notes,
            content_version=r.content_version,
            created_at=r.created_at,
        )
        for r in requests
    ]


@router.get("/posts/{post_id}/history", response_model=list[ApprovalRequestResponse])
async def get_post_approval_history(
    post_id: UUID,
    ctx: Annotated[
        WorkspaceContext, Depends(require_workspace_scope(Scope.CONTENT_READ))
    ],
    session: Annotated[Session, Depends(get_session_dependency)],
):
    """Get approval history for a post."""
    requests = approval_service.get_post_approval_history(
        session, post_id, ctx.workspace_id
    )
    return [
        ApprovalRequestResponse(
            id=r.id,
            post_id=r.post_id,
            workspace_id=r.workspace_id,
            stage_id=r.stage_id,
            submitted_by_id=r.submitted_by_id,
            assigned_approver_id=r.assigned_approver_id,
            decided_by_id=r.decided_by_id,
            status=r.status,
            submitted_at=r.submitted_at,
            decided_at=r.decided_at,
            decision_notes=r.decision_notes,
            content_version=r.content_version,
            created_at=r.created_at,
        )
        for r in requests
    ]


@router.post("/requests/{request_id}/approve", response_model=ApprovalRequestResponse)
async def approve_request(
    request_id: UUID,
    body: ApprovalDecisionRequest,
    ctx: Annotated[
        WorkspaceContext, Depends(require_workspace_scope(Scope.CONTENT_APPROVE))
    ],
    session: Annotated[Session, Depends(get_session_dependency)],
):
    """Approve an approval request. Requires content:approve scope."""
    try:
        approval_request = approval_service.approve(
            session,
            request_id,
            ctx.workspace_id,
            ctx.user_id,
            body.notes,
        )
        return ApprovalRequestResponse(
            id=approval_request.id,
            post_id=approval_request.post_id,
            workspace_id=approval_request.workspace_id,
            stage_id=approval_request.stage_id,
            submitted_by_id=approval_request.submitted_by_id,
            assigned_approver_id=approval_request.assigned_approver_id,
            decided_by_id=approval_request.decided_by_id,
            status=approval_request.status,
            submitted_at=approval_request.submitted_at,
            decided_at=approval_request.decided_at,
            decision_notes=approval_request.decision_notes,
            content_version=approval_request.content_version,
            created_at=approval_request.created_at,
        )
    except RequestNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Request not found"
        )
    except InvalidTransitionError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/requests/{request_id}/reject", response_model=ApprovalRequestResponse)
async def reject_request(
    request_id: UUID,
    body: ApprovalDecisionRequest,
    ctx: Annotated[
        WorkspaceContext, Depends(require_workspace_scope(Scope.CONTENT_APPROVE))
    ],
    session: Annotated[Session, Depends(get_session_dependency)],
):
    """Reject an approval request. Requires content:approve scope."""
    if not body.notes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Notes are required when rejecting",
        )
    try:
        approval_request = approval_service.reject(
            session,
            request_id,
            ctx.workspace_id,
            ctx.user_id,
            body.notes,
        )
        return ApprovalRequestResponse(
            id=approval_request.id,
            post_id=approval_request.post_id,
            workspace_id=approval_request.workspace_id,
            stage_id=approval_request.stage_id,
            submitted_by_id=approval_request.submitted_by_id,
            assigned_approver_id=approval_request.assigned_approver_id,
            decided_by_id=approval_request.decided_by_id,
            status=approval_request.status,
            submitted_at=approval_request.submitted_at,
            decided_at=approval_request.decided_at,
            decision_notes=approval_request.decision_notes,
            content_version=approval_request.content_version,
            created_at=approval_request.created_at,
        )
    except RequestNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Request not found"
        )
    except InvalidTransitionError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/requests/{request_id}/request-changes", response_model=ApprovalRequestResponse
)
async def request_changes(
    request_id: UUID,
    body: ApprovalDecisionRequest,
    ctx: Annotated[
        WorkspaceContext, Depends(require_workspace_scope(Scope.CONTENT_APPROVE))
    ],
    session: Annotated[Session, Depends(get_session_dependency)],
):
    """Request changes on an approval request. Requires content:approve scope."""
    if not body.notes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Notes are required when requesting changes",
        )
    try:
        approval_request = approval_service.request_changes(
            session,
            request_id,
            ctx.workspace_id,
            ctx.user_id,
            body.notes,
        )
        return ApprovalRequestResponse(
            id=approval_request.id,
            post_id=approval_request.post_id,
            workspace_id=approval_request.workspace_id,
            stage_id=approval_request.stage_id,
            submitted_by_id=approval_request.submitted_by_id,
            assigned_approver_id=approval_request.assigned_approver_id,
            decided_by_id=approval_request.decided_by_id,
            status=approval_request.status,
            submitted_at=approval_request.submitted_at,
            decided_at=approval_request.decided_at,
            decision_notes=approval_request.decision_notes,
            content_version=approval_request.content_version,
            created_at=approval_request.created_at,
        )
    except RequestNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Request not found"
        )
    except InvalidTransitionError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/requests/{request_id}/withdraw", response_model=ApprovalRequestResponse)
async def withdraw_request(
    request_id: UUID,
    ctx: Annotated[
        WorkspaceContext, Depends(require_workspace_scope(Scope.CONTENT_WRITE))
    ],
    session: Annotated[Session, Depends(get_session_dependency)],
):
    """Withdraw an approval request (submitter only)."""
    try:
        approval_request = approval_service.withdraw(
            session,
            request_id,
            ctx.workspace_id,
            ctx.user_id,
        )
        return ApprovalRequestResponse(
            id=approval_request.id,
            post_id=approval_request.post_id,
            workspace_id=approval_request.workspace_id,
            stage_id=approval_request.stage_id,
            submitted_by_id=approval_request.submitted_by_id,
            assigned_approver_id=approval_request.assigned_approver_id,
            decided_by_id=approval_request.decided_by_id,
            status=approval_request.status,
            submitted_at=approval_request.submitted_at,
            decided_at=approval_request.decided_at,
            decision_notes=approval_request.decision_notes,
            content_version=approval_request.content_version,
            created_at=approval_request.created_at,
        )
    except RequestNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Request not found"
        )
    except (InvalidTransitionError, ApprovalServiceError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# =============================================================================
# Comments
# =============================================================================


@router.post(
    "/requests/{request_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_comment(
    request_id: UUID,
    body: AddCommentRequest,
    ctx: Annotated[
        WorkspaceContext, Depends(require_workspace_scope(Scope.CONTENT_WRITE))
    ],
    session: Annotated[Session, Depends(get_session_dependency)],
):
    """Add a comment to an approval request."""
    try:
        comment = approval_service.add_comment(
            session,
            request_id,
            ctx.workspace_id,
            ctx.user_id,
            body.content,
            body.is_internal,
            body.line_reference,
        )
        return CommentResponse(
            id=comment.id,
            approval_request_id=comment.approval_request_id,
            author_id=comment.author_id,
            content=comment.content,
            is_internal=comment.is_internal,
            line_reference=comment.line_reference,
            created_at=comment.created_at,
        )
    except RequestNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Request not found"
        )


@router.get("/requests/{request_id}/comments", response_model=list[CommentResponse])
async def get_comments(
    request_id: UUID,
    ctx: Annotated[
        WorkspaceContext, Depends(require_workspace_scope(Scope.CONTENT_READ))
    ],
    session: Annotated[Session, Depends(get_session_dependency)],
    include_internal: bool = True,
):
    """Get comments for an approval request."""
    comments = approval_service.get_comments(
        session, request_id, ctx.workspace_id, include_internal
    )
    return [
        CommentResponse(
            id=c.id,
            approval_request_id=c.approval_request_id,
            author_id=c.author_id,
            content=c.content,
            is_internal=c.is_internal,
            line_reference=c.line_reference,
            created_at=c.created_at,
        )
        for c in comments
    ]
