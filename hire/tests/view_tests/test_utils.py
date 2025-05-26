# hire/tests/view_tests/test_utils.py

import datetime
from decimal import Decimal, ROUND_HALF_UP
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
    Tests for utility functions in hire/views/utils.py, specifically focusing on
    the new hire pricing strategies.
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
            daily_hire_rate=None, # Will use default from HireSettings
            hourly_hire_rate=None # Will use default from HireSettings
        )
        # Create a base HireSettings instance. Specific tests will modify this or
        # create new ones with different pricing strategies.
        self.hire_settings = create_hire_settings(
            default_daily_rate=Decimal('90.00'),
            default_hourly_rate=Decimal('15.00'),
            # Default to '24_hour_customer_friendly' as per previous discussion,
            # but tests will explicitly set for each scenario.
            hire_pricing_strategy='24_hour_customer_friendly',
            excess_hours_margin=2, # Default margin for '24_hour_plus_margin'
            minimum_hire_duration_hours=1, # Ensure this is set for general tests
        )
        self.driver_profile = create_driver_profile()

    # --- calculate_hire_price Tests for each strategy ---

    def test_calculate_hire_price_same_day_hourly(self):
        """
        Test calculate_hire_price for same-day hire, which should always be hourly
        regardless of the multi-day strategy.
        """
        pickup_date = timezone.now().date()
        pickup_time = datetime.time(9, 0)
        return_date = pickup_date
        return_time = datetime.time(11, 30) # 2.5 hours, should round up to 3 hours

        # Test with motorcycle specific rate
        expected_price_moto = self.motorcycle_with_daily_rate.hourly_hire_rate * 3
        calculated_price_moto = calculate_hire_price(
            self.motorcycle_with_daily_rate, pickup_date, return_date, pickup_time, return_time, self.hire_settings
        )
        self.assertEqual(calculated_price_moto, expected_price_moto)

        # Test with default rate
        expected_price_default = self.hire_settings.default_hourly_rate * 3
        calculated_price_default = calculate_hire_price(
            self.motorcycle_no_rate, pickup_date, return_date, pickup_time, return_time, self.hire_settings
        )
        self.assertEqual(calculated_price_default, expected_price_default)

        # Test very short duration (e.g., 15 minutes), should round up to 1 hour
        return_time_short = datetime.time(9, 15)
        expected_price_short = self.motorcycle_with_daily_rate.hourly_hire_rate * 1
        calculated_price_short = calculate_hire_price(
            self.motorcycle_with_daily_rate, pickup_date, return_date, pickup_time, return_time_short, self.hire_settings
        )
        self.assertEqual(calculated_price_short, expected_price_short)

    def test_calculate_hire_price_zero_or_negative_duration(self):
        """
        Test calculate_hire_price with zero or negative duration.
        """
        pickup_date = timezone.now().date() + datetime.timedelta(days=1)
        pickup_time = datetime.time(9, 0)
        return_date_zero = pickup_date
        return_time_zero = pickup_time # Same time, so 0 duration

        expected_price = Decimal('0.00')
        calculated_price = calculate_hire_price(
            self.motorcycle_with_daily_rate, pickup_date, return_date_zero, pickup_time, return_time_zero, self.hire_settings
        )
        self.assertEqual(calculated_price, expected_price)

        return_date_negative = pickup_date - datetime.timedelta(days=1)
        calculated_price_negative = calculate_hire_price(
            self.motorcycle_with_daily_rate, pickup_date, return_date_negative, pickup_time, return_time_zero, self.hire_settings
        )
        self.assertEqual(calculated_price_negative, expected_price)


    # --- Strategy 1: Flat 24-Hour Billing (Any excess rounds to full day) ---
    def test_calculate_hire_price_flat_24_hour_exact_days(self):
        """
        Test 'flat_24_hour' strategy for exact 24-hour multiples.
        """
        self.hire_settings.hire_pricing_strategy = 'flat_24_hour'
        self.hire_settings.save()

        pickup_date = timezone.now().date() + datetime.timedelta(days=1)
        pickup_time = datetime.time(9, 0)
        return_date = pickup_date + datetime.timedelta(days=2) # 48 hours
        return_time = datetime.time(9, 0)

        expected_price = self.motorcycle_with_daily_rate.daily_hire_rate * 2
        calculated_price = calculate_hire_price(
            self.motorcycle_with_daily_rate, pickup_date, return_date, pickup_time, return_time, self.hire_settings
        )
        self.assertEqual(calculated_price, expected_price)

    def test_calculate_hire_price_flat_24_hour_with_excess(self):
        """
        Test 'flat_24_hour' strategy with any excess hours, should round up to next full day.
        """
        self.hire_settings.hire_pricing_strategy = 'flat_24_hour'
        self.hire_settings.save()

        pickup_date = timezone.now().date() + datetime.timedelta(days=1)
        pickup_time = datetime.time(9, 0)
        return_date = pickup_date + datetime.timedelta(days=2) # 48 hours + 1 minute
        return_time = datetime.time(9, 1) # Just over 2 days

        # Should be billed for 3 days
        expected_price = self.motorcycle_with_daily_rate.daily_hire_rate * 3
        calculated_price = calculate_hire_price(
            self.motorcycle_with_daily_rate, pickup_date, return_date, pickup_time, return_time, self.hire_settings
        )
        self.assertEqual(calculated_price, expected_price)

    def test_calculate_hire_price_flat_24_hour_with_almost_full_excess(self):
        """
        Test 'flat_24_hour' strategy with almost a full day of excess.
        """
        self.hire_settings.hire_pricing_strategy = 'flat_24_hour'
        self.hire_settings.save()

        pickup_date = timezone.now().date() + datetime.timedelta(days=1)
        pickup_time = datetime.time(9, 0)
        return_date = pickup_date + datetime.timedelta(days=2)
        return_time = datetime.time(8, 59) # 47 hours 59 minutes (almost 2 full days)

        # Should still be billed for 2 days
        expected_price = self.motorcycle_with_daily_rate.daily_hire_rate * 2
        calculated_price = calculate_hire_price(
            self.motorcycle_with_daily_rate, pickup_date, return_date, pickup_time, return_time, self.hire_settings
        )
        self.assertEqual(calculated_price, expected_price)

    # --- Strategy 2: 24-Hour Billing with Margin (Excess hours within margin are free) ---
    def test_calculate_hire_price_24_hour_plus_margin_within_margin(self):
        """
        Test '24_hour_plus_margin' strategy when excess hours are within the margin.
        """
        self.hire_settings.hire_pricing_strategy = '24_hour_plus_margin'
        self.hire_settings.excess_hours_margin = 3 # Set margin to 3 hours
        self.hire_settings.save()

        pickup_date = timezone.now().date() + datetime.timedelta(days=1)
        pickup_time = datetime.time(9, 0)
        return_date = pickup_date + datetime.timedelta(days=2) # 48 hours + 2 hours excess
        return_time = datetime.time(11, 0) # 2 hours past pickup time

        # Should be billed for 2 days (excess 2 hours is within 3-hour margin)
        expected_price = self.motorcycle_with_daily_rate.daily_hire_rate * 2
        calculated_price = calculate_hire_price(
            self.motorcycle_with_daily_rate, pickup_date, return_date, pickup_time, return_time, self.hire_settings
        )
        self.assertEqual(calculated_price, expected_price)

    def test_calculate_hire_price_24_hour_plus_margin_exceeds_margin(self):
        """
        Test '24_hour_plus_margin' strategy when excess hours exceed the margin.
        """
        self.hire_settings.hire_pricing_strategy = '24_hour_plus_margin'
        self.hire_settings.excess_hours_margin = 3 # Set margin to 3 hours
        self.hire_settings.save()

        pickup_date = timezone.now().date() + datetime.timedelta(days=1)
        pickup_time = datetime.time(9, 0)
        return_date = pickup_date + datetime.timedelta(days=2) # 48 hours + 4 hours excess
        return_time = datetime.time(13, 0) # 4 hours past pickup time

        # Should be billed for 2 days + 1 extra day (because 4 hours > 3-hour margin)
        expected_price = self.motorcycle_with_daily_rate.daily_hire_rate * 3
        calculated_price = calculate_hire_price(
            self.motorcycle_with_daily_rate, pickup_date, return_date, pickup_time, return_time, self.hire_settings
        )
        self.assertEqual(calculated_price, expected_price)

    def test_calculate_hire_price_24_hour_plus_margin_no_excess(self):
        """
        Test '24_hour_plus_margin' strategy with no excess hours.
        """
        self.hire_settings.hire_pricing_strategy = '24_hour_plus_margin'
        self.hire_settings.excess_hours_margin = 3
        self.hire_settings.save()

        pickup_date = timezone.now().date() + datetime.timedelta(days=1)
        pickup_time = datetime.time(9, 0)
        return_date = pickup_date + datetime.timedelta(days=2) # Exactly 48 hours
        return_time = datetime.time(9, 0)

        expected_price = self.motorcycle_with_daily_rate.daily_hire_rate * 2
        calculated_price = calculate_hire_price(
            self.motorcycle_with_daily_rate, pickup_date, return_date, pickup_time, return_time, self.hire_settings
        )
        self.assertEqual(calculated_price, expected_price)

    # --- Strategy 3: 24-Hour Billing Customer Friendly (Excess hours: min(hourly_rate, daily_rate)) ---
    def test_calculate_hire_price_24_hour_customer_friendly_hourly_cheaper(self):
        """
        Test '24_hour_customer_friendly' strategy when hourly rate for excess is cheaper than a full day.
        """
        self.hire_settings.hire_pricing_strategy = '24_hour_customer_friendly'
        self.hire_settings.save() # Use default 20.00 hourly, 100.00 daily for moto

        pickup_date = timezone.now().date() + datetime.timedelta(days=1)
        pickup_time = datetime.time(9, 0)
        return_date = pickup_date + datetime.timedelta(days=2) # 48 hours + 3 hours excess
        return_time = datetime.time(12, 0) # 3 hours past pickup time

        # Expected: 2 * daily_rate + min(3 * hourly_rate, daily_rate)
        # 2 * 100 + min(3 * 20, 100) = 200 + min(60, 100) = 200 + 60 = 260
        expected_price = (self.motorcycle_with_daily_rate.daily_hire_rate * 2) + \
                         (self.motorcycle_with_daily_rate.hourly_hire_rate * 3)
        calculated_price = calculate_hire_price(
            self.motorcycle_with_daily_rate, pickup_date, return_date, pickup_time, return_time, self.hire_settings
        )
        self.assertEqual(calculated_price, expected_price)

    def test_calculate_hire_price_24_hour_customer_friendly_daily_cheaper(self):
        """
        Test '24_hour_customer_friendly' strategy when daily rate is cheaper for excess hours.
        """
        self.hire_settings.hire_pricing_strategy = '24_hour_customer_friendly'
        self.hire_settings.save() # Use default 20.00 hourly, 100.00 daily for moto

        pickup_date = timezone.now().date() + datetime.timedelta(days=1)
        pickup_time = datetime.time(9, 0)
        return_date = pickup_date + datetime.timedelta(days=2) # 48 hours + 6 hours excess
        return_time = datetime.time(15, 0) # 6 hours past pickup time

        # Expected: 2 * daily_rate + min(6 * hourly_rate, daily_rate)
        # 2 * 100 + min(6 * 20, 100) = 200 + min(120, 100) = 200 + 100 = 300
        expected_price = (self.motorcycle_with_daily_rate.daily_hire_rate * 2) + \
                         self.motorcycle_with_daily_rate.daily_hire_rate # The additional day
        calculated_price = calculate_hire_price(
            self.motorcycle_with_daily_rate, pickup_date, return_date, pickup_time, return_time, self.hire_settings
        )
        self.assertEqual(calculated_price, expected_price)

    def test_calculate_hire_price_24_hour_customer_friendly_no_excess(self):
        """
        Test '24_hour_customer_friendly' strategy with no excess hours.
        """
        self.hire_settings.hire_pricing_strategy = '24_hour_customer_friendly'
        self.hire_settings.save()

        pickup_date = timezone.now().date() + datetime.timedelta(days=1)
        pickup_time = datetime.time(9, 0)
        return_date = pickup_date + datetime.timedelta(days=2) # Exactly 48 hours
        return_time = datetime.time(9, 0)

        expected_price = self.motorcycle_with_daily_rate.daily_hire_rate * 2
        calculated_price = calculate_hire_price(
            self.motorcycle_with_daily_rate, pickup_date, return_date, pickup_time, return_time, self.hire_settings
        )
        self.assertEqual(calculated_price, expected_price)

    # --- Strategy 4: Daily Plus Excess Hourly (Every additional hour charged hourly) ---
    def test_calculate_hire_price_daily_plus_excess_hourly(self):
        """
        Test 'daily_plus_excess_hourly' strategy.
        """
        self.hire_settings.hire_pricing_strategy = 'daily_plus_excess_hourly'
        self.hire_settings.save()

        pickup_date = timezone.now().date() + datetime.timedelta(days=1)
        pickup_time = datetime.time(9, 0)
        return_date = pickup_date + datetime.timedelta(days=2) # 48 hours + 5.5 hours excess
        return_time = datetime.time(14, 30) # 5 hours 30 minutes past pickup time

        # Expected: 2 * daily_rate + ceil(5.5) * hourly_rate = 2 * 100 + 6 * 20 = 200 + 120 = 320
        expected_price = (self.motorcycle_with_daily_rate.daily_hire_rate * 2) + \
                         (self.motorcycle_with_daily_rate.hourly_hire_rate * 6)
        calculated_price = calculate_hire_price(
            self.motorcycle_with_daily_rate, pickup_date, return_date, pickup_time, return_time, self.hire_settings
        )
        self.assertEqual(calculated_price, expected_price)

    def test_calculate_hire_price_daily_plus_excess_hourly_no_excess(self):
        """
        Test 'daily_plus_excess_hourly' strategy with no excess hours.
        """
        self.hire_settings.hire_pricing_strategy = 'daily_plus_excess_hourly'
        self.hire_settings.save()

        pickup_date = timezone.now().date() + datetime.timedelta(days=1)
        pickup_time = datetime.time(9, 0)
        return_date = pickup_date + datetime.timedelta(days=2) # Exactly 48 hours
        return_time = datetime.time(9, 0)

        expected_price = self.motorcycle_with_daily_rate.daily_hire_rate * 2
        calculated_price = calculate_hire_price(
            self.motorcycle_with_daily_rate, pickup_date, return_date, pickup_time, return_time, self.hire_settings
        )
        self.assertEqual(calculated_price, expected_price)

    # --- calculate_hire_duration_days Tests for each strategy ---
    # Note: calculate_hire_duration_days now needs hire_settings as an argument

    def test_calculate_hire_duration_days_same_day_hire(self):
        """
        Test calculate_hire_duration_days for a hire within the same day.
        Should return 1 day if duration > 0, regardless of strategy.
        """
        pickup_date = timezone.now().date()
        pickup_time = datetime.time(9, 0)
        return_date = pickup_date
        return_time = datetime.time(17, 0)
        
        # Test with an arbitrary strategy, as same-day logic is separate
        self.hire_settings.hire_pricing_strategy = 'flat_24_hour'
        self.hire_settings.save()
        duration = calculate_hire_duration_days(
            pickup_date, return_date, pickup_time, return_time, self.hire_settings
        )
        self.assertEqual(duration, 1)

        # Test very short duration (e.g., 15 minutes)
        return_time_short = datetime.time(9, 15)
        duration_short = calculate_hire_duration_days(
            pickup_date, return_date, pickup_time, return_time_short, self.hire_settings
        )
        self.assertEqual(duration_short, 1)

    def test_calculate_hire_duration_days_zero_or_negative_duration(self):
        """
        Test calculate_hire_duration_days with zero or negative duration.
        Should return 0, regardless of strategy.
        """
        pickup_date = timezone.now().date() + datetime.timedelta(days=1)
        pickup_time = datetime.time(9, 0)
        return_date_zero = pickup_date
        return_time_zero = pickup_time # Same time, so 0 duration

        self.hire_settings.hire_pricing_strategy = 'flat_24_hour'
        self.hire_settings.save()
        duration = calculate_hire_duration_days(
            pickup_date, return_date_zero, pickup_time, return_time_zero, self.hire_settings
        )
        self.assertEqual(duration, 0)

        return_date_negative = pickup_date - datetime.timedelta(days=1)
        duration_negative = calculate_hire_duration_days(
            pickup_date, return_date_negative, pickup_time, return_time_zero, self.hire_settings
        )
        self.assertEqual(duration_negative, 0)

    def test_calculate_hire_duration_days_flat_24_hour_strategy(self):
        """
        Test calculate_hire_duration_days for 'flat_24_hour' strategy.
        """
        self.hire_settings.hire_pricing_strategy = 'flat_24_hour'
        self.hire_settings.save()

        # Exactly 24 hours
        pickup_date = timezone.now().date()
        pickup_time = datetime.time(9, 0)
        return_date = pickup_date + datetime.timedelta(days=1)
        return_time = datetime.time(9, 0)
        self.assertEqual(calculate_hire_duration_days(pickup_date, return_date, pickup_time, return_time, self.hire_settings), 1)

        # 24 hours + 1 minute (rounds up to 2 days)
        return_time_plus_minute = datetime.time(9, 1)
        self.assertEqual(calculate_hire_duration_days(pickup_date, return_date, pickup_time, return_time_plus_minute, self.hire_settings), 2)

        # 47 hours 59 minutes (rounds up to 2 days)
        return_date_almost_2_days = pickup_date + datetime.timedelta(days=1)
        return_time_almost_2_days = datetime.time(8, 59)
        self.assertEqual(calculate_hire_duration_days(pickup_date, return_date_almost_2_days, pickup_time, return_time_almost_2_days, self.hire_settings), 2)

        # 2 days and 6 hours (rounds up to 3 days)
        return_date_2_days_6_hours = pickup_date + datetime.timedelta(days=2)
        return_time_2_days_6_hours = datetime.time(15, 0)
        self.assertEqual(calculate_hire_duration_days(pickup_date, return_date_2_days_6_hours, pickup_time, return_time_2_days_6_hours, self.hire_settings), 3)


    def test_calculate_hire_duration_days_24_hour_plus_margin_strategy(self):
        """
        Test calculate_hire_duration_days for '24_hour_plus_margin' strategy.
        """
        self.hire_settings.hire_pricing_strategy = '24_hour_plus_margin'
        self.hire_settings.excess_hours_margin = 3 # Set margin to 3 hours
        self.hire_settings.save()

        pickup_date = timezone.now().date()
        pickup_time = datetime.time(9, 0)

        # Exactly 2 days (48 hours)
        return_date_exact = pickup_date + datetime.timedelta(days=2)
        return_time_exact = datetime.time(9, 0)
        self.assertEqual(calculate_hire_duration_days(pickup_date, return_date_exact, pickup_time, return_time_exact, self.hire_settings), 2)

        # 2 days + 2 hours excess (within 3-hour margin, so 2 days)
        return_time_within_margin = datetime.time(11, 0)
        self.assertEqual(calculate_hire_duration_days(pickup_date, return_date_exact, pickup_time, return_time_within_margin, self.hire_settings), 2)

        # 2 days + 3 hours excess (exactly at 3-hour margin, so 2 days)
        return_time_at_margin = datetime.time(12, 0)
        self.assertEqual(calculate_hire_duration_days(pickup_date, return_date_exact, pickup_time, return_time_at_margin, self.hire_settings), 2)

        # 2 days + 4 hours excess (exceeds 3-hour margin, so 3 days)
        return_time_exceeds_margin = datetime.time(13, 0)
        self.assertEqual(calculate_hire_duration_days(pickup_date, return_date_exact, pickup_time, return_time_exceeds_margin, self.hire_settings), 3)

    def test_calculate_hire_duration_days_24_hour_customer_friendly_strategy(self):
        """
        Test calculate_hire_duration_days for '24_hour_customer_friendly' strategy.
        This one is tricky for 'billable days' as it's cost-driven.
        If the cost of excess is less than a daily rate, it's considered part of the last full day.
        If it's equal to or more than a daily rate, it's an additional day.
        """
        self.hire_settings.hire_pricing_strategy = '24_hour_customer_friendly'
        self.hire_settings.save()

        pickup_date = timezone.now().date()
        pickup_time = datetime.time(9, 0)
        daily_rate = self.motorcycle_with_daily_rate.daily_hire_rate
        hourly_rate = self.motorcycle_with_daily_rate.hourly_hire_rate

        # Exactly 2 days (48 hours) -> 2 days
        return_date_exact = pickup_date + datetime.timedelta(days=2)
        return_time_exact = datetime.time(9, 0)
        self.assertEqual(calculate_hire_duration_days(pickup_date, return_date_exact, pickup_time, return_time_exact, self.hire_settings), 2)

        # 2 days + 3 hours excess (3 * 20 = 60, which is < 100 daily) -> still 2 days
        return_time_hourly_cheaper = datetime.time(12, 0)
        self.assertEqual(calculate_hire_duration_days(pickup_date, return_date_exact, pickup_time, return_time_hourly_cheaper, self.hire_settings), 2)

        # 2 days + 5 hours excess (5 * 20 = 100, which is == 100 daily) -> 3 days
        return_time_hourly_equals_daily = datetime.time(14, 0)
        self.assertEqual(calculate_hire_duration_days(pickup_date, return_date_exact, pickup_time, return_time_hourly_equals_daily, self.hire_settings), 3)

        # 2 days + 6 hours excess (6 * 20 = 120, which is > 100 daily) -> 3 days
        return_time_hourly_more_than_daily = datetime.time(15, 0)
        self.assertEqual(calculate_hire_duration_days(pickup_date, return_date_exact, pickup_time, return_time_hourly_more_than_daily, self.hire_settings), 3)

        # Less than 24 hours (e.g., 5 hours) -> 1 day (handled by initial same-day check)
        return_date_same_day = pickup_date
        return_time_5_hours = datetime.time(14, 0)
        self.assertEqual(calculate_hire_duration_days(return_date_same_day, return_date_same_day, pickup_time, return_time_5_hours, self.hire_settings), 1)


    def test_calculate_hire_duration_days_daily_plus_excess_hourly_strategy(self):
        """
        Test calculate_hire_duration_days for 'daily_plus_excess_hourly' strategy.
        This strategy bills full 24-hour blocks as days, and excess hours are just hours.
        So, billable days are simply the full 24-hour blocks.
        """
        self.hire_settings.hire_pricing_strategy = 'daily_plus_excess_hourly'
        self.hire_settings.save()

        pickup_date = timezone.now().date()
        pickup_time = datetime.time(9, 0)

        # Exactly 2 days (48 hours) -> 2 days
        return_date_exact = pickup_date + datetime.timedelta(days=2)
        return_time_exact = datetime.time(9, 0)
        self.assertEqual(calculate_hire_duration_days(pickup_date, return_date_exact, pickup_time, return_time_exact, self.hire_settings), 2)

        # 2 days + 5.5 hours excess -> 2 days (excess is billed hourly, not as a full day)
        return_date_excess = pickup_date + datetime.timedelta(days=2)
        return_time_excess = datetime.time(14, 30)
        self.assertEqual(calculate_hire_duration_days(pickup_date, return_date_excess, pickup_time, return_time_excess, self.hire_settings), 2)

        # 0.5 days (12 hours) -> 0 days (but this would be caught by same-day logic and return 1 for display)
        # We need to test multi-day scenarios for this part.
        # If it's a multi-day rental but less than a full 24-hour block, it's 0 full days.
        pickup_date_multi = timezone.now().date()
        return_date_multi = pickup_date_multi + datetime.timedelta(hours=12) # Not a full day, but spans across midnight
        # This scenario is tricky, as the `calculate_hire_price` handles it as hourly, but `calculate_hire_duration_days`
        # for multi-day strictly counts full 24-hour blocks.
        # Let's ensure the `calculate_hire_duration_days` reflects the *number of full days* correctly.
        # If the duration is less than 24 hours but spans midnight, it's still 0 full 24-hour blocks.
        # The `calculate_hire_price` function handles the "same day" logic first, which covers this.
        # For `calculate_hire_duration_days`, if it's not same day, it's about full 24-hour blocks.
        
        # Example: Pickup Mon 22:00, Return Tue 02:00 (4 hours total, spans midnight)
        pickup_date_span = timezone.now().date()
        pickup_time_span = datetime.time(22, 0)
        return_date_span = pickup_date_span + datetime.timedelta(days=1)
        return_time_span = datetime.time(2, 0)
        # This is a multi-day rental, but less than 24 hours.
        # Should return 0 full 24-hour blocks.
        self.assertEqual(calculate_hire_duration_days(pickup_date_span, return_date_span, pickup_time_span, return_time_span, self.hire_settings), 0)


    # --- get_overlapping_motorcycle_bookings Tests (unchanged as they already use separate date/time args) ---
    # These tests are already robust and don't depend on the pricing strategy.

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