"""
Stripe Model Context Protocol (MCP) Integration

Provides MCP tools for Stripe payment processing:
- Create/manage subscriptions
- Handle webhooks
- Sync customer data
- Generate invoices
"""

import os
import json
from typing import Optional, Dict, Any
import stripe
from datetime import datetime, timedelta

# Initialize Stripe SDK
stripe.api_key = os.getenv("STRIPE_API_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

# Tier pricing mapping
TIER_PRICING = {
    "starter": {
        "price_id": os.getenv("STRIPE_STARTER_PRICE_ID", "price_1SdOlkAYPKqxMcp8StarterMonthly"),
        "price_per_month": 29.00,
        "seats_limit": 5,
    },
    "professional": {
        "price_id": os.getenv("STRIPE_PROFESSIONAL_PRICE_ID", "price_1SdOlkAYPKqxMcp8ProfessionalMonthly"),
        "price_per_month": 99.00,
        "seats_limit": 25,
    },
    "enterprise": {
        "price_id": os.getenv("STRIPE_ENTERPRISE_PRICE_ID", "price_1SdOlkAYPKqxMcp8EnterpriseMonthly"),
        "price_per_month": 299.00,
        "seats_limit": 999,
    },
}


class StripeMCPClient:
    """MCP client for Stripe integration."""

    @staticmethod
    def create_customer(email: str, tenant_name: str, metadata: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Create a Stripe customer for a tenant.

        Args:
            email: Billing email
            tenant_name: Organization name
            metadata: Optional metadata dict (tenant_id, etc.)

        Returns:
            Stripe Customer object
        """
        try:
            customer = stripe.Customer.create(
                email=email,
                name=tenant_name,
                metadata=metadata or {},
            )
            return {
                "success": True,
                "customer_id": customer.id,
                "email": customer.email,
            }
        except stripe.error.StripeError as e:
            return {
                "success": False,
                "error": str(e),
            }

    @staticmethod
    def create_subscription(
        customer_id: str,
        tier: str,
        trial_days: int = 14,
    ) -> Dict[str, Any]:
        """
        Create a subscription for a customer.

        Args:
            customer_id: Stripe customer ID
            tier: Subscription tier (starter, professional, enterprise)
            trial_days: Trial period length

        Returns:
            Subscription object
        """
        try:
            if tier not in TIER_PRICING:
                return {"success": False, "error": f"Invalid tier: {tier}"}

            price_id = TIER_PRICING[tier]["price_id"]

            subscription = stripe.Subscription.create(
                customer=customer_id,
                items=[{"price": price_id}],
                trial_period_days=trial_days,
                payment_behavior="default_incomplete",
            )

            return {
                "success": True,
                "subscription_id": subscription.id,
                "status": subscription.status,
                "current_period_start": subscription.current_period_start,
                "current_period_end": subscription.current_period_end,
                "trial_end": subscription.trial_end,
            }
        except stripe.error.StripeError as e:
            return {
                "success": False,
                "error": str(e),
            }

    @staticmethod
    def update_subscription(subscription_id: str, tier: str) -> Dict[str, Any]:
        """
        Update subscription tier (upgrade/downgrade).

        Args:
            subscription_id: Stripe subscription ID
            tier: New tier

        Returns:
            Updated subscription object
        """
        try:
            if tier not in TIER_PRICING:
                return {"success": False, "error": f"Invalid tier: {tier}"}

            subscription = stripe.Subscription.retrieve(subscription_id)
            item_id = subscription.items.data[0].id
            new_price_id = TIER_PRICING[tier]["price_id"]

            updated_subscription = stripe.Subscription.modify(
                subscription_id,
                items=[
                    {
                        "id": item_id,
                        "price": new_price_id,
                    }
                ],
                proration_behavior="create_prorations",
            )

            return {
                "success": True,
                "subscription_id": updated_subscription.id,
                "status": updated_subscription.status,
                "tier": tier,
            }
        except stripe.error.StripeError as e:
            return {
                "success": False,
                "error": str(e),
            }

    @staticmethod
    def cancel_subscription(subscription_id: str, immediate: bool = False) -> Dict[str, Any]:
        """
        Cancel a subscription.

        Args:
            subscription_id: Stripe subscription ID
            immediate: If True, cancel at end of billing period; if False, cancel immediately

        Returns:
            Canceled subscription object
        """
        try:
            canceled_subscription = stripe.Subscription.delete(
                subscription_id,
                invoice_now=False,
            )

            return {
                "success": True,
                "subscription_id": canceled_subscription.id,
                "status": canceled_subscription.status,
                "canceled_at": canceled_subscription.canceled_at,
            }
        except stripe.error.StripeError as e:
            return {
                "success": False,
                "error": str(e),
            }

    @staticmethod
    def retrieve_subscription(subscription_id: str) -> Dict[str, Any]:
        """
        Retrieve subscription details.

        Args:
            subscription_id: Stripe subscription ID

        Returns:
            Subscription object
        """
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)

            return {
                "success": True,
                "subscription_id": subscription.id,
                "customer_id": subscription.customer,
                "status": subscription.status,
                "current_period_start": subscription.current_period_start,
                "current_period_end": subscription.current_period_end,
                "trial_end": subscription.trial_end,
                "items": [
                    {
                        "price": item.price.id,
                        "quantity": item.quantity,
                    }
                    for item in subscription.items.data
                ],
            }
        except stripe.error.StripeError as e:
            return {
                "success": False,
                "error": str(e),
            }

    @staticmethod
    def list_invoices(customer_id: str, limit: int = 10) -> Dict[str, Any]:
        """
        List invoices for a customer.

        Args:
            customer_id: Stripe customer ID
            limit: Number of invoices to retrieve

        Returns:
            List of invoices
        """
        try:
            invoices = stripe.Invoice.list(customer=customer_id, limit=limit)

            return {
                "success": True,
                "invoices": [
                    {
                        "id": inv.id,
                        "number": inv.number,
                        "amount_paid": inv.amount_paid,
                        "amount_due": inv.amount_due,
                        "status": inv.status,
                        "created": inv.created,
                        "pdf_url": inv.pdf or "",
                    }
                    for inv in invoices.data
                ],
            }
        except stripe.error.StripeError as e:
            return {
                "success": False,
                "error": str(e),
            }

    @staticmethod
    def sync_subscription_to_db(subscription_id: str, tenant_id: str, db_session) -> Dict[str, Any]:
        """
        Sync Stripe subscription data to local database.

        Args:
            subscription_id: Stripe subscription ID
            tenant_id: Local tenant ID
            db_session: SQLAlchemy session

        Returns:
            Sync result
        """
        try:
            from src.db.models import Subscription

            subscription = stripe.Subscription.retrieve(subscription_id)

            tier_map = {
                TIER_PRICING["starter"]["price_id"]: "starter",
                TIER_PRICING["professional"]["price_id"]: "professional",
                TIER_PRICING["enterprise"]["price_id"]: "enterprise",
            }

            price_id = subscription.items.data[0].price.id if subscription.items.data else None
            tier = tier_map.get(price_id, "starter")

            db_subscription = Subscription(
                id=subscription_id,
                tenant_id=tenant_id,
                stripe_subscription_id=subscription_id,
                stripe_product_id=subscription.items.data[0].price.product if subscription.items.data else None,
                status=subscription.status,
                tier=tier,
                price_per_month=TIER_PRICING.get(tier, {}).get("price_per_month"),
                seats_limit=TIER_PRICING.get(tier, {}).get("seats_limit", 5),
                started_at=datetime.fromtimestamp(subscription.current_period_start),
                ends_at=datetime.fromtimestamp(subscription.current_period_end),
                trial_ends_at=datetime.fromtimestamp(subscription.trial_end) if subscription.trial_end else None,
                auto_renew=not subscription.cancel_at_period_end,
            )

            db_session.merge(db_subscription)
            db_session.commit()

            return {
                "success": True,
                "message": f"Subscription {subscription_id} synced to tenant {tenant_id}",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    @staticmethod
    def handle_webhook_event(payload: Dict[str, Any], signature: str) -> Dict[str, Any]:
        """
        Validate and process Stripe webhook events.

        Args:
            payload: Webhook payload
            signature: Stripe signature header

        Returns:
            Webhook processing result
        """
        try:
            event = stripe.Webhook.construct_event(
                payload,
                signature,
                STRIPE_WEBHOOK_SECRET,
            )

            event_type = event["type"]
            data = event["data"]["object"]

            if event_type == "customer.subscription.updated":
                return {
                    "success": True,
                    "event_type": event_type,
                    "subscription_id": data["id"],
                    "status": data["status"],
                    "action": "subscription_updated",
                }
            elif event_type == "customer.subscription.deleted":
                return {
                    "success": True,
                    "event_type": event_type,
                    "subscription_id": data["id"],
                    "action": "subscription_canceled",
                }
            elif event_type == "invoice.payment_succeeded":
                return {
                    "success": True,
                    "event_type": event_type,
                    "invoice_id": data["id"],
                    "amount_paid": data["amount_paid"],
                    "action": "payment_succeeded",
                }
            elif event_type == "invoice.payment_failed":
                return {
                    "success": True,
                    "event_type": event_type,
                    "invoice_id": data["id"],
                    "attempt_count": data["attempt_count"],
                    "action": "payment_failed",
                }
            else:
                return {
                    "success": True,
                    "event_type": event_type,
                    "action": "unhandled_event",
                }
        except ValueError as e:
            return {
                "success": False,
                "error": "Invalid payload",
            }
        except stripe.error.SignatureVerificationError as e:
            return {
                "success": False,
                "error": "Invalid signature",
            }


# Export tools for MCP
stripe_tools = {
    "create_customer": StripeMCPClient.create_customer,
    "create_subscription": StripeMCPClient.create_subscription,
    "update_subscription": StripeMCPClient.update_subscription,
    "cancel_subscription": StripeMCPClient.cancel_subscription,
    "retrieve_subscription": StripeMCPClient.retrieve_subscription,
    "list_invoices": StripeMCPClient.list_invoices,
    "sync_subscription_to_db": StripeMCPClient.sync_subscription_to_db,
    "handle_webhook_event": StripeMCPClient.handle_webhook_event,
}
