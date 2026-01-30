"""Phase 5: Billing and payment tables.

Revision ID: 003_billing
Revises: 002_subscription
Create Date: 2026-01-16

Creates billing_events, invoices, and payment_methods tables
for Stripe integration.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "003_billing"
down_revision = "002_subscription"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ==========================================================================
    # Billing Events
    # ==========================================================================

    op.create_table(
        "billing_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
        # Event info
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("stripe_event_id", sa.String(), nullable=False),
        sa.Column("payload", sa.Text(), nullable=True),
        # Processing
        sa.Column("processed", sa.Boolean(), nullable=False, default=False),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
        sa.Column("error_message", sa.String(), nullable=True),
        # Timestamps
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_billing_events_event_type", "billing_events", ["event_type"])
    op.create_index(
        "ix_billing_events_stripe_event_id",
        "billing_events",
        ["stripe_event_id"],
        unique=True,
    )
    op.create_index(
        "ix_billing_events_workspace_id", "billing_events", ["workspace_id"]
    )
    op.create_index("ix_billing_events_processed", "billing_events", ["processed"])

    # ==========================================================================
    # Invoices
    # ==========================================================================

    op.create_table(
        "invoices",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("subscription_id", postgresql.UUID(as_uuid=True), nullable=True),
        # Stripe IDs
        sa.Column("stripe_invoice_id", sa.String(), nullable=False),
        sa.Column("stripe_customer_id", sa.String(), nullable=False),
        # Invoice details
        sa.Column("status", sa.String(), nullable=False, default="draft"),
        sa.Column("currency", sa.String(), nullable=False, default="usd"),
        # Amounts (in cents)
        sa.Column("subtotal", sa.Integer(), nullable=False, default=0),
        sa.Column("tax", sa.Integer(), nullable=False, default=0),
        sa.Column("total", sa.Integer(), nullable=False, default=0),
        sa.Column("amount_paid", sa.Integer(), nullable=False, default=0),
        sa.Column("amount_due", sa.Integer(), nullable=False, default=0),
        # Dates
        sa.Column("invoice_date", sa.DateTime(), nullable=False),
        sa.Column("due_date", sa.DateTime(), nullable=True),
        sa.Column("paid_at", sa.DateTime(), nullable=True),
        sa.Column("period_start", sa.DateTime(), nullable=True),
        sa.Column("period_end", sa.DateTime(), nullable=True),
        # URLs
        sa.Column("hosted_invoice_url", sa.String(), nullable=True),
        sa.Column("invoice_pdf", sa.String(), nullable=True),
        sa.Column("description", sa.String(), nullable=True),
        # Timestamps
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.ForeignKeyConstraint(["subscription_id"], ["account_subscriptions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_invoices_stripe_invoice_id", "invoices", ["stripe_invoice_id"], unique=True
    )
    op.create_index(
        "ix_invoices_stripe_customer_id", "invoices", ["stripe_customer_id"]
    )
    op.create_index("ix_invoices_workspace_id", "invoices", ["workspace_id"])
    op.create_index("ix_invoices_subscription_id", "invoices", ["subscription_id"])
    op.create_index("ix_invoices_status", "invoices", ["status"])

    # ==========================================================================
    # Payment Methods
    # ==========================================================================

    op.create_table(
        "payment_methods",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        # Stripe ID
        sa.Column("stripe_payment_method_id", sa.String(), nullable=False),
        sa.Column("type", sa.String(), nullable=False, default="card"),
        # Card details (masked)
        sa.Column("card_brand", sa.String(), nullable=True),
        sa.Column("card_last4", sa.String(), nullable=True),
        sa.Column("card_exp_month", sa.Integer(), nullable=True),
        sa.Column("card_exp_year", sa.Integer(), nullable=True),
        # Status
        sa.Column("is_default", sa.Boolean(), nullable=False, default=False),
        # Timestamps
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_payment_methods_stripe_payment_method_id",
        "payment_methods",
        ["stripe_payment_method_id"],
        unique=True,
    )
    op.create_index(
        "ix_payment_methods_workspace_id", "payment_methods", ["workspace_id"]
    )


def downgrade() -> None:
    op.drop_table("payment_methods")
    op.drop_table("invoices")
    op.drop_table("billing_events")
