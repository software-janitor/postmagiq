"""Add social connections and scheduled posts tables.

Revision ID: social_publishing
Revises: simplify_tiers
Create Date: 2026-01-29

Adds tables for:
- social_connections: OAuth tokens for LinkedIn, X, Threads
- scheduled_posts: Posts scheduled for future publishing
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "social_publishing"
down_revision = "simplify_tiers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create social_connections table
    op.create_table(
        "social_connections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("platform", sa.String(50), nullable=False),
        sa.Column("access_token", sa.Text, nullable=False),
        sa.Column("refresh_token", sa.Text),
        sa.Column("token_secret", sa.Text),  # For OAuth 1.0a (X)
        sa.Column("expires_at", sa.DateTime),
        sa.Column("platform_user_id", sa.String(255), nullable=False),
        sa.Column("platform_username", sa.String(255), nullable=False),
        sa.Column("platform_name", sa.String(255)),
        sa.Column("scopes", sa.Text),
        sa.Column(
            "created_at", sa.DateTime, nullable=False, server_default=sa.func.now()
        ),
        sa.Column("updated_at", sa.DateTime),
    )

    # Indexes for social_connections
    op.create_index("ix_social_connections_user_id", "social_connections", ["user_id"])
    op.create_index(
        "ix_social_connections_workspace_id", "social_connections", ["workspace_id"]
    )

    # Unique constraint: one connection per user per platform per workspace
    op.create_unique_constraint(
        "uq_social_connections_user_platform_workspace",
        "social_connections",
        ["user_id", "platform", "workspace_id"],
    )

    # Create scheduled_posts table
    op.create_table(
        "scheduled_posts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "post_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("posts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "connection_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("social_connections.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("scheduled_for", sa.DateTime, nullable=False),
        sa.Column("timezone", sa.String(50), nullable=False, server_default="UTC"),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("published_at", sa.DateTime),
        sa.Column("platform_post_id", sa.String(255)),
        sa.Column("platform_post_url", sa.Text),
        sa.Column("error_message", sa.Text),
        sa.Column("retry_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "created_at", sa.DateTime, nullable=False, server_default=sa.func.now()
        ),
        sa.Column("updated_at", sa.DateTime),
    )

    # Indexes for scheduled_posts
    op.create_index(
        "ix_scheduled_posts_workspace_id", "scheduled_posts", ["workspace_id"]
    )
    op.create_index("ix_scheduled_posts_post_id", "scheduled_posts", ["post_id"])
    op.create_index(
        "ix_scheduled_posts_connection_id", "scheduled_posts", ["connection_id"]
    )
    op.create_index(
        "ix_scheduled_posts_scheduled_for", "scheduled_posts", ["scheduled_for"]
    )
    # Index for finding pending posts to publish
    op.create_index(
        "ix_scheduled_posts_status_scheduled",
        "scheduled_posts",
        ["status", "scheduled_for"],
    )


def downgrade() -> None:
    op.drop_table("scheduled_posts")
    op.drop_table("social_connections")
