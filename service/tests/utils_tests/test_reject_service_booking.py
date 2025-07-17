from django.test import TestCase
from unittest.mock import patch, MagicMock
from service.utils.reject_service_booking import reject_service_booking
from users.tests.test_helpers.model_factories import UserFactory
from service.tests.test_helpers.model_factories import ServiceBookingFactory
from payments.tests.test_helpers.model_factories import PaymentFactory
from decimal import Decimal


class RejectServiceBookingTests(TestCase):
    def setUp(self):
        self.admin_user = UserFactory(is_staff=True)
        self.service_booking_deposit = ServiceBookingFactory(
            payment=PaymentFactory(amount=Decimal("50.00")),
            payment_status="deposit_paid",
            booking_status="pending",
        )
        self.service_booking_no_deposit = ServiceBookingFactory(
            payment=None, payment_status="no_payment", booking_status="pending"
        )

    @patch("service.utils.reject_service_booking.send_templated_email")
    @patch("service.utils.reject_service_booking.create_refund_request")
    def test_reject_service_booking_with_refund(
        self, mock_create_refund, mock_send_email
    ):
        mock_create_refund.return_value = MagicMock(pk=123)
        form_data = {
            "message": "Test rejection message",
            "send_notification": True,
            "initiate_refund": True,
            "refund_amount": Decimal("50.00"),
        }
        result = reject_service_booking(
            self.service_booking_deposit.id, self.admin_user, form_data
        )

        self.assertTrue(result["success"])
        self.assertIn("A refund request for 50.00 has been created", result["message"])
        self.assertEqual(result["refund_request_pk"], 123)

        self.service_booking_deposit.refresh_from_db()
        self.assertEqual(self.service_booking_deposit.booking_status, "declined")

        mock_create_refund.assert_called_once()
        mock_send_email.assert_not_called()

    @patch("service.utils.reject_service_booking.send_templated_email")
    def test_reject_service_booking_no_refund(self, mock_send_email):
        form_data = {
            "message": "Test rejection message",
            "send_notification": True,
            "initiate_refund": False,
        }
        result = reject_service_booking(
            self.service_booking_deposit.id, self.admin_user, form_data
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["message"], "Service booking rejected successfully.")

        self.service_booking_deposit.refresh_from_db()
        self.assertEqual(
            self.service_booking_deposit.booking_status, "DECLINED_REFUNDED"
        )

        self.assertEqual(mock_send_email.call_count, 2)

    def test_reject_service_booking_not_found(self):
        result = reject_service_booking(999, self.admin_user, {})
        self.assertFalse(result["success"])
        self.assertEqual(result["message"], "Service Booking not found.")

    def test_reject_service_booking_already_cancelled(self):
        self.service_booking_deposit.booking_status = "cancelled"
        self.service_booking_deposit.save()
        result = reject_service_booking(
            self.service_booking_deposit.id, self.admin_user, {}
        )
        self.assertFalse(result["success"])
        self.assertEqual(result["message"], "Booking already cancelled or declined.")

    @patch("service.utils.reject_service_booking.create_refund_request")
    def test_reject_service_booking_with_refund_missing_amount(
        self, mock_create_refund
    ):
        form_data = {
            "message": "Test rejection message",
            "send_notification": True,
            "initiate_refund": True,
            "refund_amount": None,
        }
        result = reject_service_booking(
            self.service_booking_deposit.id, self.admin_user, form_data
        )
        self.assertFalse(result["success"])
        self.assertEqual(
            result["message"], "Refund amount is required to initiate a refund."
        )
        mock_create_refund.assert_not_called()

    @patch("service.utils.reject_service_booking.create_refund_request")
    def test_reject_service_booking_with_refund_create_fails(self, mock_create_refund):
        mock_create_refund.return_value = None
        form_data = {
            "message": "Test rejection message",
            "send_notification": True,
            "initiate_refund": True,
            "refund_amount": Decimal("50.00"),
        }
        result = reject_service_booking(
            self.service_booking_deposit.id, self.admin_user, form_data
        )
        self.assertFalse(result["success"])
        self.assertEqual(
            result["message"], "Failed to create refund request for rejected booking."
        )
        mock_create_refund.assert_called_once()

    @patch("service.utils.reject_service_booking.send_templated_email")
    def test_reject_service_booking_no_deposit_no_refund(self, mock_send_email):
        form_data = {
            "message": "Test rejection message",
            "send_notification": True,
            "initiate_refund": False,
        }
        result = reject_service_booking(
            self.service_booking_no_deposit.id, self.admin_user, form_data
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["message"], "Service booking rejected successfully.")

        self.service_booking_no_deposit.refresh_from_db()
        self.assertEqual(self.service_booking_no_deposit.booking_status, "declined")

        self.assertEqual(mock_send_email.call_count, 2)
