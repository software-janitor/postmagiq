"""Billing routes for Stripe integration.

Routes for checkout, customer portal, webhooks, and invoice history.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Header
from pydantic import BaseModel

from api.auth.dependencies import get_current_user, require_scope
from api.auth.scopes import Scope
from api.services.billing_service import BillingService
from runner.db.models import User

router = APIRouter(prefix="/v1/w/{workspace_id}/billing", tags=["billing"])
webhook_router = APIRouter(prefix="/v1/webhooks", tags=["webhooks"])

billing_service = BillingService()


# =============================================================================
# Request/Response Models
# =============================================================================


class CreateCheckoutRequest(BaseModel):
    """Request to create checkout session."""

    tier_slug: str
    billing_period: str = "monthly"
    success_url: str
    cancel_url: str


class CheckoutResponse(BaseModel):
    """Response with checkout session URL."""

    url: str
    session_id: str


class PortalRequest(BaseModel):
    """Request to create portal session."""

    return_url: str


class PortalResponse(BaseModel):
    """Response with portal session URL."""

    url: str


class InvoiceResponse(BaseModel):
    """Response model for invoice."""

    id: str
    stripe_invoice_id: str
    status: str
    currency: str
    total: int  # in cents
    amount_paid: int
    amount_due: int
    invoice_date: str
    paid_at: Optional[str]
    hosted_invoice_url: Optional[str]
    invoice_pdf: Optional[str]


class PaymentMethodResponse(BaseModel):
    """Response model for payment method."""

    id: str
    type: str
    card_brand: Optional[str]
    card_last4: Optional[str]
    card_exp_month: Optional[int]
    card_exp_year: Optional[int]
    is_default: bool


# =============================================================================
# Billing Routes
# =============================================================================


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout_session(
    workspace_id: UUID,
    request: CreateCheckoutRequest,
    current_user: User = Depends(require_scope(Scope.WORKSPACE_SETTINGS)),
):
    """Create a Stripe checkout session for subscription.

    Requires workspace:settings scope. Returns a URL to redirect the user to.
    """
    try:
        result = billing_service.create_checkout_session(
            workspace_id=workspace_id,
            tier_slug=request.tier_slug,
            success_url=request.success_url,
            cancel_url=request.cancel_url,
            billing_period=request.billing_period,
        )
        return CheckoutResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/portal", response_model=PortalResponse)
async def create_portal_session(
    workspace_id: UUID,
    request: PortalRequest,
    current_user: User = Depends(require_scope(Scope.WORKSPACE_SETTINGS)),
):
    """Create a Stripe customer portal session.

    Requires workspace:settings scope. Returns a URL to redirect the user to
    for managing their subscription.
    """
    try:
        result = billing_service.create_portal_session(
            workspace_id=workspace_id,
            return_url=request.return_url,
        )
        return PortalResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/invoices", response_model=list[InvoiceResponse])
async def list_invoices(
    workspace_id: UUID,
    current_user: User = Depends(require_scope(Scope.WORKSPACE_SETTINGS)),
):
    """List all invoices for the workspace.

    Requires workspace:settings scope. Returns invoices ordered by date descending.
    """
    invoices = billing_service.get_invoices(workspace_id)
    return [
        InvoiceResponse(
            id=str(inv.id),
            stripe_invoice_id=inv.stripe_invoice_id,
            status=inv.status,
            currency=inv.currency,
            total=inv.total,
            amount_paid=inv.amount_paid,
            amount_due=inv.amount_due,
            invoice_date=inv.invoice_date.isoformat(),
            paid_at=inv.paid_at.isoformat() if inv.paid_at else None,
            hosted_invoice_url=inv.hosted_invoice_url,
            invoice_pdf=inv.invoice_pdf,
        )
        for inv in invoices
    ]


@router.get("/payment-methods", response_model=list[PaymentMethodResponse])
async def list_payment_methods(
    workspace_id: UUID,
    current_user: User = Depends(require_scope(Scope.WORKSPACE_SETTINGS)),
):
    """List all payment methods for the workspace.

    Requires workspace:settings scope.
    """
    methods = billing_service.get_payment_methods(workspace_id)
    return [
        PaymentMethodResponse(
            id=str(pm.id),
            type=pm.type,
            card_brand=pm.card_brand,
            card_last4=pm.card_last4,
            card_exp_month=pm.card_exp_month,
            card_exp_year=pm.card_exp_year,
            is_default=pm.is_default,
        )
        for pm in methods
    ]


# =============================================================================
# Webhook Routes (no auth required, uses Stripe signature)
# =============================================================================


@webhook_router.post("/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="Stripe-Signature"),
):
    """Handle incoming Stripe webhooks.

    Verifies webhook signature and processes events.
    """
    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature header")

    payload = await request.body()

    try:
        result = billing_service.handle_webhook(payload, stripe_signature)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
