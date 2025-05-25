import datetime
from decimal import Decimal
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone

# Import model factories for easy test data creation
from hire.tests.test_helpers.model_factories import (
    create_hire_booking,
    create_motorcycle,
    create_driver_profile,
    create_package,
    create_hire_settings,
    create_payment
)
from hire.models.hire_booking import HireBooking, PAYMENT_STATUS_CHOICES
from dashboard.models import HireSettings 


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
            total_price=Decimal('100.00') # Ensure total_price is valid to avoid other errors
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
            total_price=Decimal('100.00')
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

        # Set pickup time to be 1 hour from now (violates 2-hour lead time)
        future_pickup_datetime = timezone.now() + datetime.timedelta(hours=1)
        
        booking = create_hire_booking(
            motorcycle=self.motorcycle,
            driver_profile=self.driver_profile_aus,
            pickup_date=future_pickup_datetime.date(),
            pickup_time=future_pickup_datetime.time(),
            total_price=Decimal('100.00')
        )
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

        # Set pickup time to be 3 hours from now (valid)
        future_pickup_datetime = timezone.now() + datetime.timedelta(hours=3)

        booking = create_hire_booking(
            motorcycle=self.motorcycle,
            driver_profile=self.driver_profile_aus,
            pickup_date=future_pickup_datetime.date(),
            pickup_time=future_pickup_datetime.time(),
            total_price=Decimal('100.00')
        )
        try:
            booking.clean()
        except ValidationError:
            self.fail("ValidationError raised unexpectedly for valid pickup time.")

    def test_clean_negative_total_price_raises_error(self):
        """
        Test that clean() raises ValidationError if total_price is negative.
        """
        booking = create_hire_booking(
            motorcycle=self.motorcycle,
            driver_profile=self.driver_profile_aus,
            total_price=Decimal('-10.00')
        )
        with self.assertRaises(ValidationError) as cm:
            booking.clean()
        self.assertIn('total_price', cm.exception.message_dict)
        self.assertEqual(cm.exception.message_dict['total_price'][0], "Total price cannot be negative.")

    def test_clean_negative_deposit_amount_raises_error(self):
        """
        Test that clean() raises ValidationError if deposit_amount is negative.
        """
        booking = create_hire_booking(
            motorcycle=self.motorcycle,
            driver_profile=self.driver_profile_aus,
            total_price=Decimal('100.00'),
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
            total_price=Decimal('100.00'),
            amount_paid=Decimal('-1.00')
        )
        with self.assertRaises(ValidationError) as cm:
            booking.clean()
        self.assertIn('amount_paid', cm.exception.message_dict)
        self.assertEqual(cm.exception.message_dict['amount_paid'][0], "Amount paid cannot be negative.")

    def test_clean_paid_status_amount_not_equal_total_raises_error(self):
        """
        Test that clean() raises ValidationError if payment_status is 'paid'
        but amount_paid does not equal total_price.
        """
        booking = create_hire_booking(
            motorcycle=self.motorcycle,
            driver_profile=self.driver_profile_aus,
            total_price=Decimal('100.00'),
            amount_paid=Decimal('50.00'), # Not fully paid
            payment_status='paid'
        )
        with self.assertRaises(ValidationError) as cm:
            booking.clean()
        self.assertIn('amount_paid', cm.exception.message_dict)
        self.assertEqual(
            cm.exception.message_dict['amount_paid'][0],
            "Amount paid must equal total price when payment status is 'Paid'."
        )

    def test_clean_deposit_paid_status_no_deposit_amount_raises_error(self):
        """
        Test that clean() raises ValidationError if payment_status is 'deposit_paid'
        but deposit_amount is not set or is zero/negative.
        """
        booking = create_hire_booking(
            motorcycle=self.motorcycle,
            driver_profile=self.driver_profile_aus,
            total_price=Decimal('100.00'),
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
            total_price=Decimal('100.00'),
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
            total_price=Decimal('100.00'),
            booked_daily_rate=Decimal('-50.00')
        )
        with self.assertRaises(ValidationError) as cm:
            booking.clean()
        self.assertIn('booked_daily_rate', cm.exception.message_dict)
        self.assertEqual(cm.exception.message_dict['booked_daily_rate'][0], "Booked daily rate cannot be negative.")

    def test_clean_negative_booked_package_price_raises_error(self):
        """
        Test that clean() raises ValidationError if booked_package_price is negative.
        """
        booking = create_hire_booking(
            motorcycle=self.motorcycle,
            driver_profile=self.driver_profile_aus,
            package=self.available_package,
            total_price=Decimal('100.00'),
            booked_package_price=Decimal('-20.00')
        )
        with self.assertRaises(ValidationError) as cm:
            booking.clean()
        self.assertIn('booked_package_price', cm.exception.message_dict)
        self.assertEqual(cm.exception.message_dict['booked_package_price'][0], "Booked package price cannot be negative.")

    def test_clean_unavailable_package_raises_error(self):
        """
        Test that clean() raises ValidationError if a selected package is not available.
        """
        booking = create_hire_booking(
            motorcycle=self.motorcycle,
            driver_profile=self.driver_profile_aus,
            package=self.unavailable_package, 
            total_price=Decimal('100.00')
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
            total_price=Decimal('100.00')
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
            total_price=Decimal('200.00'),
            deposit_amount=Decimal('50.00'),
            amount_paid=Decimal('50.00'),
            payment_status='deposit_paid',
            package=self.available_package,
            booked_package_price=Decimal('30.00')
        )
        try:
            booking.clean()
        except ValidationError:
            self.fail("ValidationError raised unexpectedly for a valid booking.")

    def test_clean_paid_status_with_full_payment_passes(self):
        """
        Test that a booking with 'paid' status and amount_paid equal to total_price passes clean().
        """
        booking = create_hire_booking(
            motorcycle=self.motorcycle,
            driver_profile=self.driver_profile_aus,
            total_price=Decimal('100.00'),
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
            total_price=Decimal('100.00'),
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
        payment_obj = create_payment(payment_intent_id="pi_test_123")
        booking = create_hire_booking(
            motorcycle=self.motorcycle,
            driver_profile=self.driver_profile_aus,
            total_price=Decimal('100.00'),
            payment=payment_obj,
            stripe_payment_intent_id="pi_test_123"
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
            total_price=Decimal('100.00'),
            amount_paid=Decimal('10.00'), # Positive amount paid, but status is 'unpaid'
            payment_status='unpaid'
        )
        try:
            booking.clean()
        except ValidationError:
            self.fail("ValidationError raised unexpectedly for 'unpaid' status with positive amount_paid.")

