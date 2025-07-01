import datetime
from decimal import Decimal

from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone

from service.models import TempServiceBooking, ServiceBooking, CustomerMotorcycle, ServiceProfile, ServiceBrand
from dashboard.models import SiteSettings
from ..test_helpers.model_factories import (
    ServiceSettingsFactory,
    ServiceTypeFactory,
    ServiceBrandFactory,
)

@override_settings(ADMIN_EMAIL='admin@example.com')
class TestAnonymousInStorePaymentFlow(TestCase):

    def setUp(self):
        """
        Set up the necessary objects for the test case.
        This includes creating site settings, service settings, a service type,
        and a service brand. It also initializes the test client.
        """
        self.client = Client()
        SiteSettings.objects.create(enable_service_booking=True)
        self.service_settings = ServiceSettingsFactory(
            enable_service_booking=True,
            allow_anonymous_bookings=True,
            allow_account_bookings=True,
            enable_instore_full_payment=True,
            booking_advance_notice=1,
            drop_off_start_time=datetime.time(9, 0),
            drop_off_end_time=datetime.time(17, 0),
            booking_open_days="Mon,Tue,Wed,Thu,Fri,Sat,Sun"
        )
        self.service_type = ServiceTypeFactory(
            name='Anonymous Basic Service',
            base_price=Decimal('150.00'),
            is_active=True
        )
        ServiceBrandFactory(name='Honda')

    def test_anonymous_user_in_store_payment_flow(self):
        """
        Test the complete booking flow for an anonymous user who chooses
        to pay the full amount in-store.
        """
        # Define URLs for each step in the booking process
        step1_url = reverse('service:service_book_step1')
        step3_url = reverse('service:service_book_step3')
        step4_url = reverse('service:service_book_step4')
        step5_url = reverse('service:service_book_step5')
        step7_url = reverse('service:service_book_step7')

        # Calculate a valid future date for the service booking
        valid_future_date = timezone.now().date() + datetime.timedelta(days=self.service_settings.booking_advance_notice + 5)
        
        # Step 1: Post service type and date.
        # For an anonymous user, this should redirect to Step 3 (add motorcycle).
        step1_data = {
            'service_type': self.service_type.id,
            'service_date': valid_future_date.strftime('%Y-%m-%d'),
        }
        response = self.client.post(step1_url, step1_data, follow=True)
        self.assertRedirects(response, step3_url + f'?temp_booking_uuid={self.client.session["temp_service_booking_uuid"]}')
        
        # Step 3: Post new motorcycle details.
        motorcycle_data = {
            'brand': 'Honda', 'model': 'CBR500R', 'year': '2022', 
            'engine_size': '471cc', 'rego': 'ANONR1', 'odometer': 1500, 
            'transmission': 'MANUAL', 'vin_number': '98765432109876543',
        }
        response = self.client.post(step3_url, motorcycle_data)
        self.assertRedirects(response, step4_url)

        # Step 4: Post new user profile details.
        profile_data = {
            'name': 'Anonymous In-Store User', 'email': 'anon.instore@user.com', 'phone_number': '0487654321',
            'address_line_1': '456 Anon St', 'address_line_2': '',
            'city': 'Melbourne', 'state': 'VIC', 'post_code': '3000',
            'country': 'AU',
        }
        response = self.client.post(step4_url, profile_data)
        self.assertRedirects(response, step5_url)

        # Verify that the temporary booking has the correct profile and motorcycle data
        temp_booking = TempServiceBooking.objects.get(session_uuid=self.client.session['temp_service_booking_uuid'])
        self.assertEqual(temp_booking.service_profile.email, profile_data['email'])
        self.assertEqual(temp_booking.customer_motorcycle.rego, motorcycle_data['rego'])

        # Step 5: Post drop-off details and select in-store payment.
        # This should finalize the booking and redirect to the confirmation page (Step 7).
        step5_data = {
            'dropoff_date': valid_future_date.strftime('%Y-%m-%d'),
            'dropoff_time': '10:00',
            'payment_method': 'in_store_full',
            'service_terms_accepted': 'on',
        }
        response = self.client.post(step5_url, step5_data)
        self.assertRedirects(response, step7_url)

        # Final Verification
        # Check that a final ServiceBooking has been created and the temp one is gone.
        self.assertEqual(ServiceBooking.objects.count(), 1)
        self.assertEqual(TempServiceBooking.objects.count(), 0)

        # Go to the confirmation page and check its content.
        confirmation_response = self.client.get(step7_url)
        self.assertEqual(confirmation_response.status_code, 200)

        # Verify the details of the finalized booking.
        final_booking = ServiceBooking.objects.first()
        self.assertEqual(final_booking.payment_status, 'unpaid')
        self.assertEqual(final_booking.amount_paid, Decimal('0.00'))
        self.assertEqual(final_booking.calculated_total, self.service_type.base_price)
        self.assertEqual(final_booking.service_profile.email, profile_data['email'])
        self.assertEqual(final_booking.customer_motorcycle.rego, motorcycle_data['rego'])
        self.assertContains(confirmation_response, final_booking.service_booking_reference)
        
        # Check that the session flag for a recent successful booking has been set.
        self.assertIn('last_booking_successful_timestamp', self.client.session)
