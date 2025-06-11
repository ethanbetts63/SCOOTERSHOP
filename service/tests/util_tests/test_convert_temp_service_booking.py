from django.test import TestCase
from decimal import Decimal
import uuid
from unittest.mock import patch, Mock # Import Mock

# Import models and the converter function
from service.models import TempServiceBooking, ServiceBooking, ServiceSettings
from payments.models import Payment, RefundPolicySettings
# Updated import path for the converter utility
from service.utils.convert_temp_service_booking import convert_temp_service_booking

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

    def test_successful_conversion_without_payment_object(self):
        """
        Test that a TempServiceBooking is successfully converted to ServiceBooking
        when no Payment object is provided, and no Payment object is created.
        """
        temp_booking = TempServiceBookingFactory(
            service_type=self.service_type,
            service_profile=self.service_profile,
            customer_motorcycle=self.customer_motorcycle,
            payment_method='in_store_full', # Assuming this option doesn't require upfront payment
            calculated_total=Decimal('150.00'),
            calculated_deposit_amount=Decimal('0.00'),
            # No payment_obj passed, so converter does not create one
        )

        amount_paid = Decimal('0.00') # No payment made yet
        calculated_total = Decimal('150.00')

        service_booking = convert_temp_service_booking(
            temp_booking=temp_booking,
            payment_method='in_store_full',
            booking_payment_status='unpaid',
            amount_paid_on_booking=amount_paid,
            calculated_total_on_booking=calculated_total,
            stripe_payment_intent_id=None # No Stripe ID as no payment
        )

        # Assertions
        self.assertIsInstance(service_booking, ServiceBooking)
        self.assertFalse(TempServiceBooking.objects.filter(pk=temp_booking.pk).exists())
        self.assertEqual(ServiceBooking.objects.count(), 1)
        self.assertEqual(Payment.objects.count(), 0) # No Payment object should be created

        self.assertIsNone(service_booking.payment) # ServiceBooking should not have a linked Payment

        self.assertEqual(service_booking.amount_paid, amount_paid)
        self.assertEqual(service_booking.payment_status, 'unpaid')
        self.assertEqual(service_booking.payment_method, 'in_store_full')


    def test_successful_conversion_with_existing_payment_object(self):
        """
        Test that an existing Payment object is updated during conversion,
        and refund_policy_snapshot is populated.
        """
        existing_payment = PaymentFactory(
            amount=Decimal('50.00'), # Set an initial amount that will be overridden
            currency='USD',       # Initial dummy currency that will be overridden
            status='requires_payment_method',
            temp_service_booking=None, # Ensure it's not linked initially, or detached
            service_booking=None,
        )

        temp_booking = TempServiceBookingFactory(
            service_type=self.service_type,
            service_profile=self.service_profile,
            customer_motorcycle=self.customer_motorcycle,
            payment_method='online_full',
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
        self.assertEqual(updated_payment.amount, amount_paid) # This assertion should now pass
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
        RefundPolicySettings instance exists, when a payment_obj is provided.
        """
        # Delete existing RefundPolicySettings
        RefundPolicySettings.objects.all().delete()
        self.assertEqual(RefundPolicySettings.objects.count(), 0)

        temp_booking = TempServiceBookingFactory(
            service_type=self.service_type,
            service_profile=self.service_profile,
            customer_motorcycle=self.customer_motorcycle,
            payment_method='online_full',
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

    @patch('service.models.ServiceBooking.objects.create', side_effect=Exception("Database error!"))
    def test_exception_during_service_booking_creation(self, mock_create):
        """
        Test that exceptions during ServiceBooking creation are re-raised.
        """
        temp_booking = TempServiceBookingFactory(
            service_type=self.service_type,
            service_profile=self.service_profile,
            customer_motorcycle=self.customer_motorcycle,
            payment_method='online_full',
            calculated_total=Decimal('100.00'),
            calculated_deposit_amount=Decimal('0.00'),
        )
        
        # When mocking ServiceBooking.objects.create, the Payment object is created
        # before the ServiceBooking. We need a Payment object to be created.
        # For this test, we are explicitly passing None for payment_obj.
        
        # Expect an exception to be raised
        with self.assertRaisesMessage(Exception, "Database error!"):
            convert_temp_service_booking(
                temp_booking=temp_booking,
                payment_method='online_full',
                booking_payment_status='paid',
                amount_paid_on_booking=Decimal('100.00'),
                calculated_total_on_booking=Decimal('100.00'),
                payment_obj=None # Explicitly pass None here to match scenario
            )

        # Verify no ServiceBooking objects were created
        self.assertEqual(ServiceBooking.objects.count(), 0)
        # No Payment object should be created or affected if payment_obj was None
        self.assertEqual(Payment.objects.count(), 0) 
        # TempServiceBooking should still exist if the transaction failed before deletion
        self.assertTrue(TempServiceBooking.objects.filter(pk=temp_booking.pk).exists())

    def test_temp_service_booking_deleted_on_successful_conversion(self):
        """
        Verify that the temporary booking is deleted after successful conversion.
        This test case will also cover a scenario where no payment object is needed.
        """
        temp_booking = TempServiceBookingFactory(
            service_type=self.service_type,
            service_profile=self.service_profile,
            customer_motorcycle=self.customer_motorcycle,
            payment_method='in_store_full', # Example: no payment_obj initially
            calculated_total=Decimal('100.00'),
            calculated_deposit_amount=Decimal('0.00'),
        )
        temp_booking_pk = temp_booking.pk

        convert_temp_service_booking(
            temp_booking=temp_booking,
            payment_method='in_store_full',
            booking_payment_status='unpaid',
            amount_paid_on_booking=Decimal('0.00'),
            calculated_total_on_booking=Decimal('100.00'),
            payment_obj=None # Explicitly pass None
        )

        self.assertFalse(TempServiceBooking.objects.filter(pk=temp_booking_pk).exists())
        self.assertEqual(Payment.objects.count(), 0) # No payment object created
        self.assertEqual(ServiceBooking.objects.count(), 1) # Service booking created

    @patch('service.utils.send_booking_to_mechanicdesk.send_booking_to_mechanicdesk')
    def test_conversion_calls_mechanicdesk_sender(self, mock_mechanicdesk_sender):
        """
        Test that convert_temp_service_booking calls the MechanicDesk sender utility
        upon successful conversion.
        """
        temp_booking = TempServiceBookingFactory(
            service_type=self.service_type,
            service_profile=self.service_profile,
            customer_motorcycle=self.customer_motorcycle,
            payment_method='online_full',
            calculated_total=Decimal('250.00'),
            calculated_deposit_amount=Decimal('50.00'),
        )

        payment_obj = PaymentFactory(
            amount=Decimal('50.00'),
            currency='AUD',
            status='deposit_paid',
            temp_service_booking=temp_booking,
        )

        # Perform the conversion
        service_booking = convert_temp_service_booking(
            temp_booking=temp_booking,
            payment_method='online_deposit',
            booking_payment_status='deposit_paid',
            amount_paid_on_booking=Decimal('50.00'),
            calculated_total_on_booking=Decimal('250.00'),
            stripe_payment_intent_id='pi_test_mechanicdesk_call',
            payment_obj=payment_obj
        )

        # Assert that the service booking was created successfully
        self.assertIsInstance(service_booking, ServiceBooking)
        self.assertEqual(ServiceBooking.objects.count(), 1)

        # Assert that the temporary booking was deleted
        self.assertFalse(TempServiceBooking.objects.filter(pk=temp_booking.pk).exists())

        # Assert that send_booking_to_mechanicdesk was called exactly once
        # and that it was called with the newly created ServiceBooking instance
        mock_mechanicdesk_sender.assert_called_once_with(service_booking)

