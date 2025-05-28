import datetime
from django.test import TestCase
from django.utils import timezone

# Import your models
from inventory.models import Motorcycle, MotorcycleCondition
from hire.models import TempHireBooking, HireBooking
from hire.models.driver_profile import DriverProfile

# Import your model factories
# Adjust this import path if your model_factories.py is located elsewhere
from hire.tests.test_helpers.model_factories import (
    create_motorcycle,
    create_driver_profile,
    create_temp_hire_booking,
    create_hire_booking,
    create_motorcycle_condition,
)

class MotorcycleAvailabilityTest(TestCase):
    """
    Tests the availability logic for motorcycles, specifically checking
    how TempHireBooking instances affect perceived availability.
    """

    def setUp(self):
        """
        Set up common test data before each test method runs.
        """
        # Ensure 'hire' condition exists and is associated with the motorcycle
        self.hire_condition = create_motorcycle_condition(name='hire', display_name='For Hire')

        # Create a test motorcycle for hire
        self.motorcycle = create_motorcycle(
            brand="TestBrand",
            model="TestModel",
            year=2023,
            engine_size=600,
            daily_hire_rate=50.00,
            hourly_hire_rate=10.00,
            is_available=True, # Ensure general availability
        )
        self.motorcycle.conditions.add(self.hire_condition)
        self.motorcycle.save() # Save after adding condition to ensure it's linked

        # Create a dummy driver profile
        self.driver_profile = create_driver_profile(
            name="Test Driver",
            email="test@example.com",
            phone_number="0412345678",
            date_of_birth=datetime.date(1990, 1, 1), # Provide a valid date of birth
        )

        # Define a future date range for testing
        self.today = timezone.localdate()
        self.pickup_date = self.today + datetime.timedelta(days=7)
        self.return_date = self.today + datetime.timedelta(days=9)
        self.pickup_time = datetime.time(9, 0)
        self.return_time = datetime.time(17, 0)

    def _get_available_motorcycles(self):
        """
        Helper method to perform the availability query, simulating the *CORRECTED* BikeChoiceView's logic.
        This method now reflects the desired behavior where TempHireBookings DO NOT block availability.
        """
        return Motorcycle.objects.filter(
            is_available=True,
            conditions__name='hire' # Only consider bikes marked for hire
        ).exclude(
            # Exclude motorcycles booked by confirmed HireBookings
            # This is the ONLY exclusion that should apply for general availability
            hire_bookings__pickup_date__lt=self.return_date,
            hire_bookings__return_date__gt=self.pickup_date
        ).distinct()

    def test_temp_booking_does_not_block_motorcycle_availability(self):
        """
        Tests that a motorcycle remains available even when a TempHireBooking is created for it.
        This test should now PASS if the application's BikeChoiceView is also corrected.
        """
        print("\n--- Running test_temp_booking_does_not_block_motorcycle_availability ---")

        # 1. Check initial availability (should be available)
        initial_available_motorcycles = self._get_available_motorcycles()
        self.assertIn(self.motorcycle, initial_available_motorcycles,
                      "Motorcycle should be available initially.")
        print(f"Initial availability: {self.motorcycle in initial_available_motorcycles}")

        # 2. Create a TempHireBooking instance
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
        print(f"Created TempHireBooking: {temp_booking}")

        # 3. Check availability AFTER creating TempHireBooking (should *still* be AVAILABLE)
        # This assertion now expects the motorcycle to be present, as TempHireBookings
        # should no longer block general availability.
        available_after_temp = self._get_available_motorcycles()
        self.assertIn(self.motorcycle, available_after_temp,
                         "Motorcycle should *still* be available even with a TempHireBooking.")
        print(f"Availability after TempHireBooking (EXPECTED TO BE TRUE): {self.motorcycle in available_after_temp}")

        # Clean up the temp booking (good practice for tests, though DB is reset)
        temp_booking.delete()
        print(f"Deleted TempHireBooking: {temp_booking.session_uuid}")

        print("--- test_temp_booking_does_not_block_motorcycle_availability complete ---")

    def test_hire_booking_blocks_motorcycle_availability(self):
        """
        Tests that a motorcycle becomes unavailable when a permanent HireBooking is created for it.
        (This is expected and desired behavior, so this test should continue to pass).
        """
        print("\n--- Running test_hire_booking_blocks_motorcycle_availability ---")

        # 1. Check initial availability (should be available)
        initial_available_motorcycles = self._get_available_motorcycles()
        self.assertIn(self.motorcycle, initial_available_motorcycles,
                      "Motorcycle should be available initially.")
        print(f"Initial availability: {self.motorcycle in initial_available_motorcycles}")

        # 2. Create a permanent HireBooking instance
        hire_booking = create_hire_booking(
            motorcycle=self.motorcycle,
            driver_profile=self.driver_profile,
            pickup_date=self.pickup_date,
            pickup_time=self.pickup_time,
            return_date=self.return_date,
            return_time=self.return_time,
            grand_total=200.00, # Dummy price
            status='confirmed' # A confirmed booking
        )
        print(f"Created HireBooking: {hire_booking}")

        # 3. Check availability AFTER creating HireBooking (should be UNAVAILABLE)
        available_after_hire = self._get_available_motorcycles()
        self.assertNotIn(self.motorcycle, available_after_hire,
                         "Motorcycle should NOT be available after HireBooking is created.")
        print(f"Availability after HireBooking: {self.motorcycle in available_after_hire}")

        # Clean up (optional, as test database is reset per test)
        hire_booking.delete()
        print(f"Deleted HireBooking: {hire_booking.booking_reference}")

        print("--- test_hire_booking_blocks_motorcycle_availability complete ---")

