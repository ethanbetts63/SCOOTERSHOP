from django.test import TestCase
from unittest.mock import patch, MagicMock
from inventory.utils.reject_sales_booking import reject_sales_booking
from inventory.tests.test_helpers.model_factories import (
    SalesBookingFactory,
    MotorcycleFactory,
    UserFactory,
    PaymentFactory,
)
from decimal import Decimal


class RejectSalesBookingTests(TestCase):
    def setUp(self):
        self.admin_user = UserFactory(is_staff=True)
        self.motorcycle_new = MotorcycleFactory(
            quantity=0, condition="new", status="reserved", is_available=False
        )
        self.motorcycle_used = MotorcycleFactory(condition="used", status="reserved")

        # Ensure each sales booking gets a unique payment instance
        self.sales_booking_new_deposit = SalesBookingFactory(
            motorcycle=self.motorcycle_new,
            payment=PaymentFactory(amount=Decimal("100.00")),
            payment_status="deposit_paid",
            booking_status="pending",
        )
        self.sales_booking_used_deposit = SalesBookingFactory(
            motorcycle=self.motorcycle_used,
            payment=PaymentFactory(amount=Decimal("100.00")),
            payment_status="deposit_paid",
            booking_status="pending",
        )
        self.sales_booking_no_deposit = SalesBookingFactory(
            motorcycle=self.motorcycle_used,
            payment=None,
            payment_status="no_payment",
            booking_status="pending",
        )

    @patch("inventory.utils.reject_sales_booking.send_templated_email")
    @patch("inventory.utils.reject_sales_booking.create_refund_request")
    def test_reject_sales_booking_new_motorcycle_with_refund(
        self, mock_create_refund, mock_send_email
    ):
        mock_create_refund.return_value = MagicMock(pk=123)
        form_data = {
            "message": "Test rejection message",
            "send_notification": True,
            "initiate_refund": True,
            "refund_amount": Decimal("100.00"),
        }
        result = reject_sales_booking(
            self.sales_booking_new_deposit.id, self.admin_user, form_data
        )

        self.assertTrue(result["success"])
        self.assertIn("A refund request for 100.00 has been created", result["message"])
        self.assertEqual(result["refund_request_pk"], 123)

        self.sales_booking_new_deposit.refresh_from_db()
        self.assertEqual(self.sales_booking_new_deposit.booking_status, "declined")

        self.motorcycle_new.refresh_from_db()
        self.assertEqual(self.motorcycle_new.quantity, 1)
        self.assertTrue(self.motorcycle_new.is_available)
        self.assertEqual(self.motorcycle_new.status, "for_sale")

        mock_create_refund.assert_called_once()
        mock_send_email.assert_not_called()

    @patch("inventory.utils.reject_sales_booking.send_templated_email")
    def test_reject_sales_booking_used_motorcycle_no_refund(self, mock_send_email):
        form_data = {
            "message": "Test rejection message",
            "send_notification": True,
            "initiate_refund": False,
        }
        result = reject_sales_booking(
            self.sales_booking_used_deposit.id, self.admin_user, form_data
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["message"], "Sales booking rejected successfully.")

        self.sales_booking_used_deposit.refresh_from_db()
        self.assertEqual(
            self.sales_booking_used_deposit.booking_status, "declined_refunded"
        )

        self.motorcycle_used.refresh_from_db()
        self.assertTrue(self.motorcycle_used.is_available)
        self.assertEqual(self.motorcycle_used.status, "for_sale")

        self.assertEqual(mock_send_email.call_count, 2)

    def test_reject_sales_booking_not_found(self):
        result = reject_sales_booking(999, self.admin_user, {})
        self.assertFalse(result["success"])
        self.assertEqual(result["message"], "Sales Booking not found.")

    def test_reject_sales_booking_already_cancelled(self):
        self.sales_booking_new_deposit.booking_status = "cancelled"
        self.sales_booking_new_deposit.save()
        result = reject_sales_booking(
            self.sales_booking_new_deposit.id, self.admin_user, {}
        )
        self.assertFalse(result["success"])
        self.assertEqual(result["message"], "Booking already cancelled or declined.")

    @patch("inventory.utils.reject_sales_booking.create_refund_request")
    def test_reject_sales_booking_with_refund_missing_amount(self, mock_create_refund):
        form_data = {
            "message": "Test rejection message",
            "send_notification": True,
            "initiate_refund": True,
            "refund_amount": None,
        }
        result = reject_sales_booking(
            self.sales_booking_new_deposit.id, self.admin_user, form_data
        )
        self.assertFalse(result["success"])
        self.assertEqual(
            result["message"], "Refund amount is required to initiate a refund."
        )
        mock_create_refund.assert_not_called()

    @patch("inventory.utils.reject_sales_booking.create_refund_request")
    def test_reject_sales_booking_with_refund_create_fails(self, mock_create_refund):
        mock_create_refund.return_value = None
        form_data = {
            "message": "Test rejection message",
            "send_notification": True,
            "initiate_refund": True,
            "refund_amount": Decimal("50.00"),
        }
        result = reject_sales_booking(
            self.sales_booking_new_deposit.id, self.admin_user, form_data
        )
        self.assertFalse(result["success"])
        self.assertEqual(
            result["message"], "Failed to create refund request for rejected booking."
        )
        mock_create_refund.assert_called_once()

    @patch("inventory.utils.reject_sales_booking.send_templated_email")
    def test_reject_sales_booking_no_deposit_no_refund(self, mock_send_email):
        form_data = {
            "message": "Test rejection message",
            "send_notification": True,
            "initiate_refund": False,
        }
        result = reject_sales_booking(
            self.sales_booking_no_deposit.id, self.admin_user, form_data
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["message"], "Sales booking rejected successfully.")

        self.sales_booking_no_deposit.refresh_from_db()
        self.assertEqual(self.sales_booking_no_deposit.booking_status, "declined")

        self.motorcycle_used.refresh_from_db()
        self.assertTrue(self.motorcycle_used.is_available)
        self.assertEqual(self.motorcycle_used.status, "for_sale")

        self.assertEqual(mock_send_email.call_count, 2)
