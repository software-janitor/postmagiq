"""Service for workspace invitation and member management.

Handles inviting members, accepting invites, and managing member roles.
"""

import logging
from typing import Optional
from uuid import UUID

from runner.db.engine import engine
from runner.db.models import (
    WorkspaceMembership,
    WorkspaceRole,
    InviteStatus,
    User,
)
from runner.content.workspace_repository import (
    WorkspaceRepository,
    WorkspaceMembershipRepository,
)
from sqlmodel import Session, select

from api.services.email_service import email_service

logger = logging.getLogger(__name__)


class InviteError(Exception):
    """Base exception for invite-related errors."""

    pass


class InviteExistsError(InviteError):
    """Raised when trying to invite someone who already has an invite."""

    pass


class InviteNotFoundError(InviteError):
    """Raised when invite is not found."""

    pass


class InviteExpiredError(InviteError):
    """Raised when invite has expired."""

    pass


class InviteAlreadyAcceptedError(InviteError):
    """Raised when invite was already accepted."""

    pass


class InviteService:
    """Service for managing workspace invitations and members.

    Handles the full invite lifecycle:
    - Creating invites (invite_member)
    - Accepting invites (accept_invite)
    - Revoking pending invites (revoke_invite)
    - Updating member roles (update_member_role)
    - Removing members (remove_member)
    """

    def invite_member(
        self,
        workspace_id: UUID,
        email: str,
        role: WorkspaceRole = WorkspaceRole.viewer,
        invited_by: Optional[UUID] = None,
    ) -> WorkspaceMembership:
        """Invite a new member to a workspace.

        Creates a pending membership with an invite token. The invited
        user can accept via accept_invite() with the token.

        Args:
            workspace_id: Workspace to invite to
            email: Email address of the invitee
            role: Role to assign (default: viewer, cannot be owner)
            invited_by: User ID of who sent the invite (for audit)

        Returns:
            Created WorkspaceMembership with pending status

        Raises:
            InviteExistsError: If email already has pending/accepted membership
            ValueError: If trying to invite as owner role
        """
        if role == WorkspaceRole.owner:
            raise ValueError("Cannot invite as owner. Use transfer_ownership instead.")

        with Session(engine) as session:
            workspace_repo = WorkspaceRepository(session)
            membership_repo = WorkspaceMembershipRepository(session)

            # Verify workspace exists
            workspace = workspace_repo.get(workspace_id)
            if not workspace:
                raise InviteError("Workspace not found")

            # Check for existing membership
            existing = membership_repo.get_by_workspace_and_email(workspace_id, email)
            if existing:
                if existing.invite_status == InviteStatus.accepted:
                    raise InviteExistsError("User is already a member")
                if existing.invite_status == InviteStatus.pending:
                    raise InviteExistsError("User already has a pending invite")

                # If revoked/expired, we can create a new invite
                # Delete the old one first
                membership_repo.delete(existing.id)

            # Create new invite
            membership = membership_repo.create_invite(
                workspace_id=workspace_id,
                email=email,
                role=role,
            )

            # Get inviter name for email
            inviter_name = None
            if invited_by:
                inviter = session.exec(
                    select(User).where(User.id == invited_by)
                ).first()
                if inviter:
                    inviter_name = inviter.full_name or inviter.email

            # Send invitation email
            if membership.invite_token:
                email_sent = email_service.send_workspace_invite(
                    to_email=email,
                    workspace_name=workspace.name,
                    invite_token=membership.invite_token,
                    inviter_name=inviter_name,
                )
                if not email_sent:
                    logger.warning(f"Failed to send invite email to {email}")

            session.expunge(membership)
            return membership

    def accept_invite(
        self,
        invite_token: str,
        user_id: UUID,
    ) -> WorkspaceMembership:
        """Accept a workspace invitation.

        Links the membership to the accepting user and marks it as accepted.
        The user's email must match the invite email, or this could be used
        for privilege escalation.

        Args:
            invite_token: The unique invite token
            user_id: User accepting the invite

        Returns:
            Updated WorkspaceMembership with accepted status

        Raises:
            InviteNotFoundError: If token is invalid
            InviteExpiredError: If invite has expired
            InviteAlreadyAcceptedError: If invite was already accepted
            InviteError: If user's email doesn't match invite
        """
        with Session(engine) as session:
            membership_repo = WorkspaceMembershipRepository(session)

            # Find invite by token
            membership = membership_repo.get_by_token(invite_token)
            if not membership:
                raise InviteNotFoundError("Invalid invite token")

            # Check status
            if membership.invite_status == InviteStatus.accepted:
                raise InviteAlreadyAcceptedError("Invite was already accepted")
            if membership.invite_status == InviteStatus.revoked:
                raise InviteNotFoundError("Invite has been revoked")
            if membership.invite_status == InviteStatus.expired:
                raise InviteExpiredError("Invite has expired")

            # Verify user's email matches invite email
            user = session.get(User, user_id)
            if not user:
                raise InviteError("User not found")

            if user.email and user.email.lower() != membership.email.lower():
                raise InviteError("Invite was sent to a different email address")

            # Accept the invite
            membership = membership_repo.accept_invite(membership.id, user_id)
            if membership:
                session.expunge(membership)
            return membership

    def accept_invite_by_email(
        self,
        workspace_id: UUID,
        user_id: UUID,
        email: str,
    ) -> Optional[WorkspaceMembership]:
        """Accept an invite by email match.

        Used when a user registers with an email that has pending invites.
        This method auto-accepts invites without requiring the token.

        Args:
            workspace_id: Workspace to check
            user_id: User to accept as
            email: Email to match

        Returns:
            Updated WorkspaceMembership if found and accepted, None otherwise
        """
        with Session(engine) as session:
            membership_repo = WorkspaceMembershipRepository(session)

            membership = membership_repo.get_by_workspace_and_email(workspace_id, email)
            if not membership:
                return None
            if membership.invite_status != InviteStatus.pending:
                return None

            membership = membership_repo.accept_invite(membership.id, user_id)
            if membership:
                session.expunge(membership)
            return membership

    def get_pending_invites_for_email(self, email: str) -> list[WorkspaceMembership]:
        """Get all pending invites for an email address.

        Useful when a user registers to auto-link their pending invites.

        Args:
            email: Email address to check

        Returns:
            List of pending WorkspaceMembership invites
        """
        with Session(engine) as session:
            membership_repo = WorkspaceMembershipRepository(session)
            invites = membership_repo.list_pending_by_email(email)
            for i in invites:
                session.expunge(i)
            return invites

    def revoke_invite(self, membership_id: UUID) -> WorkspaceMembership:
        """Revoke a pending invitation.

        Only works for invites with pending status.

        Args:
            membership_id: Membership/invite UUID

        Returns:
            Updated WorkspaceMembership with revoked status

        Raises:
            InviteNotFoundError: If membership not found
            InviteError: If invite is not in pending status
        """
        with Session(engine) as session:
            membership_repo = WorkspaceMembershipRepository(session)

            membership = membership_repo.get(membership_id)
            if not membership:
                raise InviteNotFoundError("Invite not found")

            if membership.invite_status != InviteStatus.pending:
                raise InviteError("Can only revoke pending invites")

            membership = membership_repo.revoke_invite(membership_id)
            if membership:
                session.expunge(membership)
            return membership

    def update_member_role(
        self,
        membership_id: UUID,
        new_role: WorkspaceRole,
        updated_by: Optional[UUID] = None,
    ) -> WorkspaceMembership:
        """Update a member's role.

        Cannot change to owner role (use transfer_ownership instead).
        Cannot change the owner's role (would leave workspace without owner).

        Args:
            membership_id: Membership UUID
            new_role: New role to assign
            updated_by: User ID of who made the change (for audit)

        Returns:
            Updated WorkspaceMembership

        Raises:
            InviteNotFoundError: If membership not found
            ValueError: If trying to set owner role
            ValueError: If trying to change owner's role
        """
        if new_role == WorkspaceRole.owner:
            raise ValueError("Cannot assign owner role. Use transfer_ownership.")

        with Session(engine) as session:
            membership_repo = WorkspaceMembershipRepository(session)

            membership = membership_repo.get(membership_id)
            if not membership:
                raise InviteNotFoundError("Membership not found")

            if membership.role == WorkspaceRole.owner:
                raise ValueError("Cannot change owner's role. Use transfer_ownership.")

            membership = membership_repo.update_role(membership_id, new_role)
            if membership:
                session.expunge(membership)
            return membership

    def remove_member(
        self,
        membership_id: UUID,
        removed_by: Optional[UUID] = None,
    ) -> bool:
        """Remove a member from a workspace.

        Cannot remove the workspace owner.

        Args:
            membership_id: Membership UUID to remove
            removed_by: User ID of who removed them (for audit)

        Returns:
            True if removed, False if not found

        Raises:
            ValueError: If trying to remove the owner
        """
        with Session(engine) as session:
            membership_repo = WorkspaceMembershipRepository(session)

            membership = membership_repo.get(membership_id)
            if not membership:
                return False

            if membership.role == WorkspaceRole.owner:
                raise ValueError("Cannot remove workspace owner")

            return membership_repo.delete(membership_id)

    def get_member_by_id(self, membership_id: UUID) -> Optional[WorkspaceMembership]:
        """Get a membership by ID.

        Args:
            membership_id: Membership UUID

        Returns:
            WorkspaceMembership if found, None otherwise
        """
        with Session(engine) as session:
            membership_repo = WorkspaceMembershipRepository(session)
            membership = membership_repo.get(membership_id)
            if membership:
                session.expunge(membership)
            return membership

    def get_membership_by_token(
        self, invite_token: str
    ) -> Optional[WorkspaceMembership]:
        """Get a membership by invite token.

        Useful to show invite details before accepting.

        Args:
            invite_token: The unique invite token

        Returns:
            WorkspaceMembership if found, None otherwise
        """
        with Session(engine) as session:
            membership_repo = WorkspaceMembershipRepository(session)
            membership = membership_repo.get_by_token(invite_token)
            if membership:
                session.expunge(membership)
            return membership
