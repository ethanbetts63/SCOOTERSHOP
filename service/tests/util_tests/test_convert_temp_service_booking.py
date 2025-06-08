from django.test import TestCase
from decimal import Decimal
import uuid
from unittest.mock import patch, MagicMock

# Import models and the converter function
from service.models import TempServiceBooking, ServiceBooking, ServiceSettings
from payments.models import Payment, RefundPolicySettings
from service.utils import convert_temp_service_booking

# Import model factories
from ..test_helpers.model_factories import (
    TempServiceBookingFactory,
    ServiceSettingsFactory,
    RefundPolicySettingsFactory,
    PaymentFactory,
    ServiceTypeFactory,
    ServiceProfileFactory,
    CustomerMotorcycleFactory,
)

class ConvertTempServiceBookingTest(TestCase):
    """
    Tests for the convert_temp_service_booking utility function.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up common data for all tests in this class.
        """
        cls.service_settings = ServiceSettingsFactory(currency_code='AUD')
        cls.service_type = ServiceTypeFactory()
        cls.service_profile = ServiceProfileFactory()
        cls.customer_motorcycle = CustomerMotorcycleFactory(service_profile=cls.service_profile)
        
        # Ensure RefundPolicySettings exists for tests where it's expected
        cls.refund_policy_settings = RefundPolicySettingsFactory()

    def setUp(self):
        """
        Set up for each test method. Ensure a clean state.
        """
        TempServiceBooking.objects.all().delete()
        ServiceBooking.objects.all().delete()
        Payment.objects.all().delete()
        # Recreate ServiceSettings and RefundPolicySettings for each test
        # to ensure clean state if they are modified by a test (e.g., deleted)
        ServiceSettings.objects.all().delete()
        RefundPolicySettings.objects.all().delete()
        self.service_settings = ServiceSettingsFactory(currency_code='AUD')
        self.refund_policy_settings = RefundPolicySettingsFactory()

    def test_successful_conversion_with_new_payment_object(self):
        """
        Test that a TempServiceBooking is successfully converted to ServiceBooking
        and Payment, and refund_policy_snapshot is populated.
        """
        temp_booking = TempServiceBookingFactory(
            service_type=self.service_type,
            service_profile=self.service_profile,
            customer_motorcycle=self.customer_motorcycle,
            payment_option='online_full',
            calculated_total=Decimal('150.00'),
            calculated_deposit_amount=Decimal('0.00'),
            # No payment_obj passed, so converter creates one
        )

        amount_paid = Decimal('150.00')
        calculated_total = Decimal('150.00')

        service_booking = convert_temp_service_booking(
            temp_booking=temp_booking,
            payment_method='online_full',
            booking_payment_status='paid',
            amount_paid_on_booking=amount_paid,
            calculated_total_on_booking=calculated_total,
            stripe_payment_intent_id='pi_test_123'
        )

        # Assertions
        self.assertIsInstance(service_booking, ServiceBooking)
        self.assertFalse(TempServiceBooking.objects.filter(pk=temp_booking.pk).exists())
        self.assertEqual(ServiceBooking.objects.count(), 1)
        self.assertEqual(Payment.objects.count(), 1)

        created_payment = Payment.objects.get()
        self.assertEqual(created_payment.amount, amount_paid)
        self.assertEqual(created_payment.currency, 'AUD')
        self.assertEqual(created_payment.stripe_payment_intent_id, 'pi_test_123')
        self.assertEqual(created_payment.service_booking, service_booking)
        self.assertEqual(created_payment.service_customer_profile, self.service_profile)
        self.assertIsNone(created_payment.temp_service_booking) # Should be detached

        # Verify refund_policy_snapshot is populated
        self.assertIsNotNone(created_payment.refund_policy_snapshot)
        self.assertIsInstance(created_payment.refund_policy_snapshot, dict)
        self.assertGreater(len(created_payment.refund_policy_snapshot), 0)
        self.assertIn('cancellation_full_payment_full_refund_days', created_payment.refund_policy_snapshot)


    def test_successful_conversion_with_existing_payment_object(self):
        """
        Test that an existing Payment object is updated during conversion,
        and refund_policy_snapshot is populated.
        """
        existing_payment = PaymentFactory(
            amount=Decimal('0.00'), # Initial dummy amount
            currency='USD',       # Initial dummy currency
            status='requires_payment_method',
            temp_service_booking=None, # Ensure it's not linked initially, or detached
            service_booking=None,
        )

        temp_booking = TempServiceBookingFactory(
            service_type=self.service_type,
            service_profile=self.service_profile,
            customer_motorcycle=self.customer_motorcycle,
            payment_option='online_full',
            calculated_total=Decimal('200.00'),
            calculated_deposit_amount=Decimal('0.00'),
        )

        amount_paid = Decimal('200.00')
        calculated_total = Decimal('200.00')

        service_booking = convert_temp_service_booking(
            temp_booking=temp_booking,
            payment_method='online_full',
            booking_payment_status='paid',
            amount_paid_on_booking=amount_paid,
            calculated_total_on_booking=calculated_total,
            stripe_payment_intent_id='pi_test_456',
            payment_obj=existing_payment # Pass existing payment object
        )

        # Assertions
        self.assertIsInstance(service_booking, ServiceBooking)
        self.assertFalse(TempServiceBooking.objects.filter(pk=temp_booking.pk).exists())
        self.assertEqual(ServiceBooking.objects.count(), 1)
        self.assertEqual(Payment.objects.count(), 1) # Still only 1 payment object

        updated_payment = Payment.objects.get(pk=existing_payment.pk)
        self.assertEqual(updated_payment.amount, amount_paid)
        self.assertEqual(updated_payment.currency, 'AUD') # Should be updated to service_settings currency
        self.assertEqual(updated_payment.stripe_payment_intent_id, 'pi_test_456')
        self.assertEqual(updated_payment.service_booking, service_booking)
        self.assertEqual(updated_payment.service_customer_profile, self.service_profile)
        self.assertIsNone(updated_payment.temp_service_booking) # Should be detached

        # Verify refund_policy_snapshot is populated
        self.assertIsNotNone(updated_payment.refund_policy_snapshot)
        self.assertIsInstance(updated_payment.refund_policy_snapshot, dict)
        self.assertGreater(len(updated_payment.refund_policy_snapshot), 0)
        self.assertIn('cancellation_full_payment_full_refund_days', updated_payment.refund_policy_snapshot)

    def test_conversion_without_refund_policy_settings(self):
        """
        Test that refund_policy_snapshot is an empty dict if no
        RefundPolicySettings instance exists.
        """
        # Delete existing RefundPolicySettings
        RefundPolicySettings.objects.all().delete()
        self.assertEqual(RefundPolicySettings.objects.count(), 0)

        temp_booking = TempServiceBookingFactory(
            service_type=self.service_type,
            service_profile=self.service_profile,
            customer_motorcycle=self.customer_motorcycle,
            payment_option='online_full',
            calculated_total=Decimal('100.00'),
            calculated_deposit_amount=Decimal('0.00'),
        )

        payment_obj = PaymentFactory(
            amount=Decimal('0.00'),
            currency='AUD',
            status='requires_payment_method',
            temp_service_booking=None,
            service_booking=None,
        )

        convert_temp_service_booking(
            temp_booking=temp_booking,
            payment_method='online_full',
            booking_payment_status='paid',
            amount_paid_on_booking=Decimal('100.00'),
            calculated_total_on_booking=Decimal('100.00'),
            payment_obj=payment_obj
        )

        updated_payment = Payment.objects.get(pk=payment_obj.pk)
        self.assertEqual(updated_payment.refund_policy_snapshot, {})

    @patch('payments.models.RefundPolicySettings.objects.first', side_effect=Exception("DB error during snapshot"))
    def test_conversion_error_during_snapshot_creation(self, mock_first):
        """
        Test that if an error occurs during refund_policy_snapshot creation,
        it defaults to an empty dict and doesn't prevent conversion.
        """
        temp_booking = TempServiceBookingFactory(
            service_type=self.service_type,
            service_profile=self.service_profile,
            customer_motorcycle=self.customer_motorcycle,
            payment_option='online_full',
            calculated_total=Decimal('100.00'),
            calculated_deposit_amount=Decimal('0.00'),
        )

        payment_obj = PaymentFactory(
            amount=Decimal('0.00'),
            currency='AUD',
            status='requires_payment_method',
            temp_service_booking=None,
            service_booking=None,
        )

        service_booking = convert_temp_service_booking(
            temp_booking=temp_booking,
            payment_method='online_full',
            booking_payment_status='paid',
            amount_paid_on_booking=Decimal('100.00'),
            calculated_total_on_booking=Decimal('100.00'),
            payment_obj=payment_obj
        )
        
        self.assertIsInstance(service_booking, ServiceBooking) # Conversion still succeeds
        updated_payment = Payment.objects.get(pk=payment_obj.pk)
        self.assertEqual(updated_payment.refund_policy_snapshot, {}) # Snapshot is empty


    @patch('service.models.ServiceBooking.objects.create', side_effect=Exception("Database error!"))
    def test_exception_during_service_booking_creation(self, mock_create):
        """
        Test that exceptions during ServiceBooking creation are re-raised.
        """
        temp_booking = TempServiceBookingFactory(
            service_type=self.service_type,
            service_profile=self.service_profile,
            customer_motorcycle=self.customer_motorcycle,
            payment_option='online_full',
            calculated_total=Decimal('100.00'),
            calculated_deposit_amount=Decimal('0.00'),
        )

        # Expect an exception to be raised
        with self.assertRaisesMessage(Exception, "Database error!"):
            convert_temp_service_booking(
                temp_booking=temp_booking,
                payment_method='online_full',
                booking_payment_status='paid',
                amount_paid_on_booking=Decimal('100.00'),
                calculated_total_on_booking=Decimal('100.00'),
            )

        # Verify no ServiceBooking or Payment objects were created
        self.assertEqual(ServiceBooking.objects.count(), 0)
        self.assertEqual(Payment.objects.count(), 0)
        # TempServiceBooking should still exist if the transaction failed before deletion
        self.assertTrue(TempServiceBooking.objects.filter(pk=temp_booking.pk).exists())

    def test_temp_service_booking_deleted_on_successful_conversion(self):
        """
        Verify that the temporary booking is deleted after successful conversion.
        """
        temp_booking = TempServiceBookingFactory(
            service_type=self.service_type,
            service_profile=self.service_profile,
            customer_motorcycle=self.customer_motorcycle,
            payment_option='online_full',
            calculated_total=Decimal('100.00'),
            calculated_deposit_amount=Decimal('0.00'),
        )
        temp_booking_pk = temp_booking.pk

        convert_temp_service_booking(
            temp_booking=temp_booking,
            payment_method='online_full',
            booking_payment_status='paid',
            amount_paid_on_booking=Decimal('100.00'),
            calculated_total_on_booking=Decimal('100.00'),
        )

        self.assertFalse(TempServiceBooking.objects.filter(pk=temp_booking_pk).exists())

