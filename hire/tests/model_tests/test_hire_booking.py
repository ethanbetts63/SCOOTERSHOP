import datetime
from decimal import Decimal
from django.test import TestCase
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.utils import timezone
from unittest import mock
from django.db import IntegrityError # Import IntegrityError for uniqueness test

# Import model factories for easy test data creation
from hire.tests.test_helpers.model_factories import (
    create_hire_booking,
    create_motorcycle,
    create_driver_profile,
    create_package,
    create_hire_settings,
    create_payment,
    create_temp_hire_booking, # Added for conversion tests
    create_temp_booking_addon, # Added for conversion tests
    create_addon, # Added for conversion tests
)
from hire.models.hire_booking import HireBooking, PAYMENT_STATUS_CHOICES
from payments.models import Payment # Import Payment model
from hire.models import TempHireBooking, BookingAddOn, TempBookingAddOn # Import for conversion tests
from dashboard.models import HireSettings

# Import the webhook handler
from payments.webhook_handlers import handle_hire_booking_succeeded


class HireBookingModelTest(TestCase):
    """
    Unit tests for the HireBooking model, focusing on its clean() and save() methods.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up non-modified objects used by all test methods.
        This runs once for the entire test class.
        """
        # Create a default HireSettings instance for lead time tests
        cls.hire_settings = create_hire_settings(booking_lead_time_hours=2)

        # Create common related objects using factories
        cls.motorcycle = create_motorcycle()
        cls.driver_profile_aus = create_driver_profile(is_australian_resident=True)
        cls.driver_profile_int = create_driver_profile(is_australian_resident=False)
        cls.available_package = create_package(name="Available Pack", is_available=True)
        cls.unavailable_package = create_package(name="Unavailable Pack", is_available=False)

    def test_save_generates_booking_reference(self):
        """
        Test that the save method generates a booking_reference if one is not provided.
        """
        booking = create_hire_booking(
            motorcycle=self.motorcycle,
            driver_profile=self.driver_profile_aus,
            booking_reference=None # Explicitly set to None
        )
        self.assertIsNotNone(booking.booking_reference)
        self.assertTrue(booking.booking_reference.startswith("HIRE-"))
        self.assertEqual(len(booking.booking_reference), 4 + 1 + 8) # HIRE-XXXXXXXX

    def test_save_does_not_overwrite_booking_reference(self):
        """
        Test that the save method does not overwrite an existing booking_reference.
        """
        custom_ref = "CUSTOMREF123"
        booking = create_hire_booking(
            motorcycle=self.motorcycle,
            driver_profile=self.driver_profile_aus,
            booking_reference=custom_ref
        )
        # Save again to ensure it's not overwritten
        booking.save()
        self.assertEqual(booking.booking_reference, custom_ref)

    # --- clean() method tests ---

    def test_clean_return_date_before_pickup_date_raises_error(self):
        """
        Test that clean() raises ValidationError if return_date is before pickup_date.
        """
        pickup_date = timezone.now().date() + datetime.timedelta(days=5)
        return_date = pickup_date - datetime.timedelta(days=1) # Invalid return date

        booking = create_hire_booking(
            motorcycle=self.motorcycle,
            driver_profile=self.driver_profile_aus,
            pickup_date=pickup_date,
            return_date=return_date,
            grand_total=Decimal('100.00') # Ensure grand_total is valid to avoid other errors
        )
        with self.assertRaises(ValidationError) as cm:
            booking.clean()
        self.assertIn('return_date', cm.exception.message_dict)
        self.assertIn('return_time', cm.exception.message_dict)
        self.assertEqual(
            cm.exception.message_dict['return_date'][0],
            "Return date and time must be after pickup date and time."
        )

    def test_clean_return_time_before_pickup_time_on_same_day_raises_error(self):
        """
        Test that clean() raises ValidationError if return_time is before pickup_time
        on the same day.
        """
        pickup_date = timezone.now().date() + datetime.timedelta(days=5)
        pickup_time = datetime.time(14, 0)
        return_time = datetime.time(10, 0) # Invalid return time on same day

        booking = create_hire_booking(
            motorcycle=self.motorcycle,
            driver_profile=self.driver_profile_aus,
            pickup_date=pickup_date,
            pickup_time=pickup_time,
            return_date=pickup_date, # Same day
            return_time=return_time,
            grand_total=Decimal('100.00')
        )
        with self.assertRaises(ValidationError) as cm:
            booking.clean()
        self.assertIn('return_date', cm.exception.message_dict)
        self.assertIn('return_time', cm.exception.message_dict)
        self.assertEqual(
            cm.exception.message_dict['return_date'][0],
            "Return date and time must be after pickup date and time."
        )

    def test_clean_pickup_time_in_past_raises_error(self):
        """
        Test that clean() raises ValidationError if pickup_time is in the past
        relative to the booking lead time.
        """
        # Set lead time to 2 hours
        self.hire_settings.booking_lead_time_hours = 2
        self.hire_settings.save()

        # Define a fixed "now" for consistency
        fixed_now = timezone.make_aware(datetime.datetime(2025, 1, 1, 10, 0, 0))

        # Set pickup time to be 1 hour from fixed_now (violates 2-hour lead time)
        future_pickup_datetime = fixed_now + datetime.timedelta(hours=1)

        booking = create_hire_booking(
            motorcycle=self.motorcycle,
            driver_profile=self.driver_profile_aus,
            pickup_date=future_pickup_datetime.date(),
            pickup_time=future_pickup_datetime.time(),
            grand_total=Decimal('100.00')
        )

        with mock.patch('django.utils.timezone.now', return_value=fixed_now):
            with self.assertRaises(ValidationError) as cm:
                booking.clean()
            self.assertIn('pickup_date', cm.exception.message_dict)
            self.assertIn('pickup_time', cm.exception.message_dict)
            self.assertEqual(
                cm.exception.message_dict['pickup_date'][0],
                "Pickup must be at least 2 hours from now."
            )

    def test_clean_pickup_time_valid_with_lead_time(self):
        """
        Test that clean() passes if pickup_time is valid with lead time.
        """
        # Set lead time to 2 hours
        self.hire_settings.booking_lead_time_hours = 2
        self.hire_settings.save()

        # Define a fixed "now" for consistency
        fixed_now = timezone.make_aware(datetime.datetime(2025, 1, 1, 10, 0, 0))

        # Calculate the minimum valid pickup time based on fixed_now and lead time
        min_valid_pickup_datetime = fixed_now + datetime.timedelta(hours=self.hire_settings.booking_lead_time_hours)

        # Set pickup time to be safely after the minimum valid pickup time (e.g., 10 minutes later)
        safe_pickup_datetime = min_valid_pickup_datetime + datetime.timedelta(minutes=10)

        booking = create_hire_booking(
            motorcycle=self.motorcycle,
            driver_profile=self.driver_profile_aus,
            pickup_date=safe_pickup_datetime.date(),
            pickup_time=safe_pickup_datetime.time(),
            grand_total=Decimal('100.00')
        )
        # Patch timezone.now() to return our fixed_now for the duration of this test block
        with mock.patch('django.utils.timezone.now', return_value=fixed_now):
            try:
                booking.clean()
            except ValidationError:
                self.fail("ValidationError raised unexpectedly for valid pickup time.")

    def test_clean_negative_grand_total_raises_error(self):
        """
        Test that clean() raises ValidationError if grand_total is negative.
        """
        booking = create_hire_booking(
            motorcycle=self.motorcycle,
            driver_profile=self.driver_profile_aus,
            grand_total=Decimal('-10.00')
        )
        with self.assertRaises(ValidationError) as cm:
            booking.clean()
        self.assertIn('grand_total', cm.exception.message_dict)
        self.assertEqual(cm.exception.message_dict['grand_total'][0], "Grand total cannot be negative.")

    def test_clean_negative_total_hire_price_raises_error(self):
        """
        Test that clean() raises ValidationError if total_hire_price is negative.
        """
        booking = create_hire_booking(
            motorcycle=self.motorcycle,
            driver_profile=self.driver_profile_aus,
            grand_total=Decimal('100.00'),
            total_hire_price=Decimal('-10.00')
        )
        with self.assertRaises(ValidationError) as cm:
            booking.clean()
        self.assertIn('total_hire_price', cm.exception.message_dict)
        self.assertEqual(cm.exception.message_dict['total_hire_price'][0], "Total hire price cannot be negative.")

    def test_clean_negative_total_addons_price_raises_error(self):
        """
        Test that clean() raises ValidationError if total_addons_price is negative.
        """
        booking = create_hire_booking(
            motorcycle=self.motorcycle,
            driver_profile=self.driver_profile_aus,
            grand_total=Decimal('100.00'),
            total_addons_price=Decimal('-5.00')
        )
        with self.assertRaises(ValidationError) as cm:
            booking.clean()
        self.assertIn('total_addons_price', cm.exception.message_dict)
        self.assertEqual(cm.exception.message_dict['total_addons_price'][0], "Total add-ons price cannot be negative.")

    def test_clean_negative_total_package_price_raises_error(self):
        """
        Test that clean() raises ValidationError if total_package_price is negative.
        """
        booking = create_hire_booking(
            motorcycle=self.motorcycle,
            driver_profile=self.driver_profile_aus,
            package=self.available_package,
            grand_total=Decimal('100.00'),
            total_package_price=Decimal('-20.00')
        )
        with self.assertRaises(ValidationError) as cm:
            booking.clean()
        self.assertIn('total_package_price', cm.exception.message_dict)
        self.assertEqual(cm.exception.message_dict['total_package_price'][0], "Total package price cannot be negative.")


    def test_clean_negative_deposit_amount_raises_error(self):
        """
        Test that clean() raises ValidationError if deposit_amount is negative.
        """
        booking = create_hire_booking(
            motorcycle=self.motorcycle,
            driver_profile=self.driver_profile_aus,
            grand_total=Decimal('100.00'),
            deposit_amount=Decimal('-5.00')
        )
        with self.assertRaises(ValidationError) as cm:
            booking.clean()
        self.assertIn('deposit_amount', cm.exception.message_dict)
        self.assertEqual(cm.exception.message_dict['deposit_amount'][0], "Deposit amount cannot be negative.")

    def test_clean_negative_amount_paid_raises_error(self):
        """
        Test that clean() raises ValidationError if amount_paid is negative.
        """
        booking = create_hire_booking(
            motorcycle=self.motorcycle,
            driver_profile=self.driver_profile_aus,
            grand_total=Decimal('100.00'),
            amount_paid=Decimal('-1.00')
        )
        with self.assertRaises(ValidationError) as cm:
            booking.clean()
        self.assertIn('amount_paid', cm.exception.message_dict)
        self.assertEqual(cm.exception.message_dict['amount_paid'][0], "Amount paid cannot be negative.")

    def test_clean_paid_status_amount_not_equal_grand_total_raises_error(self):
        """
        Test that clean() raises ValidationError if payment_status is 'paid'
        but amount_paid does not equal grand_total.
        """
        booking = create_hire_booking(
            motorcycle=self.motorcycle,
            driver_profile=self.driver_profile_aus,
            grand_total=Decimal('100.00'),
            amount_paid=Decimal('50.00'), # Not fully paid
            payment_status='paid'
        )
        with self.assertRaises(ValidationError) as cm:
            booking.clean()
        self.assertIn('amount_paid', cm.exception.message_dict)
        self.assertEqual(
            cm.exception.message_dict['amount_paid'][0],
            "Amount paid must equal grand total when payment status is 'Paid'."
        )

    def test_clean_deposit_paid_status_no_deposit_amount_raises_error(self):
        """
        Test that clean() raises ValidationError if payment_status is 'deposit_paid'
        but deposit_amount is not set or is zero/negative.
        """
        booking = create_hire_booking(
            motorcycle=self.motorcycle,
            driver_profile=self.driver_profile_aus,
            grand_total=Decimal('100.00'),
            deposit_amount=Decimal('0.00'), # Invalid deposit amount
            amount_paid=Decimal('0.00'),
            payment_status='deposit_paid'
        )
        with self.assertRaises(ValidationError) as cm:
            booking.clean()
        self.assertIn('deposit_amount', cm.exception.message_dict)
        self.assertEqual(
            cm.exception.message_dict['deposit_amount'][0],
            "Deposit amount must be set when payment status is 'Deposit Paid'."
        )

    def test_clean_deposit_paid_status_amount_paid_not_equal_deposit_raises_error(self):
        """
        Test that clean() raises ValidationError if payment_status is 'deposit_paid'
        but amount_paid does not equal deposit_amount.
        """
        booking = create_hire_booking(
            motorcycle=self.motorcycle,
            driver_profile=self.driver_profile_aus,
            grand_total=Decimal('100.00'),
            deposit_amount=Decimal('20.00'),
            amount_paid=Decimal('10.00'), # Amount paid is not deposit amount
            payment_status='deposit_paid'
        )
        with self.assertRaises(ValidationError) as cm:
            booking.clean()
        self.assertIn('amount_paid', cm.exception.message_dict)
        self.assertEqual(
            cm.exception.message_dict['amount_paid'][0],
            "Amount paid must equal the deposit amount when payment status is 'Deposit Paid'."
        )

    def test_clean_negative_booked_daily_rate_raises_error(self):
        """
        Test that clean() raises ValidationError if booked_daily_rate is negative.
        """
        booking = create_hire_booking(
            motorcycle=self.motorcycle,
            driver_profile=self.driver_profile_aus,
            grand_total=Decimal('100.00'),
            booked_daily_rate=Decimal('-50.00')
        )
        with self.assertRaises(ValidationError) as cm:
            booking.clean()
        self.assertIn('booked_daily_rate', cm.exception.message_dict)
        self.assertEqual(cm.exception.message_dict['booked_daily_rate'][0], "Booked daily rate cannot be negative.")

    def test_clean_negative_booked_hourly_rate_raises_error(self):
        """
        Test that clean() raises ValidationError if booked_hourly_rate is negative.
        """
        booking = create_hire_booking(
            motorcycle=self.motorcycle,
            driver_profile=self.driver_profile_aus,
            grand_total=Decimal('100.00'),
            booked_hourly_rate=Decimal('-10.00')
        )
        with self.assertRaises(ValidationError) as cm:
            booking.clean()
        self.assertIn('booked_hourly_rate', cm.exception.message_dict)
        self.assertEqual(cm.exception.message_dict['booked_hourly_rate'][0], "Booked hourly rate cannot be negative.")


    def test_clean_unavailable_package_raises_error(self):
        """
        Test that clean() raises ValidationError if a selected package is not available.
        """
        booking = create_hire_booking(
            motorcycle=self.motorcycle,
            driver_profile=self.driver_profile_aus,
            package=self.unavailable_package, # This package is not available
            grand_total=Decimal('100.00')
        )
        with self.assertRaises(ValidationError) as cm:
            booking.clean()
        self.assertIn('package', cm.exception.message_dict)
        self.assertEqual(
            cm.exception.message_dict['package'][0],
            f"The selected package '{self.unavailable_package.name}' is currently not available."
        )

    def test_clean_international_booking_with_australian_resident_raises_error(self):
        """
        Test that clean() raises ValidationError if is_international_booking is True
        and the driver is an Australian resident.
        """
        booking = create_hire_booking(
            motorcycle=self.motorcycle,
            driver_profile=self.driver_profile_aus, # Australian resident
            is_international_booking=True,
            grand_total=Decimal('100.00')
        )
        with self.assertRaises(ValidationError) as cm:
            booking.clean()
        self.assertIn('is_international_booking', cm.exception.message_dict)
        self.assertEqual(
            cm.exception.message_dict['is_international_booking'][0],
            "Cannot mark as international booking if the driver is an Australian resident."
        )

    def test_clean_valid_booking_passes(self):
        """
        Test that a valid HireBooking instance passes clean() without errors.
        """
        # Set lead time to 0 for this test to simplify date calculation
        self.hire_settings.booking_lead_time_hours = 0
        self.hire_settings.save()

        pickup_date = timezone.now().date() + datetime.timedelta(days=1)
        pickup_time = datetime.time(10, 0)
        return_date = pickup_date + datetime.timedelta(days=2)
        return_time = datetime.time(16, 0)

        booking = create_hire_booking(
            motorcycle=self.motorcycle,
            driver_profile=self.driver_profile_int, # Non-Australian resident
            pickup_date=pickup_date,
            pickup_time=pickup_time,
            return_date=return_date,
            return_time=return_time,
            is_international_booking=True, # Valid for non-Australian resident
            booked_hourly_rate=Decimal('20.00'),
            booked_daily_rate=Decimal('100.00'),
            total_hire_price=Decimal('150.00'),
            total_addons_price=Decimal('20.00'),
            total_package_price=Decimal('30.00'),
            grand_total=Decimal('200.00'),
            deposit_amount=Decimal('50.00'),
            amount_paid=Decimal('50.00'),
            payment_status='deposit_paid',
            package=self.available_package,
        )
        try:
            booking.clean()
        except ValidationError:
            self.fail("ValidationError raised unexpectedly for a valid booking.")

    def test_clean_paid_status_with_full_payment_passes(self):
        """
        Test that a booking with 'paid' status and amount_paid equal to grand_total passes clean().
        """
        booking = create_hire_booking(
            motorcycle=self.motorcycle,
            driver_profile=self.driver_profile_aus,
            grand_total=Decimal('100.00'),
            amount_paid=Decimal('100.00'),
            payment_status='paid'
        )
        try:
            booking.clean()
        except ValidationError:
            self.fail("ValidationError raised unexpectedly for a fully paid booking.")

    def test_clean_unpaid_status_with_zero_amount_paid_passes(self):
        """
        Test that a booking with 'unpaid' status and zero amount_paid passes clean().
        """
        booking = create_hire_booking(
            motorcycle=self.motorcycle,
            driver_profile=self.driver_profile_aus,
            grand_total=Decimal('100.00'),
            amount_paid=Decimal('0.00'),
            payment_status='unpaid'
        )
        try:
            booking.clean()
        except ValidationError:
            self.fail("ValidationError raised unexpectedly for an unpaid booking.")

    def test_clean_payment_link_and_stripe_id_consistency(self):
        """
        Test that a booking can have a payment link and stripe ID.
        """
        # Create a Payment object with the correct field names
        payment_obj = create_payment(
            amount=Decimal('100.00'),
            currency='AUD',
            status='pending',
            stripe_payment_intent_id="pi_test_123", # Use correct field name
            stripe_payment_method_id="pm_test_abc" # Use correct field name
        )
        booking = create_hire_booking(
            motorcycle=self.motorcycle,
            driver_profile=self.driver_profile_aus,
            grand_total=Decimal('100.00'),
            payment=payment_obj,
            stripe_payment_intent_id="pi_test_123" # This is stored on HireBooking
        )
        try:
            booking.clean()
        except ValidationError:
            self.fail("ValidationError raised unexpectedly for booking with payment link and stripe ID.")

    def test_clean_unpaid_status_with_positive_amount_paid_passes(self):
        """
        Test that clean() passes even if payment_status is 'unpaid' but amount_paid is positive.
        The current clean() method allows this case to be handled by other logic if desired.
        """
        booking = create_hire_booking(
            motorcycle=self.motorcycle,
            driver_profile=self.driver_profile_aus,
            grand_total=Decimal('100.00'),
            amount_paid=Decimal('10.00'), # Positive amount paid, but status is 'unpaid'
            payment_status='unpaid'
        )
        try:
            booking.clean()
        except ValidationError:
            self.fail("ValidationError raised unexpectedly for 'unpaid' status with positive amount_paid.")

    # --- NEW TESTS FOR PAYMENT AND CONVERSION LOGIC ---

    def test_hire_booking_payment_linkage_on_creation(self):
        """
        Test that when a HireBooking is created with a Payment object,
        the linkage is correctly established in both directions.
        """
        payment_obj = create_payment(
            amount=Decimal('150.00'),
            currency='AUD',
            status='succeeded',
            stripe_payment_intent_id="pi_new_test_456"
        )
        hire_booking = create_hire_booking(
            motorcycle=self.motorcycle,
            driver_profile=self.driver_profile_aus,
            grand_total=Decimal('150.00'),
            payment=payment_obj,
            stripe_payment_intent_id="pi_new_test_456"
        )

        # Assert HireBooking links to Payment
        self.assertEqual(hire_booking.payment, payment_obj)

        # Explicitly set the ForeignKey on the Payment object
        payment_obj.hire_booking = hire_booking
        payment_obj.driver_profile = self.driver_profile_aus # Also set driver_profile
        payment_obj.save()

        # Assert Payment links back to HireBooking via the new ForeignKey
        # Refresh payment_obj from DB to ensure it has the latest state
        payment_obj.refresh_from_db()
        self.assertEqual(payment_obj.hire_booking, hire_booking)

        # Assert Payment also links to driver_profile
        self.assertEqual(payment_obj.driver_profile, self.driver_profile_aus)


    def test_stripe_payment_intent_id_uniqueness(self):
        """
        Test that creating two HireBookings with the same stripe_payment_intent_id
        raises an IntegrityError.
        """
        common_stripe_id = "pi_duplicate_id_789"
        create_hire_booking(
            motorcycle=self.motorcycle,
            driver_profile=self.driver_profile_aus,
            stripe_payment_intent_id=common_stripe_id
        )

        with self.assertRaises(IntegrityError) as cm:
            create_hire_booking(
                motorcycle=self.motorcycle,
                driver_profile=self.driver_profile_aus,
                stripe_payment_intent_id=common_stripe_id
            )
        self.assertIn("UNIQUE constraint failed: hire_hirebooking.stripe_payment_intent_id", str(cm.exception))


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

