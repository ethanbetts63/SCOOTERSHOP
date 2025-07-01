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
        ServiceBrandFactory(name='Honda')

    def test_anonymous_user_full_booking_flow_with_in_store_payment(self):
        step1_url = reverse('service:service_book_step1')
        step3_url = reverse('service:service_book_step3')
        step4_url = reverse('service:service_book_step4')
        step5_url = reverse('service:service_book_step5')
        step7_url = reverse('service:service_book_step7')

        valid_future_date = timezone.now().date() + datetime.timedelta(days=self.service_settings.booking_advance_notice + 5)
        
        step1_data = {
            'service_type': self.service_type.id,
            'service_date': valid_future_date.strftime('%Y-%m-%d'),
        }
        response = self.client.post(step1_url, step1_data, follow=True)
        
        self.assertRedirects(response, step3_url + f'?temp_booking_uuid={self.client.session["temp_service_booking_uuid"]}')
        self.assertIn('temp_service_booking_uuid', self.client.session)
        self.assertEqual(TempServiceBooking.objects.count(), 1)
        temp_booking = TempServiceBooking.objects.first()
        self.assertEqual(temp_booking.service_type, self.service_type)

        step3_data = {
            'brand': 'Honda',
            'model': 'CBR1000RR',
            'year': '2022',
            'engine_size': '1000cc',
            'rego': 'TEST1',
            'odometer': 5000,
            'transmission': 'MANUAL', 
        }
        response = self.client.post(step3_url, step3_data)
        
        self.assertRedirects(response, step4_url)
        self.assertEqual(CustomerMotorcycle.objects.count(), 1)
        motorcycle = CustomerMotorcycle.objects.first()
        self.assertEqual(motorcycle.brand, 'Honda')
        temp_booking.refresh_from_db()
        self.assertEqual(temp_booking.customer_motorcycle, motorcycle)

        step4_data = {
            'name': 'instore Anonymous User',
            'email': 'instoreanon.user@example.com',
            'phone_number': '0412345678',
            'address_line_1': '123 Test St',
            'city': 'Testville',
            'state': 'TS',
            'post_code': '1234',
            'country': 'AU',
        }
        response = self.client.post(step4_url, step4_data)
        
        self.assertRedirects(response, step5_url)
        self.assertEqual(ServiceProfile.objects.count(), 1)
        profile = ServiceProfile.objects.first()
        self.assertEqual(profile.email, 'anon.user@example.com')
        temp_booking.refresh_from_db()
        self.assertEqual(temp_booking.service_profile, profile)
        self.assertIsNone(profile.user)

        step5_data = {
            'dropoff_date': valid_future_date.strftime('%Y-%m-%d'),
            'dropoff_time': '10:00',
            'payment_method': 'in_store_full',
            'service_terms_accepted': 'on',
        }
        
        response = self.client.post(step5_url, step5_data)
        self.assertRedirects(response, step7_url)
        
        self.assertEqual(ServiceBooking.objects.count(), 1)
        self.assertEqual(TempServiceBooking.objects.count(), 0)
        self.assertIn('service_booking_reference', self.client.session)
        
        confirmation_response = self.client.get(step7_url)
        
        self.assertEqual(confirmation_response.status_code, 200)
        final_booking = ServiceBooking.objects.first()
        self.assertContains(confirmation_response, final_booking.service_booking_reference)
        self.assertEqual(final_booking.payment_status, 'unpaid')
        
        # FIX: Changed key to match the one being set in the view's debug logs.
        self.assertIn('last_booking_successful_timestamp', self.client.session)
        self.assertNotIn('temp_service_booking_uuid', self.client.session)
