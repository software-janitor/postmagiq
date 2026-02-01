"""Add workspace_daily_costs table for admin analytics.

Revision ID: admin_analytics
Revises: fix_writing_samples_schema
Create Date: 2026-01-31

Enables fast historical queries for SaaS owner analytics without
scanning workflow_runs every time. Aggregates daily costs per workspace.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "admin_analytics"
down_revision = "add_external_auth_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workspace_daily_costs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cost_date", sa.Date(), nullable=False),
        sa.Column("total_cost_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("run_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("successful_runs", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_runs", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "cost_date", name="uq_workspace_daily_costs_workspace_date"),
    )
    op.create_index(
        "ix_workspace_daily_costs_cost_date",
        "workspace_daily_costs",
        ["cost_date"],
    )
    op.create_index(
        "ix_workspace_daily_costs_workspace_id",
        "workspace_daily_costs",
        ["workspace_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_workspace_daily_costs_workspace_id", table_name="workspace_daily_costs")
    op.drop_index("ix_workspace_daily_costs_cost_date", table_name="workspace_daily_costs")
    op.drop_table("workspace_daily_costs")
