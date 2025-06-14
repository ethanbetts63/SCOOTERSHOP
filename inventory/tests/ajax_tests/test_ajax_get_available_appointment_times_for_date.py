import datetime
from django.test import TestCase, Client
from django.urls import reverse
from inventory.models import InventorySettings
from ..test_helpers.model_factories import InventorySettingsFactory, SalesBookingFactory, MotorcycleFactory, SalesProfileFactory

class GetAvailableAppointmentTimesForDateAjaxTest(TestCase):
    """
    Tests for the AJAX endpoint `get_available_appointment_times_for_date`.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up common data for all tests in this class.
        """
        cls.client = Client()

        # Create a single InventorySettings instance with specific times for testing
        cls.inventory_settings = InventorySettingsFactory(
            sales_appointment_start_time=datetime.time(9, 0), # 9:00 AM
            sales_appointment_end_time=datetime.time(17, 0),   # 5:00 PM
            sales_appointment_spacing_mins=30, # 30-minute slots
            min_advance_booking_hours=0, # Set to 0 for easier testing of today's dates initially
        )

        # Create a motorcycle and sales profile for booking factories
        cls.motorcycle = MotorcycleFactory()
        cls.sales_profile = SalesProfileFactory()

        cls.ajax_url = reverse('inventory:ajax_get_appointment_times')

    def test_missing_date_parameter(self):
        """
        Test that a 400 response is returned if 'selected_date' parameter is missing.
        """
        response = self.client.get(self.ajax_url)
        self.assertEqual(response.status_code, 400)
        self.assertJSONEqual(response.content, {'error': 'Date parameter (selected_date) is missing.'})

    def test_invalid_date_format(self):
        """
        Test that a 400 response is returned for an invalid date format.
        """
        response = self.client.get(f"{self.ajax_url}?selected_date=2025/06/24")
        self.assertEqual(response.status_code, 400)
        # Corrected: Reverted 'APAC' back to 'YYYY'
        self.assertJSONEqual(response.content, {'error': 'Invalid date format. Use YYYY-MM-DD.'})

    def test_no_inventory_settings(self):
        """
        Test that a 500 response is returned if InventorySettings do not exist.
        """
        # Delete the existing settings to simulate no settings
        InventorySettings.objects.all().delete()
        response = self.client.get(f"{self.ajax_url}?selected_date=2025-06-24")
        self.assertEqual(response.status_code, 500)
        self.assertJSONEqual(response.content, {'error': 'Inventory settings not found.'})
        # Recreate settings for subsequent tests
        self.inventory_settings = InventorySettingsFactory(
            sales_appointment_start_time=datetime.time(9, 0),
            sales_appointment_end_time=datetime.time(17, 0),
            sales_appointment_spacing_mins=30,
            min_advance_booking_hours=0,
        )


    def test_get_available_times_no_bookings(self):
        """
        Test fetching available times for a date with no existing bookings.
        Should return all possible slots within the defined range.
        """
        test_date = datetime.date.today() + datetime.timedelta(days=1) # Tomorrow's date
        response = self.client.get(f"{self.ajax_url}?selected_date={test_date.strftime('%Y-%m-%d')}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('available_times', data)

        expected_times = []
        current_time = datetime.datetime.combine(test_date, self.inventory_settings.sales_appointment_start_time)
        end_time_limit = datetime.datetime.combine(test_date, self.inventory_settings.sales_appointment_end_time)

        while current_time <= end_time_limit:
            expected_times.append({
                "value": current_time.strftime('%H:%M'),
                "display": current_time.strftime('%I:%M %p')
            })
            current_time += datetime.timedelta(minutes=self.inventory_settings.sales_appointment_spacing_mins)
        
        self.assertEqual(len(data['available_times']), len(expected_times))
        self.assertEqual(data['available_times'], expected_times)

    def test_get_available_times_with_existing_bookings(self):
        """
        Test fetching available times for a date with some existing confirmed bookings.
        Booked slots and their immediate surrounding slots (due to spacing) should be excluded.
        """
        test_date = datetime.date.today() + datetime.timedelta(days=2) # Day after tomorrow

        # Book an appointment at 10:00 AM
        SalesBookingFactory(
            motorcycle=self.motorcycle,
            sales_profile=self.sales_profile,
            appointment_date=test_date,
            appointment_time=datetime.time(10, 0), # Booked slot
            booking_status='confirmed'
        )

        # Book another appointment at 14:30 PM
        SalesBookingFactory(
            motorcycle=self.motorcycle,
            sales_profile=self.sales_profile,
            appointment_date=test_date,
            appointment_time=datetime.time(14, 30), # Booked slot
            booking_status='reserved'
        )

        response = self.client.get(f"{self.ajax_url}?selected_date={test_date.strftime('%Y-%m-%d')}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('available_times', data)

        # Generate all potential slots first
        all_potential_slots = []
        current_time_obj = self.inventory_settings.sales_appointment_start_time
        end_time_obj = self.inventory_settings.sales_appointment_end_time
        while current_time_obj <= end_time_obj:
            all_potential_slots.append(current_time_obj)
            dt_current_slot = datetime.datetime.combine(test_date, current_time_obj)
            dt_current_slot += datetime.timedelta(minutes=self.inventory_settings.sales_appointment_spacing_mins)
            current_time_obj = dt_current_slot.time()

        # Define expected blocked times based on sales_appointment_spacing_mins
        # For a 30-min spacing:
        # If 10:00 is booked, 09:30, 10:00, 10:30 are affected.
        # If 14:30 is booked, 14:00, 14:30, 15:00 are affected.
        blocked_raw_times = [
            datetime.time(9, 30), datetime.time(10, 0), datetime.time(10, 30),
            datetime.time(14, 0), datetime.time(14, 30), datetime.time(15, 0),
        ]
        
        expected_available_times = []
        for slot_time_obj in all_potential_slots:
            if slot_time_obj not in blocked_raw_times:
                expected_available_times.append({
                    "value": slot_time_obj.strftime('%H:%M'),
                    "display": slot_time_obj.strftime('%I:%M %p')
                })

        # Convert `data['available_times']` to a comparable format if necessary
        # The frontend format now includes 'display', so we compare the full dicts
        self.assertEqual(len(data['available_times']), len(expected_available_times))
        self.assertEqual(data['available_times'], expected_available_times)

    def test_get_available_times_min_advance_booking_hours(self):
        """
        Test that times too soon based on min_advance_booking_hours are excluded.
        """
        # This test case is already well-defined and tests the functionality.
        # We will keep it as is, setting min_advance_booking_hours within the test.

        # Set min_advance_booking_hours to a value that would exclude today's times
        self.inventory_settings.min_advance_booking_hours = 48 # Require 48 hours notice
        self.inventory_settings.save()

        # Try to get times for today
        today = datetime.date.today()
        response = self.client.get(f"{self.ajax_url}?selected_date={today.strftime('%Y-%m-%d')}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['available_times'], []) # Expect no times today

        # Try to get times for a date far enough in the future
        future_date = today + datetime.timedelta(days=3) # 72 hours from now
        response = self.client.get(f"{self.ajax_url}?selected_date={future_date.strftime('%Y-%m-%d')}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreater(len(data['available_times']), 0) # Expect times to be available

        # Reset settings
        self.inventory_settings.min_advance_booking_hours = 0
        self.inventory_settings.save()
