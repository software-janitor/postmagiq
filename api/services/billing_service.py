"""Service for billing operations with Stripe integration.

Handles checkout sessions, customer portal, webhook processing,
and invoice management.
"""

import json
import os
import uuid
from datetime import datetime
from typing import Optional
from uuid import UUID

import stripe
from sqlmodel import Session, select

from runner.db.engine import engine
from runner.db.models import (
    AccountSubscription, SubscriptionStatus,
    SubscriptionTier,
    UsageTracking,
    BillingEvent,
    Invoice, InvoiceStatus, InvoiceCreate,
    PaymentMethod,
    Workspace,
)

# Initialize Stripe with API key from environment
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")


class BillingService:
    """Service for Stripe billing operations.

    Handles checkout, customer portal, webhooks, and invoice management.
    """

    def __init__(self):
        """Initialize BillingService."""
        self.stripe_configured = bool(stripe.api_key)

    def create_checkout_session(
        self,
        workspace_id: UUID,
        tier_slug: str,
        success_url: str,
        cancel_url: str,
        billing_period: str = "monthly",
    ) -> dict:
        """Create a Stripe checkout session for subscription.

        Args:
            workspace_id: Workspace UUID
            tier_slug: Subscription tier slug
            success_url: URL to redirect on success
            cancel_url: URL to redirect on cancel
            billing_period: 'monthly' or 'yearly'

        Returns:
            Dict with checkout session URL and ID

        Raises:
            ValueError: If tier not found or Stripe not configured
        """
        if not self.stripe_configured:
            raise ValueError("Stripe is not configured")

        with Session(engine) as session:
            # Get tier
            tier_statement = select(SubscriptionTier).where(
                SubscriptionTier.slug == tier_slug,
                SubscriptionTier.is_active == True,
            )
            tier = session.exec(tier_statement).first()
            if not tier:
                raise ValueError(f"Tier not found: {tier_slug}")

            # Get workspace
            workspace = session.get(Workspace, workspace_id)
            if not workspace:
                raise ValueError("Workspace not found")

            # Get or create Stripe customer
            sub_statement = select(AccountSubscription).where(
                AccountSubscription.workspace_id == workspace_id,
            )
            subscription = session.exec(sub_statement).first()

            customer_id = None
            if subscription and subscription.stripe_customer_id:
                customer_id = subscription.stripe_customer_id

            # Determine price (use Stripe price IDs in production)
            # For now, create a price on the fly (not recommended for production)
            price = tier.price_yearly if billing_period == "yearly" else tier.price_monthly
            interval = "year" if billing_period == "yearly" else "month"

            # Create checkout session
            checkout_params = {
                "mode": "subscription",
                "success_url": success_url + "?session_id={CHECKOUT_SESSION_ID}",
                "cancel_url": cancel_url,
                "line_items": [
                    {
                        "price_data": {
                            "currency": "usd",
                            "product_data": {
                                "name": f"{tier.name} Plan",
                                "description": tier.description or f"Postmatiq {tier.name} subscription",
                            },
                            "unit_amount": int(price * 100),  # Convert to cents
                            "recurring": {"interval": interval},
                        },
                        "quantity": 1,
                    }
                ],
                "metadata": {
                    "workspace_id": str(workspace_id),
                    "tier_slug": tier_slug,
                    "billing_period": billing_period,
                },
                "subscription_data": {
                    "metadata": {
                        "workspace_id": str(workspace_id),
                        "tier_slug": tier_slug,
                    },
                },
            }

            if customer_id:
                checkout_params["customer"] = customer_id
            else:
                checkout_params["customer_creation"] = "always"

            checkout_session = stripe.checkout.Session.create(**checkout_params)

            return {
                "url": checkout_session.url,
                "session_id": checkout_session.id,
            }

    def create_portal_session(
        self,
        workspace_id: UUID,
        return_url: str,
    ) -> dict:
        """Create a Stripe customer portal session.

        Args:
            workspace_id: Workspace UUID
            return_url: URL to return to after portal

        Returns:
            Dict with portal session URL

        Raises:
            ValueError: If no customer ID or Stripe not configured
        """
        if not self.stripe_configured:
            raise ValueError("Stripe is not configured")

        with Session(engine) as session:
            sub_statement = select(AccountSubscription).where(
                AccountSubscription.workspace_id == workspace_id,
            )
            subscription = session.exec(sub_statement).first()

            if not subscription or not subscription.stripe_customer_id:
                raise ValueError("No Stripe customer found for this workspace")

            portal_session = stripe.billing_portal.Session.create(
                customer=subscription.stripe_customer_id,
                return_url=return_url,
            )

            return {"url": portal_session.url}

    def handle_webhook(self, payload: bytes, signature: str) -> dict:
        """Handle incoming Stripe webhook.

        Args:
            payload: Raw request body
            signature: Stripe signature header

        Returns:
            Dict with processing result

        Raises:
            ValueError: If signature verification fails
        """
        if not STRIPE_WEBHOOK_SECRET:
            raise ValueError("Stripe webhook secret not configured")

        try:
            event = stripe.Webhook.construct_event(
                payload, signature, STRIPE_WEBHOOK_SECRET
            )
        except stripe.error.SignatureVerificationError:
            raise ValueError("Invalid webhook signature")

        # Store event for idempotency
        with Session(engine) as session:
            # Check if already processed
            existing_statement = select(BillingEvent).where(
                BillingEvent.stripe_event_id == event.id
            )
            if session.exec(existing_statement).first():
                return {"status": "already_processed", "event_id": event.id}

            # Extract workspace ID from metadata if available
            workspace_id = None
            if hasattr(event.data.object, "metadata"):
                ws_id = event.data.object.metadata.get("workspace_id")
                if ws_id:
                    try:
                        workspace_id = UUID(ws_id)
                    except ValueError:
                        pass

            # Store event
            billing_event = BillingEvent(
                id=uuid.uuid4(),
                workspace_id=workspace_id,
                event_type=event.type,
                stripe_event_id=event.id,
                payload=json.dumps(event.data.object.to_dict()) if event.data.object else None,
                processed=False,
            )
            session.add(billing_event)
            session.commit()

            # Process event
            result = self._process_event(session, billing_event, event)

            # Mark as processed
            billing_event.processed = True
            billing_event.processed_at = datetime.utcnow()
            if result.get("error"):
                billing_event.error_message = result["error"]
            session.add(billing_event)
            session.commit()

            return result

    def _process_event(
        self, session: Session, billing_event: BillingEvent, event
    ) -> dict:
        """Process a specific Stripe event.

        Args:
            session: Database session
            billing_event: BillingEvent record
            event: Stripe event object

        Returns:
            Dict with processing result
        """
        event_type = event.type
        obj = event.data.object

        if event_type == "checkout.session.completed":
            return self._handle_checkout_completed(session, obj)
        elif event_type == "invoice.paid":
            return self._handle_invoice_paid(session, obj)
        elif event_type == "invoice.payment_failed":
            return self._handle_invoice_payment_failed(session, obj)
        elif event_type == "customer.subscription.updated":
            return self._handle_subscription_updated(session, obj)
        elif event_type == "customer.subscription.deleted":
            return self._handle_subscription_deleted(session, obj)
        elif event_type == "payment_method.attached":
            return self._handle_payment_method_attached(session, obj)
        else:
            return {"status": "ignored", "event_type": event_type}

    def _handle_checkout_completed(self, session: Session, checkout) -> dict:
        """Handle checkout.session.completed event."""
        workspace_id = checkout.metadata.get("workspace_id")
        tier_slug = checkout.metadata.get("tier_slug")
        billing_period = checkout.metadata.get("billing_period", "monthly")

        if not workspace_id or not tier_slug:
            return {"error": "Missing metadata in checkout session"}

        workspace_id = UUID(workspace_id)

        # Get tier
        tier_statement = select(SubscriptionTier).where(
            SubscriptionTier.slug == tier_slug
        )
        tier = session.exec(tier_statement).first()
        if not tier:
            return {"error": f"Tier not found: {tier_slug}"}

        # Update or create subscription
        sub_statement = select(AccountSubscription).where(
            AccountSubscription.workspace_id == workspace_id
        )
        subscription = session.exec(sub_statement).first()

        stripe_sub = stripe.Subscription.retrieve(checkout.subscription)

        if subscription:
            subscription.tier_id = tier.id
            subscription.status = SubscriptionStatus.active
            subscription.billing_period = billing_period
            subscription.stripe_subscription_id = checkout.subscription
            subscription.stripe_customer_id = checkout.customer
            subscription.current_period_start = datetime.fromtimestamp(
                stripe_sub.current_period_start
            )
            subscription.current_period_end = datetime.fromtimestamp(
                stripe_sub.current_period_end
            )
        else:
            subscription = AccountSubscription(
                id=uuid.uuid4(),
                workspace_id=workspace_id,
                tier_id=tier.id,
                status=SubscriptionStatus.active,
                billing_period=billing_period,
                stripe_subscription_id=checkout.subscription,
                stripe_customer_id=checkout.customer,
                current_period_start=datetime.fromtimestamp(
                    stripe_sub.current_period_start
                ),
                current_period_end=datetime.fromtimestamp(
                    stripe_sub.current_period_end
                ),
            )
        session.add(subscription)
        session.commit()

        return {"status": "subscription_created", "workspace_id": str(workspace_id)}

    def _handle_invoice_paid(self, session: Session, invoice_obj) -> dict:
        """Handle invoice.paid event - reset usage period."""
        customer_id = invoice_obj.customer

        # Find subscription by customer ID
        sub_statement = select(AccountSubscription).where(
            AccountSubscription.stripe_customer_id == customer_id
        )
        subscription = session.exec(sub_statement).first()

        if not subscription:
            return {"status": "no_subscription", "customer_id": customer_id}

        # Update subscription period
        if invoice_obj.subscription:
            stripe_sub = stripe.Subscription.retrieve(invoice_obj.subscription)
            subscription.current_period_start = datetime.fromtimestamp(
                stripe_sub.current_period_start
            )
            subscription.current_period_end = datetime.fromtimestamp(
                stripe_sub.current_period_end
            )
            subscription.status = SubscriptionStatus.active
            session.add(subscription)

        # Create invoice record
        invoice = Invoice(
            id=uuid.uuid4(),
            workspace_id=subscription.workspace_id,
            subscription_id=subscription.id,
            stripe_invoice_id=invoice_obj.id,
            stripe_customer_id=customer_id,
            status=InvoiceStatus.paid,
            currency=invoice_obj.currency,
            subtotal=invoice_obj.subtotal,
            tax=invoice_obj.tax or 0,
            total=invoice_obj.total,
            amount_paid=invoice_obj.amount_paid,
            amount_due=invoice_obj.amount_due,
            invoice_date=datetime.fromtimestamp(invoice_obj.created),
            paid_at=datetime.utcnow(),
            period_start=datetime.fromtimestamp(invoice_obj.period_start) if invoice_obj.period_start else None,
            period_end=datetime.fromtimestamp(invoice_obj.period_end) if invoice_obj.period_end else None,
            hosted_invoice_url=invoice_obj.hosted_invoice_url,
            invoice_pdf=invoice_obj.invoice_pdf,
        )
        session.add(invoice)
        session.commit()

        return {
            "status": "invoice_recorded",
            "workspace_id": str(subscription.workspace_id),
        }

    def _handle_invoice_payment_failed(self, session: Session, invoice_obj) -> dict:
        """Handle invoice.payment_failed event."""
        customer_id = invoice_obj.customer

        sub_statement = select(AccountSubscription).where(
            AccountSubscription.stripe_customer_id == customer_id
        )
        subscription = session.exec(sub_statement).first()

        if subscription:
            subscription.status = SubscriptionStatus.past_due
            session.add(subscription)
            session.commit()

        return {"status": "marked_past_due", "customer_id": customer_id}

    def _handle_subscription_updated(self, session: Session, stripe_sub) -> dict:
        """Handle customer.subscription.updated event."""
        sub_statement = select(AccountSubscription).where(
            AccountSubscription.stripe_subscription_id == stripe_sub.id
        )
        subscription = session.exec(sub_statement).first()

        if not subscription:
            return {"status": "subscription_not_found", "stripe_id": stripe_sub.id}

        # Update period dates
        subscription.current_period_start = datetime.fromtimestamp(
            stripe_sub.current_period_start
        )
        subscription.current_period_end = datetime.fromtimestamp(
            stripe_sub.current_period_end
        )

        # Update status based on Stripe status
        status_map = {
            "active": SubscriptionStatus.active,
            "past_due": SubscriptionStatus.past_due,
            "canceled": SubscriptionStatus.canceled,
            "trialing": SubscriptionStatus.trialing,
            "paused": SubscriptionStatus.paused,
        }
        subscription.status = status_map.get(
            stripe_sub.status, SubscriptionStatus.active
        )

        # Check for cancel at period end
        subscription.cancel_at_period_end = stripe_sub.cancel_at_period_end

        session.add(subscription)
        session.commit()

        return {
            "status": "subscription_updated",
            "workspace_id": str(subscription.workspace_id),
        }

    def _handle_subscription_deleted(self, session: Session, stripe_sub) -> dict:
        """Handle customer.subscription.deleted event."""
        sub_statement = select(AccountSubscription).where(
            AccountSubscription.stripe_subscription_id == stripe_sub.id
        )
        subscription = session.exec(sub_statement).first()

        if not subscription:
            return {"status": "subscription_not_found", "stripe_id": stripe_sub.id}

        subscription.status = SubscriptionStatus.canceled
        subscription.canceled_at = datetime.utcnow()
        session.add(subscription)
        session.commit()

        return {
            "status": "subscription_canceled",
            "workspace_id": str(subscription.workspace_id),
        }

    def _handle_payment_method_attached(self, session: Session, pm) -> dict:
        """Handle payment_method.attached event."""
        customer_id = pm.customer

        sub_statement = select(AccountSubscription).where(
            AccountSubscription.stripe_customer_id == customer_id
        )
        subscription = session.exec(sub_statement).first()

        if not subscription:
            return {"status": "no_subscription", "customer_id": customer_id}

        # Store payment method details
        payment_method = PaymentMethod(
            id=uuid.uuid4(),
            workspace_id=subscription.workspace_id,
            stripe_payment_method_id=pm.id,
            type=pm.type,
            card_brand=pm.card.brand if pm.type == "card" and pm.card else None,
            card_last4=pm.card.last4 if pm.type == "card" and pm.card else None,
            card_exp_month=pm.card.exp_month if pm.type == "card" and pm.card else None,
            card_exp_year=pm.card.exp_year if pm.type == "card" and pm.card else None,
            is_default=False,
        )
        session.add(payment_method)
        session.commit()

        return {
            "status": "payment_method_stored",
            "workspace_id": str(subscription.workspace_id),
        }

    def get_invoices(self, workspace_id: UUID) -> list[Invoice]:
        """Get all invoices for a workspace.

        Args:
            workspace_id: Workspace UUID

        Returns:
            List of Invoice objects ordered by date descending
        """
        with Session(engine) as session:
            statement = select(Invoice).where(
                Invoice.workspace_id == workspace_id
            ).order_by(Invoice.invoice_date.desc())
            invoices = list(session.exec(statement).all())
            for inv in invoices:
                session.expunge(inv)
            return invoices

    def get_payment_methods(self, workspace_id: UUID) -> list[PaymentMethod]:
        """Get all payment methods for a workspace.

        Args:
            workspace_id: Workspace UUID

        Returns:
            List of PaymentMethod objects
        """
        with Session(engine) as session:
            statement = select(PaymentMethod).where(
                PaymentMethod.workspace_id == workspace_id
            )
            methods = list(session.exec(statement).all())
            for m in methods:
                session.expunge(m)
            return methods
