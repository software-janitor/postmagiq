"""Add external auth provider fields to users table.

Revision ID: add_external_auth_fields
Revises: fix_writing_samples_schema
Create Date: 2026-01-30

Adds:
- external_id: External provider's user ID (e.g., Clerk user_xxx)
- external_provider: Provider name (e.g., "clerk", "auth0")

These fields enable pluggable authentication providers while keeping
authorization (roles, scopes, workspaces) in the local database.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "add_external_auth_fields"
down_revision = "fix_writing_samples_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add external_id column with index for lookups
    op.add_column(
        "users",
        sa.Column("external_id", sa.String(), nullable=True),
    )
    op.create_index(
        "ix_users_external_id",
        "users",
        ["external_id"],
    )

    # Add external_provider column
    op.add_column(
        "users",
        sa.Column("external_provider", sa.String(), nullable=True),
    )

    # Add composite unique constraint for external auth lookups
    # (external_id, external_provider) must be unique when both are set
    op.create_index(
        "ix_users_external_provider_id",
        "users",
        ["external_provider", "external_id"],
        unique=True,
        postgresql_where=sa.text("external_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_users_external_provider_id", table_name="users")
    op.drop_index("ix_users_external_id", table_name="users")
    op.drop_column("users", "external_provider")
    op.drop_column("users", "external_id")
