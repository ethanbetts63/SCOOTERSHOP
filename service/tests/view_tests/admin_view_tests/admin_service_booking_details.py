from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from users.tests.test_helpers.model_factories import StaffUserFactory, SuperUserFactory
from service.tests.test_helpers.model_factories import (
    ServiceBookingFactory,
    ServiceTypeFactory,
)


class AdminServiceBookingDetailViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff_user = StaffUserFactory(
            username="staff_user_detail"
        )
        cls.superuser = SuperUserFactory(
            username="superuser_detail"
        )

        cls.service_type = ServiceTypeFactory(name="Major Service")

        cls.booking = ServiceBookingFactory(
            service_type=cls.service_type,
            dropoff_date=timezone.now().date() + timezone.timedelta(days=7),
            dropoff_time=timezone.now().time(),
            booking_status="CONFIRMED",
            customer_notes="Customer requested a specific check on brakes.",
        )

        cls.detail_url_name = "service:admin_service_booking_detail"

    def setUp(self):
        self.client = Client()
        self.client.force_login(self.staff_user)

    def test_get_request_displays_booking_details(self):
        response = self.client.get(
            reverse(self.detail_url_name, args=[self.booking.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "service/admin_service_booking_detail.html")

        self.assertIn("service_booking", response.context)
        self.assertEqual(response.context["service_booking"], self.booking)

        self.assertIn("booking_pk", response.context)
        self.assertEqual(response.context["booking_pk"], self.booking.pk)

        

    def test_get_request_invalid_booking_pk(self):
        invalid_pk = self.booking.pk + 999
        response = self.client.get(reverse(self.detail_url_name, args=[invalid_pk]))
        self.assertEqual(response.status_code, 404)
