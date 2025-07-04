from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from service.tests.test_helpers.model_factories import (
    UserFactory,
    StaffUserFactory,
    ServiceBookingFactory,
    ServiceSettingsFactory,
    BlockedServiceDateFactory,
    ServiceBrandFactory,
    ServiceTypeFactory,
    ServiceFAQFactory,
    ServiceProfileFactory,
    CustomerMotorcycleFactory,
)

User = get_user_model()

class ServiceAdminViewsPermissionsTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.login_url = reverse("users:login")

        # Create user types
        cls.regular_user = UserFactory(password="password123")
        cls.staff_user = StaffUserFactory()

        # Create instances of all necessary models for URL kwargs
        ServiceSettingsFactory() # Singleton, pk=1
        cls.service_profile = ServiceProfileFactory()
        cls.customer_motorcycle = CustomerMotorcycleFactory(service_profile=cls.service_profile)
        cls.service_booking = ServiceBookingFactory(
            service_profile=cls.service_profile,
            customer_motorcycle=cls.customer_motorcycle
        )
        cls.blocked_date = BlockedServiceDateFactory()
        cls.service_brand = ServiceBrandFactory()
        cls.service_type = ServiceTypeFactory()
        cls.faq = ServiceFAQFactory()

    def _test_url_permissions(self, url_name, kwargs=None, method='get', data=None):
        url = reverse(url_name, kwargs=kwargs)
        success_status = 302 if method == 'post' else 200

        # Test anonymous user
        response_anon = self.client.generic(method.upper(), url, data)
        self.assertEqual(response_anon.status_code, 302, f"URL {url} did not redirect anonymous user.")
        self.assertIn(self.login_url, response_anon.url)

        # Test regular user
        self.client.login(username=self.regular_user.username, password="password123")
        response_regular = self.client.generic(method.upper(), url, data)
        self.assertEqual(response_regular.status_code, 302, f"URL {url} did not redirect regular user.")
        self.client.logout()

        # Test staff user
        self.client.login(username=self.staff_user.username, password="password123")
        response_staff = self.client.generic(method.upper(), url, data)
        self.assertEqual(response_staff.status_code, success_status, f"URL {url} returned {response_staff.status_code} for staff user, expected {success_status}.")
        self.client.logout()

    def test_service_booking_crud_permissions(self):
        self._test_url_permissions("service:service_booking_management")
        self._test_url_permissions("service:admin_service_booking_detail", kwargs={'pk': self.service_booking.pk})
        self._test_url_permissions("service:admin_create_service_booking")
        self._test_url_permissions("service:admin_edit_service_booking", kwargs={'pk': self.service_booking.pk})
        self._test_url_permissions("service:admin_delete_service_booking", kwargs={'pk': self.service_booking.pk}, method='post')

    def test_settings_and_blocked_dates_permissions(self):
        self._test_url_permissions("service:service_settings")
        self._test_url_permissions("service:blocked_service_dates_management")
        self._test_url_permissions("service:delete_blocked_service_date", kwargs={'pk': self.blocked_date.pk}, method='post')

    def test_service_brand_crud_permissions(self):
        self._test_url_permissions("service:service_brands_management")
        self._test_url_permissions("service:delete_service_brand", kwargs={'pk': self.service_brand.pk}, method='post')

    def test_service_type_crud_permissions(self):
        self._test_url_permissions("service:service_types_management")
        self._test_url_permissions("service:add_service_type")
        self._test_url_permissions("service:edit_service_type", kwargs={'pk': self.service_type.pk})
        self._test_url_permissions("service:delete_service_type", kwargs={'pk': self.service_type.pk}, method='post')

    def test_service_faq_crud_permissions(self):
        self._test_url_permissions("service:service_faq_management")
        self._test_url_permissions("service:service_faq_create")
        self._test_url_permissions("service:service_faq_update", kwargs={'pk': self.faq.pk})
        self._test_url_permissions("service:service_faq_delete", kwargs={'pk': self.faq.pk}, method='post')

    def test_service_profile_crud_permissions(self):
        self._test_url_permissions("service:admin_service_profiles")
        self._test_url_permissions("service:admin_create_service_profile")
        self._test_url_permissions("service:admin_edit_service_profile", kwargs={'pk': self.service_profile.pk})
        self._test_url_permissions("service:admin_delete_service_profile", kwargs={'pk': self.service_profile.pk}, method='post')

    def test_customer_motorcycle_crud_permissions(self):
        self._test_url_permissions("service:admin_customer_motorcycle_management")
        self._test_url_permissions("service:admin_create_customer_motorcycle")
        self._test_url_permissions("service:admin_edit_customer_motorcycle", kwargs={'pk': self.customer_motorcycle.pk})
        self._test_url_permissions("service:admin_delete_customer_motorcycle", kwargs={'pk': self.customer_motorcycle.pk}, method='post')

