from django.test import TestCase
from django.utils import timezone
import datetime
from unittest.mock import patch

                                  
from service.utils.get_available_service_dropoff_times import get_available_dropoff_times

                             
from service.models import ServiceSettings, ServiceBooking
from ..test_helpers.model_factories import (
    ServiceSettingsFactory,
    ServiceBookingFactory,
)

class GetAvailableDropoffTimesTest(TestCase):
    """
    Tests for the get_available_dropoff_times function.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up common data for all tests in this class.
        Patch timezone.now() and timezone.localdate() for consistent date tests.
        """
                                                                         
        cls.fixed_now_utc = datetime.datetime(2025, 6, 15, 10, 0, 0, tzinfo=datetime.timezone.utc)
                                                                        
                                                    
        cls.fixed_now_local_datetime = datetime.datetime(2025, 6, 15, 12, 0, 0)
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
        ServiceBooking.objects.all().delete()

                                                        
                                                                                  
                                                                       
        self.service_settings = ServiceSettingsFactory(
            enable_service_booking=True,
            drop_off_start_time=datetime.time(9, 0),
            drop_off_end_time=datetime.time(17, 0),
            drop_off_spacing_mins=30,
            latest_same_day_dropoff_time=datetime.time(17, 0),                      
            allow_after_hours_dropoff=False,
        )
                                                                               
                                                               

    def test_no_service_settings(self):
        """
        Test that an empty list is returned if no ServiceSettings exist.
        """
        ServiceSettings.objects.all().delete()                               
        available_times = get_available_dropoff_times(self.fixed_local_date)
        self.assertEqual(available_times, [])

    def test_basic_slot_generation_today(self):
        """
        Test basic slot generation for today, respecting latest_same_day_dropoff_time
        and current time.
        Fixed time: 2025-06-15 12:00 (Sunday).
        Settings: Start 09:00, End 17:00, Spacing 30min, Latest same day 12:00.
        Expected: No slots after 12:00 for today. No slots before 12:00 (current time).
        Result: Empty list because current time is 12:00 and latest is 12:00, meaning only 12:00 is allowed.
        Since 12:00 is the current time and we skip past times, nothing should be returned.
        Let's adjust fixed time or settings to make it more illustrative.
        Adjusting fixed_now_utc to 09:30 AM (meaning 11:30 AM local)
        and latest_same_day_dropoff_time to 17:00 (5 PM).
        """
                                                      
                                                                                         
                                                  
                                                                                                   
                                
        with patch('django.utils.timezone.now', return_value=datetime.datetime(2025, 6, 15, 9, 30, 1, tzinfo=datetime.timezone.utc)):
            self.service_settings.drop_off_start_time = datetime.time(9, 0)
            self.service_settings.drop_off_end_time = datetime.time(17, 0)
            self.service_settings.drop_off_spacing_mins = 30
            self.service_settings.latest_same_day_dropoff_time = datetime.time(17, 0)                                
            self.service_settings.save()

                                                                         
                                                                               
                                                                                  
                                                                                          
                                                   
                                            
            expected_times = [
                '12:00', '12:30', '13:00', '13:30', '14:00',
                '14:30', '15:00', '15:30', '16:00', '16:30', '17:00'
            ]
            available_times = get_available_dropoff_times(self.fixed_local_date)
            self.assertEqual(available_times, expected_times)

    def test_basic_slot_generation_future_date(self):
        """
        Test basic slot generation for a future date (no current time restrictions).
        """
        future_date = self.fixed_local_date + datetime.timedelta(days=7)              
        self.service_settings.drop_off_start_time = datetime.time(9, 0)
        self.service_settings.drop_off_end_time = datetime.time(17, 0)
        self.service_settings.drop_off_spacing_mins = 60               
        self.service_settings.save()

        expected_times = [
            '09:00', '10:00', '11:00', '12:00', '13:00',
            '14:00', '15:00', '16:00', '17:00'
        ]
        available_times = get_available_dropoff_times(future_date)
        self.assertEqual(available_times, expected_times)

    def test_slots_blocked_by_existing_bookings(self):
        """
        Test that slots are blocked by existing bookings within the spacing window.
        Booking at 10:00 with 30 min spacing blocks 09:30, 10:00, 10:30.
        """
        test_date = self.fixed_local_date + datetime.timedelta(days=1)         
        self.service_settings.drop_off_start_time = datetime.time(9, 0)
        self.service_settings.drop_off_end_time = datetime.time(12, 0)
        self.service_settings.drop_off_spacing_mins = 30
                                                                                
        self.service_settings.latest_same_day_dropoff_time = datetime.time(12, 0) 
        self.service_settings.save()

                                   
        ServiceBookingFactory(
            dropoff_date=test_date,
            dropoff_time=datetime.time(10, 0)
        )

                                                                                
                                                                              
        expected_times = [
            '09:00', '11:00', '11:30', '12:00'
        ]
        available_times = get_available_dropoff_times(test_date)
        self.assertEqual(available_times, expected_times)

    def test_slots_blocked_by_multiple_bookings(self):
        """
        Test that multiple bookings correctly block their respective slots.
        Bookings at 09:30 and 11:00 with 30 min spacing.
        09:30 blocks 09:00, 09:30, 10:00
        11:00 blocks 10:30, 11:00, 11:30
        """
        test_date = self.fixed_local_date + datetime.timedelta(days=1)         
        self.service_settings.drop_off_start_time = datetime.time(9, 0)
        self.service_settings.drop_off_end_time = datetime.time(12, 0)
        self.service_settings.drop_off_spacing_mins = 30
                                                                                
        self.service_settings.latest_same_day_dropoff_time = datetime.time(12, 0) 
        self.service_settings.save()

        ServiceBookingFactory(dropoff_date=test_date, dropoff_time=datetime.time(9, 30))
        ServiceBookingFactory(dropoff_date=test_date, dropoff_time=datetime.time(11, 0))

                                                                        
                                                             
                                                             
        expected_times = ['12:00']
        available_times = get_available_dropoff_times(test_date)
        self.assertEqual(available_times, expected_times)

    def test_allow_after_hours_dropoff_true(self):
        """
        Test that when allow_after_hours_dropoff is True, all 24 hours are considered,
        and current time/latest_same_day_dropoff_time do not restrict.
        """
        self.service_settings.allow_after_hours_dropoff = True
        self.service_settings.drop_off_spacing_mins = 60                        
                                                                                                          
                                                                                                      
        self.service_settings.drop_off_start_time = datetime.time(0, 0)
        self.service_settings.drop_off_end_time = datetime.time(23, 59)
        self.service_settings.latest_same_day_dropoff_time = datetime.time(23, 59)                                       
        self.service_settings.save()

                                                            
        expected_times = [f"{h:02d}:00" for h in range(24)]
        available_times = get_available_dropoff_times(self.fixed_local_date)
        self.assertEqual(available_times, expected_times)

    def test_allow_after_hours_dropoff_true_with_booking(self):
        """
        Test that even with after-hours allowed, existing bookings still block slots.
        Booking at 01:00 with 60 min spacing blocks 00:00, 01:00, 02:00.
        """
        test_date = self.fixed_local_date + datetime.timedelta(days=1)         
        self.service_settings.allow_after_hours_dropoff = True
        self.service_settings.drop_off_spacing_mins = 60
                                                      
        self.service_settings.drop_off_start_time = datetime.time(0, 0)
        self.service_settings.drop_off_end_time = datetime.time(23, 59)
        self.service_settings.latest_same_day_dropoff_time = datetime.time(23, 59)
        self.service_settings.save()

        ServiceBookingFactory(dropoff_date=test_date, dropoff_time=datetime.time(1, 0))

        expected_times = [f"{h:02d}:00" for h in range(24) if h not in [0, 1, 2]]
        available_times = get_available_dropoff_times(test_date)
        self.assertEqual(available_times, expected_times)

    def test_drop_off_spacing_mins_60(self):
        """
        Test with drop_off_spacing_mins set to 60.
        """
        test_date = self.fixed_local_date + datetime.timedelta(days=1)         
        self.service_settings.drop_off_start_time = datetime.time(9, 0)
        self.service_settings.drop_off_end_time = datetime.time(12, 0)
                                                                           
        self.service_settings.latest_same_day_dropoff_time = datetime.time(12, 0)
        self.service_settings.drop_off_spacing_mins = 60
        self.service_settings.save()

        expected_times = ['09:00', '10:00', '11:00', '12:00']
        available_times = get_available_dropoff_times(test_date)
        self.assertEqual(available_times, expected_times)

    def test_drop_off_spacing_mins_15(self):
        """
        Test with drop_off_spacing_mins set to 15.
        """
        test_date = self.fixed_local_date + datetime.timedelta(days=1)         
        self.service_settings.drop_off_start_time = datetime.time(9, 0)
        self.service_settings.drop_off_end_time = datetime.time(9, 45)                                   
                                                                           
        self.service_settings.latest_same_day_dropoff_time = datetime.time(9, 45)
        self.service_settings.drop_off_spacing_mins = 15
        self.service_settings.save()

        expected_times = ['09:00', '09:15', '09:30', '09:45']
        available_times = get_available_dropoff_times(test_date)
        self.assertEqual(available_times, expected_times)

    def test_selected_date_in_past_no_after_hours(self):
        """
        Test that if selected_date is in the past and after-hours is not allowed,
        no slots are returned because all potential slots would be "passed".
        """
        past_date = self.fixed_local_date - datetime.timedelta(days=7)              
        self.service_settings.allow_after_hours_dropoff = False
        self.service_settings.save()                                                                                  

        available_times = get_available_dropoff_times(past_date)
        self.assertEqual(available_times, [])

                                                                                     
                                                                            

    def test_current_time_boundary(self):
        """
        Test that current time correctly restricts available slots.
        If current time is 10:15 and spacing is 30, next slot is 10:30.
        """
                                                                         
        with patch('django.utils.timezone.now', return_value=datetime.datetime(2025, 6, 15, 8, 15, 0, tzinfo=datetime.timezone.utc)):
            self.service_settings.drop_off_start_time = datetime.time(9, 0)
            self.service_settings.drop_off_end_time = datetime.time(12, 0)
            self.service_settings.drop_off_spacing_mins = 30
                                                                               
            self.service_settings.latest_same_day_dropoff_time = datetime.time(12, 0)
            self.service_settings.save()

                                                                                
                                               
            expected_times = ['10:30', '11:00', '11:30', '12:00']
            available_times = get_available_dropoff_times(self.fixed_local_date)
            self.assertEqual(available_times, expected_times)

    def test_latest_same_day_dropoff_time_restriction(self):
        """
        Test that latest_same_day_dropoff_time correctly caps slots for today.
        Current time 09:00. Latest same day 10:00.
        """
                                                                                                 
        with patch('django.utils.timezone.now', return_value=datetime.datetime(2025, 6, 15, 5, 0, 0, tzinfo=datetime.timezone.utc)):
            self.service_settings.drop_off_start_time = datetime.time(9, 0)
            self.service_settings.drop_off_end_time = datetime.time(17, 0)                  
            self.service_settings.drop_off_spacing_mins = 30
            self.service_settings.latest_same_day_dropoff_time = datetime.time(10, 0)                          
            self.service_settings.save()

            expected_times = ['09:00', '09:30', '10:00']
            available_times = get_available_dropoff_times(self.fixed_local_date)
            self.assertEqual(available_times, expected_times)

    def test_full_day_blocked_by_booking(self):
        """
        Test a scenario where a single booking (or chain of bookings) blocks the entire day.
        Booking at 9:00 and 30 min spacing blocks 8:30, 9:00, 9:30.
        If start is 9:00, end 9:30, spacing 30, and booking at 9:00, then all are blocked.
        """
        test_date = self.fixed_local_date + datetime.timedelta(days=1)         
        self.service_settings.drop_off_start_time = datetime.time(9, 0)
        self.service_settings.drop_off_end_time = datetime.time(9, 30)
                                                                           
        self.service_settings.latest_same_day_dropoff_time = datetime.time(9, 30)
        self.service_settings.drop_off_spacing_mins = 30
        self.service_settings.save()

        ServiceBookingFactory(dropoff_date=test_date, dropoff_time=datetime.time(9, 0))

        expected_times = []                     
        available_times = get_available_dropoff_times(test_date)
        self.assertEqual(available_times, expected_times)

    def test_timezone_awareness(self):
        """
        Verify that timezone-aware datetimes are handled correctly throughout the function.
        This is implicitly tested by other tests if the patching and timezone activation work,
        but an explicit check can be useful.
        The main check is that no naive/aware datetime errors occur.
        """
        test_date = self.fixed_local_date + datetime.timedelta(days=1)
        self.service_settings.drop_off_start_time = datetime.time(9, 0)
        self.service_settings.drop_off_end_time = datetime.time(9, 30)
                                                                           
        self.service_settings.latest_same_day_dropoff_time = datetime.time(9, 30)
        self.service_settings.drop_off_spacing_mins = 30
        self.service_settings.save()

                                                           
        available_times = get_available_dropoff_times(test_date)
                                                                                       
        self.assertIsInstance(available_times, list)
        self.assertGreater(len(available_times), 0)

