"""Simplify tiers for launch: Free Trial, Base, Pro, Max.

Revision ID: simplify_tiers
Revises: add_default_workspace_id
Create Date: 2026-01-29

Simplifies pricing to 4 tiers:
- Free Trial: 10 credits, $0 (then converts to Base)
- Base: 50 credits, $3.50/month
- Pro: 200 credits, $10/month
- Max: 500 credits, $20/month (includes team features)
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "simplify_tiers"
down_revision = "add_default_workspace_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ==========================================================================
    # Update tiers to new simplified structure
    # ==========================================================================

    # Free -> Free Trial (10 credits, $0)
    op.execute("""
        UPDATE subscription_tiers SET
            name = 'Free Trial',
            slug = 'free',
            description = '10 credits to try Postmagiq',
            price_monthly = 0,
            price_yearly = 0,
            posts_per_month = 10,
            priority_support = false,
            api_access = false,
            display_order = 0,
            is_active = true,
            updated_at = now()
        WHERE slug = 'free'
    """)

    # Starter -> Base (50 credits, $3.50/month)
    op.execute("""
        UPDATE subscription_tiers SET
            name = 'Base',
            slug = 'base',
            description = '50 credits per month',
            price_monthly = 3.50,
            price_yearly = 35,
            posts_per_month = 50,
            priority_support = false,
            api_access = false,
            display_order = 1,
            is_active = true,
            updated_at = now()
        WHERE slug = 'starter'
    """)

    # Pro stays Pro (200 credits, $10/month)
    op.execute("""
        UPDATE subscription_tiers SET
            name = 'Pro',
            slug = 'pro',
            description = '200 credits + YouTube transcription',
            price_monthly = 10,
            price_yearly = 100,
            posts_per_month = 200,
            priority_support = true,
            api_access = false,
            display_order = 2,
            is_active = true,
            updated_at = now()
        WHERE slug = 'pro'
    """)

    # Business -> Max (500 credits, $20/month)
    op.execute("""
        UPDATE subscription_tiers SET
            name = 'Max',
            slug = 'max',
            description = '500 credits + team workspaces',
            price_monthly = 20,
            price_yearly = 200,
            posts_per_month = 500,
            priority_support = true,
            api_access = true,
            display_order = 3,
            is_active = true,
            updated_at = now()
        WHERE slug = 'business'
    """)

    # ==========================================================================
    # Reset tier_features with correct feature distribution
    # Free/Base: basic generation + direct publishing
    # Pro: + voice transcription, youtube transcription
    # Max: + team workspaces, API access
    # ==========================================================================

    # Clear existing features
    op.execute("DELETE FROM tier_features")

    # Insert new feature configuration
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
            -- Free tier: basic generation only
            ('free', 'premium_workflow', true, '{"text_limit": 50000}'),
            ('free', 'voice_transcription', false, '{}'),
            ('free', 'youtube_transcription', false, '{}'),
            ('free', 'direct_publishing', true, '{}'),
            ('free', 'priority_support', false, '{}'),
            ('free', 'api_access', false, '{}'),
            ('free', 'team_workspaces', false, '{}'),
            -- Base tier: same as free, just more credits
            ('base', 'premium_workflow', true, '{"text_limit": 50000}'),
            ('base', 'voice_transcription', false, '{}'),
            ('base', 'youtube_transcription', false, '{}'),
            ('base', 'direct_publishing', true, '{}'),
            ('base', 'priority_support', false, '{}'),
            ('base', 'api_access', false, '{}'),
            ('base', 'team_workspaces', false, '{}'),
            -- Pro tier: + voice & youtube transcription
            ('pro', 'premium_workflow', true, '{"text_limit": 100000}'),
            ('pro', 'voice_transcription', true, '{}'),
            ('pro', 'youtube_transcription', true, '{}'),
            ('pro', 'direct_publishing', true, '{}'),
            ('pro', 'priority_support', true, '{}'),
            ('pro', 'api_access', false, '{}'),
            ('pro', 'team_workspaces', false, '{}'),
            -- Max tier: + team workspaces, API access (enterprise)
            ('max', 'premium_workflow', true, '{"text_limit": 100000}'),
            ('max', 'voice_transcription', true, '{}'),
            ('max', 'youtube_transcription', true, '{}'),
            ('max', 'direct_publishing', true, '{}'),
            ('max', 'priority_support', true, '{}'),
            ('max', 'api_access', true, '{}'),
            ('max', 'team_workspaces', true, '{}')
        ) AS f(tier_slug, feature_key, enabled, config)
        WHERE t.slug = f.tier_slug
    """)


def downgrade() -> None:
    # Revert tier changes
    op.execute("""
        UPDATE subscription_tiers SET
            name = 'Free',
            slug = 'free',
            description = 'Get started with basic AI workflows',
            price_monthly = 0,
            price_yearly = 0,
            posts_per_month = 10,
            updated_at = now()
        WHERE slug = 'free'
    """)

    op.execute("""
        UPDATE subscription_tiers SET
            name = 'Starter',
            slug = 'starter',
            description = 'Unlock premium AI models and voice transcription',
            price_monthly = 1,
            price_yearly = 10,
            posts_per_month = 30,
            updated_at = now()
        WHERE slug = 'base'
    """)

    op.execute("""
        UPDATE subscription_tiers SET
            name = 'Pro',
            slug = 'pro',
            description = 'YouTube transcription and priority support',
            price_monthly = 10,
            price_yearly = 100,
            posts_per_month = 420,
            updated_at = now()
        WHERE slug = 'pro'
    """)

    op.execute("""
        UPDATE subscription_tiers SET
            name = 'Business',
            slug = 'business',
            description = 'API access, team workspaces, and white-label',
            price_monthly = 30,
            price_yearly = 300,
            posts_per_month = 1500,
            updated_at = now()
        WHERE slug = 'max'
    """)

    # Remove direct_publishing feature
    op.execute("""
        DELETE FROM tier_features WHERE feature_key = 'direct_publishing'
    """)
