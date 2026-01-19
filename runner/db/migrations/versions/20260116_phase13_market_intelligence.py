"""Market intelligence tables with pgvector.

Revision ID: phase13_market_intel
Revises: phase12_voice_profiles_modular
Create Date: 2026-01-16

Creates tables for:
- Embeddings (pgvector) for semantic search
- Audience segments for audience intelligence
- Calibrated voices for voice + audience fusion
- Niche vocabulary for domain-specific language
- Research sources for LLM-generated insights
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'phase13_market_intel'
down_revision = '009_voice_profiles_modular'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ==========================================================================
    # Enable pgvector extension
    # ==========================================================================
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # ==========================================================================
    # Embeddings table (pgvector)
    # ==========================================================================
    op.create_table(
        'embeddings',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source_type', sa.String(50), nullable=False),  # voice_sample, content, research, vocabulary
        sa.Column('source_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('embedding', postgresql.ARRAY(sa.Float), nullable=False),  # vector(1536) stored as float array
        sa.Column('chunk_text', sa.Text(), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False, default=0),
        sa.Column('metadata', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_embeddings_workspace_id', 'embeddings', ['workspace_id'])
    op.create_index('ix_embeddings_source', 'embeddings', ['source_type', 'source_id'])

    # ==========================================================================
    # Audience Segments table
    # ==========================================================================
    op.create_table(
        'audience_segments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('profile', postgresql.JSON(), nullable=False),  # demographics, psychographics, language_profile, etc.
        sa.Column('confidence_score', sa.Numeric(3, 2), nullable=True),
        sa.Column('is_primary', sa.Boolean(), nullable=False, default=False),
        sa.Column('is_validated', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_audience_segments_workspace_id', 'audience_segments', ['workspace_id'])

    # ==========================================================================
    # Calibrated Voices table
    # ==========================================================================
    op.create_table(
        'calibrated_voices',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('voice_profile_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('segment_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('platform', sa.String(50), nullable=False),
        sa.Column('voice_spec', postgresql.JSON(), nullable=False),  # preservation, adaptations, synthesis_rules, examples
        sa.Column('usage_count', sa.Integer(), nullable=False, default=0),
        sa.Column('avg_engagement_score', sa.Numeric(5, 2), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['voice_profile_id'], ['voice_profiles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['segment_id'], ['audience_segments.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('workspace_id', 'voice_profile_id', 'segment_id', 'platform', name='uq_calibrated_voice'),
    )
    op.create_index('ix_calibrated_voices_workspace_id', 'calibrated_voices', ['workspace_id'])
    op.create_index('ix_calibrated_voices_lookup', 'calibrated_voices', ['workspace_id', 'segment_id', 'platform'])

    # ==========================================================================
    # Niche Vocabulary table
    # ==========================================================================
    op.create_table(
        'niche_vocabulary',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('term', sa.String(255), nullable=False),
        sa.Column('definition', sa.Text(), nullable=True),
        sa.Column('usage_examples', postgresql.ARRAY(sa.Text), nullable=True),
        sa.Column('sentiment', sa.String(20), nullable=True),  # positive, negative, neutral
        sa.Column('formality_level', sa.Numeric(3, 2), nullable=True),
        sa.Column('segment_ids', postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
        sa.Column('source', sa.String(100), nullable=True),  # llm_generated, user_added
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('workspace_id', 'term', name='uq_vocab_term'),
    )
    op.create_index('ix_niche_vocabulary_workspace_id', 'niche_vocabulary', ['workspace_id'])
    op.create_index('ix_niche_vocabulary_term', 'niche_vocabulary', ['workspace_id', 'term'])

    # ==========================================================================
    # Research Sources table
    # ==========================================================================
    op.create_table(
        'research_sources',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source_type', sa.String(50), nullable=False),  # llm_niche, llm_competitor, user_provided
        sa.Column('source_identifier', sa.String(255), nullable=False),
        sa.Column('raw_data', postgresql.JSON(), nullable=True),
        sa.Column('processed_insights', postgresql.JSON(), nullable=True),  # vocabulary_extracted, pain_points, patterns
        sa.Column('collected_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('workspace_id', 'source_type', 'source_identifier', name='uq_research_source'),
    )
    op.create_index('ix_research_sources_workspace_id', 'research_sources', ['workspace_id'])

    # ==========================================================================
    # Generated Content table (extends existing posts with generation metadata)
    # ==========================================================================
    op.create_table(
        'generated_content',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('post_id', postgresql.UUID(as_uuid=True), nullable=True),  # Link to posts table if published
        sa.Column('content_type', sa.String(50), nullable=False),  # post, image, video_script
        sa.Column('platform', sa.String(50), nullable=False),
        sa.Column('text_content', sa.Text(), nullable=True),
        sa.Column('image_urls', postgresql.ARRAY(sa.Text), nullable=True),
        sa.Column('calibrated_voice_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('segment_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('generation_prompts', postgresql.JSON(), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, default='draft'),  # draft, approved, posted, archived
        sa.Column('engagement_metrics', postgresql.JSON(), nullable=True),
        sa.Column('moderation_result', postgresql.JSON(), nullable=True),  # safety check results
        sa.Column('posted_at', sa.DateTime(), nullable=True),
        sa.Column('post_url', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['post_id'], ['posts.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['calibrated_voice_id'], ['calibrated_voices.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['segment_id'], ['audience_segments.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_generated_content_workspace_id', 'generated_content', ['workspace_id'])
    op.create_index('ix_generated_content_status', 'generated_content', ['workspace_id', 'status'])

    # ==========================================================================
    # Content Moderation Results table
    # ==========================================================================
    op.create_table(
        'content_moderation',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('content_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('content_type', sa.String(50), nullable=False),  # generated_content, post
        sa.Column('moderation_type', sa.String(50), nullable=False),  # policy, factuality, plagiarism, brand_safety
        sa.Column('status', sa.String(20), nullable=False),  # passed, flagged, blocked
        sa.Column('confidence', sa.Numeric(3, 2), nullable=True),
        sa.Column('flags', postgresql.ARRAY(sa.String), nullable=True),  # specific issues found
        sa.Column('details', postgresql.JSON(), nullable=True),
        sa.Column('reviewed_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_content_moderation_workspace_id', 'content_moderation', ['workspace_id'])
    op.create_index('ix_content_moderation_content', 'content_moderation', ['content_id', 'content_type'])
    op.create_index('ix_content_moderation_status', 'content_moderation', ['workspace_id', 'status'])


def downgrade() -> None:
    op.drop_table('content_moderation')
    op.drop_table('generated_content')
    op.drop_table('research_sources')
    op.drop_table('niche_vocabulary')
    op.drop_table('calibrated_voices')
    op.drop_table('audience_segments')
    op.drop_table('embeddings')
    op.execute("DROP EXTENSION IF EXISTS vector")
