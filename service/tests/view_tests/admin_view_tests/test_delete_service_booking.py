from django.test import TestCase
from django.urls import reverse
from service.models import ServiceBooking
from users.tests.test_helpers.model_factories import staff_factory
from service.tests.test_helpers.model_factories import ServiceBookingFactory
from django.contrib.messages import get_messages


class AdminServiceBookingDeleteViewTest(TestCase):
    def setUp(self):
        self.admin_user = UserFactory(is_staff=True)
        self.client.force_login(self.admin_user)
        self.service_booking = ServiceBookingFactory(
            service_booking_reference="SBK-TEST"
        )

    def test_get_service_booking_delete_view(self):
        response = self.client.get(
            reverse(
                "service:admin_delete_service_booking",
                kwargs={"pk": self.service_booking.pk},
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "service/admin_service_booking_delete.html")
        self.assertIn("booking", response.context)
        self.assertEqual(response.context["booking"], self.service_booking)

    def test_post_service_booking_delete_success(self):
        initial_count = ServiceBooking.objects.count()
        response = self.client.post(
            reverse(
                "service:admin_delete_service_booking",
                kwargs={"pk": self.service_booking.pk},
            )
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("service:service_booking_management"))
        self.assertEqual(ServiceBooking.objects.count(), initial_count - 1)
        self.assertFalse(
            ServiceBooking.objects.filter(pk=self.service_booking.pk).exists()
        )
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            str(messages[0]), "Booking SBK-TEST has been successfully deleted."
        )

    def test_post_service_booking_delete_nonexistent(self):
        initial_count = ServiceBooking.objects.count()
        response = self.client.post(
            reverse("service:admin_delete_service_booking", kwargs={"pk": 999})
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(ServiceBooking.objects.count(), initial_count)

    def test_admin_required_mixin(self):
        self.client.logout()
        response = self.client.get(
            reverse(
                "service:admin_delete_service_booking",
                kwargs={"pk": self.service_booking.pk},
            )
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse("users:login")
            + "?next="
            + reverse(
                "service:admin_delete_service_booking",
                kwargs={"pk": self.service_booking.pk},
            ),
        )
