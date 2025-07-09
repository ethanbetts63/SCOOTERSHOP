
from django.test import TestCase
from payments.utils.create_refund_request import create_refund_request
from payments.models import RefundRequest
from payments.tests.test_helpers.model_factories import PaymentFactory, SalesBookingFactory, ServiceBookingFactory, UserFactory, SalesProfileFactory, ServiceProfileFactory
from decimal import Decimal
from django.utils import timezone
from unittest.mock import patch, MagicMock

class CreateRefundRequestTest(TestCase):

    def setUp(self):
        self.payment = PaymentFactory()
        self.sales_booking = SalesBookingFactory()
        self.service_booking = ServiceBookingFactory()
        self.user = UserFactory()
        self.sales_profile = SalesProfileFactory()
        self.service_profile = ServiceProfileFactory()

    def test_create_refund_request_with_payment_and_sales_booking(self):
        refund_request = create_refund_request(
            amount_to_refund=Decimal('50.00'),
            reason='Customer changed mind',
            payment=self.payment,
            sales_booking=self.sales_booking,
            requesting_user=self.user,
            sales_profile=self.sales_profile,
        )
        self.assertIsNone(refund_request)

    def test_create_refund_request_with_payment_and_service_booking(self):
        refund_request = create_refund_request(
            amount_to_refund=Decimal('75.00'),
            reason='Service cancelled',
            payment=self.payment,
            service_booking=self.service_booking,
            requesting_user=self.user,
            service_profile=self.service_profile,
        )
        self.assertIsNone(refund_request)

    def test_create_refund_request_admin_initiated_approved(self):
        refund_request = create_refund_request(
            amount_to_refund=Decimal('100.00'),
            reason='Admin approved refund',
            payment=self.payment,
            requesting_user=self.user,
            is_admin_initiated=True,
            staff_notes='Admin notes here',
            initial_status='approved',
        )
        self.assertIsInstance(refund_request, RefundRequest)
        self.assertEqual(refund_request.status, 'approved')
        self.assertTrue(refund_request.is_admin_initiated)
        self.assertEqual(refund_request.processed_by, self.user)
        self.assertIsNotNone(refund_request.processed_at)
        self.assertEqual(refund_request.staff_notes, 'Admin notes here')

    def test_create_refund_request_admin_initiated_pending_approval(self):
        refund_request = create_refund_request(
            amount_to_refund=Decimal('100.00'),
            reason='Admin review pending',
            payment=self.payment,
            requesting_user=self.user,
            is_admin_initiated=True,
            staff_notes='Admin notes here',
            initial_status='reviewed_pending_approval',
        )
        self.assertIsInstance(refund_request, RefundRequest)
        self.assertEqual(refund_request.status, 'reviewed_pending_approval')
        self.assertTrue(refund_request.is_admin_initiated)
        self.assertEqual(refund_request.processed_by, self.user)
        self.assertIsNotNone(refund_request.processed_at)

    def test_create_refund_request_no_requesting_user_but_profile_email(self):
        refund_request = create_refund_request(
            amount_to_refund=Decimal('25.00'),
            reason='No user, but sales profile',
            payment=self.payment,
            sales_profile=self.sales_profile,
        )
        self.assertIsNone(refund_request)

    def test_create_refund_request_no_email_source(self):
        refund_request = create_refund_request(
            amount_to_refund=Decimal('10.00'),
            reason='No email source',
            payment=self.payment,
        )
        self.assertIsNone(refund_request)

    def test_create_refund_request_exception_handling(self):
        with patch('payments.utils.create_refund_request.RefundRequest.objects.create') as mock_create:
            mock_create.side_effect = Exception("Database error")
            refund_request = create_refund_request(
                amount_to_refund=Decimal('10.00'),
                reason='Test error',
                payment=self.payment,
            )
            self.assertIsNone(refund_request)
