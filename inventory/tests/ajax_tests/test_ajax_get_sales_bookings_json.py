import json
from django.test import TestCase, RequestFactory
from django.urls import reverse
from inventory.ajax.ajax_get_sales_bookings_json import get_sales_bookings_json
from inventory.tests.test_helpers.model_factories import SalesBookingFactory, UserFactory

class GetSalesBookingsJsonTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.admin_user = UserFactory(is_staff=True)
        self.non_admin_user = UserFactory()
        self.booking1 = SalesBookingFactory(booking_status='confirmed')
        self.booking2 = SalesBookingFactory(booking_status='completed')
        self.booking3 = SalesBookingFactory(booking_status='pending')

    def test_get_sales_bookings_json_as_admin(self):
        request = self.factory.get(reverse('inventory:get_sales_bookings_json'))
        request.user = self.admin_user
        response = get_sales_bookings_json(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        # Extract titles from the response data for easier comparison
        returned_titles = [item['title'] for item in data]

        # Check if the expected bookings are present in the returned data
        self.assertIn(f"{self.booking1.sales_profile.name} - {self.booking1.motorcycle.title}", returned_titles)
        self.assertIn(f"{self.booking2.sales_profile.name} - {self.booking2.motorcycle.title}", returned_titles)
        self.assertEqual(len(data), 2)

    def test_get_sales_bookings_json_as_non_admin(self):
        request = self.factory.get(reverse('inventory:get_sales_bookings_json'))
        request.user = self.non_admin_user
        response = get_sales_bookings_json(request)
        self.assertEqual(response.status_code, 403)
        data = json.loads(response.content)
        self.assertEqual(data, {"status": "error", "message": "Admin access required."})