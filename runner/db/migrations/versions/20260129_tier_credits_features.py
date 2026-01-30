"""Tier-based credits and feature flags.

Revision ID: tier_credits_features
Revises: fix_workflow_runs
Create Date: 2026-01-29

Updates subscription tiers to new credit-based pricing and adds
tier_features table for configurable feature flags per tier.

Tier structure:
- Free: 10 credits/month, $0
- Starter: 30 credits/month, $1/month
- Pro: 420 credits/month, $10/month
- Business: 1500 credits/month, $30/month

1 credit = $0.01 of actual API cost (rounded up)
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "tier_credits_features"
down_revision = "fix_workflow_runs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ==========================================================================
    # Create tier_features table
    # ==========================================================================
    op.create_table(
        "tier_features",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tier_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("feature_key", sa.String(50), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, default=False),
        sa.Column("config", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["tier_id"], ["subscription_tiers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tier_id", "feature_key", name="uq_tier_feature"),
    )
    op.create_index("ix_tier_features_tier_id", "tier_features", ["tier_id"])
    op.create_index("ix_tier_features_feature_key", "tier_features", ["feature_key"])

    # ==========================================================================
    # Update subscription_tiers with new tier structure
    # ==========================================================================

    # Update Free tier (was: 5 posts, now: 10 credits)
    op.execute("""
        UPDATE subscription_tiers SET
            name = 'Free',
            slug = 'free',
            description = 'Get started with basic AI workflows',
            price_monthly = 0,
            price_yearly = 0,
            posts_per_month = 10,
            priority_support = false,
            api_access = false,
            display_order = 0,
            updated_at = now()
        WHERE slug = 'free'
    """)

    # Update Individual -> Starter (was: 50 posts @ $29, now: 30 credits @ $1)
    op.execute("""
        UPDATE subscription_tiers SET
            name = 'Starter',
            slug = 'starter',
            description = 'Unlock premium AI models and voice transcription',
            price_monthly = 1,
            price_yearly = 10,
            posts_per_month = 30,
            priority_support = false,
            api_access = false,
            display_order = 1,
            updated_at = now()
        WHERE slug = 'individual'
    """)

    # Update Team -> Pro (was: 200 posts @ $99, now: 420 credits @ $10)
    op.execute("""
        UPDATE subscription_tiers SET
            name = 'Pro',
            slug = 'pro',
            description = 'YouTube transcription and priority support',
            price_monthly = 10,
            price_yearly = 100,
            posts_per_month = 420,
            priority_support = true,
            api_access = false,
            display_order = 2,
            updated_at = now()
        WHERE slug = 'team'
    """)

    # Update Agency -> Business (was: unlimited @ $249, now: 1500 credits @ $30)
    op.execute("""
        UPDATE subscription_tiers SET
            name = 'Business',
            slug = 'business',
            description = 'API access, team workspaces, and white-label',
            price_monthly = 30,
            price_yearly = 300,
            posts_per_month = 1500,
            priority_support = true,
            api_access = true,
            display_order = 3,
            updated_at = now()
        WHERE slug = 'agency'
    """)

    # ==========================================================================
    # Seed tier_features
    # ==========================================================================

    # Get tier IDs for feature seeding
    op.execute("""
        INSERT INTO tier_features (id, tier_id, feature_key, enabled, config, created_at)
        SELECT
            gen_random_uuid(),
            t.id,
            f.feature_key,
            f.enabled,
            f.config::jsonb,
            now()
        FROM subscription_tiers t
        CROSS JOIN (VALUES
            -- Free tier features
            ('free', 'basic_workflow', true, '{"text_limit": 50000}'),
            ('free', 'premium_workflow', false, '{}'),
            ('free', 'voice_transcription', false, '{}'),
            ('free', 'youtube_transcription', false, '{}'),
            ('free', 'priority_support', false, '{}'),
            ('free', 'api_access', false, '{}'),
            ('free', 'team_workspaces', false, '{}'),
            -- Starter tier features
            ('starter', 'basic_workflow', true, '{"text_limit": 50000}'),
            ('starter', 'premium_workflow', true, '{"text_limit": 50000}'),
            ('starter', 'voice_transcription', true, '{}'),
            ('starter', 'youtube_transcription', false, '{}'),
            ('starter', 'priority_support', false, '{}'),
            ('starter', 'api_access', false, '{}'),
            ('starter', 'team_workspaces', false, '{}'),
            -- Pro tier features
            ('pro', 'basic_workflow', true, '{"text_limit": 100000}'),
            ('pro', 'premium_workflow', true, '{"text_limit": 100000}'),
            ('pro', 'voice_transcription', true, '{}'),
            ('pro', 'youtube_transcription', true, '{}'),
            ('pro', 'priority_support', true, '{}'),
            ('pro', 'api_access', false, '{}'),
            ('pro', 'team_workspaces', false, '{}'),
            -- Business tier features
            ('business', 'basic_workflow', true, '{"text_limit": 100000}'),
            ('business', 'premium_workflow', true, '{"text_limit": 100000}'),
            ('business', 'voice_transcription', true, '{}'),
            ('business', 'youtube_transcription', true, '{}'),
            ('business', 'priority_support', true, '{}'),
            ('business', 'api_access', true, '{}'),
            ('business', 'team_workspaces', true, '{}')
        ) AS f(tier_slug, feature_key, enabled, config)
        WHERE t.slug = f.tier_slug
    """)


def downgrade() -> None:
    # Drop tier_features table
    op.drop_table("tier_features")

    # Revert tier changes
    op.execute("""
        UPDATE subscription_tiers SET
            name = 'Free',
            slug = 'free',
            description = 'Get started with basic features',
            price_monthly = 0,
            price_yearly = 0,
            posts_per_month = 5,
            updated_at = now()
        WHERE slug = 'free'
    """)

    op.execute("""
        UPDATE subscription_tiers SET
            name = 'Individual',
            slug = 'individual',
            description = 'Perfect for solo creators',
            price_monthly = 29,
            price_yearly = 290,
            posts_per_month = 50,
            updated_at = now()
        WHERE slug = 'starter'
    """)

    op.execute("""
        UPDATE subscription_tiers SET
            name = 'Team',
            slug = 'team',
            description = 'For small teams and agencies',
            price_monthly = 99,
            price_yearly = 990,
            posts_per_month = 200,
            updated_at = now()
        WHERE slug = 'pro'
    """)

    op.execute("""
        UPDATE subscription_tiers SET
            name = 'Agency',
            slug = 'agency',
            description = 'Unlimited power for large agencies',
            price_monthly = 249,
            price_yearly = 2490,
            posts_per_month = 0,
            updated_at = now()
        WHERE slug = 'business'
    """)
