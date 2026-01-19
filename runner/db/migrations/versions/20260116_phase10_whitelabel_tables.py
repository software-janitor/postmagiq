"""Phase 10: White-label tables.

Revision ID: 007_whitelabel
Revises: 006_api_keys
Create Date: 2026-01-16

Creates:
- whitelabel_configs: workspace branding, custom domain, email settings
- whitelabel_assets: uploaded assets (logo, favicon, banner)
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '007_whitelabel'
down_revision = '006_api_keys'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ==========================================================================
    # WhitelabelConfig
    # ==========================================================================

    op.create_table(
        'whitelabel_configs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False),

        # Custom domain settings
        sa.Column('custom_domain', sa.String(255), nullable=True),
        sa.Column('domain_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('domain_verification_token', sa.String(255), nullable=True),
        sa.Column('domain_verification_status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('domain_verified_at', sa.DateTime(), nullable=True),

        # Branding
        sa.Column('company_name', sa.String(255), nullable=True),
        sa.Column('logo_url', sa.Text(), nullable=True),
        sa.Column('logo_dark_url', sa.Text(), nullable=True),
        sa.Column('favicon_url', sa.Text(), nullable=True),
        sa.Column('primary_color', sa.String(20), nullable=True),
        sa.Column('secondary_color', sa.String(20), nullable=True),
        sa.Column('accent_color', sa.String(20), nullable=True),

        # Portal settings
        sa.Column('portal_welcome_text', sa.Text(), nullable=True),
        sa.Column('portal_footer_text', sa.Text(), nullable=True),
        sa.Column('support_email', sa.String(255), nullable=True),

        # Email settings
        sa.Column('email_domain', sa.String(255), nullable=True),
        sa.Column('email_from_name', sa.String(255), nullable=True),
        sa.Column('email_reply_to', sa.String(255), nullable=True),
        sa.Column('email_domain_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('dkim_selector', sa.String(50), nullable=True),
        sa.Column('dkim_public_key', sa.Text(), nullable=True),
        sa.Column('dkim_private_key_ref', sa.String(255), nullable=True),

        # Status
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),

        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=True),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
    )

    op.create_index('ix_whitelabel_configs_workspace_id', 'whitelabel_configs', ['workspace_id'], unique=True)
    op.create_index('ix_whitelabel_configs_custom_domain', 'whitelabel_configs', ['custom_domain'])
    op.create_index(
        'ix_whitelabel_configs_active_verified_domain',
        'whitelabel_configs',
        ['is_active', 'domain_verified', 'custom_domain'],
    )

    # ==========================================================================
    # WhitelabelAsset
    # ==========================================================================

    op.create_table(
        'whitelabel_assets',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('asset_type', sa.String(30), nullable=False),
        sa.Column('file_path', sa.Text(), nullable=False),
        sa.Column('uploaded_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
    )

    op.create_index('ix_whitelabel_assets_workspace_id', 'whitelabel_assets', ['workspace_id'])
    op.create_index('ix_whitelabel_assets_asset_type', 'whitelabel_assets', ['asset_type'])
    op.create_index(
        'ix_whitelabel_assets_workspace_type',
        'whitelabel_assets',
        ['workspace_id', 'asset_type'],
    )


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('whitelabel_assets')
    op.drop_table('whitelabel_configs')
