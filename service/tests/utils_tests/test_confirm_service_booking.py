from django.test import TestCase
from unittest.mock import patch, MagicMock
from service.models import ServiceBooking
from service.utils.confirm_service_booking import confirm_service_booking
from service.tests.test_helpers.model_factories import ServiceBookingFactory, ServiceProfileFactory, CustomerMotorcycleFactory, SiteSettingsFactory


class ConfirmServiceBookingUtilTest(TestCase):
    def setUp(self):
        self.service_profile = ServiceProfileFactory()
        self.customer_motorcycle = CustomerMotorcycleFactory()
        self.booking = ServiceBookingFactory(
            service_profile=self.service_profile,
            customer_motorcycle=self.customer_motorcycle,
            booking_status="pending",
        )
        SiteSettingsFactory()

    @patch("mailer.utils.send_templated_email")
    def test_confirm_service_booking_success(self, mock_send_email):
        result = confirm_service_booking(self.booking.id)

        self.assertTrue(result["success"])
        self.assertEqual(result["message"], "Service booking confirmed successfully.")
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.booking_status, "confirmed")
        self.assertEqual(mock_send_email.call_count, 2)

    @patch("mailer.utils.send_templated_email")
    def test_confirm_service_booking_already_confirmed(self, mock_send_email):
        self.booking.booking_status = "confirmed"
        self.booking.save()

        result = confirm_service_booking(self.booking.id)

        self.assertFalse(result["success"])
        self.assertEqual(result["message"], "Booking already confirmed, in progress, or completed.")
        self.assertEqual(mock_send_email.call_count, 0)

    def test_confirm_service_booking_not_found(self):
        result = confirm_service_booking(99999)
        self.assertFalse(result["success"])
        self.assertEqual(result["message"], "Service Booking not found.")

    @patch("mailer.utils.send_templated_email")
    def test_confirm_service_booking_no_notification(self, mock_send_email):
        result = confirm_service_booking(self.booking.id, send_notification=False)

        self.assertTrue(result["success"])
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.booking_status, "confirmed")
        self.assertEqual(mock_send_email.call_count, 0)