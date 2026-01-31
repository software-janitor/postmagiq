"""Phase 6: Assignment and approval tables.

Revision ID: 004_approval
Revises: 003_billing
Create Date: 2026-01-16

Adds assignment fields to posts table and creates:
- post_assignment_history: tracks assignment changes over time
- approval_stages: defines approval workflow stages per workspace
- approval_requests: individual approval requests for posts
- approval_comments: feedback and comments on approvals
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "004_approval"
down_revision = "003_billing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ==========================================================================
    # Add assignment fields to posts table
    # ==========================================================================

    op.add_column(
        "posts",
        sa.Column("assignee_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "posts",
        sa.Column("due_date", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "posts",
        sa.Column("priority", sa.String(20), nullable=True),
    )
    op.add_column(
        "posts",
        sa.Column("estimated_hours", sa.Float(), nullable=True),
    )

    # Foreign key for assignee_id
    op.create_foreign_key(
        "fk_posts_assignee_id",
        "posts",
        "users",
        ["assignee_id"],
        ["id"],
    )

    # Index for assignee lookups
    op.create_index("ix_posts_assignee_id", "posts", ["assignee_id"])
    op.create_index("ix_posts_due_date", "posts", ["due_date"])
    op.create_index("ix_posts_priority", "posts", ["priority"])

    # ==========================================================================
    # Post Assignment History
    # ==========================================================================

    op.create_table(
        "post_assignment_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("post_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assigned_by_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("previous_assignee_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("new_assignee_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["assigned_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["previous_assignee_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["new_assignee_id"], ["users.id"]),
    )

    op.create_index(
        "ix_post_assignment_history_post_id", "post_assignment_history", ["post_id"]
    )
    op.create_index(
        "ix_post_assignment_history_workspace_id",
        "post_assignment_history",
        ["workspace_id"],
    )
    op.create_index(
        "ix_post_assignment_history_assigned_by_id",
        "post_assignment_history",
        ["assigned_by_id"],
    )

    # ==========================================================================
    # Approval Stages
    # ==========================================================================

    op.create_table(
        "approval_stages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("auto_approve_role", sa.String(50), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
    )

    op.create_index(
        "ix_approval_stages_workspace_id", "approval_stages", ["workspace_id"]
    )
    op.create_index("ix_approval_stages_name", "approval_stages", ["name"])
    op.create_index(
        "ix_approval_stages_order", "approval_stages", ["workspace_id", "order"]
    )

    # ==========================================================================
    # Approval Requests
    # ==========================================================================

    op.create_table(
        "approval_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("post_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("stage_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("submitted_by_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assigned_approver_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("decided_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column(
            "submitted_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("decided_at", sa.DateTime(), nullable=True),
        sa.Column("decision_notes", sa.Text(), nullable=True),
        sa.Column("content_version", sa.Integer(), nullable=True, server_default="1"),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["stage_id"], ["approval_stages.id"]),
        sa.ForeignKeyConstraint(["submitted_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["assigned_approver_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["decided_by_id"], ["users.id"]),
    )

    op.create_index("ix_approval_requests_post_id", "approval_requests", ["post_id"])
    op.create_index(
        "ix_approval_requests_workspace_id", "approval_requests", ["workspace_id"]
    )
    op.create_index("ix_approval_requests_stage_id", "approval_requests", ["stage_id"])
    op.create_index("ix_approval_requests_status", "approval_requests", ["status"])
    op.create_index(
        "ix_approval_requests_submitted_by_id", "approval_requests", ["submitted_by_id"]
    )
    op.create_index(
        "ix_approval_requests_assigned_approver_id",
        "approval_requests",
        ["assigned_approver_id"],
    )

    # ==========================================================================
    # Approval Comments
    # ==========================================================================

    op.create_table(
        "approval_comments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("approval_request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("is_internal", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("line_reference", sa.String(100), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["approval_request_id"], ["approval_requests.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"]),
    )

    op.create_index(
        "ix_approval_comments_approval_request_id",
        "approval_comments",
        ["approval_request_id"],
    )
    op.create_index(
        "ix_approval_comments_workspace_id", "approval_comments", ["workspace_id"]
    )
    op.create_index(
        "ix_approval_comments_author_id", "approval_comments", ["author_id"]
    )


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table("approval_comments")
    op.drop_table("approval_requests")
    op.drop_table("approval_stages")
    op.drop_table("post_assignment_history")

    # Drop indexes from posts
    op.drop_index("ix_posts_priority", table_name="posts")
    op.drop_index("ix_posts_due_date", table_name="posts")
    op.drop_index("ix_posts_assignee_id", table_name="posts")

    # Drop foreign key and columns from posts
    op.drop_constraint("fk_posts_assignee_id", "posts", type_="foreignkey")
    op.drop_column("posts", "estimated_hours")
    op.drop_column("posts", "priority")
    op.drop_column("posts", "due_date")
    op.drop_column("posts", "assignee_id")
