from django.test import TestCase, Client
from django.urls import reverse
from service.tests.test_helpers.model_factories import (
    UserFactory,
    ServiceBookingFactory,
    BlockedServiceDateFactory,
    ServiceBrandFactory,
    ServiceTypeFactory,
    ServiceFAQFactory,
    ServiceProfileFactory,
    CustomerMotorcycleFactory,
)

class AdminViewsAccessTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.regular_user = UserFactory(username="testuser", password="testpassword")
        self.admin_user = UserFactory(
            username="adminuser", password="testpassword", is_staff=True
        )

        # Create instances for detail/delete views
        self.service_booking = ServiceBookingFactory()
        self.blocked_date = BlockedServiceDateFactory()
        self.service_brand = ServiceBrandFactory()
        self.service_type = ServiceTypeFactory()
        self.service_faq = ServiceFAQFactory()
        self.service_profile = ServiceProfileFactory()
        self.customer_motorcycle = CustomerMotorcycleFactory()

        all_urls = [
            ("service:service_booking_management", {}),
            ("service:admin_service_booking_detail", {"pk": self.service_booking.pk}),
            ("service:admin_create_service_booking", {}),
            ("service:admin_edit_service_booking", {"pk": self.service_booking.pk}),
            ("service:admin_delete_service_booking", {"pk": self.service_booking.pk}),
            ("service:service_settings", {}),
            ("service:blocked_service_dates_management", {}),
            ("service:delete_blocked_service_date", {"pk": self.blocked_date.pk}),
            ("service:service_brands_management", {}),
            ("service:delete_service_brand", {"pk": self.service_brand.pk}),
            ("service:service_types_management", {}),
            ("service:add_service_type", {}),
            ("service:edit_service_type", {"pk": self.service_type.pk}),
            ("service:delete_service_type", {"pk": self.service_type.pk}),
            ("service:service_faq_management", {}),
            ("service:service_faq_create", {}),
            ("service:service_faq_update", {"pk": self.service_faq.pk}),
            ("service:service_faq_delete", {"pk": self.service_faq.pk}),
            ("service:admin_service_profiles", {}),
            ("service:admin_create_service_profile", {}),
            ("service:admin_edit_service_profile", {"pk": self.service_profile.pk}),
            ("service:admin_delete_service_profile", {"pk": self.service_profile.pk}),
            ("service:admin_customer_motorcycle_management", {}),
            ("service:admin_create_customer_motorcycle", {}),
            (
                "service:admin_edit_customer_motorcycle",
                {"pk": self.customer_motorcycle.pk},
            ),
            (
                "service:admin_delete_customer_motorcycle",
                {"pk": self.customer_motorcycle.pk},
            ),
            ("service:admin_api_search_customer", {}),
            (
                "service:admin_api_get_customer_details",
                {"profile_id": self.service_profile.pk},
            ),
            (
                "service:admin_api_customer_motorcycles",
                {"profile_id": self.service_profile.pk},
            ),
            (
                "service:admin_api_get_motorcycle_details",
                {"motorcycle_id": self.customer_motorcycle.pk},
            ),
            ("service:admin_api_service_date_availability", {}),
            ("service:admin_api_dropoff_time_availability", {}),
            ("service:admin_api_booking_precheck", {}),
            (
                "service:admin_api_get_service_booking_details",
                {"pk": self.service_booking.pk},
            ),
            ("service:get_service_bookings_json", {}),
            ("service:admin_api_search_bookings", {}),
            ("service:admin_api_get_estimated_pickup_date", {}),
        ]

        self.admin_cbv_urls = [u for u in all_urls if "_api_" not in u[0]]
        self.admin_ajax_urls = [u for u in all_urls if "_api_" in u[0]]

    def test_admin_cbv_views_for_regular_user(self):
        self.client.login(username="testuser", password="testpassword")
        for url_name, kwargs in self.admin_cbv_urls:
            url = reverse(url_name, kwargs=kwargs)
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302, f"URL {url_name} is not redirecting for regular user.")

    def test_admin_ajax_views_for_regular_user(self):
        self.client.login(username="testuser", password="testpassword")
        for url_name, kwargs in self.admin_ajax_urls:
            url = reverse(url_name, kwargs=kwargs)
            response = self.client.get(url)
            self.assertIn(response.status_code, [401, 403], f"URL {url_name} is not returning 401/403 for regular user.")

    def test_admin_cbv_views_for_admin_user(self):
        self.client.login(username="adminuser", password="testpassword")
        for url_name, kwargs in self.admin_cbv_urls:
            url = reverse(url_name, kwargs=kwargs)
            response = self.client.get(url)
            self.assertNotEqual(response.status_code, 302, f"URL {url_name} is redirecting for admin user.")

    def test_admin_ajax_views_for_admin_user(self):
        self.client.login(username="adminuser", password="testpassword")
        for url_name, kwargs in self.admin_ajax_urls:
            url = reverse(url_name, kwargs=kwargs)
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, f"URL {url_name} is not returning 200 for admin user.")