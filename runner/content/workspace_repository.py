"""Repository classes for Workspace and WorkspaceMembership.

These repositories handle multi-tenancy operations:
- Workspace CRUD and management
- Membership management (invites, role changes, etc.)
"""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Session, select

from runner.db.models import (
    Workspace,
    WorkspaceCreate,
    WorkspaceMembership,
    WorkspaceMembershipCreate,
    WorkspaceRole,
    InviteStatus,
)


# =============================================================================
# Workspace Repository
# =============================================================================


class WorkspaceRepository:
    """Repository for Workspace operations."""

    def __init__(self, session: Session):
        self.session = session

    def create(self, data: WorkspaceCreate) -> Workspace:
        """Create a new workspace."""
        workspace = Workspace.model_validate(data)
        self.session.add(workspace)
        self.session.commit()
        self.session.refresh(workspace)
        return workspace

    def get(self, workspace_id: UUID) -> Optional[Workspace]:
        """Get a workspace by ID."""
        return self.session.get(Workspace, workspace_id)

    def get_by_slug(self, slug: str) -> Optional[Workspace]:
        """Get a workspace by slug."""
        statement = select(Workspace).where(Workspace.slug == slug)
        return self.session.exec(statement).first()

    def list_by_owner(self, owner_id: UUID) -> list[Workspace]:
        """List all workspaces owned by a user."""
        statement = select(Workspace).where(Workspace.owner_id == owner_id)
        return list(self.session.exec(statement).all())

    def list_by_user(self, user_id: UUID) -> list[Workspace]:
        """List all workspaces a user has access to (via memberships).

        This includes workspaces the user owns and workspaces they are
        members of.
        """
        # Get workspaces through accepted memberships
        statement = (
            select(Workspace)
            .join(
                WorkspaceMembership,
                Workspace.id == WorkspaceMembership.workspace_id,
            )
            .where(
                WorkspaceMembership.user_id == user_id,
                WorkspaceMembership.invite_status == InviteStatus.accepted,
            )
        )
        return list(self.session.exec(statement).all())

    def update(self, workspace_id: UUID, **kwargs) -> Optional[Workspace]:
        """Update workspace fields."""
        workspace = self.get(workspace_id)
        if workspace:
            for key, value in kwargs.items():
                if hasattr(workspace, key):
                    setattr(workspace, key, value)
            workspace.updated_at = datetime.utcnow()
            self.session.add(workspace)
            self.session.commit()
            self.session.refresh(workspace)
        return workspace

    def delete(self, workspace_id: UUID) -> bool:
        """Delete a workspace by ID. Returns True if deleted."""
        workspace = self.get(workspace_id)
        if workspace:
            self.session.delete(workspace)
            self.session.commit()
            return True
        return False


# =============================================================================
# Workspace Membership Repository
# =============================================================================


class WorkspaceMembershipRepository:
    """Repository for WorkspaceMembership operations."""

    def __init__(self, session: Session):
        self.session = session

    def create(self, data: WorkspaceMembershipCreate) -> WorkspaceMembership:
        """Create a new workspace membership (invite)."""
        membership = WorkspaceMembership.model_validate(data)
        self.session.add(membership)
        self.session.commit()
        self.session.refresh(membership)
        return membership

    def get(self, membership_id: UUID) -> Optional[WorkspaceMembership]:
        """Get a membership by ID."""
        return self.session.get(WorkspaceMembership, membership_id)

    def get_by_token(self, invite_token: str) -> Optional[WorkspaceMembership]:
        """Get a membership by invite token."""
        statement = select(WorkspaceMembership).where(
            WorkspaceMembership.invite_token == invite_token
        )
        return self.session.exec(statement).first()

    def get_by_workspace_and_user(
        self, workspace_id: UUID, user_id: UUID
    ) -> Optional[WorkspaceMembership]:
        """Get a membership for a specific workspace and user."""
        statement = select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.user_id == user_id,
        )
        return self.session.exec(statement).first()

    def get_by_workspace_and_email(
        self, workspace_id: UUID, email: str
    ) -> Optional[WorkspaceMembership]:
        """Get a membership for a specific workspace and email."""
        statement = select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.email == email,
        )
        return self.session.exec(statement).first()

    def list_by_workspace(self, workspace_id: UUID) -> list[WorkspaceMembership]:
        """List all memberships for a workspace."""
        statement = select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == workspace_id
        )
        return list(self.session.exec(statement).all())

    def list_by_user(self, user_id: UUID) -> list[WorkspaceMembership]:
        """List all memberships for a user."""
        statement = select(WorkspaceMembership).where(
            WorkspaceMembership.user_id == user_id
        )
        return list(self.session.exec(statement).all())

    def list_pending_by_email(self, email: str) -> list[WorkspaceMembership]:
        """List all pending invites for an email address."""
        statement = select(WorkspaceMembership).where(
            WorkspaceMembership.email == email,
            WorkspaceMembership.invite_status == InviteStatus.pending,
        )
        return list(self.session.exec(statement).all())

    def create_invite(
        self,
        workspace_id: UUID,
        email: str,
        role: WorkspaceRole = WorkspaceRole.viewer,
    ) -> WorkspaceMembership:
        """Create a new invite for a workspace.

        Generates an invite token and sets status to pending.
        """
        invite_token = str(uuid4())
        data = WorkspaceMembershipCreate(
            workspace_id=workspace_id,
            email=email,
            role=role,
            invite_token=invite_token,
        )
        return self.create(data)

    def accept_invite(
        self, membership_id: UUID, user_id: UUID
    ) -> Optional[WorkspaceMembership]:
        """Accept an invite and link it to a user."""
        membership = self.get(membership_id)
        if membership and membership.invite_status == InviteStatus.pending:
            membership.user_id = user_id
            membership.invite_status = InviteStatus.accepted
            membership.accepted_at = datetime.utcnow()
            membership.invite_token = None  # Clear token after use
            self.session.add(membership)
            self.session.commit()
            self.session.refresh(membership)
        return membership

    def revoke_invite(self, membership_id: UUID) -> Optional[WorkspaceMembership]:
        """Revoke a pending invite."""
        membership = self.get(membership_id)
        if membership and membership.invite_status == InviteStatus.pending:
            membership.invite_status = InviteStatus.revoked
            membership.invite_token = None
            self.session.add(membership)
            self.session.commit()
            self.session.refresh(membership)
        return membership

    def update_role(
        self, membership_id: UUID, role: WorkspaceRole
    ) -> Optional[WorkspaceMembership]:
        """Update a member's role."""
        membership = self.get(membership_id)
        if membership:
            membership.role = role
            membership.updated_at = datetime.utcnow()
            self.session.add(membership)
            self.session.commit()
            self.session.refresh(membership)
        return membership

    def delete(self, membership_id: UUID) -> bool:
        """Delete a membership by ID. Returns True if deleted."""
        membership = self.get(membership_id)
        if membership:
            self.session.delete(membership)
            self.session.commit()
            return True
        return False

    def is_owner(self, workspace_id: UUID, user_id: UUID) -> bool:
        """Check if a user is the owner of a workspace."""
        membership = self.get_by_workspace_and_user(workspace_id, user_id)
        return membership is not None and membership.role == WorkspaceRole.owner

    def has_access(self, workspace_id: UUID, user_id: UUID) -> bool:
        """Check if a user has any access to a workspace."""
        membership = self.get_by_workspace_and_user(workspace_id, user_id)
        return (
            membership is not None and membership.invite_status == InviteStatus.accepted
        )
