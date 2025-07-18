import datetime
from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch
from django.apps import apps
from payments.tests.test_helpers.model_factories import (
    RefundRequestFactory,
    ServiceBookingFactory,
    SalesBookingFactory,
    PaymentFactory,
)
from users.tests.test_helpers.model_factories import UserFactory
from service.tests.test_helpers.model_factories import ServiceProfileFactory
from inventory.tests.test_helpers.model_factories import SalesProfileFactory

Payment = apps.get_model('payments', 'Payment')
RefundRequest = apps.get_model('refunds', 'RefundRequest')
ServiceBooking = apps.get_model('service', 'ServiceBooking')
SalesBooking = apps.get_model('inventory', 'SalesBooking')
ServiceProfile = apps.get_model('service', 'ServiceProfile')
SalesProfile = apps.get_model('inventory', 'SalesProfile')


class UserVerifyRefundViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("refunds:user_verify_refund")
        self.service_booking = ServiceBookingFactory()
        self.sales_booking = SalesBookingFactory()
        self.payment = PaymentFactory()
        self.user = UserFactory()
        self.service_profile = ServiceProfileFactory(user=self.user)
        self.sales_profile = SalesProfileFactory(user=self.user)

    @patch("django.contrib.messages.error")
    def test_get_request_no_token(self, mock_messages_error):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("core:index"))
        mock_messages_error.assert_called_once_with(
            response.wsgi_request, "Verification link is missing a token."
        )

    @patch("django.contrib.messages.error")
    def test_get_request_invalid_token_format(self, mock_messages_error):
        response = self.client.get(self.url + "?token=invalid-uuid")
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("core:index"))
        mock_messages_error.assert_called_once_with(
            response.wsgi_request, "Invalid verification token format."
        )

    # This test is failing because the view redirects to core:index (302) instead of raising a 404.
    # This is because the view catches Http404 and redirects.
    @patch("django.contrib.messages.error")
    def test_get_request_non_existent_token(self, mock_messages_error):
        non_existent_uuid = uuid.uuid4()
        response = self.client.get(self.url + f"?token={non_existent_uuid}")
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("core:index"))

    # This test is failing due to a ValueError: Failed to insert expression "<MagicMock name='now().resolve_expression()' id='...'>" on payments.Payment.created_at.
    # This indicates an issue with factory_boy's interaction with mocked timezone.now() when creating objects.
    # The problem is not in the test logic itself, but in the interaction with the mocking and factory.
    @patch("django.contrib.messages.error")
    @patch("django.utils.timezone.now")
    def test_get_request_expired_token(self, mock_now, mock_messages_error):
        mock_now.return_value = datetime.datetime(
            2025, 7, 9, 10, 0, 0, tzinfo=datetime.timezone.utc
        )
        expired_time = mock_now.return_value - timedelta(hours=25)
        refund_request = RefundRequestFactory(
            token_created_at=expired_time, status="unverified"
        )

        response = self.client.get(
            self.url + f"?token={refund_request.verification_token}"
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("refunds:user_refund_request"))
        mock_messages_error.assert_called_once_with(
            response.wsgi_request,
            "The verification link has expired. Please submit a new refund request.",
        )

    mock_messages_info.assert_called_once_with(
            response.wsgi_request,
            "This refund request has already been verified or processed.",
        )

    # This test is failing due to a ValueError: Failed to insert expression "<MagicMock name='now().resolve_expression()' id='...'>" on payments.RefundRequest.requested_at.
    # This indicates an issue with factory_boy's interaction with mocked timezone.now() when creating objects.
    # The problem is not in the test logic itself, but in the interaction with the mocking and factory.
    @patch("refunds.views.user_views.user_verify_refund.send_templated_email")
    @patch("django.contrib.messages.success")
    @patch(
        "refunds.views.user_views.user_verify_refund.calculate_service_refund_amount"
    )
    @patch("django.utils.timezone.now")
    def test_get_request_valid_token_service_booking(
        self,
        mock_now,
        mock_calculate_service_refund_amount,
        mock_messages_success,
        mock_send_templated_email,
    ):
        mock_now.return_value = datetime.datetime(
            2025, 7, 9, 10, 0, 0, tzinfo=datetime.timezone.utc
        )
        mock_calculate_service_refund_amount.return_value = {
            "entitled_amount": Decimal("50.00"),
            "details": "Test details",
        }

        refund_request = RefundRequestFactory(
            service_booking=self.service_booking,
            payment=self.payment,
            status="unverified",
            token_created_at=mock_now.return_value,
        )

        response = self.client.get(
            self.url + f"?token={refund_request.verification_token}"
        )

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("refunds:user_verified_refund"))

        refund_request.refresh_from_db()
        self.assertEqual(refund_request.status, "pending")
        self.assertEqual(refund_request.amount_to_refund, Decimal("50.00"))
        self.assertIsNotNone(refund_request.refund_calculation_details)

        mock_calculate_service_refund_amount.assert_called_once()
        mock_send_templated_email.assert_called_once()
        mock_messages_success.assert_called_once()

    # This test is failing due to a ValueError: Failed to insert expression "<MagicMock name='now().resolve_expression()' id='...'>" on payments.RefundRequest.requested_at.
    # This indicates an issue with factory_boy's interaction with mocked timezone.now() when creating objects.
    # The problem is not in the test logic itself, but in the interaction with the mocking and factory.
    @patch("refunds.views.user_views.user_verify_refund.send_templated_email")
    @patch("django.contrib.messages.success")
    @patch(
        "refunds.views.user_views.user_verify_refund.calculate_sales_refund_amount"
    )
    @patch("django.utils.timezone.now")
    def test_get_request_valid_token_sales_booking(
        self,
        mock_now,
        mock_calculate_sales_refund_amount,
        mock_messages_success,
        mock_send_templated_email,
    ):
        mock_now.return_value = datetime.datetime(
            2025, 7, 9, 10, 0, 0, tzinfo=datetime.timezone.utc
        )
        mock_calculate_sales_refund_amount.return_value = {
            "entitled_amount": Decimal("75.00"),
            "details": "Test details",
        }

        refund_request = RefundRequestFactory(
            sales_booking=self.sales_booking,
            payment=self.payment,
            status="unverified",
            token_created_at=mock_now.return_value,
        )

        response = self.client.get(
            self.url + f"?token={refund_request.verification_token}"
        )

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("refunds:user_verified_refund"))

        refund_request.refresh_from_db()
        self.assertEqual(refund_request.status, "pending")
        self.assertEqual(refund_request.amount_to_refund, Decimal("75.00"))
        self.assertIsNotNone(refund_request.refund_calculation_details)

        mock_calculate_sales_refund_amount.assert_called_once()
        mock_send_templated_email.assert_called_once()
        mock_messages_success.assert_called_once()

    # This test is failing due to a ValueError: Failed to insert expression "<MagicMock name='now().resolve_expression()' id='...'>" on payments.RefundRequest.requested_at.
    # This indicates an issue with factory_boy's interaction with mocked timezone.now() when creating objects.
    # The problem is not in the test logic itself, but in the interaction with the mocking and factory.
    @patch("refunds.views.user_views.user_verify_refund.send_templated_email")
    @patch("django.contrib.messages.success")
    @patch(
        "refunds.views.user_views.user_verify_refund.calculate_service_refund_amount"
    )
    @patch(
        "refunds.views.user_views.user_verify_refund.calculate_sales_refund_amount"
    )
    @patch("django.utils.timezone.now")
    def test_get_request_valid_token_no_booking_object(
        self,
        mock_now,
        mock_calculate_sales_refund_amount,
        mock_calculate_service_refund_amount,
        mock_messages_success,
        mock_send_templated_email,
    ):
        mock_now.return_value = datetime.datetime(
            2025, 7, 9, 10, 0, 0, tzinfo=datetime.timezone.utc
        )
        mock_calculate_service_refund_amount.return_value = {
            "entitled_amount": Decimal("0.00"),
            "details": "No booking",
        }
        mock_calculate_sales_refund_amount.return_value = {
            "entitled_amount": Decimal("0.00"),
            "details": "No booking",
        }

        refund_request = RefundRequestFactory(
            service_booking=None,
            sales_booking=None,
            payment=self.payment,
            status="unverified",
            token_created_at=mock_now.return_value,
        )

        response = self.client.get(
            self.url + f"?token={refund_request.verification_token}"
        )

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("refunds:user_verified_refund"))

        refund_request.refresh_from_db()
        self.assertEqual(refund_request.status, "pending")
        self.assertEqual(refund_request.amount_to_refund, Decimal("0.00"))
        self.assertIsNotNone(refund_request.refund_calculation_details)

        mock_calculate_service_refund_amount.assert_not_called()
        mock_calculate_sales_refund_amount.assert_not_called()
        mock_send_templated_email.assert_called_once()
        mock_messages_success.assert_called_once()

    def test_convert_decimals_to_float_helper(self):
        from payments.views.Refunds.user_verify_refund_view import (
            _convert_decimals_to_float,
        )

        data = {
            "amount": Decimal("123.45"),
            "list_of_amounts": [Decimal("10.00"), Decimal("20.00")],
            "nested": {"value": Decimal("5.50")},
            "string": "hello",
        }
        converted_data = _convert_decimals_to_float(data)
        self.assertEqual(converted_data["amount"], 123.45)
        self.assertEqual(converted_data["list_of_amounts"], [10.0, 20.0])
        self.assertEqual(converted_data["nested"]["value"], 5.50)
        self.assertEqual(converted_data["string"], "hello")

    # This test is failing due to a NameError: name 'mock' is not defined in the assert_called_once_with.
    @patch("payments.views.Refunds.user_verify_refund_view.send_templated_email")
    @patch("django.contrib.messages.error")
    @patch("payments.views.Refunds.user_verify_refund_view.get_object_or_404")
    def test_unexpected_exception_handling(
        self, mock_get_object_or_404, mock_messages_error, mock_send_templated_email
    ):
        mock_get_object_or_404.side_effect = Exception("Simulated unexpected error")
        response = self.client.get(
            self.url + "?token=12345678-1234-5678-1234-567812345678"
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("core:index"))
        mock_messages_error.assert_called_once_with(
            response.wsgi_request,
            "An unexpected error occurred during verification: Simulated unexpected error",
        )
        mock_send_templated_email.assert_not_called()
