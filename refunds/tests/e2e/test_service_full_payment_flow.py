import datetime
from decimal import Decimal
import stripe
import time
from unittest import skipIf

from django.test import TestCase, Client, override_settings
from django.conf import settings
from django.utils import timezone

from service.models import ServiceBooking
from payments.models import Payment
from refunds.models import RefundRequest
from payments.webhook_handlers.refund_handlers import handle_booking_refunded
from service.tests.test_helpers.model_factories import (
    ServiceSettingsFactory,
    ServiceTypeFactory,
    ServiceProfileFactory,
    CustomerMotorcycleFactory,
    ServiceBrandFactory,
    ServiceTermsFactory,
)
from users.tests.test_helpers.model_factories import UserFactory
from dashboard.tests.test_helpers.model_factories import SiteSettingsFactory


@skipIf(not settings.STRIPE_SECRET_KEY, "Stripe API key not configured in settings")
@override_settings(ADMIN_EMAIL="admin@example.com")
class TestServiceFullPaymentRefundFlow(TestCase):
    def setUp(self):
        self.client = Client()
        SiteSettingsFactory()
        self.full_amount = Decimal("500.00")
        self.service_settings = ServiceSettingsFactory(
            enable_online_full_payment=True,
            booking_advance_notice=1,
            drop_off_start_time=datetime.time(9, 0),
            drop_off_end_time=datetime.time(17, 0),
            booking_open_days="Mon,Tue,Wed,Thu,Fri,Sat,Sun",
            currency_code="AUD",
        )
        self.service_type = ServiceTypeFactory(
            name="Service Full Payment Refund Test",
            base_price=self.full_amount,
            is_active=True,
        )
        self.user = UserFactory(username="fullrefunduser")
        self.service_profile = ServiceProfileFactory(
            user=self.user,
            name="Full Refund Test User",
            email="fullrefund@user.com",
            country="AU",
        )
        self.motorcycle = CustomerMotorcycleFactory(
            service_profile=self.service_profile, brand="Honda", model="CBR500R"
        )
        ServiceBrandFactory(name="Honda")
        self.client.force_login(self.user)
        stripe.api_key = settings.STRIPE_SECRET_KEY
        ServiceTermsFactory(is_active=True)

        # Create a service booking with a full payment
        self.booking = self._create_service_booking_with_full_payment()

    def _create_service_booking_with_full_payment(self):
        # This is a simplified version of the booking flow
        # to create a booking with a payment object.
        payment = Payment.objects.create(
            service_booking=None,  # Initially null
            amount=self.full_amount,
            status="succeeded",
            currency="aud",
        )

        intent = stripe.PaymentIntent.create(
            amount=int(self.full_amount * 100),
            currency="aud",
            payment_method_types=["card"],
            payment_method="pm_card_visa",
            confirm=True,
        )
        payment.stripe_payment_intent_id = intent.id
        payment.save()

        booking = ServiceBooking.objects.create(
            service_profile=self.service_profile,
            customer_motorcycle=self.motorcycle,
            service_type=self.service_type,
            service_date=timezone.now().date() + datetime.timedelta(days=5),
            dropoff_date=timezone.now().date() + datetime.timedelta(days=5),
            dropoff_time="10:00",
            payment_method="online_full",
            payment_status="paid",
            booking_status="pending",
            amount_paid=self.full_amount,
            calculated_total=self.service_type.base_price,
        )
        payment.service_booking = booking
        payment.save()
        return booking

    def test_service_full_payment_refund_flow(self):
        # 1. Create a RefundRequest with status 'approved'
        payment = Payment.objects.get(service_booking=self.booking)
        refund_request = RefundRequest.objects.create(
            payment=payment,
            service_booking=self.booking,
            amount_to_refund=self.full_amount,
            status="approved",
            is_admin_initiated=True,
        )

        # 2. Manually create a refund in Stripe
        payment_intent_id = payment.stripe_payment_intent_id

        try:
            refund = stripe.Refund.create(
                payment_intent=payment_intent_id,
                amount=int(self.full_amount * 100),
                reason="requested_by_customer",
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
                    "amount": int(self.service_type.base_price * 100),
                    "amount_refunded": int(self.full_amount * 100),
                    "payment_intent": payment_intent_id,
                    "refunds": {
                        "object": "list",
                        "data": [refund.to_dict()],
                    },
                }
            },
        }

        # 4. Call the webhook handler directly
        handle_booking_refunded(payment, event_payload["data"]["object"])

        # 5. Assertions
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.payment_status, "refunded")
        self.assertEqual(self.booking.booking_status, "cancelled")

        refund_request.refresh_from_db()
        self.assertEqual(refund_request.status, "refunded")
        self.assertEqual(refund_request.amount_to_refund, self.full_amount)
