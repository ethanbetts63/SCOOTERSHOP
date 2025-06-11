from django.test import TestCase, Client
from django.urls import reverse
import datetime
from unittest.mock import patch

# Import models and factories
from service.models import BlockedServiceDate, ServiceBooking
from ..test_helpers.model_factories import (
    ServiceSettingsFactory,
    BlockedServiceDateFactory,
    ServiceBookingFactory,
    ServiceProfileFactory,
    ServiceTypeFactory,
    CustomerMotorcycleFactory,
)

# Initialize Faker for consistent date/time generation if needed
from faker import Faker
fake = Faker()

class AjaxGetServiceDateAvailabilityTest(TestCase):
    """
    Tests for the ajax_get_available_service_dates endpoint.
    This tests the Django view that serves the AJAX request.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up common data for all tests in this class.
        We'll use a mocked timezone to ensure consistent test results regardless of execution time.
        """
        # Patch timezone.now() and timezone.localtime() to return a fixed date/time
        cls.fixed_now = datetime.datetime(2025, 6, 15, 10, 0, 0, tzinfo=datetime.timezone.utc)
        cls.fixed_local_date = datetime.date(2025, 6, 15) # Corresponds to a Sunday

        # Mock timezone.now and timezone.localtime
        cls.patcher_now = patch('django.utils.timezone.now', return_value=cls.fixed_now)
        cls.patcher_localtime = patch('django.utils.timezone.localtime', return_value=cls.fixed_now)

        cls.mock_now = cls.patcher_now.start()
        cls.mock_localtime = cls.patcher_localtime.start()

        # Ensure ServiceSettings exists for all tests
        cls.service_settings = ServiceSettingsFactory(
            booking_advance_notice=1, # Default advance notice
            max_visible_slots_per_day=3, # Default max slots
            booking_open_days="Mon,Tue,Wed,Thu,Fri,Sat,Sun" # All days open by default
        )

        # Create base related objects for ServiceBookingFactory
        cls.service_profile = ServiceProfileFactory()
        cls.service_type = ServiceTypeFactory()
        cls.customer_motorcycle = CustomerMotorcycleFactory(service_profile=cls.service_profile)

    @classmethod
    def tearDownClass(cls):
        """
        Clean up mocks after all tests are done.
        """
        cls.patcher_now.stop()
        cls.patcher_localtime.stop()
        super().tearDownClass()

    def setUp(self):
        """
        Set up for each test method. Clear out any previous data.
        """
        self.client = Client()
        # Reset ServiceSettings to a default state for each test if modified
        self.service_settings.booking_advance_notice = 1
        self.service_settings.max_visible_slots_per_day = 3
        self.service_settings.booking_open_days = "Mon,Tue,Wed,Thu,Fri,Sat,Sun"
        self.service_settings.save()

        # Clear any existing blocked dates and bookings
        BlockedServiceDate.objects.all().delete()
        ServiceBooking.objects.all().delete()

    def test_ajax_success_response(self):
        """
        Test that the AJAX endpoint returns a successful JSON response with correct data.
        """
        # Given fixed_local_date (Sunday, June 15, 2025) and booking_advance_notice=1
        # The expected min_date should be Monday, June 16, 2025
        expected_min_date = (self.fixed_local_date + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        
        response = self.client.get(reverse('service:admin_api_service_date_availability'))
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertIn('min_date', data)
        self.assertIn('disabled_dates', data)
        self.assertIsInstance(data['disabled_dates'], list)
        self.assertEqual(data['min_date'], expected_min_date)
        # Initially, with default settings and no blocked dates/bookings, disabled_dates should be empty
        self.assertEqual(len(data['disabled_dates']), 0) 

    def test_ajax_response_with_blocked_dates(self):
        """
        Test that explicitly blocked dates are returned in the disabled_dates.
        """
        # Block a single day
        BlockedServiceDateFactory(
            start_date=datetime.date(2025, 6, 20), # A Friday
            end_date=datetime.date(2025, 6, 20)
        )
        # Block a range of days
        BlockedServiceDateFactory(
            start_date=datetime.date(2025, 6, 25), # A Wednesday
            end_date=datetime.date(2025, 6, 27)  # A Friday
        )

        response = self.client.get(reverse('service:admin_api_service_date_availability'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        disabled_dates = data['disabled_dates']
        # Flatpickr expects {'from': 'YYYY-MM-DD', 'to': 'YYYY-MM-DD'} for ranges,
        # but for single dates it often accepts just the string 'YYYY-MM-DD'.
        # The `get_service_date_availability` function outputs single dates as strings.
        self.assertIn({'from': '2025-06-20', 'to': '2025-06-20'}, disabled_dates)
        self.assertIn({'from': '2025-06-25', 'to': '2025-06-27'}, disabled_dates)

    def test_ajax_response_with_capacity_full(self):
        """
        Test that a date is disabled when it reaches max_visible_slots_per_day.
        """
        self.service_settings.max_visible_slots_per_day = 1 # Only 1 slot per day
        self.service_settings.booking_advance_notice = 0 # Allow today to be checked
        self.service_settings.save()

        today = self.fixed_local_date # June 15, 2025 (Sunday)
        
        # Create one booking for today, filling the capacity
        ServiceBookingFactory(
            service_profile=self.service_profile,
            service_type=self.service_type,
            customer_motorcycle=self.customer_motorcycle,
            dropoff_date=today,
            service_date=today,
            dropoff_time=datetime.time(9,0,0),
            booking_status='confirmed' # FIX: Changed from 'booked' to 'confirmed'
        )

        response = self.client.get(reverse('service:admin_api_service_date_availability'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        disabled_dates = data['disabled_dates']
        self.assertIn(str(today), disabled_dates) # Today should be disabled

    def test_ajax_response_with_non_booking_open_days(self):
        """
        Test that days not specified in booking_open_days are disabled in the response.
        Fixed current date is Sunday, June 15, 2025.
        """
        # Only allow Monday and Tuesday bookings
        self.service_settings.booking_open_days = "Mon,Tue"
        self.service_settings.booking_advance_notice = 0 # Allow today to be checked
        self.service_settings.save()

        response = self.client.get(reverse('service:admin_api_service_date_availability'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        disabled_dates = data['disabled_dates']
        
        # June 15 (Sunday) should be disabled
        self.assertIn('2025-06-15', disabled_dates)
        # June 16 (Monday) should NOT be disabled
        self.assertNotIn('2025-06-16', disabled_dates)
        # June 17 (Tuesday) should NOT be disabled
        self.assertNotIn('2025-06-17', disabled_dates)
        # June 18 (Wednesday) should be disabled
        self.assertIn('2025-06-18', disabled_dates)
        
    def test_ajax_error_handling(self):
        """
        Test that the AJAX endpoint handles errors gracefully and returns a 500.
        """
        # Simulate an error in the utility function by mocking it to raise an exception
        with patch('service.ajax.ajax_get_available_service_dates.get_service_date_availability', 
                   side_effect=Exception("Simulated utility error")):
            response = self.client.get(reverse('service:admin_api_service_date_availability'))
            
            self.assertEqual(response.status_code, 500)
            data = response.json()
            self.assertIn('error', data)
            self.assertEqual(data['error'], 'Could not retrieve service date availability.')

