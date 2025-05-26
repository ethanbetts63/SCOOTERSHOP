# hire/tests/view_tests/test_utils.py

import datetime
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
# inventory.models.Motorcycle is not directly used in tests, but create_motorcycle factory is.
# from inventory.models import Motorcycle
# hire.models.HireBooking is not directly used in tests, but create_hire_booking factory is.
# from hire.models import HireBooking
# from dashboard.models import HireSettings # HireSettings is used via create_hire_settings

from hire.views.utils import (
    calculate_motorcycle_hire_price, # Updated
    calculate_package_price,         # New
    calculate_addon_price,           # New
    calculate_total_addons_price,    # New
    calculate_booking_grand_total,   # New
    calculate_hire_duration_days,
    get_overlapping_motorcycle_bookings
)
from hire.tests.test_helpers.model_factories import (
    create_motorcycle,
    create_hire_settings,
    create_hire_booking, # For overlap tests
    create_driver_profile, # For overlap tests
    create_addon,            # New
    create_package,          # New
    create_temp_hire_booking, # New
    create_temp_booking_addon # New
)
from hire.models import AddOn, Package, TempHireBooking, TempBookingAddOn # For type hinting or direct use

class MotorcyclePricingUtilsTests(TestCase): # Renamed for clarity

    def setUp(self):
        self.motorcycle_with_rates = create_motorcycle( # Renamed for clarity
            daily_hire_rate=Decimal('100.00'),
            hourly_hire_rate=Decimal('20.00')
        )
        self.motorcycle_no_rates = create_motorcycle( # Renamed for clarity
            daily_hire_rate=None,
            hourly_hire_rate=None
        )
        self.hire_settings = create_hire_settings(
            default_daily_rate=Decimal('90.00'),
            default_hourly_rate=Decimal('15.00'),
            hire_pricing_strategy='24_hour_customer_friendly', # Default for some tests
            excess_hours_margin=2,
            minimum_hire_duration_hours=1,
        )
        # self.driver_profile = create_driver_profile() # Moved to overlap tests where needed

    def test_calculate_motorcycle_hire_price_same_day_hourly(self):
        pickup_date = timezone.now().date()
        pickup_time = datetime.time(9, 0)
        return_date = pickup_date
        return_time = datetime.time(11, 30) # 2.5 hours -> 3 hours billed
        expected_price_moto = self.motorcycle_with_rates.hourly_hire_rate * 3
        calculated_price_moto = calculate_motorcycle_hire_price(
            self.motorcycle_with_rates, pickup_date, return_date, pickup_time, return_time, self.hire_settings
        )
        self.assertEqual(calculated_price_moto, expected_price_moto)

        expected_price_default = self.hire_settings.default_hourly_rate * 3
        calculated_price_default = calculate_motorcycle_hire_price(
            self.motorcycle_no_rates, pickup_date, return_date, pickup_time, return_time, self.hire_settings
        )
        self.assertEqual(calculated_price_default, expected_price_default)

        return_time_short = datetime.time(9, 15) # 0.25 hours -> 1 hour billed
        expected_price_short = self.motorcycle_with_rates.hourly_hire_rate * 1
        calculated_price_short = calculate_motorcycle_hire_price(
            self.motorcycle_with_rates, pickup_date, return_date, pickup_time, return_time_short, self.hire_settings
        )
        self.assertEqual(calculated_price_short, expected_price_short)

    def test_calculate_motorcycle_hire_price_zero_or_negative_duration(self):
        pickup_date = timezone.now().date() + datetime.timedelta(days=1)
        pickup_time = datetime.time(9, 0)
        return_date_zero = pickup_date
        return_time_zero = pickup_time
        expected_price = Decimal('0.00')
        calculated_price = calculate_motorcycle_hire_price(
            self.motorcycle_with_rates, pickup_date, return_date_zero, pickup_time, return_time_zero, self.hire_settings
        )
        self.assertEqual(calculated_price, expected_price)

        return_date_negative = pickup_date - datetime.timedelta(days=1)
        calculated_price_negative = calculate_motorcycle_hire_price(
            self.motorcycle_with_rates, pickup_date, return_date_negative, pickup_time, return_time_zero, self.hire_settings
        )
        self.assertEqual(calculated_price_negative, expected_price)

    def test_calculate_motorcycle_hire_price_flat_24_hour_exact_days(self):
        self.hire_settings.hire_pricing_strategy = 'flat_24_hour'
        self.hire_settings.save()
        pickup_date = timezone.now().date() + datetime.timedelta(days=1) # Example: T+1 09:00
        pickup_time = datetime.time(9, 0)
        return_date = pickup_date + datetime.timedelta(days=2) # Example: T+3 09:00 (48 hours = 2 days)
        return_time = datetime.time(9, 0)
        expected_price = self.motorcycle_with_rates.daily_hire_rate * 2
        calculated_price = calculate_motorcycle_hire_price(
            self.motorcycle_with_rates, pickup_date, return_date, pickup_time, return_time, self.hire_settings
        )
        self.assertEqual(calculated_price, expected_price)

    def test_calculate_motorcycle_hire_price_flat_24_hour_with_excess(self):
        self.hire_settings.hire_pricing_strategy = 'flat_24_hour'
        self.hire_settings.save()
        pickup_date = timezone.now().date() + datetime.timedelta(days=1) # T+1 09:00
        pickup_time = datetime.time(9, 0)
        # Duration: 2 days, 1 minute (48h 1min -> 3 days)
        pickup_datetime_val = datetime.datetime.combine(pickup_date, pickup_time)
        return_datetime_val = pickup_datetime_val + datetime.timedelta(days=2, minutes=1)
        return_date = return_datetime_val.date()
        return_time = return_datetime_val.time()

        expected_price = self.motorcycle_with_rates.daily_hire_rate * 3
        calculated_price = calculate_motorcycle_hire_price(
            self.motorcycle_with_rates, pickup_date, return_date, pickup_time, return_time, self.hire_settings
        )
        self.assertEqual(calculated_price, expected_price)

    def test_calculate_motorcycle_hire_price_flat_24_hour_with_almost_full_excess(self):
        self.hire_settings.hire_pricing_strategy = 'flat_24_hour'
        self.hire_settings.save()
        pickup_date = timezone.now().date() + datetime.timedelta(days=1) # T+1 09:00
        pickup_time = datetime.time(9, 0)

        # Test 1: 23h 59min (should be 1 day)
        # This duration is not same-day, e.g., T+1 09:00 to T+2 08:59
        pickup_datetime_val_short = datetime.datetime.combine(pickup_date, pickup_time)
        duration_23h59m = datetime.timedelta(hours=23, minutes=59)
        return_datetime_val_short = pickup_datetime_val_short + duration_23h59m
        actual_return_date_short = return_datetime_val_short.date()
        actual_return_time_short = return_datetime_val_short.time()

        calculated_price_short = calculate_motorcycle_hire_price(
             self.motorcycle_with_rates, pickup_date, actual_return_date_short, pickup_time, actual_return_time_short, self.hire_settings
        )
        self.assertEqual(calculated_price_short, self.motorcycle_with_rates.daily_hire_rate * 1)

        # Test 2: 1 day 23h 59m (47h 59m total) (should be 2 days)
        # e.g., T+1 09:00 to T+3 08:59
        duration_47h59m = datetime.timedelta(hours=47, minutes=59)
        return_datetime_val_long = pickup_datetime_val_short + duration_47h59m # Using same pickup_datetime_val_short as base
        actual_return_date_long = return_datetime_val_long.date()
        actual_return_time_long = return_datetime_val_long.time()

        expected_price_long = self.motorcycle_with_rates.daily_hire_rate * 2
        calculated_price_long = calculate_motorcycle_hire_price(
            self.motorcycle_with_rates, pickup_date, actual_return_date_long, pickup_time, actual_return_time_long, self.hire_settings
        )
        self.assertEqual(calculated_price_long, expected_price_long)


    def test_calculate_motorcycle_hire_price_24_hour_plus_margin_within_margin(self):
        self.hire_settings.hire_pricing_strategy = '24_hour_plus_margin'
        self.hire_settings.excess_hours_margin = 3
        self.hire_settings.save()
        pickup_date = timezone.now().date() + datetime.timedelta(days=1) # T+1 09:00
        pickup_time = datetime.time(9, 0)
        # Duration: 2 days + 2 hours (50 hours total). 2h excess <= 3h margin.
        pickup_datetime_val = datetime.datetime.combine(pickup_date, pickup_time)
        return_datetime_val = pickup_datetime_val + datetime.timedelta(days=2, hours=2)
        return_date = return_datetime_val.date()
        return_time = return_datetime_val.time()

        expected_price = self.motorcycle_with_rates.daily_hire_rate * 2 # Bills 2 days
        calculated_price = calculate_motorcycle_hire_price(
            self.motorcycle_with_rates, pickup_date, return_date, pickup_time, return_time, self.hire_settings
        )
        self.assertEqual(calculated_price, expected_price)

    def test_calculate_motorcycle_hire_price_24_hour_plus_margin_exceeds_margin(self):
        self.hire_settings.hire_pricing_strategy = '24_hour_plus_margin'
        self.hire_settings.excess_hours_margin = 3
        self.hire_settings.save()
        pickup_date = timezone.now().date() + datetime.timedelta(days=1) # T+1 09:00
        pickup_time = datetime.time(9, 0)
        # Duration: 2 days + 4 hours (52 hours total). 4h excess > 3h margin.
        pickup_datetime_val = datetime.datetime.combine(pickup_date, pickup_time)
        return_datetime_val = pickup_datetime_val + datetime.timedelta(days=2, hours=4)
        return_date = return_datetime_val.date()
        return_time = return_datetime_val.time()

        expected_price = self.motorcycle_with_rates.daily_hire_rate * 3 # Bills 3 days
        calculated_price = calculate_motorcycle_hire_price(
            self.motorcycle_with_rates, pickup_date, return_date, pickup_time, return_time, self.hire_settings
        )
        self.assertEqual(calculated_price, expected_price)

    def test_calculate_motorcycle_hire_price_24_hour_plus_margin_no_excess(self):
        self.hire_settings.hire_pricing_strategy = '24_hour_plus_margin'
        self.hire_settings.excess_hours_margin = 3
        self.hire_settings.save()
        pickup_date = timezone.now().date() + datetime.timedelta(days=1)
        pickup_time = datetime.time(9, 0)
        return_date = pickup_date + datetime.timedelta(days=2) # Exact 2 days
        return_time = datetime.time(9, 0)
        expected_price = self.motorcycle_with_rates.daily_hire_rate * 2
        calculated_price = calculate_motorcycle_hire_price(
            self.motorcycle_with_rates, pickup_date, return_date, pickup_time, return_time, self.hire_settings
        )
        self.assertEqual(calculated_price, expected_price)

    def test_calculate_motorcycle_hire_price_24_hour_customer_friendly_hourly_cheaper(self):
        self.hire_settings.hire_pricing_strategy = '24_hour_customer_friendly'
        self.hire_settings.save()
        pickup_date = timezone.now().date() + datetime.timedelta(days=1) # T+1 09:00
        pickup_time = datetime.time(9, 0)
        # Duration: 2 days + 3 hours (51 hours total). 3h excess.
        # Cost of excess: 3 * hourly_rate (20) = 60. Daily_rate = 100. 60 < 100.
        pickup_datetime_val = datetime.datetime.combine(pickup_date, pickup_time)
        return_datetime_val = pickup_datetime_val + datetime.timedelta(days=2, hours=3)
        return_date = return_datetime_val.date()
        return_time = return_datetime_val.time()

        expected_price = (self.motorcycle_with_rates.daily_hire_rate * 2) + \
                         (self.motorcycle_with_rates.hourly_hire_rate * 3)
        calculated_price = calculate_motorcycle_hire_price(
            self.motorcycle_with_rates, pickup_date, return_date, pickup_time, return_time, self.hire_settings
        )
        self.assertEqual(calculated_price, expected_price)

    def test_calculate_motorcycle_hire_price_24_hour_customer_friendly_daily_cheaper(self):
        self.hire_settings.hire_pricing_strategy = '24_hour_customer_friendly'
        self.hire_settings.save()
        pickup_date = timezone.now().date() + datetime.timedelta(days=1) # T+1 09:00
        pickup_time = datetime.time(9, 0)
        # Duration: 2 days + 6 hours (54 hours total). 6h excess.
        # Cost of excess: 6 * hourly_rate (20) = 120. Daily_rate = 100. 100 < 120.
        pickup_datetime_val = datetime.datetime.combine(pickup_date, pickup_time)
        return_datetime_val = pickup_datetime_val + datetime.timedelta(days=2, hours=6)
        return_date = return_datetime_val.date()
        return_time = return_datetime_val.time()

        expected_price = (self.motorcycle_with_rates.daily_hire_rate * 2) + \
                         self.motorcycle_with_rates.daily_hire_rate # Add full daily rate for excess
        calculated_price = calculate_motorcycle_hire_price(
            self.motorcycle_with_rates, pickup_date, return_date, pickup_time, return_time, self.hire_settings
        )
        self.assertEqual(calculated_price, expected_price)

    def test_calculate_motorcycle_hire_price_24_hour_customer_friendly_no_excess(self):
        self.hire_settings.hire_pricing_strategy = '24_hour_customer_friendly'
        self.hire_settings.save()
        pickup_date = timezone.now().date() + datetime.timedelta(days=1)
        pickup_time = datetime.time(9, 0)
        return_date = pickup_date + datetime.timedelta(days=2) # Exact 2 days
        return_time = datetime.time(9, 0)
        expected_price = self.motorcycle_with_rates.daily_hire_rate * 2
        calculated_price = calculate_motorcycle_hire_price(
            self.motorcycle_with_rates, pickup_date, return_date, pickup_time, return_time, self.hire_settings
        )
        self.assertEqual(calculated_price, expected_price)

    def test_calculate_motorcycle_hire_price_daily_plus_excess_hourly(self):
        self.hire_settings.hire_pricing_strategy = 'daily_plus_excess_hourly'
        self.hire_settings.save()
        pickup_date = timezone.now().date() + datetime.timedelta(days=1) # T+1 09:00
        pickup_time = datetime.time(9, 0)
        # Duration: 2 days + 5.5 hours (53.5 hours total). 5.5h excess -> 6h billed hourly.
        pickup_datetime_val = datetime.datetime.combine(pickup_date, pickup_time)
        return_datetime_val = pickup_datetime_val + datetime.timedelta(days=2, hours=5, minutes=30)
        return_date = return_datetime_val.date()
        return_time = return_datetime_val.time()

        expected_price = (self.motorcycle_with_rates.daily_hire_rate * 2) + \
                         (self.motorcycle_with_rates.hourly_hire_rate * 6)
        calculated_price = calculate_motorcycle_hire_price(
            self.motorcycle_with_rates, pickup_date, return_date, pickup_time, return_time, self.hire_settings
        )
        self.assertEqual(calculated_price, expected_price)

    def test_calculate_motorcycle_hire_price_daily_plus_excess_hourly_no_excess(self):
        self.hire_settings.hire_pricing_strategy = 'daily_plus_excess_hourly'
        self.hire_settings.save()
        pickup_date = timezone.now().date() + datetime.timedelta(days=1)
        pickup_time = datetime.time(9, 0)
        return_date = pickup_date + datetime.timedelta(days=2) # Exact 2 days
        return_time = datetime.time(9, 0)
        expected_price = self.motorcycle_with_rates.daily_hire_rate * 2
        calculated_price = calculate_motorcycle_hire_price(
            self.motorcycle_with_rates, pickup_date, return_date, pickup_time, return_time, self.hire_settings
        )
        self.assertEqual(calculated_price, expected_price)

# --- Tests for calculate_hire_duration_days ---
class HireDurationUtilsTests(TestCase):
    def setUp(self):
        self.motorcycle = create_motorcycle(daily_hire_rate=Decimal('100.00'), hourly_hire_rate=Decimal('20.00'))
        self.hire_settings = create_hire_settings(excess_hours_margin=3, default_daily_rate=Decimal('100.00'), default_hourly_rate=Decimal('20.00'))
        self.base_date = timezone.now().date() # Add a base date for time arithmetic

    def test_calculate_hire_duration_days_same_day_hire(self):
        pickup_date = timezone.now().date()
        pickup_time = datetime.time(9, 0)
        return_date = pickup_date
        return_time = datetime.time(17, 0) # 8 hours, same day
        # For same-day hires, duration_days is always 1 if there's any positive duration
        for strategy in ['flat_24_hour', '24_hour_plus_margin', '24_hour_customer_friendly', 'daily_plus_excess_hourly']:
            self.hire_settings.hire_pricing_strategy = strategy
            self.hire_settings.save()
            duration = calculate_hire_duration_days(
                self.motorcycle, pickup_date, return_date, pickup_time, return_time, self.hire_settings
            )
            self.assertEqual(duration, 1, f"Failed for strategy: {strategy}")

        return_time_short = datetime.time(9, 15) # 15 mins, same day
        for strategy in ['flat_24_hour', '24_hour_plus_margin', '24_hour_customer_friendly', 'daily_plus_excess_hourly']:
            self.hire_settings.hire_pricing_strategy = strategy
            self.hire_settings.save()
            duration_short = calculate_hire_duration_days(
                self.motorcycle, pickup_date, return_date, pickup_time, return_time_short, self.hire_settings
            )
            self.assertEqual(duration_short, 1, f"Failed for strategy (short): {strategy}")

    def test_calculate_hire_duration_days_zero_or_negative_duration(self):
        pickup_date = timezone.now().date() + datetime.timedelta(days=1)
        pickup_time = datetime.time(9, 0)
        return_date_zero = pickup_date
        return_time_zero = pickup_time # Zero duration
        self.hire_settings.hire_pricing_strategy = 'flat_24_hour'
        self.hire_settings.save()
        duration = calculate_hire_duration_days(
            self.motorcycle, pickup_date, return_date_zero, pickup_time, return_time_zero, self.hire_settings
        )
        self.assertEqual(duration, 0)

        return_date_negative = pickup_date - datetime.timedelta(days=1) # Negative duration
        duration_negative = calculate_hire_duration_days(
            self.motorcycle, pickup_date, return_date_negative, pickup_time, return_time_zero, self.hire_settings
        )
        self.assertEqual(duration_negative, 0)

    def test_calculate_hire_duration_days_flat_24_hour_strategy(self):
        self.hire_settings.hire_pricing_strategy = 'flat_24_hour'
        self.hire_settings.save()
        pickup_date = timezone.now().date()
        pickup_time = datetime.time(9, 0) # T 09:00
        
        # Helper to create end date/time from duration
        def get_end_datetime_parts(start_dt, duration_delta):
            end_dt = start_dt + duration_delta
            return end_dt.date(), end_dt.time()

        start_datetime = datetime.datetime.combine(pickup_date, pickup_time)

        # Test cases:
        # 1. 24 hours exactly -> 1 day
        end_date_1, end_time_1 = get_end_datetime_parts(start_datetime, datetime.timedelta(hours=24))
        self.assertEqual(calculate_hire_duration_days(self.motorcycle, pickup_date, end_date_1, pickup_time, end_time_1, self.hire_settings), 1)
        
        # 2. 24 hours + 1 minute -> 2 days
        end_date_2, end_time_2 = get_end_datetime_parts(start_datetime, datetime.timedelta(hours=24, minutes=1))
        self.assertEqual(calculate_hire_duration_days(self.motorcycle, pickup_date, end_date_2, pickup_time, end_time_2, self.hire_settings), 2)

        # 3. 47 hours 59 minutes -> 2 days (ceil(47.98/24) = 2)
        # This was the failing test. Corrected parameters to reflect 47h 59m.
        target_duration_47h59m = datetime.timedelta(hours=47, minutes=59)
        end_datetime_for_test = datetime.datetime.combine(pickup_date, pickup_time) + target_duration_47h59m
        return_date_for_test = end_datetime_for_test.date()
        return_time_for_test = end_datetime_for_test.time()
        self.assertEqual(calculate_hire_duration_days(self.motorcycle, pickup_date, return_date_for_test, pickup_time, return_time_for_test, self.hire_settings), 2)

        # 4. 23 hours 59 minutes -> 1 day (ceil(23.98/24) = 1)
        end_date_4, end_time_4 = get_end_datetime_parts(start_datetime, datetime.timedelta(hours=23, minutes=59))
        self.assertEqual(calculate_hire_duration_days(self.motorcycle, pickup_date, end_date_4, pickup_time, end_time_4, self.hire_settings), 1)
        
        # 5. 2 days 6 hours (54 hours) -> 3 days (ceil(54/24)=3)
        end_date_5, end_time_5 = get_end_datetime_parts(start_datetime, datetime.timedelta(days=2, hours=6))
        self.assertEqual(calculate_hire_duration_days(self.motorcycle, pickup_date, end_date_5, pickup_time, end_time_5, self.hire_settings), 3)


    def test_calculate_hire_duration_days_24_hour_plus_margin_strategy(self):
        self.hire_settings.hire_pricing_strategy = '24_hour_plus_margin'
        self.hire_settings.excess_hours_margin = 3
        self.hire_settings.save()
        pickup_date = timezone.now().date()
        pickup_time = datetime.time(9, 0) # T 09:00

        start_datetime = datetime.datetime.combine(pickup_date, pickup_time)
        def get_end_parts(duration_delta):
            end_dt = start_datetime + duration_delta
            return end_dt.date(), end_dt.time()

        # Test cases:
        # 1. 48 hours (2 days exact) -> 2 days
        rd1, rt1 = get_end_parts(datetime.timedelta(days=2))
        self.assertEqual(calculate_hire_duration_days(self.motorcycle, pickup_date, rd1, pickup_time, rt1, self.hire_settings), 2)
        
        # 2. 2 days + 2 hours (within 3h margin) -> 2 days
        rd2, rt2 = get_end_parts(datetime.timedelta(days=2, hours=2))
        self.assertEqual(calculate_hire_duration_days(self.motorcycle, pickup_date, rd2, pickup_time, rt2, self.hire_settings), 2)
        
        # 3. 2 days + 3 hours (at 3h margin) -> 2 days
        rd3, rt3 = get_end_parts(datetime.timedelta(days=2, hours=3))
        self.assertEqual(calculate_hire_duration_days(self.motorcycle, pickup_date, rd3, pickup_time, rt3, self.hire_settings), 2)
        
        # 4. 2 days + 4 hours (exceeds 3h margin) -> 3 days
        rd4, rt4 = get_end_parts(datetime.timedelta(days=2, hours=4))
        self.assertEqual(calculate_hire_duration_days(self.motorcycle, pickup_date, rd4, pickup_time, rt4, self.hire_settings), 3)
        
        # 5. 10 hours (not same-day, e.g. overnight) -> 1 day
        # (total_hours_float > 0, full_24_hour_blocks = 0, but not margin_exceeded, so 1)
        # Example: T 09:00 to T 19:00 (10 hours). If this spans midnight, it's handled by multi-day logic.
        # If it's T1 09:00 to T2 01:00 (16 hours), full_24_hour_blocks = 0, remaining_excess_hours = 16.
        # If margin is 3, 16 > 3, so it should be 0 + 1 = 1 day.
        # The original test case was:
        # return_date_overnight_short = pickup_date
        # return_time_overnight_short = (datetime.datetime.combine(self.base_date, pickup_time) + datetime.timedelta(hours=10)).time()
        # This makes it a same-day hire, which is handled differently.
        # Let's test an overnight short hire: T1 22:00 to T2 08:00 (10 hours)
        pickup_time_os = datetime.time(22,0)
        start_dt_os = datetime.datetime.combine(pickup_date, pickup_time_os)
        rd5, rt5 = get_end_parts(datetime.timedelta(hours=10)) # This will use start_datetime (09:00), need to adjust
        
        end_dt_os_10h = start_dt_os + datetime.timedelta(hours=10) # pickup_date 22:00 + 10h = pickup_date+1day 08:00
        self.assertEqual(calculate_hire_duration_days(self.motorcycle, pickup_date, end_dt_os_10h.date(), pickup_time_os, end_dt_os_10h.time(), self.hire_settings), 1)


    def test_calculate_hire_duration_days_24_hour_customer_friendly_strategy(self):
        self.hire_settings.hire_pricing_strategy = '24_hour_customer_friendly'
        self.hire_settings.save()
        pickup_date = timezone.now().date()
        pickup_time = datetime.time(9, 0) # T 09:00
        motorcycle_for_test = self.motorcycle # daily 100, hourly 20

        start_datetime = datetime.datetime.combine(pickup_date, pickup_time)
        def get_end_parts(duration_delta):
            end_dt = start_datetime + duration_delta
            return end_dt.date(), end_dt.time()

        # Test cases:
        # 1. 48 hours (2 days exact) -> 2 days
        rd1, rt1 = get_end_parts(datetime.timedelta(days=2))
        self.assertEqual(calculate_hire_duration_days(motorcycle_for_test, pickup_date, rd1, pickup_time, rt1, self.hire_settings), 2)

        # 2. 2 days + 3h excess (51 hours total). (3*20=60 < 100 daily)
        # Duration counts as 3 days because it spans into the 3rd day period.
        rd2, rt2 = get_end_parts(datetime.timedelta(days=2, hours=3))
        self.assertEqual(calculate_hire_duration_days(motorcycle_for_test, pickup_date, rd2, pickup_time, rt2, self.hire_settings), 3)

        # 3. 2 days + 5h excess (53 hours total). (5*20=100 == 100 daily) -> 3 days
        rd3, rt3 = get_end_parts(datetime.timedelta(days=2, hours=5))
        self.assertEqual(calculate_hire_duration_days(motorcycle_for_test, pickup_date, rd3, pickup_time, rt3, self.hire_settings), 3)

        # 4. 2 days + 6h excess (54 hours total). (6*20=120 > 100 daily) -> 3 days
        rd4, rt4 = get_end_parts(datetime.timedelta(days=2, hours=6))
        self.assertEqual(calculate_hire_duration_days(motorcycle_for_test, pickup_date, rd4, pickup_time, rt4, self.hire_settings), 3)

        # 5. Same day, 5 hours -> 1 day (Handled by same-day hire condition at the start of calc_hire_duration_days)
        return_date_same_day = pickup_date
        return_time_5_hours = datetime.time(14, 0) # T 09:00 to T 14:00
        self.assertEqual(calculate_hire_duration_days(motorcycle_for_test, pickup_date, return_date_same_day, pickup_time, return_time_5_hours, self.hire_settings), 1)

        # 6. 10 hours (not same-day, e.g. overnight T 22:00 to T+1 08:00)
        # (10 * 20 = 200 > 100 daily). Billed as 1 day. Duration should be 1 day.
        pickup_time_overnight = datetime.time(22,0)
        start_dt_overnight = datetime.datetime.combine(pickup_date, pickup_time_overnight)
        end_dt_overnight = start_dt_overnight + datetime.timedelta(hours=10) # P_DATE 22:00 + 10h = P_DATE+1 08:00
        self.assertEqual(calculate_hire_duration_days(motorcycle_for_test, pickup_date, end_dt_overnight.date(), pickup_time_overnight, end_dt_overnight.time(), self.hire_settings), 1)


    def test_calculate_hire_duration_days_daily_plus_excess_hourly_strategy(self):
        self.hire_settings.hire_pricing_strategy = 'daily_plus_excess_hourly'
        self.hire_settings.save()
        pickup_date = timezone.now().date()
        pickup_time = datetime.time(9, 0) # T 09:00

        start_datetime = datetime.datetime.combine(pickup_date, pickup_time)
        def get_end_parts(duration_delta):
            end_dt = start_datetime + duration_delta
            return end_dt.date(), end_dt.time()

        # Test cases:
        # 1. 48 hours (2 days exact) -> 2 days
        rd1, rt1 = get_end_parts(datetime.timedelta(days=2))
        self.assertEqual(calculate_hire_duration_days(self.motorcycle, pickup_date, rd1, pickup_time, rt1, self.hire_settings), 2)

        # 2. 2 days + 5.5 hours (53.5 hours total) -> 3 days (because it spans into the 3rd day)
        rd2, rt2 = get_end_parts(datetime.timedelta(days=2, hours=5, minutes=30))
        self.assertEqual(calculate_hire_duration_days(self.motorcycle, pickup_date, rd2, pickup_time, rt2, self.hire_settings), 3)

        # 3. 4 hours total over midnight (e.g. T 22:00 to T+1 02:00) -> 1 day
        pickup_time_span = datetime.time(22, 0)
        start_dt_span = datetime.datetime.combine(pickup_date, pickup_time_span)
        end_dt_span = start_dt_span + datetime.timedelta(hours=4) # P_DATE 22:00 + 4h = P_DATE+1 02:00
        self.assertEqual(calculate_hire_duration_days(self.motorcycle, pickup_date, end_dt_span.date(), pickup_time_span, end_dt_span.time(), self.hire_settings), 1)

        # 4. 23 hours (not same-day, e.g. T 09:00 to T+1 08:00) -> 1 day
        rd4, rt4 = get_end_parts(datetime.timedelta(hours=23)) # P_DATE 09:00 + 23h = P_DATE+1 08:00
        self.assertEqual(calculate_hire_duration_days(self.motorcycle, pickup_date, rd4, pickup_time, rt4, self.hire_settings), 1)

# --- Tests for get_overlapping_motorcycle_bookings --- (Largely Unchanged)
class OverlapUtilsTests(TestCase):
    def setUp(self):
        self.motorcycle = create_motorcycle()
        self.driver_profile = create_driver_profile()
        self.hire_settings = create_hire_settings() # Though not directly used by overlap func

    def test_get_overlapping_motorcycle_bookings_no_overlap(self):
        create_hire_booking(
            motorcycle=self.motorcycle, driver_profile=self.driver_profile,
            pickup_date=timezone.now().date() + datetime.timedelta(days=1), pickup_time=datetime.time(10, 0),
            return_date=timezone.now().date() + datetime.timedelta(days=2), return_time=datetime.time(10, 0),
        )
        pickup_date = timezone.now().date() + datetime.timedelta(days=3)
        pickup_time = datetime.time(10, 0)
        return_date = timezone.now().date() + datetime.timedelta(days=4)
        return_time = datetime.time(10, 0)
        overlaps = get_overlapping_motorcycle_bookings(
            self.motorcycle, pickup_date, pickup_time, return_date, return_time
        )
        self.assertEqual(len(overlaps), 0)

    def test_get_overlapping_motorcycle_bookings_full_overlap(self):
        booking1 = create_hire_booking(
            motorcycle=self.motorcycle, driver_profile=self.driver_profile,
            pickup_date=timezone.now().date() + datetime.timedelta(days=1), pickup_time=datetime.time(10, 0),
            return_date=timezone.now().date() + datetime.timedelta(days=5), return_time=datetime.time(10, 0),
        )
        pickup_date = timezone.now().date() + datetime.timedelta(days=2)
        pickup_time = datetime.time(10, 0)
        return_date = timezone.now().date() + datetime.timedelta(days=3)
        return_time = datetime.time(10, 0)
        overlaps = get_overlapping_motorcycle_bookings(
            self.motorcycle, pickup_date, pickup_time, return_date, return_time
        )
        self.assertEqual(len(overlaps), 1)
        self.assertIn(booking1, overlaps)


    # Tests overlap check when new booking starts within and ends after an existing booking.
    def test_get_overlapping_motorcycle_bookings_partial_overlap_start_within(self):
        booking1 = create_hire_booking(
            motorcycle=self.motorcycle, driver_profile=self.driver_profile,
            pickup_date=timezone.now().date() + datetime.timedelta(days=1), pickup_time=datetime.time(10, 0),
            return_date=timezone.now().date() + datetime.timedelta(days=3), return_time=datetime.time(10, 0),
        )
        pickup_date = timezone.now().date() + datetime.timedelta(days=2)
        pickup_time = datetime.time(10, 0)
        return_date = timezone.now().date() + datetime.timedelta(days=4)
        return_time = datetime.time(10, 0)
        overlaps = get_overlapping_motorcycle_bookings(
            self.motorcycle, pickup_date, pickup_time, return_date, return_time
        )
        self.assertEqual(len(overlaps), 1)
        self.assertIn(booking1, overlaps)

    # Tests overlap check when new booking starts before and ends within an existing booking.
    def test_get_overlapping_motorcycle_bookings_partial_overlap_end_within(self):
        booking1 = create_hire_booking(
            motorcycle=self.motorcycle, driver_profile=self.driver_profile,
            pickup_date=timezone.now().date() + datetime.timedelta(days=2), pickup_time=datetime.time(10, 0),
            return_date=timezone.now().date() + datetime.timedelta(days=4), return_time=datetime.time(10, 0),
        )
        pickup_date = timezone.now().date() + datetime.timedelta(days=1)
        pickup_time = datetime.time(10, 0)
        return_date = timezone.now().date() + datetime.timedelta(days=3)
        return_time = datetime.time(10, 0)
        overlaps = get_overlapping_motorcycle_bookings(
            self.motorcycle, pickup_date, pickup_time, return_date, return_time
        )
        self.assertEqual(len(overlaps), 1)
        self.assertIn(booking1, overlaps)

    # Tests overlap check with adjacent bookings (should not overlap).
    def test_get_overlapping_motorcycle_bookings_adjacent_bookings(self):
        create_hire_booking(
            motorcycle=self.motorcycle, driver_profile=self.driver_profile,
            pickup_date=timezone.now().date() + datetime.timedelta(days=1), pickup_time=datetime.time(10, 0),
            return_date=timezone.now().date() + datetime.timedelta(days=2), return_time=datetime.time(10, 0),
        )
        pickup_date = timezone.now().date() + datetime.timedelta(days=2)
        pickup_time = datetime.time(10, 0)
        return_date = timezone.now().date() + datetime.timedelta(days=3)
        return_time = datetime.time(10, 0)
        overlaps = get_overlapping_motorcycle_bookings(
            self.motorcycle, pickup_date, pickup_time, return_date, return_time
        )
        self.assertEqual(len(overlaps), 0)

    # Tests overlap check excluding a specific booking ID.
    def test_get_overlapping_motorcycle_bookings_with_exclude_id(self):
        booking1 = create_hire_booking(
            motorcycle=self.motorcycle, driver_profile=self.driver_profile,
            pickup_date=timezone.now().date() + datetime.timedelta(days=1), pickup_time=datetime.time(10, 0),
            return_date=timezone.now().date() + datetime.timedelta(days=3), return_time=datetime.time(10, 0),
        )
        booking2 = create_hire_booking(
            motorcycle=self.motorcycle, driver_profile=self.driver_profile,
            pickup_date=timezone.now().date() + datetime.timedelta(days=2), pickup_time=datetime.time(10, 0),
            return_date=timezone.now().date() + datetime.timedelta(days=4), return_time=datetime.time(10, 0),
        )
        pickup_date = timezone.now().date() + datetime.timedelta(days=2)
        pickup_time = datetime.time(10, 0)
        return_date = timezone.now().date() + datetime.timedelta(days=3)
        return_time = datetime.time(10, 0)
        overlaps = get_overlapping_motorcycle_bookings(
            self.motorcycle, pickup_date, pickup_time, return_date, return_time,
            exclude_booking_id=booking1.id
        )
        self.assertEqual(len(overlaps), 1)
        self.assertIn(booking2, overlaps)
        self.assertNotIn(booking1, overlaps)

    # Tests that cancelled bookings are ignored in overlap checks.
    def test_get_overlapping_motorcycle_bookings_cancelled_status(self):
        create_hire_booking(
            motorcycle=self.motorcycle, driver_profile=self.driver_profile,
            pickup_date=timezone.now().date() + datetime.timedelta(days=1), pickup_time=datetime.time(10, 0),
            return_date=timezone.now().date() + datetime.timedelta(days=3), return_time=datetime.time(10, 0),
            status='cancelled'
        )
        pickup_date = timezone.now().date() + datetime.timedelta(days=2)
        pickup_time = datetime.time(10, 0)
        return_date = timezone.now().date() + datetime.timedelta(days=3)
        return_time = datetime.time(10, 0)
        overlaps = get_overlapping_motorcycle_bookings(
            self.motorcycle, pickup_date, pickup_time, return_date, return_time
        )
        self.assertEqual(len(overlaps), 0)

    # Tests that completed bookings are ignored in overlap checks.
    def test_get_overlapping_motorcycle_bookings_completed_status(self):
        create_hire_booking(
            motorcycle=self.motorcycle, driver_profile=self.driver_profile,
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
            self.motorcycle, pickup_date, pickup_time, return_date, return_time
        )
        self.assertEqual(len(overlaps), 0)

    # Tests that 'no_show' bookings are ignored in overlap checks.
    def test_get_overlapping_motorcycle_bookings_no_show_status(self):
        create_hire_booking(
            motorcycle=self.motorcycle, driver_profile=self.driver_profile,
            pickup_date=timezone.now().date() + datetime.timedelta(days=1), pickup_time=datetime.time(10, 0),
            return_date=timezone.now().date() + datetime.timedelta(days=3), return_time=datetime.time(10, 0),
            status='no_show'
        )
        pickup_date = timezone.now().date() + datetime.timedelta(days=2)
        pickup_time = datetime.time(10, 0)
        return_date = timezone.now().date() + datetime.timedelta(days=3)
        return_time = datetime.time(10, 0)
        overlaps = get_overlapping_motorcycle_bookings(
            self.motorcycle, pickup_date, pickup_time, return_date, return_time
        )
        self.assertEqual(len(overlaps), 0)

    # Tests overlap check when query return is before query pickup (invalid range).
    def test_get_overlapping_motorcycle_bookings_return_before_pickup_query(self):
        create_hire_booking(
            motorcycle=self.motorcycle, driver_profile=self.driver_profile,
            pickup_date=timezone.now().date() + datetime.timedelta(days=1), pickup_time=datetime.time(10, 0),
            return_date=timezone.now().date() + datetime.timedelta(days=3), return_time=datetime.time(10, 0),
        )
        pickup_date = timezone.now().date() + datetime.timedelta(days=2)
        pickup_time = datetime.time(10, 0)
        return_date = timezone.now().date() + datetime.timedelta(days=1)
        return_time = datetime.time(10, 0)
        overlaps = get_overlapping_motorcycle_bookings(
            self.motorcycle, pickup_date, pickup_time, return_date, return_time
        )
        self.assertEqual(len(overlaps), 0)

    # Tests overlap check when query return is same as query pickup (zero duration).
    def test_get_overlapping_motorcycle_bookings_return_equal_pickup_query(self):
        create_hire_booking(
            motorcycle=self.motorcycle, driver_profile=self.driver_profile,
            pickup_date=timezone.now().date() + datetime.timedelta(days=1), pickup_time=datetime.time(10, 0),
            return_date=timezone.now().date() + datetime.timedelta(days=3), return_time=datetime.time(10, 0),
        )
        pickup_date = timezone.now().date() + datetime.timedelta(days=2)
        pickup_time = datetime.time(10, 0)
        return_date = pickup_date
        return_time = pickup_time
        overlaps = get_overlapping_motorcycle_bookings(
            self.motorcycle, pickup_date, pickup_time, return_date, return_time
        )
        self.assertEqual(len(overlaps), 0)

# --- NEW Test Suites for Packages, Addons, Grand Total ---

class PackagePricingUtilsTests(TestCase):
    def setUp(self):
        self.hire_settings = create_hire_settings(hire_pricing_strategy='24_hour_customer_friendly', excess_hours_margin=2)
        self.package_adventure = create_package(
            name="Adventure Pack",
            hourly_cost=Decimal('10.00'),
            daily_cost=Decimal('50.00')
        )
        self.pickup_date = timezone.now().date() + datetime.timedelta(days=1)
        self.pickup_time = datetime.time(9, 0)


    def test_calculate_package_price_same_day_hourly(self):
        return_date = self.pickup_date
        return_time = datetime.time(11, 30) # 2.5 hours -> 3 hours billed
        expected_price = self.package_adventure.hourly_cost * 3
        calculated_price = calculate_package_price(
            self.package_adventure, self.pickup_date, return_date, self.pickup_time, return_time, self.hire_settings
        )
        self.assertEqual(calculated_price, expected_price)

    def test_calculate_package_price_flat_24_hour_exact_days(self):
        self.hire_settings.hire_pricing_strategy = 'flat_24_hour'
        self.hire_settings.save()
        
        pickup_datetime_val = datetime.datetime.combine(self.pickup_date, self.pickup_time)
        return_datetime_val = pickup_datetime_val + datetime.timedelta(days=2) # 2 full days
        return_date = return_datetime_val.date()
        return_time = return_datetime_val.time()

        expected_price = self.package_adventure.daily_cost * 2
        calculated_price = calculate_package_price(
            self.package_adventure, self.pickup_date, return_date, self.pickup_time, return_time, self.hire_settings
        )
        self.assertEqual(calculated_price, expected_price)

    def test_calculate_package_price_flat_24_hour_with_excess(self):
        self.hire_settings.hire_pricing_strategy = 'flat_24_hour'
        self.hire_settings.save()

        pickup_datetime_val = datetime.datetime.combine(self.pickup_date, self.pickup_time)
        # 2 days + 1 min -> 3 days billed by flat_24_hour
        return_datetime_val = pickup_datetime_val + datetime.timedelta(days=2, minutes=1)
        return_date = return_datetime_val.date()
        return_time = return_datetime_val.time()
        
        expected_price = self.package_adventure.daily_cost * 3 
        calculated_price = calculate_package_price(
            self.package_adventure, self.pickup_date, return_date, self.pickup_time, return_time, self.hire_settings
        )
        self.assertEqual(calculated_price, expected_price)

    def test_calculate_package_price_zero_duration(self):
        return_date = self.pickup_date
        return_time = self.pickup_time
        expected_price = Decimal('0.00')
        calculated_price = calculate_package_price(
            self.package_adventure, self.pickup_date, return_date, self.pickup_time, return_time, self.hire_settings
        )
        self.assertEqual(calculated_price, expected_price)


class AddOnPricingUtilsTests(TestCase):
    def setUp(self):
        self.hire_settings = create_hire_settings(hire_pricing_strategy='24_hour_customer_friendly', excess_hours_margin=2)
        self.addon_helmet = create_addon(name="Helmet", hourly_cost=Decimal('2.00'), daily_cost=Decimal('10.00'))
        self.addon_jacket = create_addon(name="Jacket", hourly_cost=Decimal('3.00'), daily_cost=Decimal('15.00'))

        self.pickup_date = timezone.now().date() + datetime.timedelta(days=1)
        self.pickup_time = datetime.time(9, 0)

        # TempBooking for calculate_total_addons_price
        self.temp_booking = create_temp_hire_booking(
            pickup_date=self.pickup_date,
            pickup_time=self.pickup_time,
            # Return date/time will be set per test for total_addons_price
        )

    def test_calculate_addon_price_same_day_hourly_single_quantity(self):
        return_date = self.pickup_date
        return_time = datetime.time(11, 30) # 2.5 hours -> 3 hours billed
        expected_price = self.addon_helmet.hourly_cost * 3
        calculated_price = calculate_addon_price(
            self.addon_helmet, 1, self.pickup_date, return_date, self.pickup_time, return_time, self.hire_settings
        )
        self.assertEqual(calculated_price, expected_price)

    def test_calculate_addon_price_same_day_hourly_multiple_quantity(self):
        return_date = self.pickup_date
        return_time = datetime.time(11, 30) # 2.5 hours -> 3 hours billed
        quantity = 2
        expected_price = (self.addon_helmet.hourly_cost * 3) * quantity
        calculated_price = calculate_addon_price(
            self.addon_helmet, quantity, self.pickup_date, return_date, self.pickup_time, return_time, self.hire_settings
        )
        self.assertEqual(calculated_price, expected_price)

    def test_calculate_addon_price_flat_24_hour_exact_days(self):
        self.hire_settings.hire_pricing_strategy = 'flat_24_hour'
        self.hire_settings.save()

        pickup_datetime_val = datetime.datetime.combine(self.pickup_date, self.pickup_time)
        return_datetime_val = pickup_datetime_val + datetime.timedelta(days=2) # 2 full days
        return_date = return_datetime_val.date()
        return_time = return_datetime_val.time()
        quantity = 2

        expected_price = (self.addon_helmet.daily_cost * 2) * quantity
        calculated_price = calculate_addon_price(
            self.addon_helmet, quantity, self.pickup_date, return_date, self.pickup_time, return_time, self.hire_settings
        )
        self.assertEqual(calculated_price, expected_price)

    def test_calculate_total_addons_price_no_addons(self):
        self.temp_booking.return_date = self.pickup_date + datetime.timedelta(days=1) # Any valid duration
        self.temp_booking.return_time = self.pickup_time
        self.temp_booking.save()

        calculated_price = calculate_total_addons_price(self.temp_booking, self.hire_settings)
        self.assertEqual(calculated_price, Decimal('0.00'))

    def test_calculate_total_addons_price_with_addons_same_day(self):
        self.temp_booking.return_date = self.pickup_date
        self.temp_booking.return_time = datetime.time(12, 0) # 3 hours duration
        self.temp_booking.save()

        create_temp_booking_addon(temp_booking=self.temp_booking, addon=self.addon_helmet, quantity=1)
        create_temp_booking_addon(temp_booking=self.temp_booking, addon=self.addon_jacket, quantity=2)

        expected_price_helmet = self.addon_helmet.hourly_cost * 3 # 3 hours billed
        expected_price_jacket = (self.addon_jacket.hourly_cost * 3) * 2
        expected_total = expected_price_helmet + expected_price_jacket

        calculated_total = calculate_total_addons_price(self.temp_booking, self.hire_settings)
        self.assertEqual(calculated_total, expected_total)

    def test_calculate_total_addons_price_with_addons_multi_day_flat_strategy(self):
        self.hire_settings.hire_pricing_strategy = 'flat_24_hour'
        self.hire_settings.save()

        pickup_datetime_val = datetime.datetime.combine(self.pickup_date, self.pickup_time)
        # 1 day + 2 hours -> 2 days billed by flat_24_hour strategy
        return_datetime_val = pickup_datetime_val + datetime.timedelta(days=1, hours=2)
        self.temp_booking.return_date = return_datetime_val.date()
        self.temp_booking.return_time = return_datetime_val.time()
        self.temp_booking.save()

        create_temp_booking_addon(temp_booking=self.temp_booking, addon=self.addon_helmet, quantity=1)
        create_temp_booking_addon(temp_booking=self.temp_booking, addon=self.addon_jacket, quantity=1)

        expected_price_helmet = self.addon_helmet.daily_cost * 2
        expected_price_jacket = self.addon_jacket.daily_cost * 2
        expected_total = expected_price_helmet + expected_price_jacket

        calculated_total = calculate_total_addons_price(self.temp_booking, self.hire_settings)
        self.assertEqual(calculated_total, expected_total)


class GrandTotalUtilsTests(TestCase):
    def setUp(self):
        self.hire_settings = create_hire_settings(
            default_daily_rate=Decimal('90.00'),
            default_hourly_rate=Decimal('15.00'),
            hire_pricing_strategy='24_hour_customer_friendly'
        )
        self.motorcycle = create_motorcycle(daily_hire_rate=Decimal('100.00'), hourly_hire_rate=Decimal('20.00'))
        self.package = create_package(name="Basic Pack", hourly_cost=Decimal('5.00'), daily_cost=Decimal('25.00'))
        self.addon1 = create_addon(name="GPS", hourly_cost=Decimal('1.00'), daily_cost=Decimal('5.00'))
        self.addon2 = create_addon(name="Lock", hourly_cost=Decimal('0.50'), daily_cost=Decimal('2.50'))

        self.temp_booking = create_temp_hire_booking(
            pickup_date=timezone.now().date() + datetime.timedelta(days=1),
            pickup_time=datetime.time(10,0),
            return_date=timezone.now().date() + datetime.timedelta(days=1), # Same day for initial setup
            return_time=datetime.time(13,0) # 3 hours duration
        )

    def test_calculate_booking_grand_total_motorcycle_only_same_day(self):
        self.temp_booking.motorcycle = self.motorcycle
        self.temp_booking.save()

        results = calculate_booking_grand_total(self.temp_booking, self.hire_settings)

        # Motorcycle: 3 hours * 20/hr = 60
        expected_moto_price = self.motorcycle.hourly_hire_rate * 3
        self.assertEqual(results['motorcycle_price'], expected_moto_price)
        self.assertEqual(results['package_price'], Decimal('0.00'))
        self.assertEqual(results['addons_total_price'], Decimal('0.00'))
        self.assertEqual(results['grand_total'], expected_moto_price)

    def test_calculate_booking_grand_total_motorcycle_package_same_day(self):
        self.temp_booking.motorcycle = self.motorcycle
        self.temp_booking.package = self.package
        self.temp_booking.save()

        results = calculate_booking_grand_total(self.temp_booking, self.hire_settings)

        # Motorcycle: 3 hours * 20/hr = 60
        # Package: 3 hours * 5/hr = 15
        expected_moto_price = self.motorcycle.hourly_hire_rate * 3
        expected_package_price = self.package.hourly_cost * 3
        expected_grand_total = expected_moto_price + expected_package_price

        self.assertEqual(results['motorcycle_price'], expected_moto_price)
        self.assertEqual(results['package_price'], expected_package_price)
        self.assertEqual(results['addons_total_price'], Decimal('0.00'))
        self.assertEqual(results['grand_total'], expected_grand_total)

    def test_calculate_booking_grand_total_motorcycle_addons_same_day(self):
        self.temp_booking.motorcycle = self.motorcycle
        self.temp_booking.save()
        create_temp_booking_addon(temp_booking=self.temp_booking, addon=self.addon1, quantity=1)
        create_temp_booking_addon(temp_booking=self.temp_booking, addon=self.addon2, quantity=2)

        results = calculate_booking_grand_total(self.temp_booking, self.hire_settings)

        # Motorcycle: 3 hours * 20/hr = 60
        # Addon1: 3 hours * 1/hr * 1 = 3
        # Addon2: 3 hours * 0.50/hr * 2 = 3
        expected_moto_price = self.motorcycle.hourly_hire_rate * 3
        expected_addon1_price = self.addon1.hourly_cost * 3 * 1
        expected_addon2_price = self.addon2.hourly_cost * 3 * 2
        expected_addons_total = expected_addon1_price + expected_addon2_price
        expected_grand_total = expected_moto_price + expected_addons_total

        self.assertEqual(results['motorcycle_price'], expected_moto_price)
        self.assertEqual(results['package_price'], Decimal('0.00'))
        self.assertEqual(results['addons_total_price'], expected_addons_total)
        self.assertEqual(results['grand_total'], expected_grand_total)

    def test_calculate_booking_grand_total_all_included_multi_day_flat_strategy(self):
        self.hire_settings.hire_pricing_strategy = 'flat_24_hour'
        self.hire_settings.save()

        self.temp_booking.motorcycle = self.motorcycle
        self.temp_booking.package = self.package
        
        pickup_datetime_val = datetime.datetime.combine(self.temp_booking.pickup_date, self.temp_booking.pickup_time)
        # 1 day + 3 hours -> 2 days billed by flat_24_hour
        return_datetime_val = pickup_datetime_val + datetime.timedelta(days=1, hours=3)
        self.temp_booking.return_date = return_datetime_val.date()
        self.temp_booking.return_time = return_datetime_val.time()
        self.temp_booking.save()
        create_temp_booking_addon(temp_booking=self.temp_booking, addon=self.addon1, quantity=1)

        results = calculate_booking_grand_total(self.temp_booking, self.hire_settings)

        # Motorcycle: 2 days (flat) * 100/day = 200
        # Package: 2 days (flat) * 25/day = 50
        # Addon1: 2 days (flat) * 5/day * 1 = 10
        expected_moto_price = self.motorcycle.daily_hire_rate * 2
        expected_package_price = self.package.daily_cost * 2
        expected_addon1_price = self.addon1.daily_cost * 2 * 1
        expected_grand_total = expected_moto_price + expected_package_price + expected_addon1_price

        self.assertEqual(results['motorcycle_price'], expected_moto_price)
        self.assertEqual(results['package_price'], expected_package_price)
        self.assertEqual(results['addons_total_price'], expected_addon1_price)
        self.assertEqual(results['grand_total'], expected_grand_total)

    def test_calculate_booking_grand_total_incomplete_booking(self):
        # No motorcycle, no package, no addons, no dates
        empty_temp_booking = create_temp_hire_booking(pickup_date=None, pickup_time=None, return_date=None, return_time=None)
        results = calculate_booking_grand_total(empty_temp_booking, self.hire_settings)
        self.assertEqual(results['motorcycle_price'], Decimal('0.00'))
        self.assertEqual(results['package_price'], Decimal('0.00'))
        self.assertEqual(results['addons_total_price'], Decimal('0.00'))
        self.assertEqual(results['grand_total'], Decimal('0.00'))

        # With dates but no items
        self.temp_booking.motorcycle = None
        self.temp_booking.package = None
        # ensure addons are cleared if any were attached from other tests to this shared instance
        TempBookingAddOn.objects.filter(temp_booking=self.temp_booking).delete()
        self.temp_booking.save()
        results_only_dates = calculate_booking_grand_total(self.temp_booking, self.hire_settings)
        self.assertEqual(results_only_dates['grand_total'], Decimal('0.00'))
