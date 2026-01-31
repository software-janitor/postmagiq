"""Approval and assignment models for Phase 6.

Includes:
- PostAssignmentHistory: tracks assignment changes over time
- ApprovalStage: defines workflow stages (e.g., draft review, final approval)
- ApprovalRequest: individual approval requests for posts
- ApprovalComment: comments/feedback on approval requests
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from sqlmodel import Field, SQLModel

from runner.db.models.base import UUIDModel, TimestampMixin


# =============================================================================
# Enums
# =============================================================================


class PostPriority(str, Enum):
    """Post priority levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class ApprovalStatus(str, Enum):
    """Status of an approval request."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CHANGES_REQUESTED = "changes_requested"
    WITHDRAWN = "withdrawn"


class AssignmentAction(str, Enum):
    """Types of assignment history actions."""

    ASSIGNED = "assigned"
    REASSIGNED = "reassigned"
    UNASSIGNED = "unassigned"


# =============================================================================
# Post Assignment History
# =============================================================================


class PostAssignmentHistoryBase(SQLModel):
    """Base fields for assignment history records."""

    action: str  # AssignmentAction value
    notes: Optional[str] = None


class PostAssignmentHistory(
    UUIDModel, PostAssignmentHistoryBase, TimestampMixin, table=True
):
    """Tracks all assignment changes for posts.

    Each row represents a single assignment event (assigned, reassigned, unassigned).
    This creates an audit trail of who worked on each post and when.
    """

    __tablename__ = "post_assignment_history"

    post_id: UUID = Field(foreign_key="posts.id", index=True)
    workspace_id: UUID = Field(foreign_key="workspaces.id", index=True)

    # Who made the assignment change
    assigned_by_id: UUID = Field(foreign_key="users.id", index=True)

    # The previous assignee (null for initial assignment)
    previous_assignee_id: Optional[UUID] = Field(
        default=None,
        foreign_key="users.id",
    )

    # The new assignee (null for unassignment)
    new_assignee_id: Optional[UUID] = Field(
        default=None,
        foreign_key="users.id",
    )


# =============================================================================
# Approval Stage
# =============================================================================


class ApprovalStageBase(SQLModel):
    """Base fields for approval stage definitions."""

    name: str = Field(index=True)  # e.g., "Draft Review", "Final Approval"
    description: Optional[str] = None
    order: int = Field(default=0)  # Stage order in workflow
    is_required: bool = Field(default=True)
    auto_approve_role: Optional[str] = None  # Role that auto-approves this stage


class ApprovalStage(UUIDModel, ApprovalStageBase, TimestampMixin, table=True):
    """Defines approval workflow stages for a workspace.

    Workspaces can configure their own approval workflows with multiple stages.
    Posts move through stages in order (based on `order` field).
    """

    __tablename__ = "approval_stages"

    workspace_id: UUID = Field(foreign_key="workspaces.id", index=True)

    # Who created this stage definition
    created_by_id: UUID = Field(foreign_key="users.id")

    # Whether this stage is active
    is_active: bool = Field(default=True)


class ApprovalStageCreate(ApprovalStageBase):
    """Schema for creating an approval stage."""

    workspace_id: UUID
    created_by_id: UUID


# =============================================================================
# Approval Request
# =============================================================================


class ApprovalRequestBase(SQLModel):
    """Base fields for approval requests."""

    status: str = Field(default=ApprovalStatus.PENDING.value, index=True)
    submitted_at: datetime = Field(default_factory=datetime.utcnow)
    decided_at: Optional[datetime] = None
    decision_notes: Optional[str] = None


class ApprovalRequest(UUIDModel, ApprovalRequestBase, TimestampMixin, table=True):
    """Individual approval request for a post at a specific stage.

    When a post is submitted for approval:
    1. An ApprovalRequest is created for the first required stage
    2. An approver reviews and approves/rejects
    3. If approved and more stages exist, the next ApprovalRequest is created
    4. If all stages complete, the post status changes to "approved"
    """

    __tablename__ = "approval_requests"

    post_id: UUID = Field(foreign_key="posts.id", index=True)
    workspace_id: UUID = Field(foreign_key="workspaces.id", index=True)
    stage_id: UUID = Field(foreign_key="approval_stages.id", index=True)

    # Who submitted this for approval
    submitted_by_id: UUID = Field(foreign_key="users.id", index=True)

    # Who is responsible for approving (can be null for any approver)
    assigned_approver_id: Optional[UUID] = Field(
        default=None,
        foreign_key="users.id",
        index=True,
    )

    # Who actually made the decision
    decided_by_id: Optional[UUID] = Field(
        default=None,
        foreign_key="users.id",
    )

    # Version of the post content at submission time (for tracking changes)
    content_version: Optional[int] = Field(default=1)


class ApprovalRequestCreate(ApprovalRequestBase):
    """Schema for creating an approval request."""

    post_id: UUID
    workspace_id: UUID
    stage_id: UUID
    submitted_by_id: UUID
    assigned_approver_id: Optional[UUID] = None


# =============================================================================
# Approval Comment
# =============================================================================


class ApprovalCommentBase(SQLModel):
    """Base fields for approval comments."""

    content: str
    is_internal: bool = Field(default=False)  # Internal notes vs visible feedback


class ApprovalComment(UUIDModel, ApprovalCommentBase, TimestampMixin, table=True):
    """Comments and feedback on approval requests.

    Supports both:
    - Visible feedback for the content creator
    - Internal notes between reviewers
    """

    __tablename__ = "approval_comments"

    approval_request_id: UUID = Field(foreign_key="approval_requests.id", index=True)
    workspace_id: UUID = Field(foreign_key="workspaces.id", index=True)

    # Who wrote this comment
    author_id: UUID = Field(foreign_key="users.id", index=True)

    # Optional: reference to a specific line/section (for inline comments)
    line_reference: Optional[str] = None


class ApprovalCommentCreate(ApprovalCommentBase):
    """Schema for creating an approval comment."""

    approval_request_id: UUID
    workspace_id: UUID
    author_id: UUID
    line_reference: Optional[str] = None
