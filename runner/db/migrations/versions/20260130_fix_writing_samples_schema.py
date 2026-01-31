"""Fix writing_samples table to match SQLModel.

Revision ID: fix_writing_samples_schema
Revises: simplify_tiers
Create Date: 2026-01-30

The writing_samples table had incorrect column names:
- source -> source_type
- sample_type (removed, not in model)
- Add missing: prompt_id, prompt_text, word_count
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "fix_writing_samples_schema"
down_revision = "encrypt_social_tokens"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Rename source to source_type
    op.alter_column(
        "writing_samples",
        "source",
        new_column_name="source_type",
    )

    # Drop sample_type column (not in model)
    op.drop_column("writing_samples", "sample_type")

    # Add missing columns
    op.add_column(
        "writing_samples",
        sa.Column("prompt_id", sa.String(), nullable=True),
    )
    op.add_column(
        "writing_samples",
        sa.Column("prompt_text", sa.String(), nullable=True),
    )
    op.add_column(
        "writing_samples",
        sa.Column("word_count", sa.Integer(), nullable=True),
    )

    # voice_profile_id exists in DB but not in model - keep it for now
    # as it may be used for linking samples to profiles


def downgrade() -> None:
    # Remove added columns
    op.drop_column("writing_samples", "word_count")
    op.drop_column("writing_samples", "prompt_text")
    op.drop_column("writing_samples", "prompt_id")

    # Re-add sample_type
    op.add_column(
        "writing_samples",
        sa.Column("sample_type", sa.String(), nullable=True),
    )

    # Rename source_type back to source
    op.alter_column(
        "writing_samples",
        "source_type",
        new_column_name="source",
    )
