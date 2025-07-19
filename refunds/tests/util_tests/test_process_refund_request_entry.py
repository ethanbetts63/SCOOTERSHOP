from django.test import TestCase
from decimal import Decimal
from refunds.utils.process_refund_request_entry import process_refund_request_entry
from payments.models import Payment
from refunds.models import RefundRequest
from service.models import ServiceBooking
from inventory.models import SalesBooking
from service.tests.test_helpers.model_factories import ServiceBookingFactory
from inventory.tests.test_helpers.model_factories import SalesBookingFactory
from payments.tests.test_helpers.model_factories import PaymentFactory
from refunds.tests.test_helpers.model_factories import RefundRequestFactory


class ProcessRefundRequestEntryTest(TestCase):
    def setUp(self):
        # Clean up database before each test
        Payment.objects.all().delete()
        RefundRequest.objects.all().delete()
        ServiceBooking.objects.all().delete()
        SalesBooking.objects.all().delete()

        self.extracted_data = {
            "stripe_refund_id": "re_test_new_refund",
            "refunded_amount_decimal": Decimal("50.00"),
        }

    def test_new_refund_request_creation_service_booking(self):
        booking = ServiceBookingFactory(amount_paid=Decimal("100.00"))
        payment = PaymentFactory(
            service_booking=booking,
            amount=Decimal("100.00"),
            status="partially_refunded",
        )

        refund_request = process_refund_request_entry(
            payment, booking, "service_booking", self.extracted_data
        )

        self.assertIsNotNone(refund_request)
        self.assertEqual(RefundRequest.objects.count(), 1)
        self.assertEqual(refund_request.payment, payment)
        self.assertEqual(refund_request.service_booking, booking)
        self.assertIsNone(refund_request.sales_booking)
        self.assertEqual(
            refund_request.stripe_refund_id, self.extracted_data["stripe_refund_id"]
        )
        self.assertEqual(
            refund_request.amount_to_refund,
            self.extracted_data["refunded_amount_decimal"],
        )
        self.assertEqual(refund_request.status, "partially_refunded")
        self.assertTrue(refund_request.is_admin_initiated)
        self.assertIsNotNone(refund_request.processed_at)

    def test_new_refund_request_creation_sales_booking(self):
        booking = SalesBookingFactory(amount_paid=Decimal("100.00"))
        payment = PaymentFactory(
            sales_booking=booking, amount=Decimal("100.00"), status="refunded"
        )

        refund_request = process_refund_request_entry(
            payment, booking, "sales_booking", self.extracted_data
        )

        self.assertIsNotNone(refund_request)
        self.assertEqual(RefundRequest.objects.count(), 1)
        self.assertEqual(refund_request.payment, payment)
        self.assertIsNone(refund_request.service_booking)
        self.assertEqual(refund_request.sales_booking, booking)
        self.assertEqual(
            refund_request.stripe_refund_id, self.extracted_data["stripe_refund_id"]
        )
        self.assertEqual(
            refund_request.amount_to_refund,
            self.extracted_data["refunded_amount_decimal"],
        )
        self.assertEqual(refund_request.status, "refunded")
        self.assertTrue(refund_request.is_admin_initiated)
        self.assertIsNotNone(refund_request.processed_at)

    def test_existing_refund_request_update_service_booking(self):
        booking = ServiceBookingFactory(amount_paid=Decimal("100.00"))
        payment = PaymentFactory(
            service_booking=booking,
            amount=Decimal("100.00"),
            status="partially_refunded",
        )

        # Create an initial refund request
        initial_refund_request = RefundRequestFactory(
            payment=payment,
            service_booking=booking,
            status="pending",
            amount_to_refund=Decimal("20.00"),
            stripe_refund_id="re_initial",
        )

        updated_extracted_data = {
            "stripe_refund_id": "re_test_updated_refund",
            "refunded_amount_decimal": Decimal("75.00"),
        }
        payment.status = "refunded"  # Simulate payment status change
        payment.save()

        refund_request = process_refund_request_entry(
            payment, booking, "service_booking", updated_extracted_data
        )

        self.assertEqual(RefundRequest.objects.count(), 1)  # Still only one request
        self.assertEqual(refund_request.pk, initial_refund_request.pk)
        self.assertEqual(
            refund_request.stripe_refund_id, updated_extracted_data["stripe_refund_id"]
        )
        self.assertEqual(
            refund_request.amount_to_refund,
            updated_extracted_data["refunded_amount_decimal"],
        )
        self.assertEqual(refund_request.status, "refunded")  # Status updated

    def test_existing_refund_request_update_sales_booking(self):
        booking = SalesBookingFactory(amount_paid=Decimal("100.00"))
        payment = PaymentFactory(
            sales_booking=booking, amount=Decimal("100.00"), status="partially_refunded"
        )

        # Create an initial refund request
        initial_refund_request = RefundRequestFactory(
            payment=payment,
            sales_booking=booking,
            status="approved",
            amount_to_refund=Decimal("30.00"),
            stripe_refund_id="re_initial_sales",
        )

        updated_extracted_data = {
            "stripe_refund_id": "re_test_updated_sales_refund",
            "refunded_amount_decimal": Decimal("80.00"),
        }
        payment.status = "partially_refunded"  # Simulate payment status change
        payment.save()

        refund_request = process_refund_request_entry(
            payment, booking, "sales_booking", updated_extracted_data
        )

        self.assertEqual(RefundRequest.objects.count(), 1)
        self.assertEqual(refund_request.pk, initial_refund_request.pk)
        self.assertEqual(
            refund_request.stripe_refund_id, updated_extracted_data["stripe_refund_id"]
        )
        self.assertEqual(
            refund_request.amount_to_refund,
            updated_extracted_data["refunded_amount_decimal"],
        )
        self.assertEqual(refund_request.status, "partially_refunded")

    def test_status_setting_refunded(self):
        booking = ServiceBookingFactory(amount_paid=Decimal("100.00"))
        payment = PaymentFactory(
            service_booking=booking, amount=Decimal("100.00"), status="refunded"
        )
        refund_request = process_refund_request_entry(
            payment, booking, "service_booking", self.extracted_data
        )
        self.assertEqual(refund_request.status, "refunded")

    def test_status_setting_partially_refunded(self):
        booking = ServiceBookingFactory(amount_paid=Decimal("100.00"))
        payment = PaymentFactory(
            service_booking=booking, amount=Decimal("100.00"), status="succeeded"
        )  # Not 'refunded'
        refund_request = process_refund_request_entry(
            payment, booking, "service_booking", self.extracted_data
        )
        self.assertEqual(refund_request.status, "partially_refunded")

    def test_is_admin_initiated_true(self):
        booking = ServiceBookingFactory(amount_paid=Decimal("100.00"))
        payment = PaymentFactory(service_booking=booking, amount=Decimal("100.00"))
        refund_request = process_refund_request_entry(
            payment, booking, "service_booking", self.extracted_data
        )
        self.assertTrue(refund_request.is_admin_initiated)

    def test_no_matching_refund_request_status(self):
        booking = ServiceBookingFactory(amount_paid=Decimal("100.00"))
        payment = PaymentFactory(service_booking=booking, amount=Decimal("100.00"))

        # Create a refund request with a status that should NOT be matched
        RefundRequestFactory(
            payment=payment,
            service_booking=booking,
            status="rejected",  # This status is not in the filter list
            amount_to_refund=Decimal("0.00"),
            stripe_refund_id="re_rejected",
        )

        # This should create a new refund request
        new_extracted_data = {
            "stripe_refund_id": "re_new_after_rejected",
            "refunded_amount_decimal": Decimal("25.00"),
        }
        refund_request = process_refund_request_entry(
            payment, booking, "service_booking", new_extracted_data
        )

        self.assertEqual(RefundRequest.objects.count(), 2)  # Two requests now
        self.assertEqual(refund_request.stripe_refund_id, "re_new_after_rejected")
        self.assertEqual(refund_request.amount_to_refund, Decimal("25.00"))
