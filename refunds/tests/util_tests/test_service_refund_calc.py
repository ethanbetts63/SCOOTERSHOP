
import pytest
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from refunds.utils.service_refund_calc import calculate_service_refund_amount
from refunds.tests.util_tests.model_factories import ServiceBookingFactory
from refunds.models import RefundSettings

@pytest.mark.django_db
class TestServiceRefundCalc:
    def setup_method(self):
        self.refund_settings = RefundSettings.objects.create(
            deposit_full_refund_days=7,
            deposit_partial_refund_days=3,
            deposit_partial_refund_percentage=50,
            deposit_no_refund_days=1,
            full_payment_full_refund_days=14,
            full_payment_partial_refund_days=7,
            full_payment_partial_refund_percentage=50,
            full_payment_no_refund_percentage=1,
        )

    def test_full_refund_deposit(self):
        booking = ServiceBookingFactory(
            payment_method="online_deposit",
            amount_paid=Decimal("100.00"),
            dropoff_date=timezone.now().date() + timedelta(days=10),
        )
        result = calculate_service_refund_amount(booking)
        assert result["entitled_amount"] == Decimal("100.00")
        assert "Full Deposit Refund" in result["policy_applied"]

    def test_partial_refund_deposit(self):
        booking = ServiceBookingFactory(
            payment_method="online_deposit",
            amount_paid=Decimal("100.00"),
            dropoff_date=timezone.now().date() + timedelta(days=5),
        )
        result = calculate_service_refund_amount(booking)
        assert result["entitled_amount"] == Decimal("50.00")
        assert "Partial Deposit Refund" in result["policy_applied"]

    def test_no_refund_deposit(self):
        booking = ServiceBookingFactory(
            payment_method="online_deposit",
            amount_paid=Decimal("100.00"),
            dropoff_date=timezone.now().date() + timedelta(days=2),
        )
        result = calculate_service_refund_amount(booking)
        assert result["entitled_amount"] == Decimal("0.00")
        assert "No Deposit Refund" in result["policy_applied"]

    def test_full_refund_full_payment(self):
        booking = ServiceBookingFactory(
            payment_method="online_full",
            amount_paid=Decimal("200.00"),
            dropoff_date=timezone.now().date() + timedelta(days=15),
        )
        result = calculate_service_refund_amount(booking)
        assert result["entitled_amount"] == Decimal("200.00")
        assert "Full Payment Refund" in result["policy_applied"]

    def test_partial_refund_full_payment(self):
        booking = ServiceBookingFactory(
            payment_method="online_full",
            amount_paid=Decimal("200.00"),
            dropoff_date=timezone.now().date() + timedelta(days=10),
        )
        result = calculate_service_refund_amount(booking)
        assert result["entitled_amount"] == Decimal("100.00")
        assert "Partial Payment Refund" in result["policy_applied"]

    def test_no_refund_full_payment(self):
        booking = ServiceBookingFactory(
            payment_method="online_full",
            amount_paid=Decimal("200.00"),
            dropoff_date=timezone.now().date() + timedelta(days=2),
        )
        result = calculate_service_refund_amount(booking)
        assert result["entitled_amount"] == Decimal("0.00")
        assert "No Payment Refund" in result["policy_applied"]

    def test_no_refund_settings(self):
        RefundSettings.objects.all().delete()
        booking = ServiceBookingFactory()
        result = calculate_service_refund_amount(booking)
        assert result["entitled_amount"] == Decimal("0.00")
        assert result["details"] == "Refund settings not configured."
