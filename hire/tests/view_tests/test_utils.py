# hire/tests/view_tests/test_utils.py

import datetime
from decimal import Decimal, ROUND_HALF_UP
from django.test import TestCase
from django.utils import timezone
from inventory.models import Motorcycle
from hire.models import HireBooking
from dashboard.models import HireSettings
from hire.views.utils import (
    calculate_hire_price,
    calculate_hire_duration_days,
    get_overlapping_motorcycle_bookings
)
from hire.tests.test_helpers.model_factories import (
    create_motorcycle,
    create_hire_settings,
    create_hire_booking,
    create_driver_profile,
)

class HireUtilsTests(TestCase):

    def setUp(self):
        self.motorcycle_with_daily_rate = create_motorcycle(
            daily_hire_rate=Decimal('100.00'),
            hourly_hire_rate=Decimal('20.00')
        )
        self.motorcycle_no_rate = create_motorcycle(
            daily_hire_rate=None,
            hourly_hire_rate=None
        )
        self.hire_settings = create_hire_settings(
            default_daily_rate=Decimal('90.00'),
            default_hourly_rate=Decimal('15.00'),
            hire_pricing_strategy='24_hour_customer_friendly',
            excess_hours_margin=2,
            minimum_hire_duration_hours=1,
        )
        self.driver_profile = create_driver_profile()

    # Tests same-day hire price calculation (should be hourly, rounded up).
    def test_calculate_hire_price_same_day_hourly(self):
        pickup_date = timezone.now().date()
        pickup_time = datetime.time(9, 0)
        return_date = pickup_date
        return_time = datetime.time(11, 30)
        expected_price_moto = self.motorcycle_with_daily_rate.hourly_hire_rate * 3
        calculated_price_moto = calculate_hire_price(
            self.motorcycle_with_daily_rate, pickup_date, return_date, pickup_time, return_time, self.hire_settings
        )
        self.assertEqual(calculated_price_moto, expected_price_moto)
        expected_price_default = self.hire_settings.default_hourly_rate * 3
        calculated_price_default = calculate_hire_price(
            self.motorcycle_no_rate, pickup_date, return_date, pickup_time, return_time, self.hire_settings
        )
        self.assertEqual(calculated_price_default, expected_price_default)
        return_time_short = datetime.time(9, 15)
        expected_price_short = self.motorcycle_with_daily_rate.hourly_hire_rate * 1
        calculated_price_short = calculate_hire_price(
            self.motorcycle_with_daily_rate, pickup_date, return_date, pickup_time, return_time_short, self.hire_settings
        )
        self.assertEqual(calculated_price_short, expected_price_short)

    # Tests hire price calculation for zero or negative duration (should be 0.00).
    def test_calculate_hire_price_zero_or_negative_duration(self):
        pickup_date = timezone.now().date() + datetime.timedelta(days=1)
        pickup_time = datetime.time(9, 0)
        return_date_zero = pickup_date
        return_time_zero = pickup_time
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

    # Tests 'flat_24_hour' price for exact 24-hour multiples.
    def test_calculate_hire_price_flat_24_hour_exact_days(self):
        self.hire_settings.hire_pricing_strategy = 'flat_24_hour'
        self.hire_settings.save()
        pickup_date = timezone.now().date() + datetime.timedelta(days=1)
        pickup_time = datetime.time(9, 0)
        return_date = pickup_date + datetime.timedelta(days=2)
        return_time = datetime.time(9, 0)
        expected_price = self.motorcycle_with_daily_rate.daily_hire_rate * 2
        calculated_price = calculate_hire_price(
            self.motorcycle_with_daily_rate, pickup_date, return_date, pickup_time, return_time, self.hire_settings
        )
        self.assertEqual(calculated_price, expected_price)

    # Tests 'flat_24_hour' price with slight excess time (should round to next day).
    def test_calculate_hire_price_flat_24_hour_with_excess(self):
        self.hire_settings.hire_pricing_strategy = 'flat_24_hour'
        self.hire_settings.save()
        pickup_date = timezone.now().date() + datetime.timedelta(days=1)
        pickup_time = datetime.time(9, 0)
        return_date = pickup_date + datetime.timedelta(days=2)
        return_time = datetime.time(9, 1)
        expected_price = self.motorcycle_with_daily_rate.daily_hire_rate * 3
        calculated_price = calculate_hire_price(
            self.motorcycle_with_daily_rate, pickup_date, return_date, pickup_time, return_time, self.hire_settings
        )
        self.assertEqual(calculated_price, expected_price)

    # Tests 'flat_24_hour' price with duration just under a 24-hour multiple.
    def test_calculate_hire_price_flat_24_hour_with_almost_full_excess(self):
        self.hire_settings.hire_pricing_strategy = 'flat_24_hour'
        self.hire_settings.save()
        pickup_date = timezone.now().date() + datetime.timedelta(days=1)
        pickup_time = datetime.time(9, 0)
        return_date = pickup_date + datetime.timedelta(days=2)
        return_time = datetime.time(8, 59)
        expected_price = self.motorcycle_with_daily_rate.daily_hire_rate * 2
        calculated_price = calculate_hire_price(
            self.motorcycle_with_daily_rate, pickup_date, return_date, pickup_time, return_time, self.hire_settings
        )
        self.assertEqual(calculated_price, expected_price)

    # Tests '24_hour_plus_margin' price when excess is within the allowed margin.
    def test_calculate_hire_price_24_hour_plus_margin_within_margin(self):
        self.hire_settings.hire_pricing_strategy = '24_hour_plus_margin'
        self.hire_settings.excess_hours_margin = 3
        self.hire_settings.save()
        pickup_date = timezone.now().date() + datetime.timedelta(days=1)
        pickup_time = datetime.time(9, 0)
        return_date = pickup_date + datetime.timedelta(days=2)
        return_time = datetime.time(11, 0)
        expected_price = self.motorcycle_with_daily_rate.daily_hire_rate * 2
        calculated_price = calculate_hire_price(
            self.motorcycle_with_daily_rate, pickup_date, return_date, pickup_time, return_time, self.hire_settings
        )
        self.assertEqual(calculated_price, expected_price)

    # Tests '24_hour_plus_margin' price when excess exceeds the allowed margin.
    def test_calculate_hire_price_24_hour_plus_margin_exceeds_margin(self):
        self.hire_settings.hire_pricing_strategy = '24_hour_plus_margin'
        self.hire_settings.excess_hours_margin = 3
        self.hire_settings.save()
        pickup_date = timezone.now().date() + datetime.timedelta(days=1)
        pickup_time = datetime.time(9, 0)
        return_date = pickup_date + datetime.timedelta(days=2)
        return_time = datetime.time(13, 0)
        expected_price = self.motorcycle_with_daily_rate.daily_hire_rate * 3
        calculated_price = calculate_hire_price(
            self.motorcycle_with_daily_rate, pickup_date, return_date, pickup_time, return_time, self.hire_settings
        )
        self.assertEqual(calculated_price, expected_price)

    # Tests '24_hour_plus_margin' price with no excess hours.
    def test_calculate_hire_price_24_hour_plus_margin_no_excess(self):
        self.hire_settings.hire_pricing_strategy = '24_hour_plus_margin'
        self.hire_settings.excess_hours_margin = 3
        self.hire_settings.save()
        pickup_date = timezone.now().date() + datetime.timedelta(days=1)
        pickup_time = datetime.time(9, 0)
        return_date = pickup_date + datetime.timedelta(days=2)
        return_time = datetime.time(9, 0)
        expected_price = self.motorcycle_with_daily_rate.daily_hire_rate * 2
        calculated_price = calculate_hire_price(
            self.motorcycle_with_daily_rate, pickup_date, return_date, pickup_time, return_time, self.hire_settings
        )
        self.assertEqual(calculated_price, expected_price)

    # Tests '24_hour_customer_friendly' price when hourly rate for excess is cheaper.
    def test_calculate_hire_price_24_hour_customer_friendly_hourly_cheaper(self):
        self.hire_settings.hire_pricing_strategy = '24_hour_customer_friendly'
        self.hire_settings.save()
        pickup_date = timezone.now().date() + datetime.timedelta(days=1)
        pickup_time = datetime.time(9, 0)
        return_date = pickup_date + datetime.timedelta(days=2)
        return_time = datetime.time(12, 0)
        expected_price = (self.motorcycle_with_daily_rate.daily_hire_rate * 2) + \
                         (self.motorcycle_with_daily_rate.hourly_hire_rate * 3)
        calculated_price = calculate_hire_price(
            self.motorcycle_with_daily_rate, pickup_date, return_date, pickup_time, return_time, self.hire_settings
        )
        self.assertEqual(calculated_price, expected_price)

    # Tests '24_hour_customer_friendly' price when daily rate for excess is cheaper.
    def test_calculate_hire_price_24_hour_customer_friendly_daily_cheaper(self):
        self.hire_settings.hire_pricing_strategy = '24_hour_customer_friendly'
        self.hire_settings.save()
        pickup_date = timezone.now().date() + datetime.timedelta(days=1)
        pickup_time = datetime.time(9, 0)
        return_date = pickup_date + datetime.timedelta(days=2)
        return_time = datetime.time(15, 0)
        expected_price = (self.motorcycle_with_daily_rate.daily_hire_rate * 2) + \
                         self.motorcycle_with_daily_rate.daily_hire_rate
        calculated_price = calculate_hire_price(
            self.motorcycle_with_daily_rate, pickup_date, return_date, pickup_time, return_time, self.hire_settings
        )
        self.assertEqual(calculated_price, expected_price)

    # Tests '24_hour_customer_friendly' price with no excess hours.
    def test_calculate_hire_price_24_hour_customer_friendly_no_excess(self):
        self.hire_settings.hire_pricing_strategy = '24_hour_customer_friendly'
        self.hire_settings.save()
        pickup_date = timezone.now().date() + datetime.timedelta(days=1)
        pickup_time = datetime.time(9, 0)
        return_date = pickup_date + datetime.timedelta(days=2)
        return_time = datetime.time(9, 0)
        expected_price = self.motorcycle_with_daily_rate.daily_hire_rate * 2
        calculated_price = calculate_hire_price(
            self.motorcycle_with_daily_rate, pickup_date, return_date, pickup_time, return_time, self.hire_settings
        )
        self.assertEqual(calculated_price, expected_price)

    # Tests 'daily_plus_excess_hourly' price calculation.
    def test_calculate_hire_price_daily_plus_excess_hourly(self):
        self.hire_settings.hire_pricing_strategy = 'daily_plus_excess_hourly'
        self.hire_settings.save()
        pickup_date = timezone.now().date() + datetime.timedelta(days=1)
        pickup_time = datetime.time(9, 0)
        return_date = pickup_date + datetime.timedelta(days=2)
        return_time = datetime.time(14, 30)
        expected_price = (self.motorcycle_with_daily_rate.daily_hire_rate * 2) + \
                         (self.motorcycle_with_daily_rate.hourly_hire_rate * 6)
        calculated_price = calculate_hire_price(
            self.motorcycle_with_daily_rate, pickup_date, return_date, pickup_time, return_time, self.hire_settings
        )
        self.assertEqual(calculated_price, expected_price)

    # Tests 'daily_plus_excess_hourly' price with no excess hours.
    def test_calculate_hire_price_daily_plus_excess_hourly_no_excess(self):
        self.hire_settings.hire_pricing_strategy = 'daily_plus_excess_hourly'
        self.hire_settings.save()
        pickup_date = timezone.now().date() + datetime.timedelta(days=1)
        pickup_time = datetime.time(9, 0)
        return_date = pickup_date + datetime.timedelta(days=2)
        return_time = datetime.time(9, 0)
        expected_price = self.motorcycle_with_daily_rate.daily_hire_rate * 2
        calculated_price = calculate_hire_price(
            self.motorcycle_with_daily_rate, pickup_date, return_date, pickup_time, return_time, self.hire_settings
        )
        self.assertEqual(calculated_price, expected_price)

    # Tests hire duration calculation for same-day hires (should be 1 day).
    def test_calculate_hire_duration_days_same_day_hire(self):
        pickup_date = timezone.now().date()
        pickup_time = datetime.time(9, 0)
        return_date = pickup_date
        return_time = datetime.time(17, 0)
        self.hire_settings.hire_pricing_strategy = 'flat_24_hour'
        self.hire_settings.save()
        duration = calculate_hire_duration_days(
            self.motorcycle_with_daily_rate, pickup_date, return_date, pickup_time, return_time, self.hire_settings
        )
        self.assertEqual(duration, 1)
        return_time_short = datetime.time(9, 15)
        duration_short = calculate_hire_duration_days(
            self.motorcycle_with_daily_rate, pickup_date, return_date, pickup_time, return_time_short, self.hire_settings
        )
        self.assertEqual(duration_short, 1)

    # Tests hire duration for zero or negative actual duration (should be 0 days).
    def test_calculate_hire_duration_days_zero_or_negative_duration(self):
        pickup_date = timezone.now().date() + datetime.timedelta(days=1)
        pickup_time = datetime.time(9, 0)
        return_date_zero = pickup_date
        return_time_zero = pickup_time
        self.hire_settings.hire_pricing_strategy = 'flat_24_hour'
        self.hire_settings.save()
        duration = calculate_hire_duration_days(
            self.motorcycle_with_daily_rate, pickup_date, return_date_zero, pickup_time, return_time_zero, self.hire_settings
        )
        self.assertEqual(duration, 0)
        return_date_negative = pickup_date - datetime.timedelta(days=1)
        duration_negative = calculate_hire_duration_days(
            self.motorcycle_with_daily_rate, pickup_date, return_date_negative, pickup_time, return_time_zero, self.hire_settings
        )
        self.assertEqual(duration_negative, 0)

    # Tests 'flat_24_hour' duration calculation for various scenarios.
    def test_calculate_hire_duration_days_flat_24_hour_strategy(self):
        self.hire_settings.hire_pricing_strategy = 'flat_24_hour'
        self.hire_settings.save()
        pickup_date = timezone.now().date()
        pickup_time = datetime.time(9, 0)
        return_date_24_hours = pickup_date + datetime.timedelta(days=1)
        return_time_24_hours = datetime.time(9, 0)
        self.assertEqual(calculate_hire_duration_days(self.motorcycle_with_daily_rate, pickup_date, return_date_24_hours, pickup_time, return_time_24_hours, self.hire_settings), 1)
        return_date_plus_minute = pickup_date + datetime.timedelta(days=1)
        return_time_plus_minute = datetime.time(9, 1)
        self.assertEqual(calculate_hire_duration_days(self.motorcycle_with_daily_rate, pickup_date, return_date_plus_minute, pickup_time, return_time_plus_minute, self.hire_settings), 2)
        return_date_47h_59m = pickup_date + datetime.timedelta(days=2)
        return_time_47h_59m = datetime.time(8, 59)
        self.assertEqual(calculate_hire_duration_days(self.motorcycle_with_daily_rate, pickup_date, return_date_47h_59m, pickup_time, return_time_47h_59m, self.hire_settings), 2)
        return_date_23h_59m = pickup_date + datetime.timedelta(days=1)
        return_time_23h_59m = datetime.time(8, 59)
        self.assertEqual(calculate_hire_duration_days(self.motorcycle_with_daily_rate, pickup_date, return_date_23h_59m, pickup_time, return_time_23h_59m, self.hire_settings), 1)
        return_date_2_days_6_hours = pickup_date + datetime.timedelta(days=2)
        return_time_2_days_6_hours = datetime.time(15, 0)
        self.assertEqual(calculate_hire_duration_days(self.motorcycle_with_daily_rate, pickup_date, return_date_2_days_6_hours, pickup_time, return_time_2_days_6_hours, self.hire_settings), 3)

    # Tests '24_hour_plus_margin' duration with excess within, at, and exceeding margin.
    def test_calculate_hire_duration_days_24_hour_plus_margin_strategy(self):
        self.hire_settings.hire_pricing_strategy = '24_hour_plus_margin'
        self.hire_settings.excess_hours_margin = 3
        self.hire_settings.save()
        pickup_date = timezone.now().date()
        pickup_time = datetime.time(9, 0)
        return_date_exact = pickup_date + datetime.timedelta(days=2)
        return_time_exact = datetime.time(9, 0) # 48 hours
        self.assertEqual(calculate_hire_duration_days(self.motorcycle_with_daily_rate, pickup_date, return_date_exact, pickup_time, return_time_exact, self.hire_settings), 2)
        return_time_within_margin = datetime.time(11, 0) # 2 days + 2 hours (within 3h margin)
        self.assertEqual(calculate_hire_duration_days(self.motorcycle_with_daily_rate, pickup_date, return_date_exact, pickup_time, return_time_within_margin, self.hire_settings), 2)
        return_time_at_margin = datetime.time(12, 0) # 2 days + 3 hours (at 3h margin)
        self.assertEqual(calculate_hire_duration_days(self.motorcycle_with_daily_rate, pickup_date, return_date_exact, pickup_time, return_time_at_margin, self.hire_settings), 2)
        return_time_exceeds_margin = datetime.time(13, 0) # 2 days + 4 hours (exceeds 3h margin)
        self.assertEqual(calculate_hire_duration_days(self.motorcycle_with_daily_rate, pickup_date, return_date_exact, pickup_time, return_time_exceeds_margin, self.hire_settings), 3)

    # Tests '24_hour_customer_friendly' duration based on cost of excess hours.
    def test_calculate_hire_duration_days_24_hour_customer_friendly_strategy(self):
        self.hire_settings.hire_pricing_strategy = '24_hour_customer_friendly'
        self.hire_settings.save()
        pickup_date = timezone.now().date()
        pickup_time = datetime.time(9, 0)
        motorcycle_for_test = self.motorcycle_with_daily_rate
        return_date_exact = pickup_date + datetime.timedelta(days=2)
        return_time_exact = datetime.time(9, 0) # 48 hours
        self.assertEqual(calculate_hire_duration_days(motorcycle_for_test, pickup_date, return_date_exact, pickup_time, return_time_exact, self.hire_settings), 2)
        return_time_hourly_cheaper = datetime.time(12, 0) # 2 days + 3h excess (3*20=60 < 100)
        self.assertEqual(calculate_hire_duration_days(motorcycle_for_test, pickup_date, return_date_exact, pickup_time, return_time_hourly_cheaper, self.hire_settings), 2)
        return_time_hourly_equals_daily = datetime.time(14, 0) # 2 days + 5h excess (5*20=100 == 100)
        self.assertEqual(calculate_hire_duration_days(motorcycle_for_test, pickup_date, return_date_exact, pickup_time, return_time_hourly_equals_daily, self.hire_settings), 3)
        return_time_hourly_more_than_daily = datetime.time(15, 0) # 2 days + 6h excess (6*20=120 > 100)
        self.assertEqual(calculate_hire_duration_days(motorcycle_for_test, pickup_date, return_date_exact, pickup_time, return_time_hourly_more_than_daily, self.hire_settings), 3)
        return_date_same_day = pickup_date
        return_time_5_hours = datetime.time(14, 0) # 5 hours same day
        self.assertEqual(calculate_hire_duration_days(motorcycle_for_test, pickup_date, return_date_same_day, pickup_time, return_time_5_hours, self.hire_settings), 1)

    # Tests 'daily_plus_excess_hourly' duration (counts only full 24h blocks).
    def test_calculate_hire_duration_days_daily_plus_excess_hourly_strategy(self):
        self.hire_settings.hire_pricing_strategy = 'daily_plus_excess_hourly'
        self.hire_settings.save()
        pickup_date = timezone.now().date()
        pickup_time = datetime.time(9, 0)
        return_date_exact = pickup_date + datetime.timedelta(days=2)
        return_time_exact = datetime.time(9, 0) # 48 hours
        self.assertEqual(calculate_hire_duration_days(self.motorcycle_with_daily_rate, pickup_date, return_date_exact, pickup_time, return_time_exact, self.hire_settings), 2)
        return_date_excess = pickup_date + datetime.timedelta(days=2)
        return_time_excess = datetime.time(14, 30) # 2 days + 5.5 hours
        self.assertEqual(calculate_hire_duration_days(self.motorcycle_with_daily_rate, pickup_date, return_date_excess, pickup_time, return_time_excess, self.hire_settings), 2)
        pickup_date_span = timezone.now().date()
        pickup_time_span = datetime.time(22, 0)
        return_date_span = pickup_date_span + datetime.timedelta(days=1)
        return_time_span = datetime.time(2, 0) # 4 hours total over midnight
        self.assertEqual(calculate_hire_duration_days(self.motorcycle_with_daily_rate, pickup_date_span, return_date_span, pickup_time_span, return_time_span, self.hire_settings), 0)

    # Tests overlap check with no overlapping bookings.
    def test_get_overlapping_motorcycle_bookings_no_overlap(self):
        create_hire_booking(
            motorcycle=self.motorcycle_with_daily_rate, driver_profile=self.driver_profile,
            pickup_date=timezone.now().date() + datetime.timedelta(days=1), pickup_time=datetime.time(10, 0),
            return_date=timezone.now().date() + datetime.timedelta(days=2), return_time=datetime.time(10, 0),
        )
        pickup_date = timezone.now().date() + datetime.timedelta(days=3)
        pickup_time = datetime.time(10, 0)
        return_date = timezone.now().date() + datetime.timedelta(days=4)
        return_time = datetime.time(10, 0)
        overlaps = get_overlapping_motorcycle_bookings(
            self.motorcycle_with_daily_rate, pickup_date, pickup_time, return_date, return_time
        )
        self.assertEqual(len(overlaps), 0)

    # Tests overlap check when new booking is fully within an existing booking.
    def test_get_overlapping_motorcycle_bookings_full_overlap(self):
        booking1 = create_hire_booking(
            motorcycle=self.motorcycle_with_daily_rate, driver_profile=self.driver_profile,
            pickup_date=timezone.now().date() + datetime.timedelta(days=1), pickup_time=datetime.time(10, 0),
            return_date=timezone.now().date() + datetime.timedelta(days=5), return_time=datetime.time(10, 0),
        )
        pickup_date = timezone.now().date() + datetime.timedelta(days=2)
        pickup_time = datetime.time(10, 0)
        return_date = timezone.now().date() + datetime.timedelta(days=3)
        return_time = datetime.time(10, 0)
        overlaps = get_overlapping_motorcycle_bookings(
            self.motorcycle_with_daily_rate, pickup_date, pickup_time, return_date, return_time
        )
        self.assertEqual(len(overlaps), 1)
        self.assertIn(booking1, overlaps)

    # Tests overlap check when new booking starts within and ends after an existing booking.
    def test_get_overlapping_motorcycle_bookings_partial_overlap_start_within(self):
        booking1 = create_hire_booking(
            motorcycle=self.motorcycle_with_daily_rate, driver_profile=self.driver_profile,
            pickup_date=timezone.now().date() + datetime.timedelta(days=1), pickup_time=datetime.time(10, 0),
            return_date=timezone.now().date() + datetime.timedelta(days=3), return_time=datetime.time(10, 0),
        )
        pickup_date = timezone.now().date() + datetime.timedelta(days=2)
        pickup_time = datetime.time(10, 0)
        return_date = timezone.now().date() + datetime.timedelta(days=4)
        return_time = datetime.time(10, 0)
        overlaps = get_overlapping_motorcycle_bookings(
            self.motorcycle_with_daily_rate, pickup_date, pickup_time, return_date, return_time
        )
        self.assertEqual(len(overlaps), 1)
        self.assertIn(booking1, overlaps)

    # Tests overlap check when new booking starts before and ends within an existing booking.
    def test_get_overlapping_motorcycle_bookings_partial_overlap_end_within(self):
        booking1 = create_hire_booking(
            motorcycle=self.motorcycle_with_daily_rate, driver_profile=self.driver_profile,
            pickup_date=timezone.now().date() + datetime.timedelta(days=2), pickup_time=datetime.time(10, 0),
            return_date=timezone.now().date() + datetime.timedelta(days=4), return_time=datetime.time(10, 0),
        )
        pickup_date = timezone.now().date() + datetime.timedelta(days=1)
        pickup_time = datetime.time(10, 0)
        return_date = timezone.now().date() + datetime.timedelta(days=3)
        return_time = datetime.time(10, 0)
        overlaps = get_overlapping_motorcycle_bookings(
            self.motorcycle_with_daily_rate, pickup_date, pickup_time, return_date, return_time
        )
        self.assertEqual(len(overlaps), 1)
        self.assertIn(booking1, overlaps)

    # Tests overlap check with adjacent bookings (should not overlap).
    def test_get_overlapping_motorcycle_bookings_adjacent_bookings(self):
        create_hire_booking(
            motorcycle=self.motorcycle_with_daily_rate, driver_profile=self.driver_profile,
            pickup_date=timezone.now().date() + datetime.timedelta(days=1), pickup_time=datetime.time(10, 0),
            return_date=timezone.now().date() + datetime.timedelta(days=2), return_time=datetime.time(10, 0),
        )
        pickup_date = timezone.now().date() + datetime.timedelta(days=2)
        pickup_time = datetime.time(10, 0)
        return_date = timezone.now().date() + datetime.timedelta(days=3)
        return_time = datetime.time(10, 0)
        overlaps = get_overlapping_motorcycle_bookings(
            self.motorcycle_with_daily_rate, pickup_date, pickup_time, return_date, return_time
        )
        self.assertEqual(len(overlaps), 0)

    # Tests overlap check excluding a specific booking ID.
    def test_get_overlapping_motorcycle_bookings_with_exclude_id(self):
        booking1 = create_hire_booking(
            motorcycle=self.motorcycle_with_daily_rate, driver_profile=self.driver_profile,
            pickup_date=timezone.now().date() + datetime.timedelta(days=1), pickup_time=datetime.time(10, 0),
            return_date=timezone.now().date() + datetime.timedelta(days=3), return_time=datetime.time(10, 0),
        )
        booking2 = create_hire_booking(
            motorcycle=self.motorcycle_with_daily_rate, driver_profile=self.driver_profile,
            pickup_date=timezone.now().date() + datetime.timedelta(days=2), pickup_time=datetime.time(10, 0),
            return_date=timezone.now().date() + datetime.timedelta(days=4), return_time=datetime.time(10, 0),
        )
        pickup_date = timezone.now().date() + datetime.timedelta(days=2)
        pickup_time = datetime.time(10, 0)
        return_date = timezone.now().date() + datetime.timedelta(days=3)
        return_time = datetime.time(10, 0)
        overlaps = get_overlapping_motorcycle_bookings(
            self.motorcycle_with_daily_rate, pickup_date, pickup_time, return_date, return_time,
            exclude_booking_id=booking1.id
        )
        self.assertEqual(len(overlaps), 1)
        self.assertIn(booking2, overlaps)
        self.assertNotIn(booking1, overlaps)

    # Tests that cancelled bookings are ignored in overlap checks.
    def test_get_overlapping_motorcycle_bookings_cancelled_status(self):
        create_hire_booking(
            motorcycle=self.motorcycle_with_daily_rate, driver_profile=self.driver_profile,
            pickup_date=timezone.now().date() + datetime.timedelta(days=1), pickup_time=datetime.time(10, 0),
            return_date=timezone.now().date() + datetime.timedelta(days=3), return_time=datetime.time(10, 0),
            status='cancelled'
        )
        pickup_date = timezone.now().date() + datetime.timedelta(days=2)
        pickup_time = datetime.time(10, 0)
        return_date = timezone.now().date() + datetime.timedelta(days=3)
        return_time = datetime.time(10, 0)
        overlaps = get_overlapping_motorcycle_bookings(
            self.motorcycle_with_daily_rate, pickup_date, pickup_time, return_date, return_time
        )
        self.assertEqual(len(overlaps), 0)

    # Tests that completed bookings are ignored in overlap checks.
    def test_get_overlapping_motorcycle_bookings_completed_status(self):
        create_hire_booking(
            motorcycle=self.motorcycle_with_daily_rate, driver_profile=self.driver_profile,
            pickup_date=timezone.now().date() - datetime.timedelta(days=5),
            pickup_time=datetime.time(10, 0),
            return_date=timezone.now().date() - datetime.timedelta(days=3),
            return_time=datetime.time(10, 0),
            status='completed'
        )
        pickup_date = timezone.now().date() + datetime.timedelta(days=2)
        pickup_time = datetime.time(10, 0)
        return_date = timezone.now().date() + datetime.timedelta(days=3)
        return_time = datetime.time(10, 0)
        overlaps = get_overlapping_motorcycle_bookings(
            self.motorcycle_with_daily_rate, pickup_date, pickup_time, return_date, return_time
        )
        self.assertEqual(len(overlaps), 0)

    # Tests that 'no_show' bookings are ignored in overlap checks.
    def test_get_overlapping_motorcycle_bookings_no_show_status(self):
        create_hire_booking(
            motorcycle=self.motorcycle_with_daily_rate, driver_profile=self.driver_profile,
            pickup_date=timezone.now().date() + datetime.timedelta(days=1), pickup_time=datetime.time(10, 0),
            return_date=timezone.now().date() + datetime.timedelta(days=3), return_time=datetime.time(10, 0),
            status='no_show'
        )
        pickup_date = timezone.now().date() + datetime.timedelta(days=2)
        pickup_time = datetime.time(10, 0)
        return_date = timezone.now().date() + datetime.timedelta(days=3)
        return_time = datetime.time(10, 0)
        overlaps = get_overlapping_motorcycle_bookings(
            self.motorcycle_with_daily_rate, pickup_date, pickup_time, return_date, return_time
        )
        self.assertEqual(len(overlaps), 0)

    # Tests overlap check when query return is before query pickup (invalid range).
    def test_get_overlapping_motorcycle_bookings_return_before_pickup_query(self):
        create_hire_booking(
            motorcycle=self.motorcycle_with_daily_rate, driver_profile=self.driver_profile,
            pickup_date=timezone.now().date() + datetime.timedelta(days=1), pickup_time=datetime.time(10, 0),
            return_date=timezone.now().date() + datetime.timedelta(days=3), return_time=datetime.time(10, 0),
        )
        pickup_date = timezone.now().date() + datetime.timedelta(days=2)
        pickup_time = datetime.time(10, 0)
        return_date = timezone.now().date() + datetime.timedelta(days=1)
        return_time = datetime.time(10, 0)
        overlaps = get_overlapping_motorcycle_bookings(
            self.motorcycle_with_daily_rate, pickup_date, pickup_time, return_date, return_time
        )
        self.assertEqual(len(overlaps), 0)

    # Tests overlap check when query return is same as query pickup (zero duration).
    def test_get_overlapping_motorcycle_bookings_return_equal_pickup_query(self):
        create_hire_booking(
            motorcycle=self.motorcycle_with_daily_rate, driver_profile=self.driver_profile,
            pickup_date=timezone.now().date() + datetime.timedelta(days=1), pickup_time=datetime.time(10, 0),
            return_date=timezone.now().date() + datetime.timedelta(days=3), return_time=datetime.time(10, 0),
        )
        pickup_date = timezone.now().date() + datetime.timedelta(days=2)
        pickup_time = datetime.time(10, 0)
        return_date = pickup_date
        return_time = pickup_time
        overlaps = get_overlapping_motorcycle_bookings(
            self.motorcycle_with_daily_rate, pickup_date, pickup_time, return_date, return_time
        )
        self.assertEqual(len(overlaps), 0)
