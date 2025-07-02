                                                                    

import datetime
from django.test import TestCase
from inventory.models import InventorySettings, BlockedSalesDate
from inventory.utils.get_sales_appointment_date_info import get_sales_appointment_date_info
from ..test_helpers.model_factories import InventorySettingsFactory, BlockedSalesDateFactory

class GetSalesAppointmentDateInfoTest(TestCase):
    #--

    @classmethod
    def setUpTestData(cls):
        #--
                                                                                      
        cls.default_inventory_settings = InventorySettingsFactory(
            sales_appointment_start_time=datetime.time(9, 0),
            sales_appointment_end_time=datetime.time(17, 0),
            sales_appointment_spacing_mins=30,
            min_advance_booking_hours=24,                            
            max_advance_booking_days=90,                                 
            deposit_lifespan_days=5,                                         
            sales_booking_open_days="Mon,Tue,Wed,Thu,Fri",                         
        )

    def tearDown(self):
        #--
                                                                 
        self.default_inventory_settings.refresh_from_db()
        self.default_inventory_settings.sales_appointment_start_time = datetime.time(9, 0)
        self.default_inventory_settings.sales_appointment_end_time = datetime.time(17, 0)
        self.default_inventory_settings.sales_appointment_spacing_mins = 30
        self.default_inventory_settings.min_advance_booking_hours = 24
        self.default_inventory_settings.max_advance_booking_days = 90
        self.default_inventory_settings.deposit_lifespan_days = 5
        self.default_inventory_settings.sales_booking_open_days = "Mon,Tue,Wed,Thu,Fri"
        self.default_inventory_settings.save()
        BlockedSalesDate.objects.all().delete()                                               


    def test_default_behavior(self):
        #--
                                                                    
                                                                                     
                                                                             
        
                                                                                  
        self.default_inventory_settings.min_advance_booking_hours = 0
        self.default_inventory_settings.save()

        min_date, max_date, blocked_dates = get_sales_appointment_date_info(self.default_inventory_settings)

        today = datetime.date.today()
                                                                    
        self.assertEqual(min_date, today)
                                                       
        self.assertEqual(max_date, today + datetime.timedelta(days=90))

                                                                                          
        expected_blocked_dates = []
        current_day = today
        while current_day <= max_date:
            if current_day.weekday() >= 5:                             
                expected_blocked_dates.append(current_day.strftime('%Y-%m-%d'))
            current_day += datetime.timedelta(days=1)
        
        self.assertEqual(blocked_dates, sorted(list(set(expected_blocked_dates))))

    def test_no_inventory_settings_provided(self):
        #--
                                                                
        InventorySettings.objects.all().delete()
        min_date, max_date, blocked_dates = get_sales_appointment_date_info(None)            

        today = datetime.date.today()
        self.assertEqual(min_date, today)
        self.assertEqual(max_date, today + datetime.timedelta(days=90))
        self.assertEqual(blocked_dates, [])
                                  
        self.default_inventory_settings = InventorySettingsFactory()


    def test_min_advance_booking_hours(self):
        #--
                                                                     
        self.default_inventory_settings.min_advance_booking_hours = 24
        self.default_inventory_settings.save()

        min_date, _, _ = get_sales_appointment_date_info(self.default_inventory_settings)
        expected_min_date = datetime.date.today() + datetime.timedelta(days=1)           
        self.assertEqual(min_date, expected_min_date)

                                                                                                  
        self.default_inventory_settings.min_advance_booking_hours = 48
        self.default_inventory_settings.save()
        min_date, _, _ = get_sales_appointment_date_info(self.default_inventory_settings)
        expected_min_date = datetime.date.today() + datetime.timedelta(days=2)                     
        self.assertEqual(min_date, expected_min_date)

    def test_max_advance_booking_days(self):
        #--
        self.default_inventory_settings.max_advance_booking_days = 30
        self.default_inventory_settings.save()

        _, max_date, _ = get_sales_appointment_date_info(self.default_inventory_settings)
        expected_max_date = datetime.date.today() + datetime.timedelta(days=30)
        self.assertEqual(max_date, expected_max_date)

    def test_deposit_flow_caps_max_date(self):
        #--
        self.default_inventory_settings.max_advance_booking_days = 90
        self.default_inventory_settings.deposit_lifespan_days = 10                   
        self.default_inventory_settings.min_advance_booking_hours = 0                                       
        self.default_inventory_settings.save()

                                                                                                 
        min_date, max_date, _ = get_sales_appointment_date_info(self.default_inventory_settings, is_deposit_flow=True)
        expected_max_date = datetime.date.today() + datetime.timedelta(days=10)
        self.assertEqual(max_date, expected_max_date)
        self.assertEqual(min_date, datetime.date.today())              

                                                                              
        self.default_inventory_settings.max_advance_booking_days = 5
        self.default_inventory_settings.deposit_lifespan_days = 10                  
        self.default_inventory_settings.save()

        min_date, max_date, _ = get_sales_appointment_date_info(self.default_inventory_settings, is_deposit_flow=True)
        expected_max_date = datetime.date.today() + datetime.timedelta(days=5)                           
        self.assertEqual(max_date, expected_max_date)

    def test_blocked_sales_dates(self):
        #--
        today = datetime.date.today()
                                
        BlockedSalesDateFactory(
            start_date=today + datetime.timedelta(days=5),
            end_date=today + datetime.timedelta(days=7),
            description="Test Block"
        )
                             
        BlockedSalesDateFactory(
            start_date=today + datetime.timedelta(days=10),
            end_date=today + datetime.timedelta(days=10),
            description="Single Day Block"
        )

        self.default_inventory_settings.min_advance_booking_hours = 0
        self.default_inventory_settings.sales_booking_open_days = "Mon,Tue,Wed,Thu,Fri,Sat,Sun"                                            
        self.default_inventory_settings.save()

        min_date, max_date, blocked_dates = get_sales_appointment_date_info(self.default_inventory_settings)

        expected_blocked_dates = []
        for i in range(5, 8):               
            expected_blocked_dates.append((today + datetime.timedelta(days=i)).strftime('%Y-%m-%d'))
        expected_blocked_dates.append((today + datetime.timedelta(days=10)).strftime('%Y-%m-%d'))

        self.assertIn((today + datetime.timedelta(days=5)).strftime('%Y-%m-%d'), blocked_dates)
        self.assertIn((today + datetime.timedelta(days=6)).strftime('%Y-%m-%d'), blocked_dates)
        self.assertIn((today + datetime.timedelta(days=7)).strftime('%Y-%m-%d'), blocked_dates)
        self.assertIn((today + datetime.timedelta(days=10)).strftime('%Y-%m-%d'), blocked_dates)
                                                                    
        for i in range(max(0, self.default_inventory_settings.min_advance_booking_hours // 24), 15):
            d = today + datetime.timedelta(days=i)
            d_str = d.strftime('%Y-%m-%d')
            if d_str not in expected_blocked_dates:
                self.assertNotIn(d_str, blocked_dates)
        
                                         
        self.assertEqual(blocked_dates, sorted(list(set(blocked_dates))))


    def test_sales_booking_open_days(self):
        #--
        today = datetime.date.today()
                                                  
        self.default_inventory_settings.sales_booking_open_days = "Mon,Tue"
        self.default_inventory_settings.min_advance_booking_hours = 0
        self.default_inventory_settings.max_advance_booking_days = 7                                 
        self.default_inventory_settings.save()

        min_date, max_date, blocked_dates = get_sales_appointment_date_info(self.default_inventory_settings)

        expected_blocked_dates = []
        current_day = min_date
        while current_day <= max_date:
                                                                            
            if current_day.weekday() not in [0, 1]:
                expected_blocked_dates.append(current_day.strftime('%Y-%m-%d'))
            current_day += datetime.timedelta(days=1)
        
        self.assertEqual(blocked_dates, sorted(list(set(expected_blocked_dates))))

    def test_max_date_capped_by_min_date(self):
        #--
                                                 
        self.default_inventory_settings.min_advance_booking_hours = 720          
                                               
        self.default_inventory_settings.max_advance_booking_days = 1
        self.default_inventory_settings.save()

        min_date, max_date, _ = get_sales_appointment_date_info(self.default_inventory_settings)

        expected_min_date = datetime.date.today() + datetime.timedelta(days=30)
        self.assertEqual(min_date, expected_min_date)
                                               
        self.assertEqual(max_date, expected_min_date)

    def test_combined_blocking_factors(self):
        #--
        today = datetime.date.today()

                         
        self.default_inventory_settings.min_advance_booking_hours = 24                       
        self.default_inventory_settings.max_advance_booking_days = 14                
        self.default_inventory_settings.sales_booking_open_days = "Mon,Wed,Fri"               
        self.default_inventory_settings.save()

                                                
        blocked_date_in_range = today + datetime.timedelta(days=5)                                  
        BlockedSalesDateFactory(
            start_date=blocked_date_in_range,
            end_date=blocked_date_in_range,
            description="Specific blocked day"
        )
        
        min_date, max_date, blocked_dates = get_sales_appointment_date_info(self.default_inventory_settings)

        expected_min_date = today + datetime.timedelta(days=1)
        expected_max_date = today + datetime.timedelta(days=14)

        self.assertEqual(min_date, expected_min_date)
        self.assertEqual(max_date, expected_max_date)

        calculated_blocked_dates = []
        current_day = min_date
        while current_day <= max_date:
                                                                                 
                                                
            if current_day.weekday() not in [0, 2, 4]:
                calculated_blocked_dates.append(current_day.strftime('%Y-%m-%d'))
            
                                               
            if current_day == blocked_date_in_range:
                calculated_blocked_dates.append(current_day.strftime('%Y-%m-%d'))

            current_day += datetime.timedelta(days=1)
        
                                                                        
        self.assertEqual(blocked_dates, sorted(list(set(calculated_blocked_dates))))

