"""Add view_as_tier_id to users.

Revision ID: add_user_ip_view_tier
Revises: fix_workflow_runs
Create Date: 2026-01-29

Adds:
- view_as_tier_id: Allow owner to simulate other tiers for testing
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "add_user_ip_view_tier"
down_revision = "fix_workflow_runs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add view_as_tier_id for owner tier simulation
    op.add_column(
        "users",
        sa.Column(
            "view_as_tier_id",
            sa.UUID(),
            sa.ForeignKey("subscription_tiers.id"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "view_as_tier_id")
