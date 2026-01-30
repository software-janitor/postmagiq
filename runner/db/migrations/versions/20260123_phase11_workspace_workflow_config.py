"""Phase 11: Add workflow_config_id to workspaces.

Revision ID: 20260123_workspace_workflow
Revises: 20260123_workflow_configs
Create Date: 2026-01-23

Adds workflow_config_id foreign key to workspaces table for
workspace-specific workflow configuration preference.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "20260123_workspace_workflow"
down_revision: Union[str, None] = "20260123_workflow_configs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add workflow_config_id column to workspaces table."""
    # Add the column (nullable, no default)
    op.add_column(
        "workspaces",
        sa.Column("workflow_config_id", postgresql.UUID(as_uuid=True), nullable=True),
    )

    # Add foreign key constraint
    op.create_foreign_key(
        "fk_workspaces_workflow_config_id",
        "workspaces",
        "workflow_configs",
        ["workflow_config_id"],
        ["id"],
        ondelete="SET NULL",  # If config deleted, set to NULL (use default)
    )

    # Add index for efficient lookups
    op.create_index(
        "ix_workspaces_workflow_config_id", "workspaces", ["workflow_config_id"]
    )


def downgrade() -> None:
    """Remove workflow_config_id column from workspaces table."""
    op.drop_index("ix_workspaces_workflow_config_id", table_name="workspaces")
    op.drop_constraint(
        "fk_workspaces_workflow_config_id", "workspaces", type_="foreignkey"
    )
    op.drop_column("workspaces", "workflow_config_id")
