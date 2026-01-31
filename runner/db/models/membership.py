"""Workspace membership model for multi-tenancy RBAC.

Links users to workspaces with specific roles. Each membership defines
what a user can do within a workspace.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from sqlmodel import Field, SQLModel

from runner.db.models.base import UUIDModel, TimestampMixin


class WorkspaceRole(str, Enum):
    """Role enum for workspace memberships.

    Roles define permission levels within a workspace:
    - owner: Billing owner, all permissions, can delete workspace
    - admin: Manage users, edit strategy, configure integrations
    - editor: Create/edit posts, run workflows, view strategy
    - viewer: View posts, view analytics, approve/reject (if enabled)
    """

    owner = "owner"
    admin = "admin"
    editor = "editor"
    viewer = "viewer"


class InviteStatus(str, Enum):
    """Status enum for workspace invitations."""

    pending = "pending"
    accepted = "accepted"
    expired = "expired"
    revoked = "revoked"


class WorkspaceMembershipBase(SQLModel):
    """Base membership fields shared across Create/Read/Update."""

    role: WorkspaceRole = Field(default=WorkspaceRole.viewer)


class WorkspaceMembership(
    UUIDModel, WorkspaceMembershipBase, TimestampMixin, table=True
):
    """Workspace membership table - links users to workspaces.

    This is the junction table that enables multi-tenancy. Each row
    grants a user access to a workspace with a specific role.
    """

    __tablename__ = "workspace_memberships"

    workspace_id: UUID = Field(foreign_key="workspaces.id", index=True)
    user_id: Optional[UUID] = Field(
        default=None,
        foreign_key="users.id",
        index=True,
    )

    # Email for pending invites (before user accepts)
    email: str = Field(index=True)

    # Invitation tracking
    invite_status: InviteStatus = Field(default=InviteStatus.pending)
    invite_token: Optional[str] = Field(default=None, index=True)
    invited_at: datetime = Field(default_factory=datetime.utcnow)
    accepted_at: Optional[datetime] = None

    # Compound unique constraint: one membership per user per workspace
    __table_args__ = (
        # Note: Unique constraint created in Alembic migration:
        # UniqueConstraint('workspace_id', 'user_id', name='uq_membership_workspace_user')
    )


class WorkspaceMembershipCreate(WorkspaceMembershipBase):
    """Schema for creating a new workspace membership."""

    workspace_id: UUID
    email: str
    user_id: Optional[UUID] = None
    invite_token: Optional[str] = None


class WorkspaceMembershipRead(WorkspaceMembershipBase):
    """Schema for reading workspace membership data."""

    id: UUID
    workspace_id: UUID
    user_id: Optional[UUID]
    email: str
    invite_status: InviteStatus
    invited_at: datetime
    accepted_at: Optional[datetime]
    created_at: datetime
