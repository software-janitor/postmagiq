"""Add default_workspace_id to users table.

Revision ID: add_default_workspace_id
Revises: tier_credits_features
Create Date: 2026-01-29

Adds:
- default_workspace_id column to users table
- Foreign key to workspaces.id
- Backfills existing users with their first workspace

This supports the "hide multi-tenancy" feature where individual tier
users don't see workspace concepts - their workspace is inferred from
this default_workspace_id field.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "add_default_workspace_id"
down_revision = "tier_credits_features"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add default_workspace_id column (nullable initially for backfill)
    op.add_column(
        "users",
        sa.Column(
            "default_workspace_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )

    # Add foreign key constraint
    op.create_foreign_key(
        "fk_users_default_workspace",
        "users",
        "workspaces",
        ["default_workspace_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Create index for faster lookups
    op.create_index(
        "ix_users_default_workspace_id",
        "users",
        ["default_workspace_id"],
    )

    # Backfill: Set the first workspace (by created_at) as default for each user
    # This uses the workspace where the user is a member, ordered by membership created_at
    op.execute("""
        UPDATE users u
        SET default_workspace_id = (
            SELECT wm.workspace_id
            FROM workspace_memberships wm
            WHERE wm.user_id = u.id
              AND wm.invite_status = 'accepted'
            ORDER BY wm.created_at ASC
            LIMIT 1
        )
        WHERE u.default_workspace_id IS NULL
    """)


def downgrade() -> None:
    op.drop_index("ix_users_default_workspace_id", table_name="users")
    op.drop_constraint("fk_users_default_workspace", "users", type_="foreignkey")
    op.drop_column("users", "default_workspace_id")
