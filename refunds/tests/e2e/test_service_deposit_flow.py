
import datetime
from decimal import Decimal
import stripe
import time
from unittest import skipIf

from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.conf import settings
from django.utils import timezone

from service.models import ServiceBooking
from dashboard.models import SiteSettings
from payments.models import Payment
from refunds.models import RefundRequest
from payments.webhook_handlers.refund_handlers import handle_booking_refunded
from service.tests.test_helpers.model_factories import (
    ServiceSettingsFactory,
    ServiceTypeFactory,
    UserFactory,
    ServiceProfileFactory,
    CustomerMotorcycleFactory,
    ServiceBrandFactory,
    ServiceTermsFactory,
)


@skipIf(not settings.STRIPE_SECRET_KEY, "Stripe API key not configured in settings")
@override_settings(ADMIN_EMAIL="admin@example.com")
class TestServiceDepositRefundFlow(TestCase):

    def setUp(self):
        self.client = Client()
        SiteSettings.objects.create()
        self.deposit_amount = Decimal("50.00")
        self.service_settings = ServiceSettingsFactory(
            enable_online_deposit=True,
            deposit_calc_method="FLAT_FEE",
            deposit_flat_fee_amount=self.deposit_amount,
            booking_advance_notice=1,
            drop_off_start_time=datetime.time(9, 0),
            drop_off_end_time=datetime.time(17, 0),
            booking_open_days="Mon,Tue,Wed,Thu,Fri,Sat,Sun",
            currency_code="AUD",
        )
        self.service_type = ServiceTypeFactory(
            name="Service Deposit Refund Test", base_price=Decimal("500.00"), is_active=True
        )
        self.user = UserFactory(username="refunduser")
        self.service_profile = ServiceProfileFactory(
            user=self.user, name="Refund Test User", email="refund@user.com", country="AU"
        )
        self.motorcycle = CustomerMotorcycleFactory(
            service_profile=self.service_profile, brand="Yamaha", model="MT-07"
        )
        ServiceBrandFactory(name="Yamaha")
        self.client.force_login(self.user)
        stripe.api_key = settings.STRIPE_SECRET_KEY
        ServiceTermsFactory(is_active=True)

        # Create a service booking with a deposit
        self.booking = self._create_service_booking_with_deposit()

    def _create_service_booking_with_deposit(self):
        # This is a simplified version of the booking flow
        # to create a booking with a payment object.
        payment = Payment.objects.create(
            service_booking=None, # Initially null
            amount=self.deposit_amount,
            payment_method_type='card',
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

        booking = ServiceBooking.objects.create(
            service_profile=self.service_profile,
            customer_motorcycle=self.motorcycle,
            service_type=self.service_type,
            service_date=timezone.now().date() + datetime.timedelta(days=5),
            dropoff_time="10:00",
            payment_method="online_deposit",
            payment_status="deposit_paid",
            status="confirmed",
            amount_paid=self.deposit_amount,
            calculated_total=self.service_type.base_price,
        )
        payment.service_booking = booking
        payment.save()
        return booking

    def test_service_deposit_refund_flow(self):
        # 1. Manually create a refund in Stripe
        payment = Payment.objects.get(service_booking=self.booking)
        payment_intent_id = payment.stripe_payment_intent_id

        try:
            refund = stripe.Refund.create(
                payment_intent=payment_intent_id,
                amount=int(self.deposit_amount * 100),
                reason='requested_by_customer',
            )
        except stripe.error.StripeError as e:
            self.fail(f"Stripe API call failed during test: {e}")

        # 2. Simulate the Stripe webhook for charge.refunded
        
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
                    "amount_refunded": int(self.deposit_amount * 100),
                    "payment_intent": payment_intent_id,
                    "refunds": {
                        "object": "list",
                        "data": [refund.to_dict()],
                    }
                }
            }
        }
        
        # 3. Call the webhook handler directly
        handle_booking_refunded(event_payload)

        # 4. Assertions
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.payment_status, "refunded")
        self.assertEqual(self.booking.status, "cancelled")

        refund_request = RefundRequest.objects.get(booking_reference=self.booking.service_booking_reference)
        self.assertEqual(refund_request.status, "approved")
        self.assertEqual(refund_request.refund_amount, self.deposit_amount)
