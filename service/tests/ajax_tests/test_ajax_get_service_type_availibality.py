from django.test import TestCase
from django.urls import reverse
from service.tests.test_helpers.model_factories import ServiceTypeFactory, ServiceSettingsFactory, ServiceBookingFactory
from service.models import ServiceBooking
import datetime
import json

class AjaxGetServiceTypeAvailabilityTest(TestCase):
    def setUp(self):
        self.service_settings = ServiceSettingsFactory(daily_service_slots=5)
        self.service_type_small = ServiceTypeFactory(slots_required=1)
        self.service_type_large = ServiceTypeFactory(slots_required=3)
        self.url = reverse('service:get_service_type_availability')

    def test_get_availability_for_small_service_type(self):
        # Book 3 small services, leaving 2 slots
        for _ in range(3):
            ServiceBookingFactory(
                service_type=self.service_type_small,
                dropoff_date=datetime.date.today() + datetime.timedelta(days=7),
                booking_status="confirmed"
            )
        
        response = self.client.get(self.url, {'service_type_id': self.service_type_small.pk})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        disabled_dates = json.loads(data['disabled_dates'])
        
        # The date should still be available for small service (3/5 slots used)
        self.assertNotIn(str(datetime.date.today() + datetime.timedelta(days=7)), disabled_dates)

        # Book 2 more small services, filling all slots
        for _ in range(2):
            ServiceBookingFactory(
                service_type=self.service_type_small,
                dropoff_date=datetime.date.today() + datetime.timedelta(days=7),
                booking_status="confirmed"
            )
        
        response = self.client.get(self.url, {'service_type_id': self.service_type_small.pk})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        disabled_dates = json.loads(data['disabled_dates'])
        
        # Now the date should be disabled for small service (5/5 slots used)
        self.assertIn(str(datetime.date.today() + datetime.timedelta(days=7)), disabled_dates)

    def test_get_availability_for_large_service_type(self):
        # Book 1 large service, leaving 2 slots
        ServiceBookingFactory(
            service_type=self.service_type_large,
            dropoff_date=datetime.date.today() + datetime.timedelta(days=7),
            booking_status="confirmed"
        )
        
        response = self.client.get(self.url, {'service_type_id': self.service_type_large.pk})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        disabled_dates = json.loads(data['disabled_dates'])
        
        # The date should be disabled for large service (3/5 slots used, but large needs 3, so 3+3 > 5)
        self.assertIn(str(datetime.date.today() + datetime.timedelta(days=7)), disabled_dates)

    def test_get_availability_with_mixed_services(self):
        # Book 2 small services (2 slots used)
        for _ in range(2):
            ServiceBookingFactory(
                service_type=self.service_type_small,
                dropoff_date=datetime.date.today() + datetime.timedelta(days=7),
                booking_status="confirmed"
            )
        
        # Check availability for a large service (2 used, large needs 3, 2+3 = 5, so it should be available)
        response = self.client.get(self.url, {'service_type_id': self.service_type_large.pk})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        disabled_dates = json.loads(data['disabled_dates'])
        self.assertNotIn(str(datetime.date.today() + datetime.timedelta(days=7)), disabled_dates)

        # Book one more small service (3 slots used)
        ServiceBookingFactory(
            service_type=self.service_type_small,
            dropoff_date=datetime.date.today() + datetime.timedelta(days=7),
            booking_status="confirmed"
        )

        # Now check availability for a large service (3 used, large needs 3, 3+3 > 5, so it should be disabled)
        response = self.client.get(self.url, {'service_type_id': self.service_type_large.pk})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        disabled_dates = json.loads(data['disabled_dates'])
        self.assertIn(str(datetime.date.today() + datetime.timedelta(days=7)), disabled_dates)

    def test_no_service_type_id_provided(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 500) # Or appropriate error code/handling

    def test_invalid_service_type_id(self):
        response = self.client.get(self.url, {'service_type_id': 99999})
        self.assertEqual(response.status_code, 500) # Or appropriate error code/handling