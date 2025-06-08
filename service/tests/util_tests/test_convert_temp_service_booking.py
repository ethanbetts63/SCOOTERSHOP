from django.test import TestCase
from django.db import transaction
from decimal import Decimal
import datetime
from unittest.mock import patch

from service.utils.convert_temp_service_booking import convert_temp_service_booking
from service.utils.get_available_service_dropoff_times import get_available_dropoff_times
from service.models import ServiceBooking, TempServiceBooking
from payments.models import Payment
from ..test_helpers.model_factories import (
    TempServiceBookingFactory,
    ServiceBookingFactory,
    PaymentFactory,
    ServiceSettingsFactory,
    ServiceProfileFactory,
    CustomerMotorcycleFactory,
    ServiceTypeFactory,
    RefundPolicySettingsFactory, # Import RefundPolicySettingsFactory
)
from payments.models import RefundPolicySettings


class ConvertTempToFinalServiceTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        ServiceSettingsFactory.create(pk=1)
        RefundPolicySettingsFactory.create(pk=1) # Ensure RefundPolicySettings exists
        cls.service_type = ServiceTypeFactory()
        cls.service_profile = ServiceProfileFactory()
        cls.customer_motorcycle = CustomerMotorcycleFactory(service_profile=cls.service_profile)


    def setUp(self):
        ServiceBooking.objects.all().delete()
        TempServiceBooking.objects.all().delete()
        Payment.objects.all().delete()
        self.service_settings = ServiceSettingsFactory(pk=1) # Ensure fresh service settings for each test
        self.refund_settings = RefundPolicySettings.objects.get(pk=1) # Retrieve refund settings for assertions


    def test_successful_conversion_without_payment_obj(self):
        temp_booking = TempServiceBookingFactory(
            service_type=self.service_type,
            service_profile=self.service_profile,
            customer_motorcycle=self.customer_motorcycle,
            payment_option='in_store_full',
            calculated_deposit_amount=Decimal('0.00'),
            customer_notes='Test notes for in-store booking.',
        )

        initial_temp_booking_count = TempServiceBooking.objects.count()
        initial_service_booking_count = ServiceBooking.objects.count()

        payment_method = 'in_store_full'
        booking_payment_status = 'pending'
        amount_paid_on_booking = Decimal('0.00')
        calculated_total = temp_booking.service_type.base_price

        final_booking = convert_temp_service_booking(
            temp_booking=temp_booking,
            payment_method=payment_method,
            booking_payment_status=booking_payment_status,
            amount_paid_on_booking=amount_paid_on_booking,
            calculated_total_on_booking=calculated_total,
            stripe_payment_intent_id=None,
            payment_obj=None,
        )

        self.assertIsNotNone(final_booking)
        self.assertEqual(ServiceBooking.objects.count(), initial_service_booking_count + 1)
        self.assertEqual(TempServiceBooking.objects.count(), initial_temp_booking_count - 1)
        self.assertFalse(TempServiceBooking.objects.filter(id=temp_booking.id).exists())

        self.assertEqual(final_booking.service_type, temp_booking.service_type)
        self.assertEqual(final_booking.service_profile, temp_booking.service_profile)
        self.assertEqual(final_booking.customer_motorcycle, temp_booking.customer_motorcycle)
        self.assertEqual(final_booking.payment_option, temp_booking.payment_option)
        self.assertEqual(final_booking.calculated_total, calculated_total)
        self.assertEqual(final_booking.calculated_deposit_amount, Decimal('0.00'))
        self.assertEqual(final_booking.amount_paid, amount_paid_on_booking)
        self.assertEqual(final_booking.payment_status, booking_payment_status)
        self.assertEqual(final_booking.payment_method, payment_method)
        self.assertEqual(final_booking.currency, self.service_settings.currency_code)
        self.assertIsNone(final_booking.stripe_payment_intent_id)
        self.assertEqual(final_booking.service_date, temp_booking.service_date)
        self.assertEqual(final_booking.dropoff_date, temp_booking.dropoff_date)
        self.assertEqual(final_booking.dropoff_time, temp_booking.dropoff_time)
        self.assertEqual(final_booking.estimated_pickup_date, temp_booking.estimated_pickup_date)
        self.assertEqual(final_booking.booking_status, 'confirmed')
        self.assertEqual(final_booking.customer_notes, temp_booking.customer_notes)
        self.assertIsNone(final_booking.payment)

        self.assertIsNotNone(final_booking.service_booking_reference)
        # Changed prefix to match SVC-
        self.assertTrue(final_booking.service_booking_reference.startswith('SVC-'))


    def test_successful_conversion_with_payment_obj(self):
        temp_booking = TempServiceBookingFactory(
            service_type=self.service_type,
            service_profile=self.service_profile,
            customer_motorcycle=self.customer_motorcycle,
            payment_option='online_full',
            calculated_deposit_amount=Decimal('0.00'),
        )
        calculated_total = temp_booking.service_type.base_price + Decimal('50.00')
        amount_paid = calculated_total
        stripe_pi_id = 'pi_test_intent_123'

        payment_obj = PaymentFactory(
            amount=amount_paid,
            currency='AUD',
            status='succeeded',
            stripe_payment_intent_id=stripe_pi_id,
            # Ensure these are explicitly None if not being tested
            temp_hire_booking=None, 
            hire_booking=None,
            driver_profile=None,
            temp_service_booking=temp_booking, # Link temp_booking here for initial state
            service_customer_profile=temp_booking.service_profile, # Link profile here for initial state
        )

        initial_temp_booking_count = TempServiceBooking.objects.count()
        initial_service_booking_count = ServiceBooking.objects.count()
        
        final_booking = convert_temp_service_booking(
            temp_booking=temp_booking,
            payment_method='online_full',
            booking_payment_status='paid',
            amount_paid_on_booking=amount_paid,
            calculated_total_on_booking=calculated_total,
            stripe_payment_intent_id=stripe_pi_id,
            payment_obj=payment_obj,
        )

        payment_obj.refresh_from_db()

        self.assertIsNotNone(final_booking)
        self.assertEqual(ServiceBooking.objects.count(), initial_service_booking_count + 1)
        self.assertEqual(TempServiceBooking.objects.count(), initial_temp_booking_count - 1)
        self.assertFalse(TempServiceBooking.objects.filter(id=temp_booking.id).exists())

        self.assertEqual(final_booking.calculated_total, calculated_total)
        self.assertEqual(final_booking.amount_paid, amount_paid)
        self.assertEqual(final_booking.payment_status, 'paid')
        self.assertEqual(final_booking.payment_method, 'online_full')
        self.assertEqual(final_booking.stripe_payment_intent_id, stripe_pi_id)
        self.assertEqual(final_booking.currency, self.service_settings.currency_code)
        self.assertEqual(final_booking.booking_status, 'confirmed')

        self.assertIsNotNone(final_booking.payment)
        self.assertEqual(final_booking.payment.id, payment_obj.id)
        self.assertEqual(payment_obj.service_booking, final_booking)
        self.assertEqual(payment_obj.service_customer_profile, final_booking.service_profile)
        
        self.assertIsNone(payment_obj.temp_service_booking)

        # Assert specific keys are present in the snapshot (populated by Payment.save())
        self.assertIn('cancellation_full_payment_full_refund_days', payment_obj.refund_policy_snapshot)
        self.assertIn('stripe_fee_fixed_domestic', payment_obj.refund_policy_snapshot)
        self.assertEqual(payment_obj.refund_policy_snapshot['cancellation_full_payment_full_refund_days'], float(self.refund_settings.cancellation_full_payment_full_refund_days))


    def test_transaction_rollback_on_error(self):
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

        with patch('service.models.ServiceBooking.objects.create') as mock_create:
            mock_create.side_effect = Exception("Simulated database error during ServiceBooking creation")

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

        self.assertEqual(ServiceBooking.objects.count(), 0)
        self.assertTrue(TempServiceBooking.objects.filter(id=temp_booking.id).exists())
        self.assertEqual(TempServiceBooking.objects.count(), 1)


    def test_calculated_deposit_amount_default_if_none_in_temp(self):
        temp_booking = TempServiceBookingFactory(
            service_type=self.service_type,
            service_profile=self.service_profile,
            customer_motorcycle=self.customer_motorcycle,
            payment_option='online_full',
            calculated_deposit_amount=None,
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
        # Update ServiceSettings currency code
        self.service_settings.currency_code = 'EUR'
        self.service_settings.save()

        # Update RefundPolicySettings currency code (if it were part of the snapshot)
        # Note: currency_code is a field on Payment and ServiceBooking, not RefundPolicySettings.
        # So, we expect payment_obj.currency to be 'EUR', not in refund_policy_snapshot.
        # However, for the purpose of demonstrating the snapshot itself,
        # we can assert on other refund policy fields that ARE in the snapshot.

        temp_booking = TempServiceBookingFactory(
            service_type=self.service_type,
            service_profile=self.service_profile,
            customer_motorcycle=self.customer_motorcycle,
            payment_option='online_full',
            calculated_deposit_amount=Decimal('0.00'),
        )
        calculated_total = temp_booking.service_type.base_price

        # First, test without a pre-existing payment object
        final_booking_without_payment = convert_temp_service_booking(
            temp_booking=temp_booking,
            payment_method='online_full',
            booking_payment_status='paid',
            amount_paid_on_booking=calculated_total,
            calculated_total_on_booking=calculated_total,
            stripe_payment_intent_id='pi_currency_test_no_obj',
            payment_obj=None, # No payment_obj provided, so it's created internally if needed
        )
        self.assertEqual(final_booking_without_payment.currency, 'EUR')


        # Now, test with a pre-existing payment object
        payment_obj = PaymentFactory(
            amount=calculated_total,
            currency='AUD', # This will be overwritten by the Payment.save() logic
            status='succeeded',
            stripe_payment_intent_id='pi_currency_test_2',
            temp_service_booking=TempServiceBookingFactory(), # Create a new temp booking for this payment
            service_customer_profile=ServiceProfileFactory(), # Create a new profile for this payment
        )
        
        final_booking_with_payment = convert_temp_service_booking(
            temp_booking=payment_obj.temp_service_booking, # Use the temp booking linked to payment_obj
            payment_method='online_full',
            booking_payment_status='paid',
            amount_paid_on_booking=calculated_total,
            calculated_total_on_booking=calculated_total,
            stripe_payment_intent_id='pi_currency_test_2',
            payment_obj=payment_obj,
        )
        
        payment_obj.refresh_from_db()
        # Assert that the currency on the Payment object itself is correct
        self.assertEqual(payment_obj.currency, 'EUR') 

        # Assert that a key from the refund policy snapshot is present and correct
        self.assertIn('cancellation_full_payment_full_refund_days', payment_obj.refund_policy_snapshot)
        self.assertEqual(
            payment_obj.refund_policy_snapshot['cancellation_full_payment_full_refund_days'], 
            float(self.refund_settings.cancellation_full_payment_full_refund_days)
        )
        # Also assert that the service customer profile is linked correctly if a payment object is present
        self.assertEqual(payment_obj.service_customer_profile, final_booking_with_payment.service_profile)

