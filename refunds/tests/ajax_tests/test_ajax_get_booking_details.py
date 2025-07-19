
import json
from django.test import TestCase, Client
from django.urls import reverse
from users.tests.test_helpers.model_factories import UserFactory
from service.tests.test_helpers.model_factories import ServiceBookingFactory
from inventory.tests.test_helpers.model_factories import SalesBookingFactory

class AjaxGetBookingDetailsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = UserFactory(is_staff=True, is_superuser=True)
        self.client.force_login(self.admin_user)

        self.service_booking = ServiceBookingFactory(payment__status='succeeded')
        self.sales_booking = SalesBookingFactory(payment__status='succeeded')

        self.url = reverse('refunds:ajax_get_booking_details_by_reference')

    def test_get_details_for_service_booking(self):
        response = self.client.get(self.url, {'booking_reference': self.service_booking.service_booking_reference})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['service_booking_reference'], self.service_booking.service_booking_reference)
        self.assertIn('entitled_refund_amount', data)
        self.assertIn('refund_calculation_details', data)

    def test_get_details_for_sales_booking(self):
        response = self.client.get(self.url, {'booking_reference': self.sales_booking.sales_booking_reference})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['sales_booking_reference'], self.sales_booking.sales_booking_reference)
        self.assertIn('entitled_refund_amount', data)
        self.assertIn('refund_calculation_details', data)

    def test_booking_not_found(self):
        response = self.client.get(self.url, {'booking_reference': 'SVC-NOT-FOUND'})
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.content)
        self.assertEqual(data['error'], 'Service booking not found.')

    def test_invalid_booking_reference_format(self):
        response = self.client.get(self.url, {'booking_reference': 'INVALID-REF'})
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertEqual(data['error'], 'Invalid booking reference format.')

    def test_missing_booking_reference(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertEqual(data['error'], 'Booking reference is required.')

    def test_unauthenticated_access(self):
        self.client.logout()
        response = self.client.get(self.url, {'booking_reference': self.service_booking.service_booking_reference})
        self.assertEqual(response.status_code, 401) # Should return 401 Unauthorized
