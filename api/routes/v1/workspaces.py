"""Workspace management routes.

Routes for workspace CRUD, member management, and invitations.
"""

from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from api.auth.dependencies import CurrentUser, get_current_user
from api.auth.scopes import Scope
from api.routes.v1.dependencies import WorkspaceCtx, require_workspace_scope
from api.services.workspace_service import WorkspaceService
from api.services.invite_service import InviteService
from runner.db.models import (
    WorkspaceRead,
    WorkspaceMembershipRead,
    WorkspaceRole,
)


router = APIRouter(prefix="/v1", tags=["workspaces"])


# =============================================================================
# Request/Response Models
# =============================================================================


class CreateWorkspaceRequest(BaseModel):
    """Request to create a new workspace."""

    name: str = Field(min_length=1, max_length=100)
    slug: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


class UpdateWorkspaceRequest(BaseModel):
    """Request to update workspace settings."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    slug: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


class InviteMemberRequest(BaseModel):
    """Request to invite a member to workspace."""

    email: EmailStr
    role: WorkspaceRole = WorkspaceRole.editor


class UpdateMemberRoleRequest(BaseModel):
    """Request to update a member's role."""

    role: WorkspaceRole


class WorkspaceSummary(BaseModel):
    """Workspace with summary info for listing."""

    id: UUID
    name: str
    slug: str
    description: Optional[str]
    role: WorkspaceRole
    member_count: int


class InviteResponse(BaseModel):
    """Response after creating an invitation."""

    membership_id: UUID
    email: str
    role: WorkspaceRole
    invite_token: str


# =============================================================================
# User's Workspaces (no workspace_id in path)
# =============================================================================


@router.get("/workspaces", response_model=list[WorkspaceSummary])
async def list_my_workspaces(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """List all workspaces the current user has access to."""
    service = WorkspaceService()
    workspaces = service.list_user_workspaces(current_user.user_id)

    result = []
    for workspace in workspaces:
        membership = service.get_user_membership(workspace.id, current_user.user_id)
        members = service.get_workspace_members(workspace.id)

        result.append(
            WorkspaceSummary(
                id=workspace.id,
                name=workspace.name,
                slug=workspace.slug,
                description=workspace.description,
                role=membership.role if membership else WorkspaceRole.viewer,
                member_count=len(
                    [m for m in members if m.invite_status.value == "accepted"]
                ),
            )
        )

    return result


@router.post(
    "/workspaces", response_model=WorkspaceRead, status_code=status.HTTP_201_CREATED
)
async def create_workspace(
    request: CreateWorkspaceRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """Create a new workspace.

    The current user becomes the owner.
    """
    service = WorkspaceService()

    try:
        workspace = service.create_workspace(
            owner_id=current_user.user_id,
            name=request.name,
            slug=request.slug,
            description=request.description,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return WorkspaceRead(
        id=workspace.id,
        name=workspace.name,
        slug=workspace.slug,
        description=workspace.description,
        owner_id=workspace.owner_id,
        created_at=workspace.created_at,
    )


# =============================================================================
# Workspace-scoped routes (with workspace_id in path)
# =============================================================================


@router.get("/w/{workspace_id}", response_model=WorkspaceRead)
async def get_workspace(ctx: WorkspaceCtx):
    """Get workspace details."""
    return WorkspaceRead(
        id=ctx.workspace.id,
        name=ctx.workspace.name,
        slug=ctx.workspace.slug,
        description=ctx.workspace.description,
        owner_id=ctx.workspace.owner_id,
        created_at=ctx.workspace.created_at,
    )


@router.patch("/w/{workspace_id}", response_model=WorkspaceRead)
async def update_workspace(
    request: UpdateWorkspaceRequest,
    ctx: Annotated[
        WorkspaceCtx, Depends(require_workspace_scope(Scope.WORKSPACE_SETTINGS))
    ],
):
    """Update workspace settings.

    Requires workspace:settings scope (admin or owner).
    """
    service = WorkspaceService()

    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )

    try:
        workspace = service.update_workspace(ctx.workspace_id, **updates)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    return WorkspaceRead(
        id=workspace.id,
        name=workspace.name,
        slug=workspace.slug,
        description=workspace.description,
        owner_id=workspace.owner_id,
        created_at=workspace.created_at,
    )


@router.delete("/w/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(
    ctx: Annotated[
        WorkspaceCtx, Depends(require_workspace_scope(Scope.WORKSPACE_DELETE))
    ],
):
    """Delete workspace and all associated data.

    Requires workspace:delete scope (owner only).
    """
    service = WorkspaceService()
    deleted = service.delete_workspace(ctx.workspace_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )


# =============================================================================
# Member Management
# =============================================================================


@router.get("/w/{workspace_id}/members", response_model=list[WorkspaceMembershipRead])
async def list_members(ctx: WorkspaceCtx):
    """List all members of the workspace."""
    service = WorkspaceService()
    members = service.get_workspace_members(ctx.workspace_id)

    return [
        WorkspaceMembershipRead(
            id=m.id,
            workspace_id=m.workspace_id,
            user_id=m.user_id,
            email=m.email,
            role=m.role,
            invite_status=m.invite_status,
            invited_at=m.invited_at,
            accepted_at=m.accepted_at,
            created_at=m.created_at,
        )
        for m in members
    ]


@router.post(
    "/w/{workspace_id}/members",
    response_model=InviteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def invite_member(
    request: InviteMemberRequest,
    ctx: Annotated[
        WorkspaceCtx, Depends(require_workspace_scope(Scope.WORKSPACE_USERS))
    ],
):
    """Invite a new member to the workspace.

    Requires workspace:users scope (admin or owner).
    """
    from api.services.invite_service import InviteExistsError, InviteError

    service = InviteService()

    try:
        membership = service.invite_member(
            workspace_id=ctx.workspace_id,
            email=request.email,
            role=request.role,
            invited_by=ctx.user_id,
        )
    except InviteExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except (ValueError, InviteError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return InviteResponse(
        membership_id=membership.id,
        email=membership.email,
        role=membership.role,
        invite_token=membership.invite_token or "",
    )


@router.patch(
    "/w/{workspace_id}/members/{member_id}", response_model=WorkspaceMembershipRead
)
async def update_member_role(
    member_id: UUID,
    request: UpdateMemberRoleRequest,
    ctx: Annotated[
        WorkspaceCtx, Depends(require_workspace_scope(Scope.WORKSPACE_USERS))
    ],
):
    """Update a member's role.

    Requires workspace:users scope (admin or owner).
    Cannot change the owner's role (use transfer_ownership instead).
    """
    from api.services.invite_service import InviteNotFoundError

    service = InviteService()

    try:
        membership = service.update_member_role(
            membership_id=member_id,
            new_role=request.role,
            updated_by=ctx.user_id,
        )
    except InviteNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return WorkspaceMembershipRead(
        id=membership.id,
        workspace_id=membership.workspace_id,
        user_id=membership.user_id,
        email=membership.email,
        role=membership.role,
        invite_status=membership.invite_status,
        invited_at=membership.invited_at,
        accepted_at=membership.accepted_at,
    )


@router.delete(
    "/w/{workspace_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def remove_member(
    member_id: UUID,
    ctx: Annotated[
        WorkspaceCtx, Depends(require_workspace_scope(Scope.WORKSPACE_USERS))
    ],
):
    """Remove a member from the workspace.

    Requires workspace:users scope (admin or owner).
    Cannot remove the owner.
    """
    service = InviteService()

    try:
        removed = service.remove_member(
            membership_id=member_id,
            removed_by=ctx.user_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )


# =============================================================================
# Invite Acceptance (no auth required, uses token)
# =============================================================================


@router.post("/invites/{token}/accept", response_model=WorkspaceMembershipRead)
async def accept_invite(
    token: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """Accept a workspace invitation.

    The logged-in user accepts the invite associated with the token.
    """
    from api.services.invite_service import (
        InviteNotFoundError,
        InviteExpiredError,
        InviteAlreadyAcceptedError,
        InviteError,
    )

    service = InviteService()

    try:
        membership = service.accept_invite(
            invite_token=token,
            user_id=current_user.user_id,
        )
    except InviteNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or expired invite token",
        )
    except InviteExpiredError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invite has expired",
        )
    except InviteAlreadyAcceptedError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invite was already accepted",
        )
    except InviteError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return WorkspaceMembershipRead(
        id=membership.id,
        workspace_id=membership.workspace_id,
        user_id=membership.user_id,
        email=membership.email,
        role=membership.role,
        invite_status=membership.invite_status,
        invited_at=membership.invited_at,
        accepted_at=membership.accepted_at,
    )
