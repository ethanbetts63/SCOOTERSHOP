from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
import json

from service.tests.test_helpers.model_factories import (
    UserFactory,
    StaffUserFactory,
    ServiceProfileFactory,
    CustomerMotorcycleFactory,
    ServiceBookingFactory,
    ServiceTypeFactory,
)

User = get_user_model()

class ServiceAdminAjaxPermissionsTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.regular_user = UserFactory(password="password123")
        cls.staff_user = StaffUserFactory()

        # Create instances for URL kwargs
        cls.service_profile = ServiceProfileFactory()
        cls.customer_motorcycle = CustomerMotorcycleFactory(service_profile=cls.service_profile)
        cls.service_booking = ServiceBookingFactory(
            service_profile=cls.service_profile,
            customer_motorcycle=cls.customer_motorcycle,
            service_type=ServiceTypeFactory() # Ensure service_type is created
        )
        ServiceSettingsFactory() # Ensure ServiceSettings exists for tests

    def _test_ajax_permissions(self, url_name, kwargs=None, method='get', data=None):
        url = reverse(url_name, kwargs=kwargs)

        # Test anonymous user
        response_anon = self.client.generic(method.upper(), url, data)
        self.assertEqual(response_anon.status_code, 401, f"URL {url} did not return 401 for anonymous user.")
        self.assertEqual(json.loads(response_anon.content), {"status": "error", "message": "Authentication required."})

        # Test regular user
        self.client.login(username=self.regular_user.username, password="password123")
        response_regular = self.client.generic(method.upper(), url, data)
        self.assertEqual(response_regular.status_code, 403, f"URL {url} did not return 403 for regular user.")
        self.assertEqual(json.loads(response_regular.content), {"status": "error", "message": "Admin access required."})
        self.client.logout()

        # Test staff user
        self.client.login(username=self.staff_user.username, password="password123")
        response_staff = self.client.generic(method.upper(), url, data)
        self.assertEqual(response_staff.status_code, 200, f"URL {url} did not return 200 for staff user.")
        self.client.logout()

    def test_admin_ajax_endpoints_permissions(self):
        # URLs that don't require kwargs
        self._test_ajax_permissions("service:admin_api_search_customer")
        self._test_ajax_permissions("service:admin_api_service_date_availability")
        self._test_ajax_permissions("service:admin_api_dropoff_time_availability", data={'date': '2025-01-01'})
        self._test_ajax_permissions("service:admin_api_booking_precheck")
        self._test_ajax_permissions("service:get_service_bookings_json")
        self._test_ajax_permissions("service:admin_api_search_bookings")
        self._test_ajax_permissions("service:admin_api_get_estimated_pickup_date")

        # URLs that require kwargs
        self._test_ajax_permissions("service:admin_api_get_customer_details", kwargs={'profile_id': self.service_profile.pk})
        self._test_ajax_permissions("service:admin_api_customer_motorcycles", kwargs={'profile_id': self.service_profile.pk})
        self._test_ajax_permissions("service:admin_api_get_motorcycle_details", kwargs={'motorcycle_id': self.customer_motorcycle.pk})
        self._test_ajax_permissions("service:admin_api_get_service_booking_details", kwargs={'pk': self.service_booking.pk})
