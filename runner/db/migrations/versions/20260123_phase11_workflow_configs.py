"""Phase 11: Workflow configurations table.

Revision ID: 20260123_workflow_configs
Revises: 20260118_password_reset
Create Date: 2026-01-23

Creates:
- workflow_configs: dynamic workflow configuration metadata
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "20260123_workflow_configs"
down_revision: Union[str, None] = "20260118_password_reset"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create workflow_configs table."""
    op.create_table(
        "workflow_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("config_file", sa.String(255), nullable=False),
        sa.Column(
            "environment", sa.String(20), nullable=False, server_default="production"
        ),
        sa.Column("features", postgresql.JSON(), nullable=True),
        sa.Column("tier_required", sa.String(50), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Unique constraint on slug
    op.create_index(
        "ix_workflow_configs_slug", "workflow_configs", ["slug"], unique=True
    )

    # Index for name lookups
    op.create_index("ix_workflow_configs_name", "workflow_configs", ["name"])

    # Index for environment filtering
    op.create_index(
        "ix_workflow_configs_environment", "workflow_configs", ["environment"]
    )

    # Index for enabled configs
    op.create_index("ix_workflow_configs_enabled", "workflow_configs", ["enabled"])

    # Index for tier filtering
    op.create_index(
        "ix_workflow_configs_tier_required", "workflow_configs", ["tier_required"]
    )

    # Composite index for the common query: enabled configs for an environment
    op.create_index(
        "ix_workflow_configs_enabled_env",
        "workflow_configs",
        ["enabled", "environment"],
    )


def downgrade() -> None:
    """Drop workflow_configs table."""
    op.drop_index("ix_workflow_configs_enabled_env", table_name="workflow_configs")
    op.drop_index("ix_workflow_configs_tier_required", table_name="workflow_configs")
    op.drop_index("ix_workflow_configs_enabled", table_name="workflow_configs")
    op.drop_index("ix_workflow_configs_environment", table_name="workflow_configs")
    op.drop_index("ix_workflow_configs_name", table_name="workflow_configs")
    op.drop_index("ix_workflow_configs_slug", table_name="workflow_configs")
    op.drop_table("workflow_configs")
