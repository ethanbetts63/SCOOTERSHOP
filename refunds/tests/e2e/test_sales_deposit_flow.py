import datetime
from decimal import Decimal
import stripe
import time
from unittest import skipIf

from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.conf import settings
from django.utils import timezone

from inventory.models import SalesBooking
from dashboard.models import SiteSettings
from payments.models import Payment
from refunds.models import RefundRequest
from payments.webhook_handlers.refund_handlers import handle_booking_refunded
from ..test_helpers.model_factories import (
    MotorcycleFactory,
    SalesProfileFactory,
    UserFactory,
    SiteSettingsFactory,
)


@skipIf(not settings.STRIPE_SECRET_KEY, "Stripe API key not configured in settings")
@override_settings(ADMIN_EMAIL="admin@example.com")
class TestSalesDepositRefundFlow(TestCase):

    def setUp(self):
        self.client = Client()
        SiteSettingsFactory()
        self.deposit_amount = Decimal("100.00")
        self.motorcycle = MotorcycleFactory(price=Decimal("10000.00"))
        self.user = UserFactory(username="salesrefunduser")
        self.sales_profile = SalesProfileFactory(
            user=self.user, name="Sales Refund Test User", email="salesrefund@user.com", country="AU"
        )
        self.client.force_login(self.user)
        stripe.api_key = settings.STRIPE_SECRET_KEY

        # Create a sales booking with a deposit
        self.booking = self._create_sales_booking_with_deposit()

    def _create_sales_booking_with_deposit(self):
        # This is a simplified version of the booking flow
        # to create a booking with a payment object.
        payment = Payment.objects.create(
            sales_booking=None, # Initially null
            amount=self.deposit_amount,
            status='succeeded',
            currency='aud',
        )
        
        intent = stripe.PaymentIntent.create(
            amount=int(self.deposit_amount * 100),
            currency='aud',
            payment_method_types=['card'],
            payment_method='pm_card_visa',
            confirm=True,
        )
        payment.stripe_payment_intent_id = intent.id
        payment.save()

        booking = SalesBooking.objects.create(
            sales_profile=self.sales_profile,
            motorcycle=self.motorcycle,
            payment_status="deposit_paid",
            booking_status="confirmed",
            amount_paid=self.deposit_amount,
        )
        payment.sales_booking = booking
        payment.save()
        return booking

    def test_sales_deposit_refund_flow(self):
        # 1. Create a RefundRequest with status 'approved'
        payment = Payment.objects.get(sales_booking=self.booking)
        refund_request = RefundRequest.objects.create(
            payment=payment,
            sales_booking=self.booking,
            amount_to_refund=self.deposit_amount,
            status="approved",
            is_admin_initiated=True,
        )

        # 2. Manually create a refund in Stripe
        payment_intent_id = payment.stripe_payment_intent_id

        try:
            refund = stripe.Refund.create(
                payment_intent=payment_intent_id,
                amount=int(self.deposit_amount * 100),
                reason='requested_by_customer',
            )
        except stripe.error.StripeError as e:
            self.fail(f"Stripe API call failed during test: {e}")

        # 3. Simulate the Stripe webhook for charge.refunded
        
        # Retrieve the charge associated with the payment intent
        payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        charge_id = payment_intent.latest_charge

        # Construct the event payload
        event_payload = {
            "id": "evt_test_webhook",
            "object": "event",
            "api_version": "2020-08-27",
            "created": int(time.time()),
            "type": "charge.refunded",
            "data": {
                "object": {
                    "id": charge_id,
                    "object": "charge",
                    "amount": int(self.motorcycle.price * 100),
                    "amount_refunded": int(self.deposit_amount * 100),
                    "payment_intent": payment_intent_id,
                    "refunds": {
                        "object": "list",
                        "data": [refund.to_dict()],
                    }
                }
            }
        }
        
        # 4. Call the webhook handler directly
        handle_booking_refunded(payment, event_payload['data']['object'])

        # 5. Assertions
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.payment_status, "refunded")
        self.assertEqual(self.booking.booking_status, "declined_refunded")

        refund_request.refresh_from_db()
        self.assertEqual(refund_request.status, "refunded")
        self.assertEqual(refund_request.amount_to_refund, self.deposit_amount)