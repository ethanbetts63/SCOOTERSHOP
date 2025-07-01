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
    UserFactory,
    ServiceProfileFactory,
    CustomerMotorcycleFactory,
)

@skipIf(not settings.STRIPE_SECRET_KEY, "Stripe API key not configured in settings")
@override_settings(ADMIN_EMAIL='admin@example.com')
class TestLoggedInOnlinePaymentFlow(TestCase):

    def setUp(self):
        self.client = Client()
        SiteSettings.objects.create(enable_service_booking=True)
        self.service_settings = ServiceSettingsFactory(
            enable_service_booking=True,
            allow_account_bookings=True,
            enable_online_full_payment=True,
            booking_advance_notice=1,
            drop_off_start_time=datetime.time(9, 0),
            drop_off_end_time=datetime.time(17, 0),
            booking_open_days="Mon,Tue,Wed,Thu,Fri,Sat,Sun",
            currency_code='AUD'
        )
        self.service_type = ServiceTypeFactory(
            name='Premium Online Service',
            base_price=Decimal('450.00'),
            is_active=True
        )
        # Create a user, profile, and motorcycle for the test
        self.user = UserFactory(username='onlineuser')
        self.service_profile = ServiceProfileFactory(user=self.user, name='Online Test User', email='online.test@user.com', country='AU')
        self.motorcycle = CustomerMotorcycleFactory(service_profile=self.service_profile, brand='Ducati', model='Monster')
        # Ensure the brand exists for form validation
        ServiceBrandFactory(name='Ducati')
        # Log the user in for the test
        self.client.force_login(self.user)
        stripe.api_key = settings.STRIPE_SECRET_KEY

    def test_logged_in_user_online_payment_flow(self):
        # Define URLs for the booking flow
        step1_url = reverse('service:service_book_step1')
        step2_url = reverse('service:service_book_step2')
        step4_url = reverse('service:service_book_step4')
        step5_url = reverse('service:service_book_step5')
        step6_url = reverse('service:service_book_step6')
        step7_url = reverse('service:service_book_step7')

        valid_future_date = timezone.now().date() + datetime.timedelta(days=self.service_settings.booking_advance_notice + 5)
        
        # Step 1: Select service and date
        self.client.post(step1_url, {'service_type': self.service_type.id, 'service_date': valid_future_date.strftime('%Y-%m-%d')}, follow=True)
        
        # Step 2: Select the existing motorcycle
        self.client.post(step2_url, {'selected_motorcycle': self.motorcycle.id})

        # Step 4: Confirm personal details
        self.client.post(step4_url, {
            'name': self.service_profile.name, 'email': self.service_profile.email, 'phone_number': self.service_profile.phone_number,
            'address_line_1': self.service_profile.address_line_1, 'address_line_2': self.service_profile.address_line_2,
            'city': self.service_profile.city, 'state': self.service_profile.state, 'post_code': self.service_profile.post_code,
            'country': self.service_profile.country,
        })

        # Step 5: Select online payment method
        response = self.client.post(step5_url, {
            'dropoff_date': valid_future_date.strftime('%Y-%m-%d'), 'dropoff_time': '14:30',
            'payment_method': 'online_full', 'service_terms_accepted': 'on',
        })
        self.assertRedirects(response, step6_url)

        # Step 6: Load payment page to create the Stripe PaymentIntent
        self.client.get(step6_url)
        self.assertEqual(Payment.objects.count(), 1)
        payment_obj = Payment.objects.first()
        payment_intent_id = payment_obj.stripe_payment_intent_id

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

        # Simulate the webhook by calling the handler directly
        updated_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        handle_service_booking_succeeded(payment_obj, updated_intent)

        # Assert that the booking was finalized correctly
        self.assertEqual(ServiceBooking.objects.count(), 1)
        self.assertEqual(TempServiceBooking.objects.count(), 0)
        final_booking = ServiceBooking.objects.first()
        self.assertEqual(final_booking.payment_status, 'paid')
        self.assertEqual(final_booking.amount_paid, self.service_type.base_price)
        self.assertEqual(final_booking.service_profile, self.service_profile)
        self.assertEqual(final_booking.customer_motorcycle, self.motorcycle)

        # Check the confirmation page
        confirmation_url_with_param = f"{step7_url}?payment_intent_id={payment_intent_id}"
        confirmation_response = self.client.get(confirmation_url_with_param)
        self.assertEqual(confirmation_response.status_code, 200)
        self.assertContains(confirmation_response, final_booking.service_booking_reference)
        self.assertIn('last_booking_successful_timestamp', self.client.session)
