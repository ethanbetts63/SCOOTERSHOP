# hire/tests/view_tests/test_hire_pricing.py

import datetime
from decimal import Decimal, ROUND_HALF_UP # Added ROUND_HALF_UP import
from django.test import TestCase
from django.utils import timezone

from hire.hire_pricing import (
    calculate_motorcycle_hire_price, # Updated
    calculate_package_price,         # New
    calculate_addon_price,           # New
    calculate_total_addons_price,    # New
    calculate_booking_grand_total
  )

from hire.utils import (
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

    def test_calculate_motorcycle_hire_price_overnight_less_than_24_hours_uses_daily_rate(self):
        pickup_date = timezone.now().date() + datetime.timedelta(days=1) # Day T+1
        pickup_time = datetime.time(22, 0) # 10 PM
        return_date = pickup_date + datetime.timedelta(days=1) # Day T+2
        return_time = datetime.time(8, 0) # 8 AM (10 hours duration)

        # This new rule should apply regardless of the detailed strategy for >24h hires
        for strategy in ['flat_24_hour', '24_hour_plus_margin', '24_hour_customer_friendly', 'daily_plus_excess_hourly', 'daily_plus_proportional_excess', '24_hour_plus_margin_proportional']:
            self.hire_settings.hire_pricing_strategy = strategy
            self.hire_settings.save()

            # Test with motorcycle having specific rates
            expected_price_moto = self.motorcycle_with_rates.daily_hire_rate
            calculated_price_moto = calculate_motorcycle_hire_price(
                self.motorcycle_with_rates, pickup_date, return_date, pickup_time, return_time, self.hire_settings
            )
            self.assertEqual(calculated_price_moto, expected_price_moto, f"Failed for motorcycle with rates, strategy: {strategy}")

            # Test with motorcycle using default rates from hire_settings
            # Ensure motorcycle_no_rates uses the default daily rate from hire_settings
            expected_price_default = self.hire_settings.default_daily_rate
            calculated_price_default = calculate_motorcycle_hire_price(
                self.motorcycle_no_rates, pickup_date, return_date, pickup_time, return_time, self.hire_settings
            )
            self.assertEqual(calculated_price_default, expected_price_default, f"Failed for motorcycle no rates, strategy: {strategy}")

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

        # Test 1: 23h 59min (should be 1 day) - This is now handled by the new overnight rule if dates differ.
        # If it's T+1 09:00 to T+2 08:59 (pickup_date != return_date, duration < 24h)
        # it should be daily_rate * 1 due to the new rule.
        pickup_datetime_val_short = datetime.datetime.combine(pickup_date, pickup_time)
        duration_23h59m = datetime.timedelta(hours=23, minutes=59)
        return_datetime_val_short = pickup_datetime_val_short + duration_23h59m
        actual_return_date_short = return_datetime_val_short.date() # This will be pickup_date + 1 day
        actual_return_time_short = return_datetime_val_short.time()

        # Check if dates are different
        self.assertNotEqual(pickup_date, actual_return_date_short, "Test setup error: dates should be different for overnight rule.")

        calculated_price_short = calculate_motorcycle_hire_price(
             self.motorcycle_with_rates, pickup_date, actual_return_date_short, pickup_time, actual_return_time_short, self.hire_settings
        )
        # New rule: overnight < 24h is daily_rate
        self.assertEqual(calculated_price_short, self.motorcycle_with_rates.daily_hire_rate * 1)


        # Test 2: 1 day 23h 59m (47h 59m total) (should be 2 days by flat_24_hour)
        # e.g., T+1 09:00 to T+3 08:59. This is > 24h, so new rule doesn't apply.
        duration_47h59m = datetime.timedelta(hours=47, minutes=59) # total_duration_hours = 47.98...
        return_datetime_val_long = pickup_datetime_val_short + duration_47h59m # Base is T+1 09:00
        actual_return_date_long = return_datetime_val_long.date()
        actual_return_time_long = return_datetime_val_long.time()

        expected_price_long = self.motorcycle_with_rates.daily_hire_rate * 2 # ceil(47.98 / 24) = 2
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

    def test_calculate_motorcycle_hire_price_daily_plus_proportional_excess(self):
        self.hire_settings.hire_pricing_strategy = 'daily_plus_proportional_excess'
        self.hire_settings.save()
        pickup_date = timezone.now().date() + datetime.timedelta(days=1)
        pickup_time = datetime.time(9, 0)

        # Case 1: 2 days + 6 hours (54 hours total)
        # 2 full days + (6/24) * daily_rate
        return_datetime_val_1 = datetime.datetime.combine(pickup_date, pickup_time) + datetime.timedelta(days=2, hours=6)
        return_date_1 = return_datetime_val_1.date()
        return_time_1 = return_datetime_val_1.time()
        
        expected_price_1 = (self.motorcycle_with_rates.daily_hire_rate * 2) + \
                           (Decimal('6') / Decimal('24')) * self.motorcycle_with_rates.daily_hire_rate
        expected_price_1 = expected_price_1.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        calculated_price_1 = calculate_motorcycle_hire_price(
            self.motorcycle_with_rates, pickup_date, return_date_1, pickup_time, return_time_1, self.hire_settings
        )
        self.assertEqual(calculated_price_1, expected_price_1)

        # Case 2: 1 day + 12 hours (36 hours total)
        # 1 full day + (12/24) * daily_rate
        return_datetime_val_2 = datetime.datetime.combine(pickup_date, pickup_time) + datetime.timedelta(days=1, hours=12)
        return_date_2 = return_datetime_val_2.date()
        return_time_2 = return_datetime_val_2.time()

        expected_price_2 = (self.motorcycle_with_rates.daily_hire_rate * 1) + \
                           (Decimal('12') / Decimal('24')) * self.motorcycle_with_rates.daily_hire_rate
        expected_price_2 = expected_price_2.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        calculated_price_2 = calculate_motorcycle_hire_price(
            self.motorcycle_with_rates, pickup_date, return_date_2, pickup_time, return_time_2, self.hire_settings
        )
        self.assertEqual(calculated_price_2, expected_price_2)

        # Case 3: Exact days (no excess)
        return_datetime_val_3 = datetime.datetime.combine(pickup_date, pickup_time) + datetime.timedelta(days=2)
        return_date_3 = return_datetime_val_3.date()
        return_time_3 = return_datetime_val_3.time()

        expected_price_3 = self.motorcycle_with_rates.daily_hire_rate * 2
        calculated_price_3 = calculate_motorcycle_hire_price(
            self.motorcycle_with_rates, pickup_date, return_date_3, pickup_time, return_time_3, self.hire_settings
        )
        self.assertEqual(calculated_price_3, expected_price_3)

    def test_calculate_motorcycle_hire_price_24_hour_plus_margin_proportional(self):
        self.hire_settings.hire_pricing_strategy = '24_hour_plus_margin_proportional'
        self.hire_settings.excess_hours_margin = 3 # Margin of 3 hours
        self.hire_settings.save()
        pickup_date = timezone.now().date() + datetime.timedelta(days=1)
        pickup_time = datetime.time(9, 0)

        # Case 1: Excess within margin (2 days + 2 hours). Should be 2 full days.
        return_datetime_val_1 = datetime.datetime.combine(pickup_date, pickup_time) + datetime.timedelta(days=2, hours=2)
        return_date_1 = return_datetime_val_1.date()
        return_time_1 = return_datetime_val_1.time()

        expected_price_1 = self.motorcycle_with_rates.daily_hire_rate * 2
        calculated_price_1 = calculate_motorcycle_hire_price(
            self.motorcycle_with_rates, pickup_date, return_date_1, pickup_time, return_time_1, self.hire_settings
        )
        self.assertEqual(calculated_price_1, expected_price_1)

        # Case 2: Excess exceeds margin (2 days + 4 hours). 1 hour beyond margin.
        # Should be 2 full days + (1/24) * daily_rate
        return_datetime_val_2 = datetime.datetime.combine(pickup_date, pickup_time) + datetime.timedelta(days=2, hours=4)
        return_date_2 = return_datetime_val_2.date()
        return_time_2 = return_datetime_val_2.time()

        expected_price_2 = (self.motorcycle_with_rates.daily_hire_rate * 2) + \
                           ((Decimal('4') - self.hire_settings.excess_hours_margin) / Decimal('24')) * self.motorcycle_with_rates.daily_hire_rate
        expected_price_2 = expected_price_2.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        calculated_price_2 = calculate_motorcycle_hire_price(
            self.motorcycle_with_rates, pickup_date, return_date_2, pickup_time, return_time_2, self.hire_settings
        )
        self.assertEqual(calculated_price_2, expected_price_2)

        # Case 3: Exact days (no excess). Should be 2 full days.
        return_datetime_val_3 = datetime.datetime.combine(pickup_date, pickup_time) + datetime.timedelta(days=2)
        return_date_3 = return_datetime_val_3.date()
        return_time_3 = return_datetime_val_3.time()

        expected_price_3 = self.motorcycle_with_rates.daily_hire_rate * 2
        calculated_price_3 = calculate_motorcycle_hire_price(
            self.motorcycle_with_rates, pickup_date, return_date_3, pickup_time, return_time_3, self.hire_settings
        )
        self.assertEqual(calculated_price_3, expected_price_3)

        # Case 4: Larger excess beyond margin (2 days + 10 hours). 7 hours beyond margin.
        # Should be 2 full days + (7/24) * daily_rate
        return_datetime_val_4 = datetime.datetime.combine(pickup_date, pickup_time) + datetime.timedelta(days=2, hours=10)
        return_date_4 = return_datetime_val_4.date()
        return_time_4 = return_datetime_val_4.time()

        expected_price_4 = (self.motorcycle_with_rates.daily_hire_rate * 2) + \
                           ((Decimal('10') - self.hire_settings.excess_hours_margin) / Decimal('24')) * self.motorcycle_with_rates.daily_hire_rate
        expected_price_4 = expected_price_4.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        calculated_price_4 = calculate_motorcycle_hire_price(
            self.motorcycle_with_rates, pickup_date, return_date_4, pickup_time, return_time_4, self.hire_settings
        )
        self.assertEqual(calculated_price_4, expected_price_4)


# --- NEW Test Suites for Packages, Addons, Grand Total ---

class PackagePricingUtilsTests(TestCase):
    def setUp(self):
        self.hire_settings = create_hire_settings(hire_pricing_strategy='24_hour_customer_friendly', excess_hours_margin=2, default_daily_rate=Decimal('50.00'), default_hourly_rate=Decimal('10.00')) # Added defaults for robustness
        self.package_adventure = create_package(
            name="Adventure Pack",
            hourly_cost=Decimal('10.00'),
            daily_cost=Decimal('50.00')
        )
        self.package_no_rates = create_package( # For testing fallback or missing rates
            name="Basic Pack No Rates",
            hourly_cost=None,
            daily_cost=None
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

    def test_calculate_package_price_overnight_less_than_24_hours_uses_daily_rate(self):
        pickup_date_overnight = self.pickup_date 
        pickup_time_overnight = datetime.time(22, 0) # 10 PM
        return_date_overnight = pickup_date_overnight + datetime.timedelta(days=1) 
        return_time_overnight = datetime.time(8, 0) # 8 AM (10 hours duration)

        for strategy in ['flat_24_hour', '24_hour_plus_margin', '24_hour_customer_friendly', 'daily_plus_excess_hourly', 'daily_plus_proportional_excess', '24_hour_plus_margin_proportional']:
            self.hire_settings.hire_pricing_strategy = strategy
            self.hire_settings.save()

            expected_price = self.package_adventure.daily_cost
            calculated_price = calculate_package_price(
                self.package_adventure, pickup_date_overnight, return_date_overnight, pickup_time_overnight, return_time_overnight, self.hire_settings
            )
            self.assertEqual(calculated_price, expected_price, f"Failed for package with rates, strategy: {strategy}")
            
            # Test with a package that has no direct rates, should use defaults from hire_settings if applicable
            # However, calculate_package_price uses package's own rates directly. If None, it returns 0.
            # Let's ensure our hire_settings has defaults that could be used if logic changed, but for now, it's direct.
            # If package_no_rates.daily_cost is None, the initial check in calculate_package_price
            # `if daily_rate is None or hourly_rate is None: return Decimal('0.00')` will trigger.
            calculated_price_no_rates = calculate_package_price(
                 self.package_no_rates, pickup_date_overnight, return_date_overnight, pickup_time_overnight, return_time_overnight, self.hire_settings
            )
            self.assertEqual(calculated_price_no_rates, Decimal('0.00'), f"Failed for package with no rates (should be 0), strategy: {strategy}")


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
        self.hire_settings = create_hire_settings(hire_pricing_strategy='24_hour_customer_friendly', excess_hours_margin=2, default_daily_rate=Decimal('10.00'), default_hourly_rate=Decimal('2.00'))
        self.addon_helmet = create_addon(name="Helmet", hourly_cost=Decimal('2.00'), daily_cost=Decimal('10.00'))
        self.addon_jacket = create_addon(name="Jacket", hourly_cost=Decimal('3.00'), daily_cost=Decimal('15.00'))
        self.addon_no_rates = create_addon(name="Gloves", hourly_cost=None, daily_cost=None)


        self.pickup_date = timezone.now().date() + datetime.timedelta(days=1)
        self.pickup_time = datetime.time(9, 0)

        self.temp_booking = create_temp_hire_booking(
            pickup_date=self.pickup_date,
            pickup_time=self.pickup_time,
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

    def test_calculate_addon_price_overnight_less_than_24_hours_uses_daily_rate(self):
        pickup_date_overnight = self.pickup_date
        pickup_time_overnight = datetime.time(22, 0)  # 10 PM
        return_date_overnight = pickup_date_overnight + datetime.timedelta(days=1)
        return_time_overnight = datetime.time(8, 0)  # 8 AM (10 hours duration)
        quantity = 2

        for strategy in ['flat_24_hour', '24_hour_plus_margin', '24_hour_customer_friendly', 'daily_plus_excess_hourly', 'daily_plus_proportional_excess', '24_hour_plus_margin_proportional']:
            self.hire_settings.hire_pricing_strategy = strategy
            self.hire_settings.save()

            expected_price_single_unit = self.addon_helmet.daily_cost
            expected_total_price = expected_price_single_unit * quantity
            calculated_price = calculate_addon_price(
                self.addon_helmet, quantity, pickup_date_overnight, return_date_overnight, pickup_time_overnight, return_time_overnight, self.hire_settings
            )
            self.assertEqual(calculated_price, expected_total_price, f"Failed for addon with rates, strategy: {strategy}")

            calculated_price_no_rates = calculate_addon_price(
                self.addon_no_rates, quantity, pickup_date_overnight, return_date_overnight, pickup_time_overnight, return_time_overnight, self.hire_settings
            )
            self.assertEqual(calculated_price_no_rates, Decimal('0.00'), f"Failed for addon with no rates (should be 0), strategy: {strategy}")


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
        self.temp_booking.return_date = self.pickup_date + datetime.timedelta(days=1) 
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

        expected_price_helmet = self.addon_helmet.hourly_cost * 3 
        expected_price_jacket = (self.addon_jacket.hourly_cost * 3) * 2
        expected_total = expected_price_helmet + expected_price_jacket

        calculated_total = calculate_total_addons_price(self.temp_booking, self.hire_settings)
        self.assertEqual(calculated_total, expected_total)

    def test_calculate_total_addons_price_with_addons_multi_day_flat_strategy(self):
        self.hire_settings.hire_pricing_strategy = 'flat_24_hour'
        self.hire_settings.save()

        pickup_datetime_val = datetime.datetime.combine(self.pickup_date, self.pickup_time)
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
            return_date=timezone.now().date() + datetime.timedelta(days=1), 
            return_time=datetime.time(13,0) 
        )

    def test_calculate_booking_grand_total_motorcycle_only_same_day(self):
        self.temp_booking.motorcycle = self.motorcycle
        self.temp_booking.save()

        results = calculate_booking_grand_total(self.temp_booking, self.hire_settings)

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
        return_datetime_val = pickup_datetime_val + datetime.timedelta(days=1, hours=3)
        self.temp_booking.return_date = return_datetime_val.date()
        self.temp_booking.return_time = return_datetime_val.time()
        self.temp_booking.save()
        create_temp_booking_addon(temp_booking=self.temp_booking, addon=self.addon1, quantity=1)

        results = calculate_booking_grand_total(self.temp_booking, self.hire_settings)

        expected_moto_price = self.motorcycle.daily_hire_rate * 2
        expected_package_price = self.package.daily_cost * 2
        expected_addon1_price = self.addon1.daily_cost * 2 * 1
        expected_grand_total = expected_moto_price + expected_package_price + expected_addon1_price

        self.assertEqual(results['motorcycle_price'], expected_moto_price)
        self.assertEqual(results['package_price'], expected_package_price)
        self.assertEqual(results['addons_total_price'], expected_addon1_price)
        self.assertEqual(results['grand_total'], expected_grand_total)
        
    def test_calculate_booking_grand_total_overnight_less_than_24h_all_items(self):
        # Set temp_booking for overnight < 24h
        self.temp_booking.pickup_time = datetime.time(22,0) # 10 PM
        self.temp_booking.return_date = self.temp_booking.pickup_date + datetime.timedelta(days=1)
        self.temp_booking.return_time = datetime.time(8,0) # 8 AM (10 hours duration)
        
        self.temp_booking.motorcycle = self.motorcycle
        self.temp_booking.package = self.package
        self.temp_booking.save()
        create_temp_booking_addon(temp_booking=self.temp_booking, addon=self.addon1, quantity=1)
        create_temp_booking_addon(temp_booking=self.temp_booking, addon=self.addon2, quantity=2)

        # The new rule should apply daily_rate for each item, regardless of hire_settings.hire_pricing_strategy
        for strategy in ['flat_24_hour', '24_hour_plus_margin', '24_hour_customer_friendly', 'daily_plus_excess_hourly', 'daily_plus_proportional_excess', '24_hour_plus_margin_proportional']:
            self.hire_settings.hire_pricing_strategy = strategy
            self.hire_settings.save()

            results = calculate_booking_grand_total(self.temp_booking, self.hire_settings)

            expected_moto_price = self.motorcycle.daily_hire_rate
            expected_package_price = self.package.daily_cost
            expected_addon1_price = self.addon1.daily_cost * 1
            expected_addon2_price = self.addon2.daily_cost * 2
            expected_addons_total = expected_addon1_price + expected_addon2_price
            expected_grand_total = expected_moto_price + expected_package_price + expected_addons_total

            self.assertEqual(results['motorcycle_price'], expected_moto_price, f"Moto price failed for strategy {strategy}")
            self.assertEqual(results['package_price'], expected_package_price, f"Package price failed for strategy {strategy}")
            self.assertEqual(results['addons_total_price'], expected_addons_total, f"Addons total price failed for strategy {strategy}")
            self.assertEqual(results['grand_total'], expected_grand_total, f"Grand total failed for strategy {strategy}")


    def test_calculate_booking_grand_total_incomplete_booking(self):
        empty_temp_booking = create_temp_hire_booking(pickup_date=None, pickup_time=None, return_date=None, return_time=None)
        results = calculate_booking_grand_total(empty_temp_booking, self.hire_settings)
        self.assertEqual(results['motorcycle_price'], Decimal('0.00'))
        self.assertEqual(results['package_price'], Decimal('0.00'))
        self.assertEqual(results['addons_total_price'], Decimal('0.00'))
        self.assertEqual(results['grand_total'], Decimal('0.00'))

        self.temp_booking.motorcycle = None
        self.temp_booking.package = None
        TempBookingAddOn.objects.filter(temp_booking=self.temp_booking).delete()
        self.temp_booking.save() # Save changes to self.temp_booking (which has dates from its setUp)
        results_only_dates = calculate_booking_grand_total(self.temp_booking, self.hire_settings)
        self.assertEqual(results_only_dates['grand_total'], Decimal('0.00'))
