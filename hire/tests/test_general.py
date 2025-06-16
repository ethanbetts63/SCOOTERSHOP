import datetime
from django.test import TestCase
from django.utils import timezone

from inventory.models import Motorcycle, MotorcycleCondition
from hire.models import TempHireBooking, HireBooking
from hire.models.driver_profile import DriverProfile

from hire.tests.test_helpers.model_factories import (
    create_motorcycle,
    create_driver_profile,
    create_temp_hire_booking,
    create_hire_booking,
    create_motorcycle_condition,
)

class MotorcycleAvailabilityTest(TestCase):

    def setUp(self):
        self.hire_condition = create_motorcycle_condition(name='hire', display_name='For Hire')

        self.motorcycle = create_motorcycle(
            brand="TestBrand",
            model="TestModel",
            year=2023,
            engine_size=600,
            daily_hire_rate=50.00,
            hourly_hire_rate=10.00,
            is_available=True,
        )
        self.motorcycle.conditions.add(self.hire_condition)
        self.motorcycle.save()

        self.driver_profile = create_driver_profile(
            name="Test Driver",
            email="test@example.com",
            phone_number="0412345678",
            date_of_birth=datetime.date(1990, 1, 1),
        )

        self.today = timezone.localdate()
        self.pickup_date = self.today + datetime.timedelta(days=7)
        self.return_date = self.today + datetime.timedelta(days=9)
        self.pickup_time = datetime.time(9, 0)
        self.return_time = datetime.time(17, 0)

    def _get_available_motorcycles(self):
        return Motorcycle.objects.filter(
            is_available=True,
            conditions__name='hire'
        ).exclude(
            hire_bookings__pickup_date__lt=self.return_date,
            hire_bookings__return_date__gt=self.pickup_date
        ).distinct()

    def test_temp_booking_does_not_block_motorcycle_availability(self):
        initial_available_motorcycles = self._get_available_motorcycles()
        self.assertIn(self.motorcycle, initial_available_motorcycles,
                      "Motorcycle should be available initially.")

        temp_booking = create_temp_hire_booking(
            motorcycle=self.motorcycle,
            pickup_date=self.pickup_date,
            pickup_time=self.pickup_time,
            return_date=self.return_date,
            return_time=self.return_time,
            has_motorcycle_license=True,
            driver_profile=self.driver_profile,
            total_hire_price=100.00,
            grand_total=100.00,
        )

        available_after_temp = self._get_available_motorcycles()
        self.assertIn(self.motorcycle, available_after_temp,
                      "Motorcycle should *still* be available even with a TempHireBooking.")

        temp_booking.delete()

    def test_hire_booking_blocks_motorcycle_availability(self):
        initial_available_motorcycles = self._get_available_motorcycles()
        self.assertIn(self.motorcycle, initial_available_motorcycles,
                      "Motorcycle should be available initially.")

        hire_booking = create_hire_booking(
            motorcycle=self.motorcycle,
            driver_profile=self.driver_profile,
            pickup_date=self.pickup_date,
            pickup_time=self.pickup_time,
            return_date=self.return_date,
            return_time=self.return_time,
            grand_total=200.00,
            status='confirmed'
        )

        available_after_hire = self._get_available_motorcycles()
        self.assertNotIn(self.motorcycle, available_after_hire,
                         "Motorcycle should NOT be available after HireBooking is created.")

        hire_booking.delete()
