from decimal import Decimal
from django.test import TestCase
from django.core.exceptions import ObjectDoesNotExist
from unittest import mock

# Import model factories for easy test data creation
from hire.tests.test_helpers.model_factories import (
    create_motorcycle,
    create_driver_profile,
    create_hire_settings,
    create_payment,
    create_temp_hire_booking, # Added for conversion tests
    create_temp_booking_addon, # Added for conversion tests
    create_addon, # Added for conversion tests
)
from hire.models.hire_booking import HireBooking, PAYMENT_STATUS_CHOICES
from hire.models import TempHireBooking, BookingAddOn, TempBookingAddOn # Import for conversion tests

# Import the webhook handler
from payments.webhook_handlers import handle_hire_booking_succeeded

class WebhookHandlerTest(TestCase):
    """
    Tests for the webhook handler functions, specifically focusing on booking conversion.
    """
    @classmethod
    def setUpTestData(cls):
        cls.hire_settings = create_hire_settings(booking_lead_time_hours=0) # Set to 0 for easier date handling
        cls.motorcycle = create_motorcycle()
        cls.driver_profile = create_driver_profile(is_australian_resident=True)
        cls.addon1 = create_addon(name="GPS", hourly_cost=Decimal('2.00'), daily_cost=Decimal('15.00'))
        cls.addon2 = create_addon(name="Jacket", hourly_cost=Decimal('5.00'), daily_cost=Decimal('25.00'))

    def test_handle_hire_booking_succeeded_full_conversion(self):
        """
        Tests the complete flow of handle_hire_booking_succeeded for a full payment.
        """
        # 1. Setup: Create TempHireBooking, Payment, and TempBookingAddOn
        temp_booking = create_temp_hire_booking(
            motorcycle=self.motorcycle,
            driver_profile=self.driver_profile,
            payment_option='online_full',
            grand_total=Decimal('200.00'),
            total_addons_price=Decimal('40.00'),
            total_hire_price=Decimal('160.00'),
            total_package_price=Decimal('0.00'),
            deposit_amount=Decimal('0.00'), # No deposit for full payment
            currency='AUD'
        )
        create_temp_booking_addon(temp_booking, self.addon1, quantity=1, booked_addon_price=self.addon1.daily_cost)
        create_temp_booking_addon(temp_booking, self.addon2, quantity=1, booked_addon_price=self.addon2.daily_cost)

        payment_obj = create_payment(
            amount=Decimal('200.00'),
            currency='AUD',
            status='requires_payment_method', # Initial status
            stripe_payment_intent_id="pi_full_payment_123",
        )
        # Link payment to temp_booking
        payment_obj.temp_hire_booking = temp_booking
        payment_obj.save()

        # Mock payment_intent_data (simplified for test)
        payment_intent_data = {
            'id': "pi_full_payment_123",
            'amount': 20000, # Cents
            'currency': 'aud',
            'status': 'succeeded',
            'metadata': {'booking_type': 'hire_booking', 'payment_id': str(payment_obj.id)}
        }

        # 2. Action: Call the handler
        handle_hire_booking_succeeded(payment_obj, payment_intent_data)

        # 3. Assertions
        # Check if TempHireBooking is deleted
        with self.assertRaises(ObjectDoesNotExist):
            TempHireBooking.objects.get(id=temp_booking.id)

        # Check if HireBooking is created
        hire_booking = HireBooking.objects.get(stripe_payment_intent_id="pi_full_payment_123")
        self.assertIsNotNone(hire_booking)
        self.assertEqual(hire_booking.grand_total, Decimal('200.00'))
        self.assertEqual(hire_booking.total_hire_price, Decimal('160.00'))
        self.assertEqual(hire_booking.total_addons_price, Decimal('40.00'))
        self.assertEqual(hire_booking.total_package_price, Decimal('0.00'))
        self.assertEqual(hire_booking.amount_paid, Decimal('200.00'))
        self.assertEqual(hire_booking.payment_status, 'paid')
        self.assertEqual(hire_booking.status, 'confirmed')
        self.assertEqual(hire_booking.motorcycle, self.motorcycle)
        self.assertEqual(hire_booking.driver_profile, self.driver_profile)

        # Check if Payment object is updated and linked
        payment_obj.refresh_from_db() # Get latest state from DB
        self.assertIsNone(payment_obj.temp_hire_booking) # Temp link removed
        self.assertEqual(payment_obj.hire_booking, hire_booking) # Permanent link established
        self.assertEqual(payment_obj.driver_profile, self.driver_profile) # Driver profile linked
        self.assertEqual(payment_obj.status, 'succeeded') # Status updated by webhook

        # Check if BookingAddOns are created
        booking_addons = BookingAddOn.objects.filter(booking=hire_booking)
        self.assertEqual(len(booking_addons), 2)
        self.assertTrue(booking_addons.filter(addon=self.addon1, quantity=1).exists())
        self.assertTrue(booking_addons.filter(addon=self.addon2, quantity=1).exists())

        # Check if TempBookingAddOns are deleted by filtering on the original temp_booking_id
        self.assertEqual(TempBookingAddOn.objects.filter(temp_booking__id=temp_booking.id).count(), 0)


    def test_handle_hire_booking_succeeded_deposit_payment(self):
        """
        Tests the complete flow of handle_hire_booking_succeeded for a deposit payment.
        """
        # 1. Setup: Create TempHireBooking, Payment, and TempBookingAddOn for deposit
        temp_booking = create_temp_hire_booking(
            motorcycle=self.motorcycle,
            driver_profile=self.driver_profile,
            payment_option='online_deposit',
            grand_total=Decimal('200.00'),
            total_hire_price=Decimal('150.00'),
            total_addons_price=Decimal('50.00'),
            total_package_price=Decimal('0.00'),
            deposit_amount=Decimal('50.00'), # Deposit amount
            currency='AUD'
        )
        payment_obj = create_payment(
            amount=Decimal('50.00'), # Only deposit amount paid
            currency='AUD',
            status='requires_payment_method',
            stripe_payment_intent_id="pi_deposit_payment_456",
        )
        payment_obj.temp_hire_booking = temp_booking
        payment_obj.save()

        payment_intent_data = {
            'id': "pi_deposit_payment_456",
            'amount': 5000, # Cents
            'currency': 'aud',
            'status': 'succeeded',
            'metadata': {'booking_type': 'hire_booking', 'payment_id': str(payment_obj.id)}
        }

        # 2. Action: Call the handler
        handle_hire_booking_succeeded(payment_obj, payment_intent_data)

        # 3. Assertions
        hire_booking = HireBooking.objects.get(stripe_payment_intent_id="pi_deposit_payment_456")
        self.assertEqual(hire_booking.grand_total, Decimal('200.00'))
        self.assertEqual(hire_booking.total_hire_price, Decimal('150.00'))
        self.assertEqual(hire_booking.total_addons_price, Decimal('50.00'))
        self.assertEqual(hire_booking.total_package_price, Decimal('0.00'))
        self.assertEqual(hire_booking.amount_paid, Decimal('50.00'))
        self.assertEqual(hire_booking.payment_status, 'deposit_paid') # Should be deposit_paid

        payment_obj.refresh_from_db()
        self.assertIsNone(payment_obj.temp_hire_booking)
        self.assertEqual(payment_obj.hire_booking, hire_booking)
        self.assertEqual(payment_obj.driver_profile, self.driver_profile)
        self.assertEqual(payment_obj.status, 'succeeded') # Status updated by webhook


    def test_handle_hire_booking_succeeded_temp_booking_does_not_exist(self):
        """
        Tests handle_hire_booking_succeeded when the associated TempHireBooking is missing.
        """
        # Create a payment object that is NOT linked to any existing TempHireBooking
        payment_obj = create_payment(
            amount=Decimal('100.00'),
            currency='AUD',
            status='succeeded',
            stripe_payment_intent_id="pi_missing_temp_booking_789",
        )
        # Do NOT link payment_obj.temp_hire_booking or link to a non-existent ID
        # For this test, we'll simulate a missing temp booking by not setting the link.

        payment_intent_data = {
            'id': "pi_missing_temp_booking_789",
            'amount': 10000,
            'currency': 'aud',
            'status': 'succeeded',
            'metadata': {'booking_type': 'hire_booking', 'payment_id': str(payment_obj.id)}
        }

        # Mock the logger to check if error is logged
        with mock.patch('payments.webhook_handlers.logger.error') as mock_logger_error:
            # The handler should now explicitly raise TempHireBooking.DoesNotExist
            with self.assertRaises(ObjectDoesNotExist):
                handle_hire_booking_succeeded(payment_obj, payment_intent_data)

            # Assert that the error was logged
            mock_logger_error.assert_called_with(
                f"TempHireBooking not found for Payment ID {payment_obj.id}. Cannot finalize booking."
            )

        # Assert no HireBooking was created
        self.assertEqual(HireBooking.objects.count(), 0)

        # Assert Payment object is NOT updated with hire_booking or driver_profile links
        payment_obj.refresh_from_db()
        self.assertIsNone(payment_obj.hire_booking)
        self.assertIsNone(payment_obj.driver_profile)


    def test_handle_hire_booking_succeeded_transaction_rollback_on_error(self):
        """
        Tests that the transaction rolls back if an error occurs during conversion.
        """
        # 1. Setup: Create TempHireBooking, Payment, and TempBookingAddOn
        temp_booking = create_temp_hire_booking(
            motorcycle=self.motorcycle,
            driver_profile=self.driver_profile,
            payment_option='online_full',
            grand_total=Decimal('200.00'),
            total_hire_price=Decimal('160.00'),
            total_addons_price=Decimal('40.00'),
            total_package_price=Decimal('0.00'),
            currency='AUD'
        )
        create_temp_booking_addon(temp_booking, self.addon1, quantity=1)

        payment_obj = create_payment(
            amount=Decimal('200.00'),
            currency='AUD',
            status='requires_payment_method',
            stripe_payment_intent_id="pi_rollback_test_123",
        )
        payment_obj.temp_hire_booking = temp_booking
        payment_obj.save()

        payment_intent_data = {
            'id': "pi_rollback_test_123",
            'amount': 20000,
            'currency': 'aud',
            'status': 'succeeded',
            'metadata': {'booking_type': 'hire_booking', 'payment_id': str(payment_obj.id)}
        }

        # Mock a critical error during the creation of BookingAddOn
        with mock.patch('hire.models.BookingAddOn.objects.create', side_effect=ValueError("Simulated DB error")):
            with self.assertRaises(ValueError): # Expecting the simulated error to be re-raised
                handle_hire_booking_succeeded(payment_obj, payment_intent_data)

        # Assertions: Check that everything was rolled back
        # TempHireBooking should NOT be deleted
        self.assertTrue(TempHireBooking.objects.filter(id=temp_booking.id).exists())
        # Check TempBookingAddOns by filtering on the original temp_booking_id
        self.assertEqual(TempBookingAddOn.objects.filter(temp_booking__id=temp_booking.id).count(), 1) # Temp add-on still exists

        # HireBooking should NOT be created
        self.assertEqual(HireBooking.objects.filter(stripe_payment_intent_id="pi_rollback_test_123").count(), 0)
        self.assertEqual(BookingAddOn.objects.count(), 0) # No permanent add-ons created

        # Payment object should NOT be updated (links should remain as they were)
        payment_obj.refresh_from_db()
        self.assertEqual(payment_obj.temp_hire_booking, temp_booking) # Temp link should still be there
        self.assertIsNone(payment_obj.hire_booking) # Permanent link should NOT be set
        self.assertIsNone(payment_obj.driver_profile) # Driver profile link should NOT be set

