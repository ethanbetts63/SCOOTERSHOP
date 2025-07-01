from django.test import TestCase
from django.utils import timezone
import datetime
from unittest.mock import patch

                                  
from service.utils.get_drop_off_date_availability import get_drop_off_date_availability

                             
from service.models import ServiceSettings, BlockedServiceDate
from ..test_helpers.model_factories import (
    ServiceSettingsFactory,
    TempServiceBookingFactory,
    BlockedServiceDateFactory,
)

class GetDropOffDateAvailabilityTest(TestCase):
    """
    Tests for the get_drop_off_date_availability function.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up common data for all tests in this class.
        Patch timezone.now() and timezone.localdate() for consistent date tests.
        """
                                                                                  
        cls.fixed_now_utc = datetime.datetime(2025, 6, 15, 10, 0, 0, tzinfo=datetime.timezone.utc)
                                                                        
                                                    
        cls.fixed_local_date = datetime.date(2025, 6, 15)                        

                                                                         
        cls.patcher_now = patch('django.utils.timezone.now', return_value=cls.fixed_now_utc)
                                                                          
        cls.patcher_localdate = patch('django.utils.timezone.localdate', return_value=cls.fixed_local_date)
        
        cls.mock_now = cls.patcher_now.start()
        cls.mock_localdate = cls.patcher_localdate.start()

                                                                 
        timezone.activate('Europe/Copenhagen')

    @classmethod
    def tearDownClass(cls):
        """
        Clean up mocks after all tests are done.
        """
        cls.patcher_now.stop()
        cls.patcher_localdate.stop()
        timezone.deactivate()
        super().tearDownClass()

    def setUp(self):
        """
        Set up for each test method. Ensure a clean state and default settings.
        """
        ServiceSettings.objects.all().delete()
        BlockedServiceDate.objects.all().delete()

                                                        
        self.service_settings = ServiceSettingsFactory(
            max_advance_dropoff_days=7,
            allow_after_hours_dropoff=False,
            booking_open_days="Mon,Tue,Wed,Thu,Fri,Sat,Sun"                                              
        )
                                                   
        self.temp_booking = TempServiceBookingFactory(
            service_date=self.fixed_local_date + datetime.timedelta(days=3)                                 
        )

    def test_basic_availability_all_days_open(self):
        """
        Test basic date generation when all days are open and no blocks exist.
        today: Sunday, Jun 15, 2025
        service_date: Wednesday, Jun 18, 2025
        max_advance_dropoff_days: 7
        min_dropoff_date = service_date - 7 days = Jun 11
        However, min_dropoff_date cannot be before today (Jun 15), so it becomes Jun 15.
        max_dropoff_date = service_date = Jun 18
        Expected: Jun 15, Jun 16, Jun 17, Jun 18
        """
                                                               
        self.service_settings.max_advance_dropoff_days = 7
        self.service_settings.booking_open_days = "Mon,Tue,Wed,Thu,Fri,Sat,Sun"
        self.service_settings.allow_after_hours_dropoff = False
        self.service_settings.save()

                                                 
        self.temp_booking.service_date = self.fixed_local_date + datetime.timedelta(days=3)                
        self.temp_booking.save()

        expected_dates = [
            '2025-06-15',                 
            '2025-06-16',         
            '2025-06-17',          
            '2025-06-18'                            
        ]
        available_dates = get_drop_off_date_availability(self.temp_booking, self.service_settings)
        self.assertEqual(available_dates, expected_dates)

    def test_max_advance_dropoff_days_restriction(self):
        """
        Test that drop-off dates are restricted by max_advance_dropoff_days.
        service_date: June 20 (Fri)
        max_advance_dropoff_days: 3
        min_dropoff_date = June 20 - 3 days = June 17 (Tue)
        today: June 15 (Sun) - but min_dropoff_date (June 17) is after today.
        max_dropoff_date = June 20 (Fri)
        Expected: June 17, June 18, June 19, June 20
        """
        self.service_settings.max_advance_dropoff_days = 3
        self.service_settings.booking_open_days = "Mon,Tue,Wed,Thu,Fri,Sat,Sun"
        self.service_settings.save()

        self.temp_booking.service_date = self.fixed_local_date + datetime.timedelta(days=5)                
        self.temp_booking.save()

        expected_dates = [
            '2025-06-17',          
            '2025-06-18',            
            '2025-06-19',           
            '2025-06-20'                         
        ]
        available_dates = get_drop_off_date_availability(self.temp_booking, self.service_settings)
        self.assertEqual(available_dates, expected_dates)

    def test_dropoff_date_cannot_be_after_service_date(self):
        """
        Test that the drop-off date cannot be after the service date.
        (This is a core logic of the function, max_dropoff_date = service_date)
        service_date: June 16 (Mon)
        max_advance_dropoff_days: 7 (will allow back to June 9, but restricted by today: June 15)
        min_dropoff_date = June 15 (today)
        max_dropoff_date = June 16 (service_date)
        Expected: June 15, June 16
        """
        self.service_settings.max_advance_dropoff_days = 7
        self.service_settings.booking_open_days = "Mon,Tue,Wed,Thu,Fri,Sat,Sun"
        self.service_settings.save()

        self.temp_booking.service_date = self.fixed_local_date + datetime.timedelta(days=1)                
        self.temp_booking.save()

        expected_dates = [
            '2025-06-15',                 
            '2025-06-16'                         
        ]
        available_dates = get_drop_off_date_availability(self.temp_booking, self.service_settings)
        self.assertEqual(available_dates, expected_dates)

    def test_blocked_service_date_single_day(self):
        """
        Test that a single blocked date is correctly excluded.
        service_date: June 18 (Wed)
        Blocked: June 16 (Mon)
        Expected: June 15, June 17, June 18
        """
        self.service_settings.booking_open_days = "Mon,Tue,Wed,Thu,Fri,Sat,Sun"
        self.service_settings.save()

        self.temp_booking.service_date = self.fixed_local_date + datetime.timedelta(days=3)                
        self.temp_booking.save()

        BlockedServiceDateFactory(
            start_date=self.fixed_local_date + datetime.timedelta(days=1),                
            end_date=self.fixed_local_date + datetime.timedelta(days=1)                  
        )

        expected_dates = [
            '2025-06-15',         
            '2025-06-17',          
            '2025-06-18'             
        ]
        available_dates = get_drop_off_date_availability(self.temp_booking, self.service_settings)
        self.assertEqual(available_dates, expected_dates)

    def test_blocked_service_date_range(self):
        """
        Test that a range of blocked dates is correctly excluded.
        service_date: June 22 (Sun)
        Blocked: June 17-19 (Tue-Thu)
        Expected: June 15, June 16, June 20, June 21, June 22
        """
        self.service_settings.booking_open_days = "Mon,Tue,Wed,Thu,Fri,Sat,Sun"
        self.service_settings.save()

        self.temp_booking.service_date = self.fixed_local_date + datetime.timedelta(days=7)                
        self.temp_booking.save()

        BlockedServiceDateFactory(
            start_date=self.fixed_local_date + datetime.timedelta(days=2),                
            end_date=self.fixed_local_date + datetime.timedelta(days=4)                  
        )

        expected_dates = [
            '2025-06-15',         
            '2025-06-16',         
            '2025-06-20',         
            '2025-06-21',           
            '2025-06-22'          
        ]
        available_dates = get_drop_off_date_availability(self.temp_booking, self.service_settings)
        self.assertEqual(available_dates, expected_dates)

    def test_allow_after_hours_dropoff_true_ignores_open_days(self):
        """
        Test that when allow_after_hours_dropoff is True, booking_open_days are ignored.
        service_date: June 18 (Wed)
        booking_open_days: Only Mon,Tue
        Expected: June 15, 16, 17, 18 (all days from range should be available)
        """
        self.service_settings.allow_after_hours_dropoff = True
        self.service_settings.booking_open_days = "Mon,Tue"                  
        self.service_settings.save()

        self.temp_booking.service_date = self.fixed_local_date + datetime.timedelta(days=3)                
        self.temp_booking.save()

        expected_dates = [
            '2025-06-15',         
            '2025-06-16',         
            '2025-06-17',          
            '2025-06-18'             
        ]
        available_dates = get_drop_off_date_availability(self.temp_booking, self.service_settings)
        self.assertEqual(available_dates, expected_dates)

    def test_allow_after_hours_dropoff_false_respects_open_days(self):
        """
        Test that when allow_after_hours_dropoff is False, booking_open_days are respected.
        service_date: June 18 (Wed)
        booking_open_days: Only Mon,Tue
        Expected: June 16, 17 (Jun 15 and 18 are not Mon/Tue)
        """
        self.service_settings.allow_after_hours_dropoff = False
        self.service_settings.booking_open_days = "Mon,Tue"
        self.service_settings.save()

        self.temp_booking.service_date = self.fixed_local_date + datetime.timedelta(days=3)                
        self.temp_booking.save()
        
                                                            
                                               
                                                                   
        expected_dates = [
            '2025-06-16',         
            '2025-06-17'           
        ]
        available_dates = get_drop_off_date_availability(self.temp_booking, self.service_settings)
        self.assertEqual(available_dates, expected_dates)

    def test_service_date_in_past(self):
        """
        Test that if service_date is in the past, availability is restricted to today.
        service_date: June 13 (Fri)
        today: June 15 (Sun)
        min_dropoff_date = June 13 - 7 days = June 6, but clamped to June 15 (today)
        max_dropoff_date = June 13 (service_date)
        Since min_dropoff_date (Jun 15) > max_dropoff_date (Jun 13), should return empty.
        """
        self.service_settings.booking_open_days = "Mon,Tue,Wed,Thu,Fri,Sat,Sun"
        self.service_settings.save()

        self.temp_booking.service_date = self.fixed_local_date - datetime.timedelta(days=2)                
        self.temp_booking.save()

        expected_dates = []
        available_dates = get_drop_off_date_availability(self.temp_booking, self.service_settings)
        self.assertEqual(available_dates, expected_dates)

    def test_max_advance_days_is_zero(self):
        """
        Test with max_advance_dropoff_days set to 0.
        This means drop-off date must be exactly the service date.
        service_date: June 18 (Wed)
        Expected: June 18
        """
        self.service_settings.max_advance_dropoff_days = 0
        self.service_settings.booking_open_days = "Mon,Tue,Wed,Thu,Fri,Sat,Sun"
        self.service_settings.save()

        self.temp_booking.service_date = self.fixed_local_date + datetime.timedelta(days=3)                
        self.temp_booking.save()

        expected_dates = ['2025-06-18']
        available_dates = get_drop_off_date_availability(self.temp_booking, self.service_settings)
        self.assertEqual(available_dates, expected_dates)

    def test_empty_booking_open_days_no_after_hours(self):
        """
        Test with empty booking_open_days string and allow_after_hours_dropoff is False.
        Should return an empty list because no days are open.
        """
                                                                          
                                                                      
                                                                      
                                                                                    
        self.service_settings.booking_open_days = "Mon,Tue,Wed,Thu,Fri,Sat,Sun"                                  
        self.service_settings.allow_after_hours_dropoff = False
        self.service_settings.save()

        self.temp_booking.service_date = self.fixed_local_date + datetime.timedelta(days=3)                
        self.temp_booking.save()

                                                                                             
                                                                        
                                                                                  
        dummy_settings = ServiceSettings(
            max_advance_dropoff_days=self.service_settings.max_advance_dropoff_days,
            allow_after_hours_dropoff=False,
            booking_open_days=""                                               
        )
        
        expected_dates = []
        available_dates = get_drop_off_date_availability(self.temp_booking, dummy_settings)
        self.assertEqual(available_dates, expected_dates)

    def test_all_dates_blocked(self):
        """
        Test a scenario where all potential dates are blocked by BlockedServiceDate entries.
        service_date: June 18 (Wed)
        Blocked: June 15-18 (Sun-Wed)
        Expected: Empty list
        """
        self.service_settings.booking_open_days = "Mon,Tue,Wed,Thu,Fri,Sat,Sun"
        self.service_settings.save()

        self.temp_booking.service_date = self.fixed_local_date + datetime.timedelta(days=3)                
        self.temp_booking.save()

                                                           
        BlockedServiceDateFactory(
            start_date=self.fixed_local_date,          
            end_date=self.fixed_local_date + datetime.timedelta(days=3)          
        )

        expected_dates = []
        available_dates = get_drop_off_date_availability(self.temp_booking, self.service_settings)
        self.assertEqual(available_dates, expected_dates)
