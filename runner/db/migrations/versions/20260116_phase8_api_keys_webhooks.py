"""Phase 8: API Keys and Webhooks tables.

Revision ID: 006_api_keys
Revises: 005_notification
Create Date: 2026-01-16

Creates:
- api_keys: API keys for programmatic access
- webhooks: webhook endpoint registrations
- webhook_deliveries: delivery attempt records
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "006_api_keys"
down_revision = "005_notification"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ==========================================================================
    # API Keys
    # ==========================================================================

    op.create_table(
        "api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("key_hash", sa.String(64), nullable=False),
        sa.Column("key_prefix", sa.String(8), nullable=False),
        sa.Column("scopes", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "rate_limit_per_minute", sa.Integer(), nullable=False, server_default="60"
        ),
        sa.Column(
            "rate_limit_per_day", sa.Integer(), nullable=False, server_default="10000"
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.Column("total_requests", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("revoked_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["revoked_by_id"], ["users.id"]),
    )

    op.create_index("ix_api_keys_workspace_id", "api_keys", ["workspace_id"])
    op.create_index("ix_api_keys_key_hash", "api_keys", ["key_hash"])
    op.create_index("ix_api_keys_status", "api_keys", ["status"])
    op.create_index("ix_api_keys_name", "api_keys", ["name"])
    op.create_index("ix_api_keys_created_by_id", "api_keys", ["created_by_id"])

    # ==========================================================================
    # Webhooks
    # ==========================================================================

    op.create_table(
        "webhooks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("events", sa.Text(), nullable=False, server_default=""),
        sa.Column("secret_hash", sa.String(64), nullable=False),
        sa.Column("secret_prefix", sa.String(8), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("max_retries", sa.Integer(), nullable=False, server_default="3"),
        sa.Column(
            "retry_delay_seconds", sa.Integer(), nullable=False, server_default="60"
        ),
        sa.Column("headers", sa.Text(), nullable=True),
        sa.Column("total_deliveries", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "successful_deliveries", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "failed_deliveries", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("last_delivery_at", sa.DateTime(), nullable=True),
        sa.Column("last_success_at", sa.DateTime(), nullable=True),
        sa.Column("last_failure_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
    )

    op.create_index("ix_webhooks_workspace_id", "webhooks", ["workspace_id"])
    op.create_index("ix_webhooks_status", "webhooks", ["status"])
    op.create_index("ix_webhooks_name", "webhooks", ["name"])
    op.create_index("ix_webhooks_created_by_id", "webhooks", ["created_by_id"])

    # ==========================================================================
    # Webhook Deliveries
    # ==========================================================================

    op.create_table(
        "webhook_deliveries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("webhook_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("event_id", sa.String(64), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("response_status_code", sa.Integer(), nullable=True),
        sa.Column("response_body", sa.Text(), nullable=True),
        sa.Column("response_headers", sa.Text(), nullable=True),
        sa.Column("delivered_at", sa.DateTime(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("attempt_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("next_retry_at", sa.DateTime(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("resource_type", sa.String(50), nullable=True),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["webhook_id"], ["webhooks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"], ondelete="CASCADE"
        ),
    )

    op.create_index(
        "ix_webhook_deliveries_webhook_id", "webhook_deliveries", ["webhook_id"]
    )
    op.create_index(
        "ix_webhook_deliveries_workspace_id", "webhook_deliveries", ["workspace_id"]
    )
    op.create_index(
        "ix_webhook_deliveries_event_type", "webhook_deliveries", ["event_type"]
    )
    op.create_index(
        "ix_webhook_deliveries_event_id", "webhook_deliveries", ["event_id"]
    )
    op.create_index("ix_webhook_deliveries_status", "webhook_deliveries", ["status"])
    op.create_index(
        "ix_webhook_deliveries_next_retry", "webhook_deliveries", ["next_retry_at"]
    )


def downgrade() -> None:
    op.drop_table("webhook_deliveries")
    op.drop_table("webhooks")
    op.drop_table("api_keys")
