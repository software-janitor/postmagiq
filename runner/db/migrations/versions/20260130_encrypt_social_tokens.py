"""Encrypt social connection tokens with pgcrypto.

Revision ID: encrypt_social_tokens
Revises: social_publishing
Create Date: 2026-01-30

Uses PostgreSQL pgcrypto extension for symmetric encryption of OAuth tokens.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "encrypt_social_tokens"
down_revision = "social_publishing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable pgcrypto extension
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    # Change token columns to bytea for encrypted storage
    op.alter_column(
        "social_connections",
        "access_token",
        type_=sa.LargeBinary(),
        postgresql_using="access_token::bytea",
    )
    op.alter_column(
        "social_connections",
        "refresh_token",
        type_=sa.LargeBinary(),
        postgresql_using="refresh_token::bytea",
    )
    op.alter_column(
        "social_connections",
        "token_secret",
        type_=sa.LargeBinary(),
        postgresql_using="token_secret::bytea",
    )


def downgrade() -> None:
    # Revert to text columns (data will be lost if encrypted)
    op.alter_column(
        "social_connections",
        "access_token",
        type_=sa.Text(),
        postgresql_using="access_token::text",
    )
    op.alter_column(
        "social_connections",
        "refresh_token",
        type_=sa.Text(),
        postgresql_using="refresh_token::text",
    )
    op.alter_column(
        "social_connections",
        "token_secret",
        type_=sa.Text(),
        postgresql_using="token_secret::text",
    )
