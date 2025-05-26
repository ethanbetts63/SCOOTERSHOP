import datetime
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone

# Import models
from inventory.models import Motorcycle
from hire.models import HireBooking
from dashboard.models import HireSettings

# Import utility functions to be tested
from hire.views.utils import (
    calculate_hire_price,
    calculate_hire_duration_days,
    get_overlapping_motorcycle_bookings
)

# Import model factories for easy object creation
from hire.tests.test_helpers.model_factories import (
    create_motorcycle,
    create_hire_settings,
    create_hire_booking,
    create_driver_profile,
)


class HireUtilsTests(TestCase):
    """
    Tests for utility functions in hire/views/utils.py
    """

    def setUp(self):
        """
        Set up common test data for all tests.
        """
        self.motorcycle_with_daily_rate = create_motorcycle(
            daily_hire_rate=Decimal('100.00'),
            hourly_hire_rate=Decimal('20.00')
        )
        self.motorcycle_no_rate = create_motorcycle(
            daily_hire_rate=None,
            hourly_hire_rate=None # Ensure no hourly rate as well
        )
        self.hire_settings = create_hire_settings(
            default_daily_rate=Decimal('90.00'),
            default_hourly_rate=Decimal('15.00')
        )
        self.driver_profile = create_driver_profile()

        # Ensure HireSettings exists for tests that rely on it
        if not HireSettings.objects.exists():
            create_hire_settings()

    # --- calculate_hire_price Tests ---

    def test_calculate_hire_price_daily_rate_motorcycle_specific(self):
        """
        Test calculate_hire_price when motorcycle has a daily rate for multi-day hire.
        """
        pickup_date = timezone.now().date() + datetime.timedelta(days=1)
        pickup_time = datetime.time(9, 0)
        return_date = pickup_date + datetime.timedelta(days=3) # 3 billing days
        return_time = datetime.time(17, 0) # Later time to ensure full day count

        expected_price = self.motorcycle_with_daily_rate.daily_hire_rate * 3
        calculated_price = calculate_hire_price(
            self.motorcycle_with_daily_rate, pickup_date, return_date, pickup_time, return_time, self.hire_settings
        )
        self.assertEqual(calculated_price, expected_price)

    def test_calculate_hire_price_daily_rate_default(self):
        """
        Test calculate_hire_price when motorcycle has no daily rate,
        should use default from HireSettings for multi-day hire.
        """
        pickup_date = timezone.now().date() + datetime.timedelta(days=1)
        pickup_time = datetime.time(9, 0)
        return_date = pickup_date + datetime.timedelta(days=2) # 2 billing days
        return_time = datetime.time(10, 0) # Later time to ensure full day count

        expected_price = self.hire_settings.default_daily_rate * 2
        calculated_price = calculate_hire_price(
            self.motorcycle_no_rate, pickup_date, return_date, pickup_time, return_time, self.hire_settings
        )
        self.assertEqual(calculated_price, expected_price)

    def test_calculate_hire_price_hourly_rate_motorcycle_specific(self):
        """
        Test calculate_hire_price when motorcycle has an hourly rate for same-day hire.
        """
        pickup_date = timezone.now().date()
        pickup_time = datetime.time(9, 0)
        return_date = pickup_date
        return_time = datetime.time(11, 30) # 2.5 hours, should round up to 3 hours

        expected_price = self.motorcycle_with_daily_rate.hourly_hire_rate * 3 # 3 hours
        calculated_price = calculate_hire_price(
            self.motorcycle_with_daily_rate, pickup_date, return_date, pickup_time, return_time, self.hire_settings
        )
        self.assertEqual(calculated_price, expected_price)

    def test_calculate_hire_price_hourly_rate_default(self):
        """
        Test calculate_hire_price when motorcycle has no hourly rate,
        should use default from HireSettings for same-day hire.
        """
        pickup_date = timezone.now().date()
        pickup_time = datetime.time(14, 0)
        return_date = pickup_date
        return_time = datetime.time(14, 50) # 50 minutes, should round up to 1 hour

        expected_price = self.hire_settings.default_hourly_rate * 1 # 1 hour
        calculated_price = calculate_hire_price(
            self.motorcycle_no_rate, pickup_date, return_date, pickup_time, return_time, self.hire_settings
        )
        self.assertEqual(calculated_price, expected_price)

    def test_calculate_hire_price_zero_duration(self):
        """
        Test calculate_hire_price with zero duration (return_datetime <= pickup_datetime).
        """
        pickup_date = timezone.now().date() + datetime.timedelta(days=1)
        pickup_time = datetime.time(9, 0)
        return_date = pickup_date
        return_time = pickup_time # Same time, so 0 duration

        expected_price = Decimal('0.00')
        calculated_price = calculate_hire_price(
            self.motorcycle_with_daily_rate, pickup_date, return_date, pickup_time, return_time, self.hire_settings
        )
        self.assertEqual(calculated_price, expected_price)

    def test_calculate_hire_price_less_than_one_hour_positive_duration(self):
        """
        Test calculate_hire_price for a very short positive duration (e.g., 15 minutes).
        Should round up to 1 hour.
        """
        pickup_date = timezone.now().date()
        pickup_time = datetime.time(9, 0)
        return_date = pickup_date
        return_time = datetime.time(9, 15) # 15 minutes

        expected_price = self.motorcycle_with_daily_rate.hourly_hire_rate * 1 # Rounds up to 1 hour
        calculated_price = calculate_hire_price(
            self.motorcycle_with_daily_rate, pickup_date, return_date, pickup_time, return_time, self.hire_settings
        )
        self.assertEqual(calculated_price, expected_price)

    # --- calculate_hire_duration_days Tests (already correctly structured) ---

    def test_calculate_hire_duration_days_same_day_hire(self):
        """
        Test calculate_hire_duration_days for a hire within the same day.
        """
        pickup_date = timezone.now().date()
        pickup_time = datetime.time(9, 0)
        return_date = pickup_date
        return_time = datetime.time(17, 0)
        duration = calculate_hire_duration_days(
            pickup_date, return_date, pickup_time, return_time
        )
        self.assertEqual(duration, 1)

    def test_calculate_hire_duration_days_exact_24_hours(self):
        """
        Test calculate_hire_duration_days for an exact 24-hour period.
        """
        pickup_date = timezone.now().date()
        pickup_time = datetime.time(9, 0)
        return_date = pickup_date + datetime.timedelta(days=1)
        return_time = datetime.time(9, 0)
        duration = calculate_hire_duration_days(
            pickup_date, return_date, pickup_time, return_time
        )
        self.assertEqual(duration, 1)

    def test_calculate_hire_duration_days_multi_day_different_times(self):
        """
        Test calculate_hire_duration_days for multi-day hire with different times.
        """
        pickup_date = timezone.now().date()
        pickup_time = datetime.time(9, 0)
        return_date = pickup_date + datetime.timedelta(days=2)
        return_time = datetime.time(17, 0) # Return later than pickup on final day
        duration = calculate_hire_duration_days(
            pickup_date, return_date, pickup_time, return_time
        )
        self.assertEqual(duration, 3) # Day 1 (partial), Day 2 (full), Day 3 (partial)

    def test_calculate_hire_duration_days_multi_day_earlier_return_time(self):
        """
        Test calculate_hire_duration_days for multi-day hire with earlier return time.
        """
        pickup_date = timezone.now().date()
        pickup_time = datetime.time(17, 0)
        return_date = pickup_date + datetime.timedelta(days=2)
        return_time = datetime.time(9, 0) # Return earlier than pickup on final day
        duration = calculate_hire_duration_days(
            pickup_date, return_date, pickup_time, return_time
        )
        self.assertEqual(duration, 2) # Day 1 (partial), Day 2 (full)

    def test_calculate_hire_duration_days_return_before_pickup(self):
        """
        Test calculate_hire_duration_days when return datetime is before pickup datetime.
        """
        pickup_date = timezone.now().date() + datetime.timedelta(days=1)
        pickup_time = datetime.time(9, 0)
        return_date = timezone.now().date()
        return_time = datetime.time(17, 0)
        duration = calculate_hire_duration_days(
            pickup_date, return_date, pickup_time, return_time
        )
        self.assertEqual(duration, 0)

    def test_calculate_hire_duration_days_return_equal_pickup(self):
        """
        Test calculate_hire_duration_days when return datetime is equal to pickup datetime.
        """
        pickup_date = timezone.now().date()
        pickup_time = datetime.time(9, 0)
        return_date = pickup_date
        return_time = pickup_time
        duration = calculate_hire_duration_days(
            pickup_date, return_date, pickup_time, return_time
        )
        self.assertEqual(duration, 0)

    # --- get_overlapping_motorcycle_bookings Tests (unchanged as they already use separate date/time args) ---

    def test_get_overlapping_motorcycle_bookings_no_overlap(self):
        """
        Test get_overlapping_motorcycle_bookings with no overlapping bookings.
        """
        # Existing booking: Day 1 10:00 to Day 2 10:00
        create_hire_booking(
            motorcycle=self.motorcycle_with_daily_rate,
            driver_profile=self.driver_profile,
            pickup_date=timezone.now().date() + datetime.timedelta(days=1),
            pickup_time=datetime.time(10, 0),
            return_date=timezone.now().date() + datetime.timedelta(days=2),
            return_time=datetime.time(10, 0),
        )

        # Check period: Day 3 10:00 to Day 4 10:00 (no overlap)
        pickup_date = timezone.now().date() + datetime.timedelta(days=3)
        pickup_time = datetime.time(10, 0)
        return_date = timezone.now().date() + datetime.timedelta(days=4)
        return_time = datetime.time(10, 0)

        overlaps = get_overlapping_motorcycle_bookings(
            self.motorcycle_with_daily_rate, pickup_date, pickup_time, return_date, return_time
        )
        self.assertEqual(len(overlaps), 0)

    def test_get_overlapping_motorcycle_bookings_full_overlap(self):
        """
        Test get_overlapping_motorcycle_bookings with a full overlap.
        """
        # Existing booking: Day 1 10:00 to Day 5 10:00
        booking1 = create_hire_booking(
            motorcycle=self.motorcycle_with_daily_rate,
            driver_profile=self.driver_profile,
            pickup_date=timezone.now().date() + datetime.timedelta(days=1),
            pickup_time=datetime.time(10, 0),
            return_date=timezone.now().date() + datetime.timedelta(days=5),
            return_time=datetime.time(10, 0),
        )

        # Check period: Day 2 10:00 to Day 3 10:00 (full overlap within booking1)
        pickup_date = timezone.now().date() + datetime.timedelta(days=2)
        pickup_time = datetime.time(10, 0)
        return_date = timezone.now().date() + datetime.timedelta(days=3)
        return_time = datetime.time(10, 0)

        overlaps = get_overlapping_motorcycle_bookings(
            self.motorcycle_with_daily_rate, pickup_date, pickup_time, return_date, return_time
        )
        self.assertEqual(len(overlaps), 1)
        self.assertIn(booking1, overlaps)

    def test_get_overlapping_motorcycle_bookings_partial_overlap_start_within(self):
        """
        Test get_overlapping_motorcycle_bookings with partial overlap (start within, end after).
        """
        # Existing booking: Day 1 10:00 to Day 3 10:00
        booking1 = create_hire_booking(
            motorcycle=self.motorcycle_with_daily_rate,
            driver_profile=self.driver_profile,
            pickup_date=timezone.now().date() + datetime.timedelta(days=1),
            pickup_time=datetime.time(10, 0),
            return_date=timezone.now().date() + datetime.timedelta(days=3),
            return_time=datetime.time(10, 0),
        )

        # Check period: Day 2 10:00 to Day 4 10:00 (overlaps with booking1)
        pickup_date = timezone.now().date() + datetime.timedelta(days=2)
        pickup_time = datetime.time(10, 0)
        return_date = timezone.now().date() + datetime.timedelta(days=4)
        return_time = datetime.time(10, 0)

        overlaps = get_overlapping_motorcycle_bookings(
            self.motorcycle_with_daily_rate, pickup_date, pickup_time, return_date, return_time
        )
        self.assertEqual(len(overlaps), 1)
        self.assertIn(booking1, overlaps)

    def test_get_overlapping_motorcycle_bookings_partial_overlap_end_within(self):
        """
        Test get_overlapping_motorcycle_bookings with partial overlap (start before, end within).
        """
        # Existing booking: Day 2 10:00 to Day 4 10:00
        booking1 = create_hire_booking(
            motorcycle=self.motorcycle_with_daily_rate,
            driver_profile=self.driver_profile,
            pickup_date=timezone.now().date() + datetime.timedelta(days=2),
            pickup_time=datetime.time(10, 0),
            return_date=timezone.now().date() + datetime.timedelta(days=4),
            return_time=datetime.time(10, 0),
        )

        # Check period: Day 1 10:00 to Day 3 10:00 (overlaps with booking1)
        pickup_date = timezone.now().date() + datetime.timedelta(days=1)
        pickup_time = datetime.time(10, 0)
        return_date = timezone.now().date() + datetime.timedelta(days=3)
        return_time = datetime.time(10, 0)

        overlaps = get_overlapping_motorcycle_bookings(
            self.motorcycle_with_daily_rate, pickup_date, pickup_time, return_date, return_time
        )
        self.assertEqual(len(overlaps), 1)
        self.assertIn(booking1, overlaps)

    def test_get_overlapping_motorcycle_bookings_adjacent_bookings(self):
        """
        Test get_overlapping_motorcycle_bookings with adjacent bookings (no overlap).
        """
        # Existing booking: Day 1 10:00 to Day 2 10:00
        create_hire_booking(
            motorcycle=self.motorcycle_with_daily_rate,
            driver_profile=self.driver_profile,
            pickup_date=timezone.now().date() + datetime.timedelta(days=1),
            pickup_time=datetime.time(10, 0),
            return_date=timezone.now().date() + datetime.timedelta(days=2),
            return_time=datetime.time(10, 0),
        )

        # Check period: Day 2 10:00 to Day 3 10:00 (adjacent, no overlap based on [start, end) interval)
        pickup_date = timezone.now().date() + datetime.timedelta(days=2)
        pickup_time = datetime.time(10, 0)
        return_date = timezone.now().date() + datetime.timedelta(days=3)
        return_time = datetime.time(10, 0)

        overlaps = get_overlapping_motorcycle_bookings(
            self.motorcycle_with_daily_rate, pickup_date, pickup_time, return_date, return_time
        )
        self.assertEqual(len(overlaps), 0)

    def test_get_overlapping_motorcycle_bookings_with_exclude_id(self):
        """
        Test get_overlapping_motorcycle_bookings with exclude_booking_id.
        """
        # Existing booking 1: Day 1 10:00 to Day 3 10:00
        booking1 = create_hire_booking(
            motorcycle=self.motorcycle_with_daily_rate,
            driver_profile=self.driver_profile,
            pickup_date=timezone.now().date() + datetime.timedelta(days=1),
            pickup_time=datetime.time(10, 0),
            return_date=timezone.now().date() + datetime.timedelta(days=3),
            return_time=datetime.time(10, 0),
        )
        # Existing booking 2: Day 2 10:00 to Day 4 10:00
        booking2 = create_hire_booking(
            motorcycle=self.motorcycle_with_daily_rate,
            driver_profile=self.driver_profile,
            pickup_date=timezone.now().date() + datetime.timedelta(days=2),
            pickup_time=datetime.time(10, 0),
            return_date=timezone.now().date() + datetime.timedelta(days=4),
            return_time=datetime.time(10, 0),
        )

        # Check period: Day 2 10:00 to Day 3 10:00
        # Should overlap with both booking1 and booking2
        pickup_date = timezone.now().date() + datetime.timedelta(days=2)
        pickup_time = datetime.time(10, 0)
        return_date = timezone.now().date() + datetime.timedelta(days=3)
        return_time = datetime.time(10, 0)

        # Exclude booking1, so only booking2 should be returned
        overlaps = get_overlapping_motorcycle_bookings(
            self.motorcycle_with_daily_rate, pickup_date, pickup_time, return_date, return_time,
            exclude_booking_id=booking1.id
        )
        self.assertEqual(len(overlaps), 1)
        self.assertIn(booking2, overlaps)
        self.assertNotIn(booking1, overlaps)

    def test_get_overlapping_motorcycle_bookings_cancelled_status(self):
        """
        Test get_overlapping_motorcycle_bookings ignores cancelled bookings.
        """
        # Existing cancelled booking: Day 1 10:00 to Day 3 10:00
        create_hire_booking(
            motorcycle=self.motorcycle_with_daily_rate,
            driver_profile=self.driver_profile,
            pickup_date=timezone.now().date() + datetime.timedelta(days=1),
            pickup_time=datetime.time(10, 0),
            return_date=timezone.now().date() + datetime.timedelta(days=3),
            return_time=datetime.time(10, 0),
            status='cancelled'
        )

        # Check period: Day 2 10:00 to Day 3 10:00 (would overlap if not cancelled)
        pickup_date = timezone.now().date() + datetime.timedelta(days=2)
        pickup_time = datetime.time(10, 0)
        return_date = timezone.now().date() + datetime.timedelta(days=3)
        return_time = datetime.time(10, 0)

        overlaps = get_overlapping_motorcycle_bookings(
            self.motorcycle_with_daily_rate, pickup_date, pickup_time, return_date, return_time
        )
        self.assertEqual(len(overlaps), 0)

    def test_get_overlapping_motorcycle_bookings_completed_status(self):
        """
        Test get_overlapping_motorcycle_bookings ignores completed bookings.
        """
        # Existing completed booking: Day 1 10:00 to Day 3 10:00
        create_hire_booking(
            motorcycle=self.motorcycle_with_daily_rate,
            driver_profile=self.driver_profile,
            pickup_date=timezone.now().date() - datetime.timedelta(days=5), # In the past
            pickup_time=datetime.time(10, 0),
            return_date=timezone.now().date() - datetime.timedelta(days=3), # In the past
            return_time=datetime.time(10, 0),
            status='completed'
        )

        # Check period: Day 2 10:00 to Day 3 10:00 (would overlap if not completed)
        # Use future dates for the check period to ensure it's not about past vs future
        pickup_date = timezone.now().date() + datetime.timedelta(days=2)
        pickup_time = datetime.time(10, 0)
        return_date = timezone.now().date() + datetime.timedelta(days=3)
        return_time = datetime.time(10, 0)

        overlaps = get_overlapping_motorcycle_bookings(
            self.motorcycle_with_daily_rate, pickup_date, pickup_time, return_date, return_time
        )
        self.assertEqual(len(overlaps), 0)

    def test_get_overlapping_motorcycle_bookings_no_show_status(self):
        """
        Test get_overlapping_motorcycle_bookings ignores no_show bookings.
        """
        # Existing no_show booking: Day 1 10:00 to Day 3 10:00
        create_hire_booking(
            motorcycle=self.motorcycle_with_daily_rate,
            driver_profile=self.driver_profile,
            pickup_date=timezone.now().date() + datetime.timedelta(days=1),
            pickup_time=datetime.time(10, 0),
            return_date=timezone.now().date() + datetime.timedelta(days=3),
            return_time=datetime.time(10, 0),
            status='no_show'
        )

        # Check period: Day 2 10:00 to Day 3 10:00 (would overlap if not no_show)
        pickup_date = timezone.now().date() + datetime.timedelta(days=2)
        pickup_time = datetime.time(10, 0)
        return_date = timezone.now().date() + datetime.timedelta(days=3)
        return_time = datetime.time(10, 0)

        overlaps = get_overlapping_motorcycle_bookings(
            self.motorcycle_with_daily_rate, pickup_date, pickup_time, return_date, return_time
        )
        self.assertEqual(len(overlaps), 0)

    def test_get_overlapping_motorcycle_bookings_return_before_pickup_query(self):
        """
        Test get_overlapping_motorcycle_bookings when query return datetime is before pickup datetime.
        Should return an empty list.
        """
        # Existing booking (irrelevant as query is invalid): Day 1 10:00 to Day 3 10:00
        create_hire_booking(
            motorcycle=self.motorcycle_with_daily_rate,
            driver_profile=self.driver_profile,
            pickup_date=timezone.now().date() + datetime.timedelta(days=1),
            pickup_time=datetime.time(10, 0),
            return_date=timezone.now().date() + datetime.timedelta(days=3),
            return_time=datetime.time(10, 0),
        )

        # Invalid query period: Return before pickup
        pickup_date = timezone.now().date() + datetime.timedelta(days=2)
        pickup_time = datetime.time(10, 0)
        return_date = timezone.now().date() + datetime.timedelta(days=1)
        return_time = datetime.time(10, 0)

        overlaps = get_overlapping_motorcycle_bookings(
            self.motorcycle_with_daily_rate, pickup_date, pickup_time, return_date, return_time
        )
        self.assertEqual(len(overlaps), 0)

    def test_get_overlapping_motorcycle_bookings_return_equal_pickup_query(self):
        """
        Test get_overlapping_motorcycle_bookings when query return datetime is equal to pickup datetime.
        Should return an empty list.
        """
        # Existing booking (irrelevant as query is invalid): Day 1 10:00 to Day 3 10:00
        create_hire_booking(
            motorcycle=self.motorcycle_with_daily_rate,
            driver_profile=self.driver_profile,
            pickup_date=timezone.now().date() + datetime.timedelta(days=1),
            pickup_time=datetime.time(10, 0),
            return_date=timezone.now().date() + datetime.timedelta(days=3),
            return_time=datetime.time(10, 0),
        )

        # Invalid query period: Return equal to pickup
        pickup_date = timezone.now().date() + datetime.timedelta(days=2)
        pickup_time = datetime.time(10, 0)
        return_date = pickup_date
        return_time = pickup_time

        overlaps = get_overlapping_motorcycle_bookings(
            self.motorcycle_with_daily_rate, pickup_date, pickup_time, return_date, return_time
        )
        self.assertEqual(len(overlaps), 0)
