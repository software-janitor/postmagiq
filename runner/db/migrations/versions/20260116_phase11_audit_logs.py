"""Phase 11: Audit logs table.

Revision ID: 007_audit_logs
Revises: 006_api_keys_webhooks
Create Date: 2026-01-16

Creates:
- audit_logs: comprehensive audit trail for all significant actions
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "008_audit_logs"
down_revision = "007_whitelabel"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ==========================================================================
    # Audit Logs
    # ==========================================================================

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("resource_type", sa.String(100), nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("old_value", postgresql.JSON(), nullable=True),
        sa.Column("new_value", postgresql.JSON(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )

    # Index for workspace queries (most common filter)
    op.create_index("ix_audit_logs_workspace_id", "audit_logs", ["workspace_id"])

    # Index for user queries
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])

    # Index for action type queries
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])

    # Index for resource lookups
    op.create_index(
        "ix_audit_logs_resource",
        "audit_logs",
        ["resource_type", "resource_id"],
    )

    # Index for time-based queries (most recent first)
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])

    # Composite index for the most common query pattern:
    # workspace + time-based ordering
    op.create_index(
        "ix_audit_logs_workspace_created",
        "audit_logs",
        ["workspace_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
