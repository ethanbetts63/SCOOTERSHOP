from django.test import TestCase
from decimal import Decimal
from django.apps import apps
from refunds.utils.create_refund_request import create_refund_request
from refunds.tests.test_helpers.model_factories import RefundRequestFactory
from users.tests.test_helpers.model_factories import UserFactory, SuperUserFactory
from service.tests.test_helpers.model_factories import (
    ServiceBookingFactory,
    ServiceProfileFactory,
)
from inventory.tests.test_helpers.model_factories import (
    SalesBookingFactory,
    SalesProfileFactory,
)
from payments.tests.test_helpers.model_factories import PaymentFactory

Payment = apps.get_model('payments', 'Payment')
RefundRequest = apps.get_model('refunds', 'RefundRequest')
ServiceBooking = apps.get_model('service', 'ServiceBooking')
ServiceProfile = apps.get_model('service', 'ServiceProfile')
SalesBooking = apps.get_model('inventory', 'SalesBooking')
SalesProfile = apps.get_model('inventory', 'SalesProfile')


class CreateRefundRequestTest(TestCase):
    def setUp(self):
        PaymentFactory.reset_sequence()
        RefundRequestFactory.reset_sequence()
        ServiceBookingFactory.reset_sequence()
        SalesBookingFactory.reset_sequence()
        ServiceProfileFactory.reset_sequence()
        SalesProfileFactory.reset_sequence()

        self.user = UserFactory(email="testuser@example.com")
        self.admin_user = SuperUserFactory(email="admin@example.com")
        self.service_profile = ServiceProfileFactory(
            user=self.user, email="service@example.com"
        )
        self.sales_profile = SalesProfileFactory(
            user=self.user, email="sales@example.com"
        )
        self.payment = PaymentFactory(amount=Decimal("100.00"))

    def test_create_refund_request_service_booking(self):
        booking = ServiceBookingFactory(service_profile=self.service_profile)
        refund_request = create_refund_request(
            amount_to_refund=Decimal("50.00"),
            reason="Customer changed mind",
            payment=self.payment,
            service_booking=booking,
            requesting_user=self.user,
            service_profile=self.service_profile,
        )

        self.assertIsNotNone(refund_request)
        self.assertEqual(RefundRequest.objects.count(), 1)
        self.assertEqual(refund_request.amount_to_refund, Decimal("50.00"))
        self.assertEqual(refund_request.reason, "Customer changed mind")
        self.assertEqual(refund_request.payment, self.payment)
        self.assertEqual(refund_request.service_booking, booking)
        self.assertIsNone(refund_request.sales_booking)
        self.assertEqual(refund_request.request_email, self.user.email)
        self.assertEqual(refund_request.status, "pending")
        self.assertIsNone(refund_request.processed_by)
        self.assertIsNone(refund_request.processed_at)
        self.assertFalse(refund_request.is_admin_initiated)

    def test_create_refund_request_sales_booking(self):
        booking = SalesBookingFactory(sales_profile=self.sales_profile)
        refund_request = create_refund_request(
            amount_to_refund=Decimal("75.00"),
            reason="Item not needed",
            payment=self.payment,
            sales_booking=booking,
            requesting_user=self.user,
            sales_profile=self.sales_profile,
        )

        self.assertIsNotNone(refund_request)
        self.assertEqual(RefundRequest.objects.count(), 1)
        self.assertEqual(refund_request.amount_to_refund, Decimal("75.00"))
        self.assertEqual(refund_request.reason, "Item not needed")
        self.assertEqual(refund_request.payment, self.payment)
        self.assertIsNone(refund_request.service_booking)
        self.assertEqual(refund_request.sales_booking, booking)
        self.assertEqual(refund_request.request_email, self.user.email)
        self.assertEqual(refund_request.status, "pending")
        self.assertIsNone(refund_request.processed_by)
        self.assertIsNone(refund_request.processed_at)
        self.assertFalse(refund_request.is_admin_initiated)

    def test_create_refund_request_admin_initiated_approved(self):
        booking = ServiceBookingFactory(service_profile=self.service_profile)
        refund_request = create_refund_request(
            amount_to_refund=Decimal("100.00"),
            reason="Admin initiated adjustment",
            payment=self.payment,
            service_booking=booking,
            requesting_user=self.admin_user,
            service_profile=self.service_profile,
            is_admin_initiated=True,
            staff_notes="Internal notes for admin action",
            initial_status="approved",
        )

        self.assertIsNotNone(refund_request)
        self.assertEqual(RefundRequest.objects.count(), 1)
        self.assertEqual(refund_request.request_email, self.admin_user.email)
        self.assertEqual(refund_request.status, "approved")
        self.assertEqual(refund_request.processed_by, self.admin_user)
        self.assertIsNotNone(refund_request.processed_at)
        self.assertTrue(refund_request.is_admin_initiated)
        self.assertEqual(refund_request.staff_notes, "Internal notes for admin action")

    def test_create_refund_request_admin_initiated_pending_approval(self):
        booking = SalesBookingFactory(sales_profile=self.sales_profile)
        refund_request = create_refund_request(
            amount_to_refund=Decimal("25.00"),
            reason="Admin initiated review",
            payment=self.payment,
            sales_booking=booking,
            requesting_user=self.admin_user,
            sales_profile=self.sales_profile,
            is_admin_initiated=True,
            initial_status="reviewed_pending_approval",
        )

        self.assertIsNotNone(refund_request)
        self.assertEqual(RefundRequest.objects.count(), 1)
        self.assertEqual(refund_request.request_email, self.admin_user.email)
        self.assertEqual(refund_request.status, "reviewed_pending_approval")
        self.assertEqual(refund_request.processed_by, self.admin_user)
        self.assertIsNotNone(refund_request.processed_at)
        self.assertTrue(refund_request.is_admin_initiated)

    def test_create_refund_request_no_user_email_from_service_profile(self):
        service_profile_no_user = ServiceProfileFactory(
            user=None, email="profileonly@example.com"
        )
        booking = ServiceBookingFactory(service_profile=service_profile_no_user)
        refund_request = create_refund_request(
            amount_to_refund=Decimal("10.00"),
            reason="No user, service profile email",
            payment=self.payment,
            service_booking=booking,
            service_profile=service_profile_no_user,
            requesting_user=None,
        )

        self.assertIsNotNone(refund_request)
        self.assertEqual(refund_request.request_email, "profileonly@example.com")

    def test_create_refund_request_no_user_email_from_sales_profile(self):
        sales_profile_no_user = SalesProfileFactory(
            user=None, email="salesprofileonly@example.com"
        )
        booking = SalesBookingFactory(sales_profile=sales_profile_no_user)
        refund_request = create_refund_request(
            amount_to_refund=Decimal("10.00"),
            reason="No user, sales profile email",
            payment=self.payment,
            sales_booking=booking,
            sales_profile=sales_profile_no_user,
            requesting_user=None,
        )

        self.assertIsNotNone(refund_request)
        self.assertEqual(refund_request.request_email, "salesprofileonly@example.com")

    def test_create_refund_request_no_email_available(self):
        service_profile_no_email = ServiceProfileFactory(
            user=None, email="noemail@example.com"
        )  # Provide a default email
        booking = ServiceBookingFactory(service_profile=service_profile_no_email)
        refund_request = create_refund_request(
            amount_to_refund=Decimal("10.00"),
            reason="No email available",
            payment=self.payment,
            service_booking=booking,
            service_profile=service_profile_no_email,
            requesting_user=None,
        )

        self.assertIsNotNone(refund_request)
        self.assertEqual(refund_request.request_email, "noemail@example.com")

    def test_create_refund_request_exception_handling(self):
        # Simulate an error by passing an invalid argument type
        refund_request = create_refund_request(
            amount_to_refund="invalid_amount",
            reason="Test exception",
            payment=self.payment,
        )
        self.assertIsNone(refund_request)

    def test_processed_at_not_set_for_pending_status(self):
        booking = ServiceBookingFactory(service_profile=self.service_profile)
        refund_request = create_refund_request(
            amount_to_refund=Decimal("50.00"),
            reason="Customer changed mind",
            payment=self.payment,
            service_booking=booking,
            requesting_user=self.admin_user,
            service_profile=self.service_profile,
            is_admin_initiated=True,
            initial_status="pending",  # Should not set processed_at
        )
        self.assertIsNotNone(refund_request)
        self.assertIsNone(refund_request.processed_at)

    def test_processed_at_not_set_for_unverified_status(self):
        booking = ServiceBookingFactory(service_profile=self.service_profile)
        refund_request = create_refund_request(
            amount_to_refund=Decimal("50.00"),
            reason="Customer changed mind",
            payment=self.payment,
            service_booking=booking,
            requesting_user=self.admin_user,
            service_profile=self.service_profile,
            is_admin_initiated=True,
            initial_status="unverified",  # Should not set processed_at
        )
        self.assertIsNotNone(refund_request)
        self.assertIsNone(refund_request.processed_at)
