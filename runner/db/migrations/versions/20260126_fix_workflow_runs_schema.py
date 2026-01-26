"""Fix workflow_runs schema to match model.

Revision ID: fix_workflow_runs
Revises: fix_workflow_outputs
Create Date: 2026-01-26
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "fix_workflow_runs"
down_revision = "fix_workflow_outputs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Rename columns to match model
    op.alter_column("workflow_runs", "story_name", new_column_name="story")
    op.alter_column("workflow_runs", "error_message", new_column_name="error")
    op.alter_column("workflow_runs", "total_cost", new_column_name="total_cost_usd")

    # Add missing column
    op.add_column("workflow_runs", sa.Column("final_state", sa.String(), nullable=True))

    # Drop columns that don't exist in model
    op.drop_column("workflow_runs", "total_transitions")
    op.drop_column("workflow_runs", "post_id")
    op.drop_column("workflow_runs", "created_at")
    op.drop_column("workflow_runs", "updated_at")


def downgrade() -> None:
    # Re-add dropped columns
    op.add_column("workflow_runs", sa.Column("updated_at", sa.DateTime(), nullable=True))
    op.add_column("workflow_runs", sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")))
    op.add_column("workflow_runs", sa.Column("post_id", sa.UUID(), nullable=True))
    op.add_column("workflow_runs", sa.Column("total_transitions", sa.Integer(), nullable=True))

    # Drop added column
    op.drop_column("workflow_runs", "final_state")

    # Rename columns back
    op.alter_column("workflow_runs", "total_cost_usd", new_column_name="total_cost")
    op.alter_column("workflow_runs", "error", new_column_name="error_message")
    op.alter_column("workflow_runs", "story", new_column_name="story_name")
