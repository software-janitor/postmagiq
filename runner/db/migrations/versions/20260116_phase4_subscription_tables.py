"""Phase 4: Subscription and usage tracking tables.

Revision ID: 002_subscription
Revises: 001_initial
Create Date: 2026-01-16

Creates subscription tiers, account subscriptions, usage tracking,
and credit reservation tables for the multi-tenancy billing system.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002_subscription'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ==========================================================================
    # Subscription Tiers
    # ==========================================================================

    op.create_table(
        'subscription_tiers',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('slug', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        # Pricing
        sa.Column('price_monthly', sa.Numeric(precision=10, scale=2), nullable=False, default=0),
        sa.Column('price_yearly', sa.Numeric(precision=10, scale=2), nullable=False, default=0),
        # Limits
        sa.Column('posts_per_month', sa.Integer(), nullable=False, default=0),
        sa.Column('workspaces_limit', sa.Integer(), nullable=False, default=1),
        sa.Column('members_per_workspace', sa.Integer(), nullable=False, default=1),
        sa.Column('storage_gb', sa.Integer(), nullable=False, default=1),
        # Features
        sa.Column('overage_enabled', sa.Boolean(), nullable=False, default=False),
        sa.Column('overage_rate', sa.Numeric(precision=10, scale=2), nullable=False, default=0),
        sa.Column('priority_support', sa.Boolean(), nullable=False, default=False),
        sa.Column('api_access', sa.Boolean(), nullable=False, default=False),
        sa.Column('white_label', sa.Boolean(), nullable=False, default=False),
        # Display
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('display_order', sa.Integer(), nullable=False, default=0),
        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_subscription_tiers_name', 'subscription_tiers', ['name'])
    op.create_index('ix_subscription_tiers_slug', 'subscription_tiers', ['slug'], unique=True)

    # ==========================================================================
    # Account Subscriptions
    # ==========================================================================

    op.create_table(
        'account_subscriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tier_id', postgresql.UUID(as_uuid=True), nullable=False),
        # Status
        sa.Column('status', sa.String(), nullable=False, default='active'),
        sa.Column('billing_period', sa.String(), nullable=False, default='monthly'),
        # Billing dates
        sa.Column('current_period_start', sa.DateTime(), nullable=False),
        sa.Column('current_period_end', sa.DateTime(), nullable=False),
        sa.Column('canceled_at', sa.DateTime(), nullable=True),
        sa.Column('cancel_at_period_end', sa.Boolean(), nullable=False, default=False),
        # Stripe integration
        sa.Column('stripe_subscription_id', sa.String(), nullable=True),
        sa.Column('stripe_customer_id', sa.String(), nullable=True),
        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id']),
        sa.ForeignKeyConstraint(['tier_id'], ['subscription_tiers.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_account_subscriptions_workspace_id', 'account_subscriptions', ['workspace_id'], unique=True)
    op.create_index('ix_account_subscriptions_tier_id', 'account_subscriptions', ['tier_id'])
    op.create_index('ix_account_subscriptions_stripe_subscription_id', 'account_subscriptions', ['stripe_subscription_id'])
    op.create_index('ix_account_subscriptions_stripe_customer_id', 'account_subscriptions', ['stripe_customer_id'])

    # ==========================================================================
    # Usage Tracking
    # ==========================================================================

    op.create_table(
        'usage_tracking',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False),
        # Period
        sa.Column('period_start', sa.DateTime(), nullable=False),
        sa.Column('period_end', sa.DateTime(), nullable=False),
        # Usage counts
        sa.Column('posts_created', sa.Integer(), nullable=False, default=0),
        sa.Column('posts_limit', sa.Integer(), nullable=False, default=0),
        sa.Column('overage_posts', sa.Integer(), nullable=False, default=0),
        # Storage
        sa.Column('storage_used_bytes', sa.BigInteger(), nullable=False, default=0),
        sa.Column('storage_limit_bytes', sa.BigInteger(), nullable=False, default=0),
        # API usage
        sa.Column('api_calls', sa.Integer(), nullable=False, default=0),
        sa.Column('api_calls_limit', sa.Integer(), nullable=False, default=0),
        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_usage_tracking_workspace_id', 'usage_tracking', ['workspace_id'])
    op.create_index('ix_usage_tracking_period', 'usage_tracking', ['workspace_id', 'period_start', 'period_end'])

    # ==========================================================================
    # Credit Reservations
    # ==========================================================================

    op.create_table(
        'credit_reservations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('usage_tracking_id', postgresql.UUID(as_uuid=True), nullable=False),
        # Resource info
        sa.Column('resource_type', sa.String(), nullable=False),
        sa.Column('resource_id', sa.String(), nullable=True),
        sa.Column('amount', sa.Integer(), nullable=False, default=1),
        # Status
        sa.Column('status', sa.String(), nullable=False, default='pending'),
        # Idempotency
        sa.Column('idempotency_key', sa.String(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id']),
        sa.ForeignKeyConstraint(['usage_tracking_id'], ['usage_tracking.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_credit_reservations_workspace_id', 'credit_reservations', ['workspace_id'])
    op.create_index('ix_credit_reservations_usage_tracking_id', 'credit_reservations', ['usage_tracking_id'])
    op.create_index('ix_credit_reservations_resource_type', 'credit_reservations', ['resource_type'])
    op.create_index('ix_credit_reservations_idempotency_key', 'credit_reservations', ['idempotency_key'], unique=True)

    # ==========================================================================
    # Seed Default Tiers
    # ==========================================================================

    op.execute("""
        INSERT INTO subscription_tiers (
            id, name, slug, description,
            price_monthly, price_yearly,
            posts_per_month, workspaces_limit, members_per_workspace, storage_gb,
            overage_enabled, overage_rate, priority_support, api_access, white_label,
            is_active, display_order, created_at
        ) VALUES
        (
            gen_random_uuid(), 'Free', 'free', 'Get started with basic features',
            0.00, 0.00,
            5, 1, 1, 1,
            false, 0, false, false, false,
            true, 0, now()
        ),
        (
            gen_random_uuid(), 'Individual', 'individual', 'Perfect for solo creators',
            29.00, 290.00,
            50, 1, 1, 5,
            false, 0, false, false, false,
            true, 1, now()
        ),
        (
            gen_random_uuid(), 'Team', 'team', 'For small teams and agencies',
            99.00, 990.00,
            200, 3, 5, 25,
            true, 1.00, true, true, false,
            true, 2, now()
        ),
        (
            gen_random_uuid(), 'Agency', 'agency', 'Unlimited power for large agencies',
            249.00, 2490.00,
            0, 10, 25, 100,
            true, 0.50, true, true, true,
            true, 3, now()
        );
    """)


def downgrade() -> None:
    op.drop_table('credit_reservations')
    op.drop_table('usage_tracking')
    op.drop_table('account_subscriptions')
    op.drop_table('subscription_tiers')
