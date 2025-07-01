import datetime
from decimal import Decimal
import stripe
from unittest import skipIf

from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.conf import settings
from django.utils import timezone

from service.models import TempServiceBooking, ServiceBooking, CustomerMotorcycle, ServiceProfile, ServiceBrand
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
class TestAnonymousFullOnlinePaymentFlow(TestCase):

    def setUp(self):
        """
        Set up the necessary objects for the test case.
        This includes creating site settings, service settings for anonymous online payments,
        a service type, a service brand, and initializing the Stripe API.
        """
        self.client = Client()
        SiteSettings.objects.create(enable_service_booking=True)
        self.service_settings = ServiceSettingsFactory(
            enable_service_booking=True,
            allow_anonymous_bookings=True,
            enable_online_full_payment=True,
            booking_advance_notice=1,
            drop_off_start_time=datetime.time(9, 0),
            drop_off_end_time=datetime.time(17, 0),
            booking_open_days="Mon,Tue,Wed,Thu,Fri,Sat,Sun",
            currency_code='AUD'
        )
        self.service_type = ServiceTypeFactory(
            name='Anonymous Online Special',
            base_price=Decimal('350.00'),
            is_active=True
        )
        ServiceBrandFactory(name='Yamaha')
        stripe.api_key = settings.STRIPE_SECRET_KEY

    def test_anonymous_user_full_online_payment_flow(self):
        """
        Test the complete booking and payment flow for an anonymous user
        who chooses to pay the full amount online using Stripe.
        """
        # Define URLs for each step in the booking process
        step1_url = reverse('service:service_book_step1')
        step3_url = reverse('service:service_book_step3')
        step4_url = reverse('service:service_book_step4')
        step5_url = reverse('service:service_book_step5')
        step6_url = reverse('service:service_book_step6')
        step7_url = reverse('service:service_book_step7')

        # Calculate a valid future date for the service booking
        valid_future_date = timezone.now().date() + datetime.timedelta(days=self.service_settings.booking_advance_notice + 5)
        
        # Step 1: Select service and date
        self.client.post(step1_url, {'service_type': self.service_type.id, 'service_date': valid_future_date.strftime('%Y-%m-%d')}, follow=True)
        
        # Step 3: Enter motorcycle details
        motorcycle_data = {
            'brand': 'Yamaha', 'model': 'MT-07', 'year': '2020', 
            'engine_size': '689cc', 'rego': 'ANONONL', 'odometer': 8000, 
            'transmission': 'MANUAL', 'vin_number': 'VINANONONLINE1234', # FIX: Changed to 17 characters
        }
        response = self.client.post(step3_url, motorcycle_data)
        self.assertRedirects(response, step4_url, msg_prefix="Redirect from Step 3 to 4 failed, the motorcycle form is likely invalid.")


        # Step 4: Enter personal details
        profile_data = {
            'name': 'Anon Online User', 'email': 'anon.online@user.com', 'phone_number': '0411223344',
            'address_line_1': '789 Online Ave', 'address_line_2': '',
            'city': 'Perth', 'state': 'WA', 'post_code': '6000',
            'country': 'AU',
        }
        response = self.client.post(step4_url, profile_data)
        self.assertRedirects(response, step5_url)

        # Step 5: Select online payment method
        response = self.client.post(step5_url, {
            'dropoff_date': valid_future_date.strftime('%Y-%m-%d'), 'dropoff_time': '14:00',
            'payment_method': 'online_full', 'service_terms_accepted': 'on',
        })
        self.assertRedirects(response, step6_url)

        # Step 6: Load payment page, which creates the Stripe PaymentIntent
        self.client.get(step6_url)
        self.assertEqual(Payment.objects.count(), 1)
        payment_obj = Payment.objects.first()
        payment_intent_id = payment_obj.stripe_payment_intent_id
        self.assertEqual(payment_obj.amount, self.service_type.base_price)

        # Simulate a successful payment confirmation via the Stripe API
        try:
            confirmation_url_path = reverse('service:service_book_step7')
            full_return_url = f"http://testserver{confirmation_url_path}"
            stripe.PaymentIntent.confirm(
                payment_intent_id,
                payment_method="pm_card_visa", # Use a test card
                return_url=full_return_url
            )
        except stripe.error.StripeError as e:
            self.fail(f"Stripe API call failed during test: {e}")

        # Simulate the webhook by calling the handler directly with the updated intent
        updated_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        handle_service_booking_succeeded(payment_obj, updated_intent)

        # Final Assertions
        # Check that the booking was finalized correctly
        self.assertEqual(ServiceBooking.objects.count(), 1)
        self.assertEqual(TempServiceBooking.objects.count(), 0)
        
        final_booking = ServiceBooking.objects.first()
        self.assertEqual(final_booking.payment_status, 'paid')
        self.assertEqual(final_booking.amount_paid, self.service_type.base_price)
        self.assertEqual(final_booking.service_profile.email, profile_data['email'])
        self.assertEqual(final_booking.customer_motorcycle.rego, motorcycle_data['rego'])

        # Check the confirmation page
        confirmation_url_with_param = f"{step7_url}?payment_intent_id={payment_intent_id}"
        confirmation_response = self.client.get(confirmation_url_with_param)
        self.assertEqual(confirmation_response.status_code, 200)
        self.assertContains(confirmation_response, final_booking.service_booking_reference)
        
        # Check that the session flag for a recent successful booking is set
        self.assertIn('last_booking_successful_timestamp', self.client.session)
