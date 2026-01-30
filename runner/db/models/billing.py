"""Billing and payment models.

Implements billing events tracking, invoices, and payment history
for the multi-tenancy billing system with Stripe integration.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from sqlmodel import Field, SQLModel

from runner.db.models.base import UUIDModel, TimestampMixin


class BillingEventType(str, Enum):
    """Types of billing events."""

    checkout_completed = "checkout.session.completed"
    invoice_paid = "invoice.paid"
    invoice_payment_failed = "invoice.payment_failed"
    subscription_created = "customer.subscription.created"
    subscription_updated = "customer.subscription.updated"
    subscription_deleted = "customer.subscription.deleted"
    payment_method_attached = "payment_method.attached"
    trial_will_end = "customer.subscription.trial_will_end"


class InvoiceStatus(str, Enum):
    """Status of an invoice."""

    draft = "draft"
    open = "open"
    paid = "paid"
    void = "void"
    uncollectible = "uncollectible"


# =============================================================================
# Billing Events
# =============================================================================


class BillingEventBase(SQLModel):
    """Base fields for billing events."""

    event_type: str = Field(index=True)
    stripe_event_id: str = Field(unique=True, index=True)

    # Event data
    payload: Optional[str] = None  # JSON string of Stripe event data

    # Processing status
    processed: bool = Field(default=False)
    processed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class BillingEvent(UUIDModel, BillingEventBase, TimestampMixin, table=True):
    """Billing event table.

    Stores all Stripe webhook events for idempotency and audit trail.
    """

    __tablename__ = "billing_events"

    workspace_id: Optional[UUID] = Field(
        default=None, foreign_key="workspaces.id", index=True
    )


class BillingEventRead(BillingEventBase):
    """Schema for reading billing event data."""

    id: UUID
    workspace_id: Optional[UUID]
    created_at: datetime


# =============================================================================
# Invoices
# =============================================================================


class InvoiceBase(SQLModel):
    """Base fields for invoices."""

    stripe_invoice_id: str = Field(unique=True, index=True)
    stripe_customer_id: str = Field(index=True)

    # Invoice details
    status: InvoiceStatus = Field(default=InvoiceStatus.draft)
    currency: str = Field(default="usd")

    # Amounts (in cents)
    subtotal: int = Field(default=0)
    tax: int = Field(default=0)
    total: int = Field(default=0)
    amount_paid: int = Field(default=0)
    amount_due: int = Field(default=0)

    # Dates
    invoice_date: datetime
    due_date: Optional[datetime] = None
    paid_at: Optional[datetime] = None

    # Period
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None

    # URLs
    hosted_invoice_url: Optional[str] = None
    invoice_pdf: Optional[str] = None

    # Description
    description: Optional[str] = None


class Invoice(UUIDModel, InvoiceBase, TimestampMixin, table=True):
    """Invoice table.

    Stores invoice records synced from Stripe.
    """

    __tablename__ = "invoices"

    workspace_id: UUID = Field(foreign_key="workspaces.id", index=True)
    subscription_id: Optional[UUID] = Field(
        default=None, foreign_key="account_subscriptions.id", index=True
    )


class InvoiceRead(InvoiceBase):
    """Schema for reading invoice data."""

    id: UUID
    workspace_id: UUID
    subscription_id: Optional[UUID]
    created_at: datetime


class InvoiceCreate(SQLModel):
    """Schema for creating an invoice."""

    stripe_invoice_id: str
    stripe_customer_id: str
    workspace_id: UUID
    subscription_id: Optional[UUID] = None
    status: InvoiceStatus = InvoiceStatus.draft
    currency: str = "usd"
    subtotal: int = 0
    tax: int = 0
    total: int = 0
    amount_paid: int = 0
    amount_due: int = 0
    invoice_date: datetime
    due_date: Optional[datetime] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    hosted_invoice_url: Optional[str] = None
    invoice_pdf: Optional[str] = None
    description: Optional[str] = None


# =============================================================================
# Payment Methods (for display purposes)
# =============================================================================


class PaymentMethodType(str, Enum):
    """Types of payment methods."""

    card = "card"
    bank_account = "bank_account"
    paypal = "paypal"


class PaymentMethodBase(SQLModel):
    """Base fields for payment methods."""

    stripe_payment_method_id: str = Field(unique=True, index=True)
    type: PaymentMethodType = Field(default=PaymentMethodType.card)

    # Card details (masked)
    card_brand: Optional[str] = None  # visa, mastercard, etc.
    card_last4: Optional[str] = None
    card_exp_month: Optional[int] = None
    card_exp_year: Optional[int] = None

    # Status
    is_default: bool = Field(default=False)


class PaymentMethod(UUIDModel, PaymentMethodBase, TimestampMixin, table=True):
    """Payment method table.

    Stores payment method metadata for display purposes.
    Actual payment data is stored in Stripe.
    """

    __tablename__ = "payment_methods"

    workspace_id: UUID = Field(foreign_key="workspaces.id", index=True)


class PaymentMethodRead(PaymentMethodBase):
    """Schema for reading payment method data."""

    id: UUID
    workspace_id: UUID
    created_at: datetime
