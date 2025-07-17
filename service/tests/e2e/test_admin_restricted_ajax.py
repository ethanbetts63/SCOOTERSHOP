from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
import json
import datetime
from unittest.mock import patch
from users.tests.test_helpers.model_factories import UserFactory, StaffUserFactory
from service.tests.test_helpers.model_factories import ServiceBookingFactory, ServiceProfileFactory, ServiceTypeFactory, ServiceSettingsFactory, ServiceTermsFactory, ServicefaqFactory, CustomerMotorcycleFactory
from inventory.tests.test_helpers.model_factories import SalesBookingFactory, SalesProfileFactory
from payments.tests.test_helpers.model_factories import PaymentFactory, WebhookEventFactory
from refunds.tests.test_helpers.model_factories import RefundRequestFactory, RefundSettingsFactory

User = get_user_model()

@override_settings(MOCK_PAYMENT=True)
class ServiceAdminAjaxPermissionsTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.regular_user = UserFactory(password="password123")
        cls.staff_user = StaffUserFactory()
        cls.service_profile = ServiceProfileFactory()
        cls.customer_motorcycle = CustomerMotorcycleFactory(service_profile=cls.service_profile)
        cls.service_type = ServiceTypeFactory()
        cls.service_booking = ServiceBookingFactory(
            service_profile=cls.service_profile,
            customer_motorcycle=cls.customer_motorcycle,
            service_type=cls.service_type
        )
        ServiceSettingsFactory(drop_off_start_time=datetime.time(9, 0), drop_off_end_time=datetime.time(17, 0), drop_off_spacing_mins=30)

    def _test_ajax_permissions(self, url_name, kwargs=None, method='get', data=None):
        if data is None:
            data = {}
        url = reverse(url_name, kwargs=kwargs)
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
        self.assertIn(response_staff.status_code, [200, 400], f"URL {url} did not return 200 or 400 for staff user.")
        self.client.logout()

    @patch('service.ajax.ajax_get_service_booking_details.calculate_service_refund_amount')
    def test_admin_ajax_endpoints_permissions(self, mock_refund_calc):
        mock_refund_calc.return_value = {
            'entitled_amount': 0,
            'details': 'mocked',
            'policy_applied': 'mocked',
            'days_before_dropoff': 0
        }

        # URLs that don't require kwargs
        self._test_ajax_permissions("service:admin_api_search_customer", data={'query': 'test'})
        self._test_ajax_permissions("service:get_service_bookings_json")
        self._test_ajax_permissions("service:admin_api_search_bookings", data={'query': 'test'})
        
        # URLs that require kwargs
        self._test_ajax_permissions("service:admin_api_get_service_booking_details", kwargs={'pk': self.service_booking.pk})

        # Special case for booking precheck
        self._test_ajax_permissions(
            "service:admin_api_booking_precheck",
            method='post',
            data={
                'service_type': self.service_type.pk,
                'service_date': '2025-01-01',
                'dropoff_time': '09:00'
            }
        )

        # Special case for estimated pickup date
        self._test_ajax_permissions(
            "service:admin_api_get_estimated_pickup_date",
            data={
                'service_type_id': self.service_type.pk,
                'service_date': '2025-01-01'
            }
        )
