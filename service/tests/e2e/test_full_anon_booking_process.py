import datetime
from decimal import Decimal
from unittest import skipIf

from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.conf import settings
from django.utils import timezone

from service.models import TempServiceBooking, ServiceBooking, CustomerMotorcycle, ServiceProfile
from dashboard.models import SiteSettings
# Corrected import path as per your project structure
from ..test_helpers.model_factories import (
    ServiceSettingsFactory,
    ServiceTypeFactory,
)

@override_settings(ADMIN_EMAIL='admin@example.com')
class TestAnonymousInStorePaymentFlow(TestCase):
    """
    Test suite for the complete, end-to-end booking process for an anonymous user
    who chooses to pay in-store. This represents the most straightforward booking path.
    """

    def setUp(self):
        """
        Set up the necessary objects for the test case before each test runs.
        This includes creating an anonymous client, default service settings,
        and a basic service type.
        """
        self.client = Client()
        
        SiteSettings.objects.create(enable_service_booking=True)
        self.service_settings = ServiceSettingsFactory(
            enable_service_booking=True,
            allow_anonymous_bookings=True,
            enable_instore_full_payment=True,
            booking_advance_notice=1,
            drop_off_start_time=datetime.time(9, 0),
            drop_off_end_time=datetime.time(17, 0),
            booking_open_days="Mon,Tue,Wed,Thu,Fri,Sat,Sun"
        )
        
        self.service_type = ServiceTypeFactory(
            name='Standard Oil Change',
            base_price=Decimal('150.00'),
            is_active=True
        )

    def test_anonymous_user_full_booking_flow_with_in_store_payment(self):
        """
        This single test method simulates the entire booking journey for an anonymous user.
        It follows the user from the first step to the final confirmation page.
        
        Flow:
        1. Select Service Details (Service Type & Date)
        2. Add a new Motorcycle
        3. Provide Personal Contact Details
        4. Select Drop-off Time and In-Store Payment
        5. View the final Confirmation page
        """
        
        # --- Step 1: Select Service and Date ---
        step1_url = reverse('service:service_book_step1')
        # The URL for an anonymous user to add a new bike is step 3
        step3_url = reverse('service:service_book_step3')
        step4_url = reverse('service:service_book_step4')
        step5_url = reverse('service:service_book_step5')
        step7_url = reverse('service:service_book_step7')

        # To ensure the date is always valid, we calculate it relative to the current day
        # It must be after the 'booking_advance_notice' period
        valid_future_date = timezone.now().date() + datetime.timedelta(days=self.service_settings.booking_advance_notice + 5)
        
        step1_data = {
            'service_type': self.service_type.id,
            'service_date': valid_future_date.strftime('%Y-%m-%d'),
        }
        # We add 'follow=True' to automatically follow the first redirect
        response = self.client.post(step1_url, step1_data, follow=True)
        
        self.assertRedirects(response, step3_url + f'?temp_booking_uuid={self.client.session["temp_service_booking_uuid"]}')
        self.assertIn('temp_service_booking_uuid', self.client.session)
        self.assertEqual(TempServiceBooking.objects.count(), 1)
        temp_booking = TempServiceBooking.objects.first()
        self.assertEqual(temp_booking.service_type, self.service_type)

        # --- Step 3: Add Motorcycle Details ---
        step3_data = {
            'brand': 'Honda',
            'model': 'CBR1000RR',
            'year': '2022',
            'engine_size': '1000cc',
            'rego': 'TEST1',
            'transmission': 'Manual', # FIX: Added likely required 'transmission' field
        }
        response = self.client.post(step3_url, step3_data)
        
        # This assertion should now pass
        self.assertRedirects(response, step4_url)
        self.assertEqual(CustomerMotorcycle.objects.count(), 1)
        motorcycle = CustomerMotorcycle.objects.first()
        self.assertEqual(motorcycle.brand, 'Honda')
        temp_booking.refresh_from_db()
        self.assertEqual(temp_booking.customer_motorcycle, motorcycle)

        # --- Step 4: Add Service Profile (Personal Details) ---
        step4_data = {
            'name': 'Anonymous User',
            'email': 'anon.user@example.com',
            'phone_number': '0412345678',
            'address_line_1': '123 Test St',
            'city': 'Testville',
            'state': 'TS',
            'post_code': '1234',
        }
        response = self.client.post(step4_url, step4_data)
        
        self.assertRedirects(response, step5_url)
        self.assertEqual(ServiceProfile.objects.count(), 1)
        profile = ServiceProfile.objects.first()
        self.assertEqual(profile.email, 'anon.user@example.com')
        temp_booking.refresh_from_db()
        self.assertEqual(temp_booking.service_profile, profile)
        self.assertIsNone(profile.user)

        # --- Step 5: Choose Payment, Drop-off, and Accept Terms ---
        step5_data = {
            'dropoff_date': valid_future_date.strftime('%Y-%m-%d'),
            'dropoff_time': '10:00',
            'payment_method': 'in_store_full',
            'terms_accepted': 'on',
        }
        response = self.client.post(step5_url, step5_data)
        
        self.assertRedirects(response, step7_url)
        self.assertEqual(ServiceBooking.objects.count(), 1)
        self.assertEqual(TempServiceBooking.objects.count(), 0)
        self.assertIn('service_booking_reference', self.client.session)
        
        # --- Step 7: Confirmation Page ---
        final_booking = ServiceBooking.objects.first()
        confirmation_response = self.client.get(response.url)
        
        self.assertEqual(confirmation_response.status_code, 200)
        self.assertContains(confirmation_response, final_booking.service_booking_reference)
        self.assertEqual(final_booking.payment_status, 'unpaid')
        self.assertEqual(final_booking.payment_method, 'in_store_full')
        self.assertEqual(final_booking.service_profile.name, 'Anonymous User')
        self.assertEqual(final_booking.customer_motorcycle.model, 'CBR1000RR')
        self.assertIn('last_booking_timestamp', self.client.session)
        self.assertNotIn('temp_service_booking_uuid', self.client.session)
