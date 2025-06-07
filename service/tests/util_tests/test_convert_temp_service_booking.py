from django.test import TestCase
from django.db import transaction
from decimal import Decimal
import datetime
from unittest.mock import patch

# Import the function to be tested
from service.utils import convert_temp_service_booking
from service.utils.get_available_service_dropoff_times import get_available_dropoff_times
# Import models and factories
from service.models import ServiceBooking, TempServiceBooking
from payments.models import Payment # Import the Payment model
from ..test_helpers.model_factories import (
    TempServiceBookingFactory,
    ServiceBookingFactory, # Although we create it, good to have if needed for comparison
    PaymentFactory,
    ServiceSettingsFactory,
    ServiceProfileFactory,
    CustomerMotorcycleFactory,
    ServiceTypeFactory,
)


class ConvertTempToFinalServiceTest(TestCase):
    """
    Tests for the convert_temp_service_booking function.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up common data for all tests in this class.
        Create a single ServiceSettings instance as it's a singleton and required
        for refund policy snapshots.
        """
        # Ensure a clean slate for ServiceSettings before creating the singleton
        ServiceSettingsFactory.create(pk=1)
        # Create a ServiceType instance
        cls.service_type = ServiceTypeFactory()
        # Create a ServiceProfile instance
        cls.service_profile = ServiceProfileFactory()
        # Create a CustomerMotorcycle instance linked to the ServiceProfile
        cls.customer_motorcycle = CustomerMotorcycleFactory(service_profile=cls.service_profile)


    def setUp(self):
        """
        Set up for each test method. Ensure a clean state for bookings and payments.
        """
        ServiceBooking.objects.all().delete()
        TempServiceBooking.objects.all().delete()
        Payment.objects.all().delete()
        # Re-fetch ServiceSettings for each test to ensure it's up-to-date
        self.service_settings = ServiceSettingsFactory(pk=1)


    def test_successful_conversion_without_payment_obj(self):
        """
        Test that a TempServiceBooking is successfully converted to ServiceBooking
        when no Payment object is initially provided.
        """
        # Create a TempServiceBooking
        temp_booking = TempServiceBookingFactory(
            service_type=self.service_type,
            service_profile=self.service_profile,
            customer_motorcycle=self.customer_motorcycle,
            payment_option='in_store_full',
            calculated_deposit_amount=Decimal('0.00'), # No deposit for full in-store
            customer_notes='Test notes for in-store booking.',
        )

        initial_temp_booking_count = TempServiceBooking.objects.count()
        initial_service_booking_count = ServiceBooking.objects.count()

        payment_method = 'in_store_full'
        booking_payment_status = 'pending' # For in-store, might be pending initially
        amount_paid_on_booking = Decimal('0.00') # No payment made yet for in-store
        calculated_total = temp_booking.service_type.base_price # Use base price as total for simplicity

        # Perform the conversion
        final_booking = convert_temp_service_booking(
            temp_booking=temp_booking,
            payment_method=payment_method,
            booking_payment_status=booking_payment_status,
            amount_paid_on_booking=amount_paid_on_booking,
            calculated_total_on_booking=calculated_total,
            stripe_payment_intent_id=None,
            payment_obj=None,
        )

        # Assertions
        self.assertIsNotNone(final_booking)
        self.assertEqual(ServiceBooking.objects.count(), initial_service_booking_count + 1)
        self.assertEqual(TempServiceBooking.objects.count(), initial_temp_booking_count - 1)
        self.assertFalse(TempServiceBooking.objects.filter(id=temp_booking.id).exists())

        # Verify data transfer
        self.assertEqual(final_booking.service_type, temp_booking.service_type)
        self.assertEqual(final_booking.service_profile, temp_booking.service_profile)
        self.assertEqual(final_booking.customer_motorcycle, temp_booking.customer_motorcycle)
        self.assertEqual(final_booking.payment_option, temp_booking.payment_option)
        self.assertEqual(final_booking.calculated_total, calculated_total)
        self.assertEqual(final_booking.calculated_deposit_amount, Decimal('0.00')) # Check default if None
        self.assertEqual(final_booking.amount_paid, amount_paid_on_booking)
        self.assertEqual(final_booking.payment_status, booking_payment_status)
        self.assertEqual(final_booking.payment_method, payment_method)
        self.assertEqual(final_booking.currency, self.service_settings.currency_code)
        self.assertIsNone(final_booking.stripe_payment_intent_id)
        self.assertEqual(final_booking.service_date, temp_booking.service_date)
        self.assertEqual(final_booking.dropoff_date, temp_booking.dropoff_date)
        self.assertEqual(final_booking.dropoff_time, temp_booking.dropoff_time)
        self.assertEqual(final_booking.estimated_pickup_date, temp_booking.estimated_pickup_date)
        self.assertEqual(final_booking.booking_status, 'confirmed') # Should be confirmed upon conversion
        self.assertEqual(final_booking.customer_notes, temp_booking.customer_notes)
        self.assertIsNone(final_booking.payment) # No payment object should be linked

        # Verify service_booking_reference was generated by the model's save method
        self.assertIsNotNone(final_booking.service_booking_reference)
        self.assertTrue(final_booking.service_booking_reference.startswith('SERVICE-'))


    def test_successful_conversion_with_payment_obj(self):
        """
        Test that a TempServiceBooking is successfully converted to ServiceBooking
        and the provided Payment object is correctly linked and updated.
        """
        # Create a TempServiceBooking and an associated Payment object
        temp_booking = TempServiceBookingFactory(
            service_type=self.service_type,
            service_profile=self.service_profile,
            customer_motorcycle=self.customer_motorcycle,
            payment_option='online_full',
            calculated_deposit_amount=Decimal('0.00'),
        )
        calculated_total = temp_booking.service_type.base_price + Decimal('50.00') # Simulate a higher total
        amount_paid = calculated_total
        stripe_pi_id = 'pi_test_intent_123'

        # Create a Payment object, initially linked to TempServiceBooking (if your Payment model supports this)
        # Assuming Payment model has a temp_service_booking FK, otherwise skip linking here.
        payment_obj = PaymentFactory(
            amount=amount_paid,
            currency='AUD',
            status='succeeded',
            stripe_payment_intent_id=stripe_pi_id,
            temp_hire_booking=None, # Ensure this is compatible with your Payment model's FKs
            hire_booking=None,
            # If Payment has a temp_service_booking FK, link it. Adjust if your factory doesn't have it.
            # For this test, we assume payment_obj doesn't have a temp_service_booking FK defined on it directly yet,
            # but is associated contextually in the webhook.
        )

        initial_temp_booking_count = TempServiceBooking.objects.count()
        initial_service_booking_count = ServiceBooking.objects.count()
        initial_payment_booking_link = payment_obj.service_booking # Should be None or old link
        initial_payment_temp_link = None # Assuming no direct FK from Payment to TempServiceBooking before conversion

        # Perform the conversion
        final_booking = convert_temp_service_booking(
            temp_booking=temp_booking,
            payment_method='online_full',
            booking_payment_status='paid',
            amount_paid_on_booking=amount_paid,
            calculated_total_on_booking=calculated_total,
            stripe_payment_intent_id=stripe_pi_id,
            payment_obj=payment_obj,
        )

        # Re-fetch the payment_obj to get its updated state from the DB
        payment_obj.refresh_from_db()

        # Assertions
        self.assertIsNotNone(final_booking)
        self.assertEqual(ServiceBooking.objects.count(), initial_service_booking_count + 1)
        self.assertEqual(TempServiceBooking.objects.count(), initial_temp_booking_count - 1)
        self.assertFalse(TempServiceBooking.objects.filter(id=temp_booking.id).exists())

        # Verify data transfer
        self.assertEqual(final_booking.calculated_total, calculated_total)
        self.assertEqual(final_booking.amount_paid, amount_paid)
        self.assertEqual(final_booking.payment_status, 'paid')
        self.assertEqual(final_booking.payment_method, 'online_full')
        self.assertEqual(final_booking.stripe_payment_intent_id, stripe_pi_id)
        self.assertEqual(final_booking.currency, self.service_settings.currency_code)
        self.assertEqual(final_booking.booking_status, 'confirmed')

        # Verify Payment object linkage and update
        self.assertIsNotNone(final_booking.payment)
        self.assertEqual(final_booking.payment.id, payment_obj.id)
        self.assertEqual(payment_obj.service_booking, final_booking)
        self.assertEqual(payment_obj.customer_profile, final_booking.service_profile)
        
        # This part depends on if your Payment model *had* a FK to TempServiceBooking
        # If it does, ensure it's cleared. If not, this check will fail or is not needed.
        # Assuming your Payment model might have a 'temp_service_booking' FK that needs clearing:
        if hasattr(payment_obj, 'temp_service_booking'):
             self.assertIsNone(payment_obj.temp_service_booking)


        # Verify refund policy snapshot
        self.assertIsNotNone(payment_obj.refund_policy_snapshot)
        self.assertIn('cancel_full_payment_max_refund_days', payment_obj.refund_policy_snapshot)
        self.assertEqual(payment_obj.refund_policy_snapshot['currency_code'], self.service_settings.currency_code) # Ensure currency is part of snapshot


    def test_transaction_rollback_on_error(self):
        """
        Test that if an error occurs during the conversion, the transaction is rolled back,
        and no partial data remains in the database.
        """
        temp_booking = TempServiceBookingFactory(
            service_type=self.service_type,
            service_profile=self.service_profile,
            customer_motorcycle=self.customer_motorcycle,
            payment_option='online_full',
            calculated_deposit_amount=Decimal('0.00'),
        )
        calculated_total = temp_booking.service_type.base_price
        amount_paid = calculated_total
        stripe_pi_id = 'pi_error_intent'

        # Mock the ServiceBooking.objects.create to raise an exception
        # This simulates a database error during the creation of the final booking.
        with patch('service.models.ServiceBooking.objects.create') as mock_create:
            mock_create.side_effect = Exception("Simulated database error during ServiceBooking creation")

            # Expect an exception to be raised by convert_temp_service_booking
            with self.assertRaises(Exception):
                convert_temp_service_booking(
                    temp_booking=temp_booking,
                    payment_method='online_full',
                    booking_payment_status='paid',
                    amount_paid_on_booking=amount_paid,
                    calculated_total_on_booking=calculated_total,
                    stripe_payment_intent_id=stripe_pi_id,
                    payment_obj=None,
                )

        # Assert that no ServiceBooking was created
        self.assertEqual(ServiceBooking.objects.count(), 0)
        # Assert that the TempServiceBooking was NOT deleted (rollback)
        self.assertTrue(TempServiceBooking.objects.filter(id=temp_booking.id).exists())
        self.assertEqual(TempServiceBooking.objects.count(), 1)


    def test_calculated_deposit_amount_default_if_none_in_temp(self):
        """
        Test that calculated_deposit_amount correctly defaults to Decimal('0.00')
        in ServiceBooking if it was None in TempServiceBooking.
        """
        temp_booking = TempServiceBookingFactory(
            service_type=self.service_type,
            service_profile=self.service_profile,
            customer_motorcycle=self.customer_motorcycle,
            payment_option='online_full',
            calculated_deposit_amount=None, # Explicitly set to None for this test
            customer_notes='Testing deposit default.',
        )
        calculated_total = temp_booking.service_type.base_price

        final_booking = convert_temp_service_booking(
            temp_booking=temp_booking,
            payment_method='online_full',
            booking_payment_status='paid',
            amount_paid_on_booking=calculated_total,
            calculated_total_on_booking=calculated_total,
            stripe_payment_intent_id='pi_deposit_test',
            payment_obj=None,
        )

        self.assertEqual(final_booking.calculated_deposit_amount, Decimal('0.00'))


    def test_currency_snapshot_from_settings(self):
        """
        Test that the currency of the ServiceBooking is taken from ServiceSettings.
        """
        # Change settings currency
        self.service_settings.currency_code = 'EUR'
        self.service_settings.save()

        temp_booking = TempServiceBookingFactory(
            service_type=self.service_type,
            service_profile=self.service_profile,
            customer_motorcycle=self.customer_motorcycle,
            payment_option='online_full',
            calculated_deposit_amount=Decimal('0.00'),
        )
        calculated_total = temp_booking.service_type.base_price

        final_booking = convert_temp_service_booking(
            temp_booking=temp_booking,
            payment_method='online_full',
            booking_payment_status='paid',
            amount_paid_on_booking=calculated_total,
            calculated_total_on_booking=calculated_total,
            stripe_payment_intent_id='pi_currency_test',
            payment_obj=None,
        )

        self.assertEqual(final_booking.currency, 'EUR')
        # If a payment object is also used, check its snapshot
        payment_obj = PaymentFactory(
            amount=calculated_total,
            currency='AUD', # This will be overridden by the snapshot
            status='succeeded',
            stripe_payment_intent_id='pi_currency_test_2',
        )
        
        final_booking_with_payment = convert_temp_service_booking(
            temp_booking=TempServiceBookingFactory(
                service_type=self.service_type,
                service_profile=self.service_profile,
                customer_motorcycle=self.customer_motorcycle,
                payment_option='online_full',
                calculated_deposit_amount=Decimal('0.00'),
            ),
            payment_method='online_full',
            booking_payment_status='paid',
            amount_paid_on_booking=calculated_total,
            calculated_total_on_booking=calculated_total,
            stripe_payment_intent_id='pi_currency_test_2',
            payment_obj=payment_obj,
        )
        
        payment_obj.refresh_from_db()
        self.assertIn('currency_code', payment_obj.refund_policy_snapshot)
        self.assertEqual(payment_obj.refund_policy_snapshot['currency_code'], 'EUR')

