from django.test import TestCase
from django.urls import reverse
from django.contrib.messages import get_messages
from unittest.mock import patch
from service.tests.test_helpers.model_factories import (
    ServiceBookingFactory,
)
from users.tests.test_helpers.model_factories import StaffUserFactory


class ServiceBookingActionViewTest(TestCase):
    def setUp(self):
        self.admin_user = StaffUserFactory()
        self.client.force_login(self.admin_user)
        self.service_booking = ServiceBookingFactory()

    def test_get_confirm_action(self):
        response = self.client.get(
            reverse(
                "service:admin_service_booking_action",
                kwargs={"pk": self.service_booking.pk, "action_type": "confirm"},
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "service/admin_service_booking_action.html")
        self.assertEqual(response.context["action_type"], "confirm")
        self.assertIn("form", response.context)

    def test_get_reject_action(self):
        response = self.client.get(
            reverse(
                "service:admin_service_booking_action",
                kwargs={"pk": self.service_booking.pk, "action_type": "reject"},
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "service/admin_service_booking_action.html")
        self.assertEqual(response.context["action_type"], "reject")
        self.assertIn("form", response.context)

    def test_dispatch_invalid_action(self):
        response = self.client.get(
            reverse(
                "service:admin_service_booking_action",
                kwargs={"pk": self.service_booking.pk, "action_type": "invalid"},
            )
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("service:service_booking_management"))

    def test_dispatch_nonexistent_booking(self):
        response = self.client.get(
            reverse(
                "service:admin_service_booking_action",
                kwargs={"pk": 999, "action_type": "confirm"},
            )
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("service:service_booking_management"))

    @patch(
        "service.views.admin_views.admin_service_booking_action_view.confirm_service_booking"
    )
    def test_post_confirm_action_success(self, mock_confirm):
        mock_confirm.return_value = {"success": True, "message": "Booking confirmed."}
        form_data = {
            "service_booking_id": self.service_booking.pk,
            "action": "confirm",
            "send_notification": True,
            "message": "Test confirmation message",
            "estimated_pickup_date": "2025-12-25",
            "estimated_pickup_time": "12:00",
        }
        response = self.client.post(
            reverse(
                "service:admin_service_booking_action",
                kwargs={"pk": self.service_booking.pk, "action_type": "confirm"},
            ),
            data=form_data,
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("service:service_booking_management"))
        mock_confirm.assert_called_once()
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Booking confirmed.")

        self.service_booking.refresh_from_db()
        self.assertEqual(str(self.service_booking.estimated_pickup_date), "2025-12-25")
        self.assertEqual(str(self.service_booking.estimated_pickup_time), "12:00:00")

    @patch(
        "service.views.admin_views.admin_service_booking_action_view.reject_service_booking"
    )
    def test_post_reject_action_success(self, mock_reject):
        mock_reject.return_value = {"success": True, "message": "Booking rejected."}
        form_data = {
            "service_booking_id": self.service_booking.pk,
            "action": "reject",
            "send_notification": False,
            "message": "Test rejection message",
        }
        response = self.client.post(
            reverse(
                "service:admin_service_booking_action",
                kwargs={"pk": self.service_booking.pk, "action_type": "reject"},
            ),
            data=form_data,
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("service:service_booking_management"))
        mock_reject.assert_called_once()
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Booking rejected.")

    @patch(
        "service.views.admin_views.admin_service_booking_action_view.reject_service_booking"
    )
    def test_post_reject_action_with_refund_success(self, mock_reject):
        # Create a service booking with deposit paid
        service_booking_with_deposit = ServiceBookingFactory(
            payment_status="deposit_paid", amount_paid=100.00
        )

        mock_reject.return_value = {
            "success": True,
            "message": "Booking rejected and refund initiated.",
            "refund_request_pk": 123,  # Mock a refund request PK
        }

        form_data = {
            "service_booking_id": service_booking_with_deposit.pk,
            "action": "reject",
            "send_notification": True,
            "message": "Test rejection message with refund",
            "initiate_refund": True,
            "refund_amount": 100.00,
        }

        response = self.client.post(
            reverse(
                "service:admin_service_booking_action",
                kwargs={"pk": service_booking_with_deposit.pk, "action_type": "reject"},
            ),
            data=form_data,
        )

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response, reverse("refunds:initiate_refund_process", kwargs={"pk": 123})
        )
        mock_reject.assert_called_once()
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Booking rejected and refund initiated.")
