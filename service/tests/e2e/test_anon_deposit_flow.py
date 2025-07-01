import datetime
from decimal import Decimal
import stripe
from unittest import skipIf

from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.conf import settings
from django.utils import timezone

from service.models import TempServiceBooking, ServiceBooking
from dashboard.models import SiteSettings
from payments.models import Payment
from payments.webhook_handlers.service_handlers import handle_service_booking_succeeded
from ..test_helpers.model_factories import (
    ServiceSettingsFactory,
    ServiceTypeFactory,
    ServiceBrandFactory,
)

@skipIf(not settings.STRIPE_SECRET_KEY, "Stripe API key not configured in settings")
@override_settings(ADMIN_EMAIL='admin@example.com')
class TestAnonymousDepositPaymentFlow(TestCase):

    def setUp(self):
        self.client = Client()
        SiteSettings.objects.create(enable_service_booking=True)
        self.deposit_amount = Decimal('50.00')
        self.service_settings = ServiceSettingsFactory(
            enable_service_booking=True,
            allow_anonymous_bookings=True,
            enable_deposit=True, # Enable deposits
            enable_online_deposit=True, # Enable online deposits
            deposit_calc_method='FLAT_FEE', # Use a flat fee for the deposit
            deposit_flat_fee_amount=self.deposit_amount,
            booking_advance_notice=1,
            drop_off_start_time=datetime.time(9, 0),
            drop_off_end_time=datetime.time(17, 0),
            booking_open_days="Mon,Tue,Wed,Thu,Fri,Sat,Sun",
            currency_code='AUD'
        )
        self.service_type = ServiceTypeFactory(
            name='Deposit Service',
            base_price=Decimal('500.00'),
            is_active=True
        )
        ServiceBrandFactory(name='Suzuki')
        stripe.api_key = settings.STRIPE_SECRET_KEY

    def test_anonymous_user_deposit_payment_flow(self):
        # Define URLs for the booking flow
        step1_url = reverse('service:service_book_step1')
        step3_url = reverse('service:service_book_step3')
        step4_url = reverse('service:service_book_step4')
        step5_url = reverse('service:service_book_step5')
        step6_url = reverse('service:service_book_step6')
        step7_url = reverse('service:service_book_step7')

        valid_future_date = timezone.now().date() + datetime.timedelta(days=self.service_settings.booking_advance_notice + 5)
        
        # Go through the booking steps
        self.client.post(step1_url, {'service_type': self.service_type.id, 'service_date': valid_future_date.strftime('%Y-%m-%d')}, follow=True)
        
        self.client.post(step3_url, {
            'brand': 'Suzuki', 'model': 'Hayabusa', 'year': '2022', 'engine_size': '1340cc',
            'rego': 'DEPO1', 'odometer': 3000, 'transmission': 'MANUAL',
        })

        self.client.post(step4_url, {
            'name': 'Anon Deposit Payer', 'email': 'anondeposit.payer@example.com', 'phone_number': '0444555666',
            'address_line_1': '789 Deposit Dr', 'city': 'Bankstown', 'state': 'NSW', 'post_code': '2200', 'country': 'AU',
        })

        # In Step 5, select 'online_deposit' as the payment method
        response = self.client.post(step5_url, {
            'dropoff_date': valid_future_date.strftime('%Y-%m-%d'), 'dropoff_time': '09:30',
            'payment_method': 'online_deposit', 'service_terms_accepted': 'on',
        })
        self.assertRedirects(response, step6_url)

        # Load the payment page to create the Stripe PaymentIntent
        self.client.get(step6_url)
        self.assertEqual(Payment.objects.count(), 1)
        payment_obj = Payment.objects.first()
        payment_intent_id = payment_obj.stripe_payment_intent_id
        # The amount to pay should be the deposit amount, not the full service price
        self.assertEqual(payment_obj.amount, self.deposit_amount)

        # Simulate a successful payment via the Stripe API
        try:
            confirmation_url_path = reverse('service:service_book_step7')
            full_return_url = f"http://testserver{confirmation_url_path}"
            stripe.PaymentIntent.confirm(
                payment_intent_id,
                payment_method="pm_card_visa",
                return_url=full_return_url
            )
        except stripe.error.StripeError as e:
            self.fail(f"Stripe API call failed during test: {e}")

        # Simulate the webhook call
        updated_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        handle_service_booking_succeeded(payment_obj, updated_intent)

        # Assert that the final booking reflects a deposit payment
        self.assertEqual(ServiceBooking.objects.count(), 1)
        self.assertEqual(TempServiceBooking.objects.count(), 0)
        final_booking = ServiceBooking.objects.first()
        self.assertEqual(final_booking.payment_status, 'deposit_paid')
        self.assertEqual(final_booking.amount_paid, self.deposit_amount)
        self.assertEqual(final_booking.calculated_total, self.service_type.base_price)

        # Check the confirmation page
        confirmation_url_with_param = f"{step7_url}?payment_intent_id={payment_intent_id}"
        confirmation_response = self.client.get(confirmation_url_with_param)
        self.assertEqual(confirmation_response.status_code, 200)
        self.assertContains(confirmation_response, final_booking.service_booking_reference)
        self.assertIn('last_booking_successful_timestamp', self.client.session)
