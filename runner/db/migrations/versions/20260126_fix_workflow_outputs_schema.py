"""Fix workflow_outputs schema to match model.

Revision ID: fix_workflow_outputs
Revises: phase13_embeddings_vector
Create Date: 2026-01-26
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "fix_workflow_outputs"
down_revision = "phase13_embeddings_vector"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop existing foreign key constraint (references id, should reference run_id)
    op.drop_constraint("workflow_outputs_run_id_fkey", "workflow_outputs", type_="foreignkey")

    # Drop index on old run_id column
    op.drop_index("ix_workflow_outputs_run_id", table_name="workflow_outputs")

    # Drop old columns that don't match model
    op.drop_column("workflow_outputs", "file_path")
    op.drop_column("workflow_outputs", "version")
    op.drop_column("workflow_outputs", "run_id")

    # Add new columns to match model
    op.add_column("workflow_outputs", sa.Column("state_name", sa.String(), nullable=False, server_default="unknown"))
    op.add_column("workflow_outputs", sa.Column("agent", sa.String(), nullable=True))
    op.add_column("workflow_outputs", sa.Column("updated_at", sa.DateTime(), nullable=True))
    op.add_column("workflow_outputs", sa.Column("run_id", sa.String(), nullable=False, server_default=""))

    # Remove server defaults after column creation
    op.alter_column("workflow_outputs", "state_name", server_default=None)
    op.alter_column("workflow_outputs", "run_id", server_default=None)

    # Create indexes
    op.create_index("ix_workflow_outputs_state_name", "workflow_outputs", ["state_name"])
    op.create_index("ix_workflow_outputs_run_id", "workflow_outputs", ["run_id"])

    # Add foreign key to workflow_runs.run_id (string column)
    op.create_foreign_key(
        "workflow_outputs_run_id_fkey",
        "workflow_outputs",
        "workflow_runs",
        ["run_id"],
        ["run_id"],
    )


def downgrade() -> None:
    # Drop new foreign key
    op.drop_constraint("workflow_outputs_run_id_fkey", "workflow_outputs", type_="foreignkey")

    # Drop new indexes
    op.drop_index("ix_workflow_outputs_state_name", table_name="workflow_outputs")
    op.drop_index("ix_workflow_outputs_run_id", table_name="workflow_outputs")

    # Drop new columns
    op.drop_column("workflow_outputs", "updated_at")
    op.drop_column("workflow_outputs", "agent")
    op.drop_column("workflow_outputs", "state_name")
    op.drop_column("workflow_outputs", "run_id")

    # Re-add old columns
    op.add_column("workflow_outputs", sa.Column("run_id", sa.UUID(), nullable=False))
    op.add_column("workflow_outputs", sa.Column("file_path", sa.String(), nullable=True))
    op.add_column("workflow_outputs", sa.Column("version", sa.Integer(), nullable=False, server_default="1"))

    # Re-create old index
    op.create_index("ix_workflow_outputs_run_id", "workflow_outputs", ["run_id"])

    # Re-add old foreign key (to id, not run_id)
    op.create_foreign_key(
        "workflow_outputs_run_id_fkey",
        "workflow_outputs",
        "workflow_runs",
        ["run_id"],
        ["id"],
    )
