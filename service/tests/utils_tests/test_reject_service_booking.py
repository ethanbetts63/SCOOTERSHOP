from django.test import TestCase
from unittest.mock import patch, MagicMock
from service.models import ServiceBooking
from service.utils.reject_service_booking import reject_service_booking
from service.tests.test_helpers.model_factories import ServiceBookingFactory, ServiceProfileFactory, CustomerMotorcycleFactory, PaymentFactory, UserFactory, SiteSettingsFactory
from decimal import Decimal


class RejectServiceBookingUtilTest(TestCase):
    def setUp(self):
        self.service_profile = ServiceProfileFactory()
        self.customer_motorcycle = CustomerMotorcycleFactory()
        self.user = UserFactory()
        self.payment = PaymentFactory(amount=Decimal("100.00"))
        self.booking = ServiceBookingFactory(
            service_profile=self.service_profile,
            customer_motorcycle=self.customer_motorcycle,
            booking_status="pending",
            payment_status="deposit_paid",
            amount_paid=Decimal("100.00"),
            payment=self.payment,
        )
        SiteSettingsFactory()

    @patch("mailer.utils.send_templated_email")
    def test_reject_service_booking_success_no_refund(self, mock_send_email):
        form_data = {"initiate_refund": False, "message": "No longer needed."}
        result = reject_service_booking(
            self.booking.id, requesting_user=self.user, form_data=form_data
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["message"], "Service booking rejected successfully.")
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.booking_status, "DECLINED_REFUNDED")
        self.assertEqual(mock_send_email.call_count, 2)

    @patch("refunds.utils.create_refund_request.create_refund_request")
    @patch("mailer.utils.send_templated_email")
    def test_reject_service_booking_success_with_refund(self, mock_send_email, mock_create_refund_request):
        mock_refund_request = MagicMock(pk=123)
        mock_create_refund_request.return_value = mock_refund_request

        form_data = {
            "initiate_refund": True,
            "refund_amount": Decimal("50.00"),
            "message": "Customer changed mind.",
        }
        result = reject_service_booking(
            self.booking.id, requesting_user=self.user, form_data=form_data
        )

        self.assertTrue(result["success"])
        self.assertIn("A refund request for 50.00 has been created", result["message"])
        self.assertEqual(result["refund_request_pk"], 123)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.booking_status, "declined")
        mock_create_refund_request.assert_called_once()
        self.assertEqual(mock_send_email.call_count, 0) # No email sent by reject_service_booking if refund is initiated

    def test_reject_service_booking_not_found(self):
        result = reject_service_booking(99999)
        self.assertFalse(result["success"])
        self.assertEqual(result["message"], "Service Booking not found.")

    @patch("mailer.utils.send_templated_email")
    def test_reject_service_booking_already_declined(self, mock_send_email):
        self.booking.booking_status = "declined"
        self.booking.save()

        form_data = {"initiate_refund": False}
        result = reject_service_booking(
            self.booking.id, requesting_user=self.user, form_data=form_data
        )

        self.assertFalse(result["success"])
        self.assertEqual(result["message"], "Booking already cancelled or declined.")
        self.assertEqual(mock_send_email.call_count, 0)

    @patch("refunds.utils.create_refund_request.create_refund_request")
    @patch("mailer.utils.send_templated_email")
    def test_reject_service_booking_no_notification(self, mock_send_email, mock_create_refund_request):
        form_data = {"initiate_refund": False}
        result = reject_service_booking(
            self.booking.id, requesting_user=self.user, form_data=form_data, send_notification=False
        )

        self.assertTrue(result["success"])
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.booking_status, "DECLINED_REFUNDED")
        self.assertEqual(mock_send_email.call_count, 0)

    @patch("refunds.utils.create_refund_request.create_refund_request")
    @patch("mailer.utils.send_templated_email")
    def test_reject_service_booking_refund_amount_missing(self, mock_send_email, mock_create_refund_request):
        form_data = {"initiate_refund": True, "refund_amount": None}
        result = reject_service_booking(
            self.booking.id, requesting_user=self.user, form_data=form_data
        )

        self.assertFalse(result["success"])
        self.assertEqual(result["message"], "Refund amount is required to initiate a refund.")
        mock_create_refund_request.assert_not_called()
        self.assertEqual(mock_send_email.call_count, 0)

    @patch("refunds.utils.create_refund_request.create_refund_request", return_value=None)
    @patch("mailer.utils.send_templated_email")
    def test_reject_service_booking_refund_creation_failure(self, mock_send_email, mock_create_refund_request):
        form_data = {"initiate_refund": True, "refund_amount": Decimal("50.00")}
        result = reject_service_booking(
            self.booking.id, requesting_user=self.user, form_data=form_data
        )

        self.assertFalse(result["success"])
        self.assertEqual(result["message"], "Failed to create refund request for rejected booking.")
        mock_create_refund_request.assert_called_once()
        self.assertEqual(mock_send_email.call_count, 0)
