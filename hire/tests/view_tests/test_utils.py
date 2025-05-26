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

from hire.views.utils import (  # New
    calculate_hire_duration_days,
    get_overlapping_motorcycle_bookings
)
from hire.views.hire_pricing import (
    calculate_motorcycle_hire_price, # Updated
    calculate_package_price,         # New
    calculate_addon_price,           # New
    calculate_total_addons_price,    # New
    calculate_booking_grand_total
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













# --- Tests for get_overlapping_motorcycle_bookings --- 
class OverlapUtilsTests(TestCase):
    def setUp(self):
        self.motorcycle = create_motorcycle()
        self.driver_profile = create_driver_profile()
        self.hire_settings = create_hire_settings() 

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

# --- Tests for calculate_hire_duration_days ---
class HireDurationUtilsTests(TestCase):
    def setUp(self):
        self.motorcycle = create_motorcycle(daily_hire_rate=Decimal('100.00'), hourly_hire_rate=Decimal('20.00'))
        self.hire_settings = create_hire_settings(excess_hours_margin=3, default_daily_rate=Decimal('100.00'), default_hourly_rate=Decimal('20.00'))
        self.base_date = timezone.now().date() 

    def test_calculate_hire_duration_days_same_day_hire(self):
        pickup_date = timezone.now().date()
        pickup_time = datetime.time(9, 0)
        return_date = pickup_date
        return_time = datetime.time(17, 0) 
        for strategy in ['flat_24_hour', '24_hour_plus_margin', '24_hour_customer_friendly', 'daily_plus_excess_hourly']:
            self.hire_settings.hire_pricing_strategy = strategy
            self.hire_settings.save()
            duration = calculate_hire_duration_days(
                self.motorcycle, pickup_date, return_date, pickup_time, return_time, self.hire_settings
            )
            self.assertEqual(duration, 1, f"Failed for strategy: {strategy}")

        return_time_short = datetime.time(9, 15) 
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
        return_time_zero = pickup_time 
        self.hire_settings.hire_pricing_strategy = 'flat_24_hour'
        self.hire_settings.save()
        duration = calculate_hire_duration_days(
            self.motorcycle, pickup_date, return_date_zero, pickup_time, return_time_zero, self.hire_settings
        )
        self.assertEqual(duration, 0)

        return_date_negative = pickup_date - datetime.timedelta(days=1) 
        duration_negative = calculate_hire_duration_days(
            self.motorcycle, pickup_date, return_date_negative, pickup_time, return_time_zero, self.hire_settings
        )
        self.assertEqual(duration_negative, 0)

    def test_calculate_hire_duration_days_flat_24_hour_strategy(self):
        self.hire_settings.hire_pricing_strategy = 'flat_24_hour'
        self.hire_settings.save()
        pickup_date = timezone.now().date()
        pickup_time = datetime.time(9, 0) 
        
        def get_end_datetime_parts(start_dt, duration_delta):
            end_dt = start_dt + duration_delta
            return end_dt.date(), end_dt.time()

        start_datetime = datetime.datetime.combine(pickup_date, pickup_time)

        end_date_1, end_time_1 = get_end_datetime_parts(start_datetime, datetime.timedelta(hours=24))
        self.assertEqual(calculate_hire_duration_days(self.motorcycle, pickup_date, end_date_1, pickup_time, end_time_1, self.hire_settings), 1)
        
        end_date_2, end_time_2 = get_end_datetime_parts(start_datetime, datetime.timedelta(hours=24, minutes=1))
        self.assertEqual(calculate_hire_duration_days(self.motorcycle, pickup_date, end_date_2, pickup_time, end_time_2, self.hire_settings), 2)

        target_duration_47h59m = datetime.timedelta(hours=47, minutes=59)
        end_datetime_for_test = datetime.datetime.combine(pickup_date, pickup_time) + target_duration_47h59m
        return_date_for_test = end_datetime_for_test.date()
        return_time_for_test = end_datetime_for_test.time()
        self.assertEqual(calculate_hire_duration_days(self.motorcycle, pickup_date, return_date_for_test, pickup_time, return_time_for_test, self.hire_settings), 2)

        end_date_4, end_time_4 = get_end_datetime_parts(start_datetime, datetime.timedelta(hours=23, minutes=59))
        self.assertEqual(calculate_hire_duration_days(self.motorcycle, pickup_date, end_date_4, pickup_time, end_time_4, self.hire_settings), 1)
        
        end_date_5, end_time_5 = get_end_datetime_parts(start_datetime, datetime.timedelta(days=2, hours=6))
        self.assertEqual(calculate_hire_duration_days(self.motorcycle, pickup_date, end_date_5, pickup_time, end_time_5, self.hire_settings), 3)


    def test_calculate_hire_duration_days_24_hour_plus_margin_strategy(self):
        self.hire_settings.hire_pricing_strategy = '24_hour_plus_margin'
        self.hire_settings.excess_hours_margin = 3
        self.hire_settings.save()
        pickup_date = timezone.now().date()
        pickup_time = datetime.time(9, 0) 

        start_datetime = datetime.datetime.combine(pickup_date, pickup_time)
        def get_end_parts(duration_delta):
            end_dt = start_datetime + duration_delta
            return end_dt.date(), end_dt.time()

        rd1, rt1 = get_end_parts(datetime.timedelta(days=2))
        self.assertEqual(calculate_hire_duration_days(self.motorcycle, pickup_date, rd1, pickup_time, rt1, self.hire_settings), 2)
        
        rd2, rt2 = get_end_parts(datetime.timedelta(days=2, hours=2))
        self.assertEqual(calculate_hire_duration_days(self.motorcycle, pickup_date, rd2, pickup_time, rt2, self.hire_settings), 2)
        
        rd3, rt3 = get_end_parts(datetime.timedelta(days=2, hours=3))
        self.assertEqual(calculate_hire_duration_days(self.motorcycle, pickup_date, rd3, pickup_time, rt3, self.hire_settings), 2)
        
        rd4, rt4 = get_end_parts(datetime.timedelta(days=2, hours=4))
        self.assertEqual(calculate_hire_duration_days(self.motorcycle, pickup_date, rd4, pickup_time, rt4, self.hire_settings), 3)
        
        pickup_time_os = datetime.time(22,0)
        start_dt_os = datetime.datetime.combine(pickup_date, pickup_time_os)
        end_dt_os_10h = start_dt_os + datetime.timedelta(hours=10) 
        self.assertEqual(calculate_hire_duration_days(self.motorcycle, pickup_date, end_dt_os_10h.date(), pickup_time_os, end_dt_os_10h.time(), self.hire_settings), 1)


    def test_calculate_hire_duration_days_24_hour_customer_friendly_strategy(self):
        self.hire_settings.hire_pricing_strategy = '24_hour_customer_friendly'
        self.hire_settings.save()
        pickup_date = timezone.now().date()
        pickup_time = datetime.time(9, 0) 
        motorcycle_for_test = self.motorcycle 

        start_datetime = datetime.datetime.combine(pickup_date, pickup_time)
        def get_end_parts(duration_delta):
            end_dt = start_datetime + duration_delta
            return end_dt.date(), end_dt.time()

        rd1, rt1 = get_end_parts(datetime.timedelta(days=2))
        self.assertEqual(calculate_hire_duration_days(motorcycle_for_test, pickup_date, rd1, pickup_time, rt1, self.hire_settings), 2)

        rd2, rt2 = get_end_parts(datetime.timedelta(days=2, hours=3))
        self.assertEqual(calculate_hire_duration_days(motorcycle_for_test, pickup_date, rd2, pickup_time, rt2, self.hire_settings), 3)

        rd3, rt3 = get_end_parts(datetime.timedelta(days=2, hours=5))
        self.assertEqual(calculate_hire_duration_days(motorcycle_for_test, pickup_date, rd3, pickup_time, rt3, self.hire_settings), 3)

        rd4, rt4 = get_end_parts(datetime.timedelta(days=2, hours=6))
        self.assertEqual(calculate_hire_duration_days(motorcycle_for_test, pickup_date, rd4, pickup_time, rt4, self.hire_settings), 3)

        return_date_same_day = pickup_date
        return_time_5_hours = datetime.time(14, 0) 
        self.assertEqual(calculate_hire_duration_days(motorcycle_for_test, pickup_date, return_date_same_day, pickup_time, return_time_5_hours, self.hire_settings), 1)

        pickup_time_overnight = datetime.time(22,0)
        start_dt_overnight = datetime.datetime.combine(pickup_date, pickup_time_overnight)
        end_dt_overnight = start_dt_overnight + datetime.timedelta(hours=10) 
        self.assertEqual(calculate_hire_duration_days(motorcycle_for_test, pickup_date, end_dt_overnight.date(), pickup_time_overnight, end_dt_overnight.time(), self.hire_settings), 1)


    def test_calculate_hire_duration_days_daily_plus_excess_hourly_strategy(self):
        self.hire_settings.hire_pricing_strategy = 'daily_plus_excess_hourly'
        self.hire_settings.save()
        pickup_date = timezone.now().date()
        pickup_time = datetime.time(9, 0) 

        start_datetime = datetime.datetime.combine(pickup_date, pickup_time)
        def get_end_parts(duration_delta):
            end_dt = start_datetime + duration_delta
            return end_dt.date(), end_dt.time()

        rd1, rt1 = get_end_parts(datetime.timedelta(days=2))
        self.assertEqual(calculate_hire_duration_days(self.motorcycle, pickup_date, rd1, pickup_time, rt1, self.hire_settings), 2)

        rd2, rt2 = get_end_parts(datetime.timedelta(days=2, hours=5, minutes=30))
        self.assertEqual(calculate_hire_duration_days(self.motorcycle, pickup_date, rd2, pickup_time, rt2, self.hire_settings), 3)

        pickup_time_span = datetime.time(22, 0)
        start_dt_span = datetime.datetime.combine(pickup_date, pickup_time_span)
        end_dt_span = start_dt_span + datetime.timedelta(hours=4) 
        self.assertEqual(calculate_hire_duration_days(self.motorcycle, pickup_date, end_dt_span.date(), pickup_time_span, end_dt_span.time(), self.hire_settings), 1)

        rd4, rt4 = get_end_parts(datetime.timedelta(hours=23)) 
        self.assertEqual(calculate_hire_duration_days(self.motorcycle, pickup_date, rd4, pickup_time, rt4, self.hire_settings), 1)
