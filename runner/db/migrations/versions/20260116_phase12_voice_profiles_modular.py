"""Phase 12: Modular voice profiles.

Revision ID: 008_voice_profiles_modular
Revises: 007_audit_logs
Create Date: 2026-01-16

Modifies:
- voice_profiles: Add new columns for modular voice system
  - slug (unique identifier)
  - tone_description (how the voice sounds)
  - word_choices (preferred word choices)
  - example_excerpts (writing samples)
  - is_preset (boolean for system presets)
  Note: avoid_patterns and signature_phrases already exist in initial migration

- workflow_personas: Add voice profile reference and new columns
  - voice_profile_id (FK to voice_profiles.id)
  - slug (unique identifier)
  - content (persona prompt content)
  - is_system (boolean for system personas)
  - model_tier (optional model tier preference)
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "009_voice_profiles_modular"
down_revision = "008_audit_logs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ==========================================================================
    # voice_profiles: Add new modular voice columns
    # ==========================================================================

    # Add slug column (unique identifier for the voice profile)
    op.add_column(
        "voice_profiles",
        sa.Column("slug", sa.String(), nullable=True),
    )
    op.create_index("ix_voice_profiles_slug", "voice_profiles", ["slug"])

    # Add tone_description (more descriptive than the existing 'tone' column)
    op.add_column(
        "voice_profiles",
        sa.Column("tone_description", sa.Text(), nullable=True),
    )

    # Add word_choices (preferred word choices)
    op.add_column(
        "voice_profiles",
        sa.Column("word_choices", sa.Text(), nullable=True),
    )

    # Add example_excerpts (writing samples)
    op.add_column(
        "voice_profiles",
        sa.Column("example_excerpts", sa.Text(), nullable=True),
    )

    # Add is_preset (boolean for system presets)
    op.add_column(
        "voice_profiles",
        sa.Column("is_preset", sa.Boolean(), nullable=False, server_default="false"),
    )

    # ==========================================================================
    # workflow_personas: Add voice profile reference and new columns
    # ==========================================================================

    # Add slug column (unique identifier for the persona)
    op.add_column(
        "workflow_personas",
        sa.Column("slug", sa.String(), nullable=True),
    )
    op.create_index("ix_workflow_personas_slug", "workflow_personas", ["slug"])

    # Add content column (persona prompt content)
    op.add_column(
        "workflow_personas",
        sa.Column("content", sa.Text(), nullable=True),
    )

    # Add is_system column (boolean for system personas)
    op.add_column(
        "workflow_personas",
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default="false"),
    )

    # Add model_tier column (optional model tier preference)
    op.add_column(
        "workflow_personas",
        sa.Column("model_tier", sa.String(), nullable=True),
    )

    # Add voice_profile_id FK column
    op.add_column(
        "workflow_personas",
        sa.Column("voice_profile_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_workflow_personas_voice_profile_id",
        "workflow_personas",
        "voice_profiles",
        ["voice_profile_id"],
        ["id"],
    )
    op.create_index(
        "ix_workflow_personas_voice_profile_id",
        "workflow_personas",
        ["voice_profile_id"],
    )

    # ==========================================================================
    # Seed system personas
    # ==========================================================================

    # Ensure system user exists
    op.execute("""
        INSERT INTO users (id, email, full_name, is_active, is_superuser, created_at)
        VALUES (gen_random_uuid(), 'system@local', 'System', true, false, now())
        ON CONFLICT (email) DO NOTHING;
    """)

    # Seed system personas (description goes into content column)
    op.execute("""
        INSERT INTO workflow_personas (
            id, name, slug, content, is_active, is_system, model_tier,
            user_id, workspace_id, created_at
        )
        SELECT
            gen_random_uuid(),
            v.name,
            v.slug,
            v.description,
            true,
            true,
            v.model_tier,
            u.id,
            NULL,
            now()
        FROM (VALUES
            ('Writer', 'writer', 'Drafting agent that writes LinkedIn posts from source material', 'writer'),
            ('Auditor', 'auditor', 'Quality gate agent that audits drafts against voice guidelines', 'auditor'),
            ('Synthesizer', 'synthesizer', 'Synthesis agent that combines multiple drafts into a final post', 'writer'),
            ('Story Processor', 'story-processor', 'Extracts post elements from raw story material', 'writer'),
            ('Story Reviewer', 'story-reviewer', 'Reviews processed stories for completeness and quality', 'auditor'),
            ('Input Validator', 'input-validator', 'Validates input material has sufficient content', 'auditor'),
            ('AI Detector', 'ai-detector', 'Checks drafts for AI-sounding patterns', 'auditor')
        ) AS v(name, slug, description, model_tier)
        CROSS JOIN users u
        WHERE u.email = 'system@local'
        ON CONFLICT DO NOTHING;
    """)


def downgrade() -> None:
    # ==========================================================================
    # workflow_personas: Remove voice profile reference and new columns
    # ==========================================================================
    op.drop_index(
        "ix_workflow_personas_voice_profile_id", table_name="workflow_personas"
    )
    op.drop_constraint(
        "fk_workflow_personas_voice_profile_id", "workflow_personas", type_="foreignkey"
    )
    op.drop_column("workflow_personas", "voice_profile_id")
    op.drop_column("workflow_personas", "model_tier")
    op.drop_column("workflow_personas", "is_system")
    op.drop_column("workflow_personas", "content")
    op.drop_index("ix_workflow_personas_slug", table_name="workflow_personas")
    op.drop_column("workflow_personas", "slug")

    # ==========================================================================
    # voice_profiles: Remove modular voice columns
    # ==========================================================================
    op.drop_column("voice_profiles", "is_preset")
    op.drop_column("voice_profiles", "example_excerpts")
    op.drop_column("voice_profiles", "word_choices")
    op.drop_column("voice_profiles", "tone_description")
    op.drop_index("ix_voice_profiles_slug", table_name="voice_profiles")
    op.drop_column("voice_profiles", "slug")
