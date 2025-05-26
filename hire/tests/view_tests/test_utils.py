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

