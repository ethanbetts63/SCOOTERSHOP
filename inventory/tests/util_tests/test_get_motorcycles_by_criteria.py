from django.test import TestCase
from decimal import Decimal
import datetime
from inventory.models import Motorcycle
from inventory.utils.get_motorcycles_by_criteria import get_motorcycles_by_criteria
from ..test_helpers.model_factories import MotorcycleFactory, MotorcycleConditionFactory

class GetMotorcyclesByCriteriaTest(TestCase):
    

    @classmethod
    def setUpTestData(cls):
        
                                         
        cls.condition_new = MotorcycleConditionFactory(name='new', display_name='New')
        cls.condition_used = MotorcycleConditionFactory(name='used', display_name='Used')
        cls.condition_demo = MotorcycleConditionFactory(name='demo', display_name='Demo')
                                                                                        
        base_time_setup = datetime.datetime(2023, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
        delta_seconds = 0

                                                                  
        def create_and_set_date(brand, model, year, price, engine_size, conditions):
            nonlocal delta_seconds
            moto = MotorcycleFactory(
                brand=brand,
                model=model,
                year=year,
                price=price,
                engine_size=engine_size,
                conditions=conditions,
            )
                                                                               
            moto.date_posted = base_time_setup + datetime.timedelta(seconds=delta_seconds)
            moto.save()
            delta_seconds += 1                                    
            return moto

                                                                                                        
                                                                                                       

                                                            
        cls.honda_new = create_and_set_date('Honda', 'CBR', 2023, Decimal('15000.00'), 1000, [cls.condition_new.name])
        cls.yamaha_new = create_and_set_date('Yamaha', 'YZF', 2022, Decimal('12000.00'), 800, [cls.condition_new.name])
        cls.suzuki_new = create_and_set_date('Suzuki', 'GSXR', 2023, Decimal('13000.00'), 750, [cls.condition_new.name])
        cls.honda_used = create_and_set_date('Honda', 'CRF', 2020, Decimal('8000.00'), 650, [cls.condition_used.name])
        cls.kawasaki_used = create_and_set_date('Kawasaki', 'Ninja', 2019, Decimal('7000.00'), 400, [cls.condition_used.name])
        cls.yamaha_demo = create_and_set_date('Yamaha', 'MT', 2021, Decimal('9500.00'), 900, [cls.condition_demo.name])
        cls.ducati_demo = create_and_set_date('Ducati', 'Monster', 2021, Decimal('11000.00'), 1100, [cls.condition_demo.name])
                                                                                          
        cls.expected_default_order_full_dataset = [
            cls.ducati_demo,
            cls.yamaha_demo,
            cls.kawasaki_used,
            cls.honda_used,
            cls.suzuki_new,
            cls.yamaha_new,
            cls.honda_new,
        ]

    def test_get_motorcycles_no_filters(self):
        
        queryset = get_motorcycles_by_criteria()
        self.assertEqual(queryset.count(), 7)
        self.assertQuerySetEqual(queryset, self.expected_default_order_full_dataset, ordered=True)

    def test_filter_by_new_condition_slug(self):
        
        queryset = get_motorcycles_by_criteria(condition_slug='new')
        self.assertEqual(queryset.count(), 3)
        self.assertIn(self.honda_new, queryset)
        self.assertIn(self.yamaha_new, queryset)
        self.assertIn(self.suzuki_new, queryset)
        self.assertNotIn(self.honda_used, queryset)
        self.assertNotIn(self.yamaha_demo, queryset)

    def test_filter_by_used_condition_slug(self):
        
        queryset = get_motorcycles_by_criteria(condition_slug='used')
        self.assertEqual(queryset.count(), 4)                                                                                                  
        self.assertIn(self.honda_used, queryset)
        self.assertIn(self.kawasaki_used, queryset)
        self.assertIn(self.yamaha_demo, queryset)
        self.assertIn(self.ducati_demo, queryset)
        self.assertNotIn(self.honda_new, queryset)                               

    def test_filter_by_brand(self):
        
        queryset = get_motorcycles_by_criteria(brand='Honda')
        self.assertEqual(queryset.count(), 2)
        self.assertIn(self.honda_new, queryset)
        self.assertIn(self.honda_used, queryset)

    def test_filter_by_model_contains(self):
        
                                                        
        queryset = get_motorcycles_by_criteria(model='R')
        self.assertEqual(queryset.count(), 4)                              
        self.assertIn(self.honda_new, queryset)
        self.assertIn(self.suzuki_new, queryset)
        self.assertIn(self.honda_used, queryset)                   
        self.assertIn(self.ducati_demo, queryset)                         
        self.assertNotIn(self.yamaha_new, queryset)

        queryset_ninja = get_motorcycles_by_criteria(model='ninja')                   
        self.assertEqual(queryset_ninja.count(), 1)
        self.assertIn(self.kawasaki_used, queryset_ninja)

    def test_filter_by_year_range(self):
        
        queryset = get_motorcycles_by_criteria(year_min=2021, year_max=2022)
        self.assertEqual(queryset.count(), 3)                                                            
        self.assertIn(self.yamaha_new, queryset)
        self.assertIn(self.yamaha_demo, queryset)
        self.assertIn(self.ducati_demo, queryset)
        self.assertNotIn(self.honda_new, queryset)       
        self.assertNotIn(self.honda_used, queryset)       

        queryset_min_only = get_motorcycles_by_criteria(year_min=2022)
        self.assertEqual(queryset_min_only.count(), 3)                                                         
        self.assertIn(self.honda_new, queryset_min_only)
        self.assertIn(self.yamaha_new, queryset_min_only)
        self.assertIn(self.suzuki_new, queryset_min_only)

    def test_filter_by_price_range(self):
        
                                        
        queryset = get_motorcycles_by_criteria(price_min=Decimal('9000.00'), price_max=Decimal('13000.00'))
                                                                                                                
        self.assertEqual(queryset.count(), 4)
        self.assertIn(self.yamaha_new, queryset)
        self.assertIn(self.suzuki_new, queryset)
        self.assertIn(self.yamaha_demo, queryset)
        self.assertIn(self.ducati_demo, queryset)
        self.assertNotIn(self.honda_new, queryset)        
        self.assertNotIn(self.honda_used, queryset)       

                        
        queryset_max_only = get_motorcycles_by_criteria(price_max=Decimal('7000.00'))
                                                            
        self.assertEqual(queryset_max_only.count(), 1)
        self.assertIn(self.kawasaki_used, queryset_max_only)

    def test_filter_by_engine_size_range(self):
        
                                           
        queryset = get_motorcycles_by_criteria(engine_min_cc=700, engine_max_cc=1000)
                                                                                           
        self.assertEqual(queryset.count(), 4)
        self.assertIn(self.honda_new, queryset)
        self.assertIn(self.yamaha_new, queryset)
        self.assertIn(self.suzuki_new, queryset)
        self.assertIn(self.yamaha_demo, queryset)
        self.assertNotIn(self.honda_used, queryset)      
        self.assertNotIn(self.ducati_demo, queryset)       

    def test_combined_filters(self):
        
                                                                         
        queryset = get_motorcycles_by_criteria(
            condition_slug='used',
            brand='Honda',
            year_min=2020,
            year_max=2021,
            price_max=Decimal('9000.00')
        )
                                                
        self.assertEqual(queryset.count(), 1)
        self.assertIn(self.honda_used, queryset)
        self.assertNotIn(self.honda_new, queryset)                
        self.assertNotIn(self.yamaha_demo, queryset)            

                                         
        queryset_new_large_engine = get_motorcycles_by_criteria(
            condition_slug='new',
            engine_min_cc=800
        )
                                                      
        self.assertEqual(queryset_new_large_engine.count(), 2)
        self.assertIn(self.honda_new, queryset_new_large_engine)
        self.assertIn(self.yamaha_new, queryset_new_large_engine)
        self.assertNotIn(self.suzuki_new, queryset_new_large_engine)        

    def test_ordering_price_low_to_high(self):
        
        queryset = get_motorcycles_by_criteria(order='price_low_to_high')
                                                                                    
                                                               
        prices = [bike.price for bike in queryset if bike.price is not None]
        sorted_prices = sorted(prices)
        self.assertEqual(prices, sorted_prices)

    def test_ordering_price_high_to_low(self):
        
        queryset = get_motorcycles_by_criteria(order='price_high_to_low')
        prices = [bike.price for bike in queryset if bike.price is not None]
        sorted_prices = sorted(prices, reverse=True)
        self.assertEqual(prices, sorted_prices)

    def test_ordering_age_new_to_old(self):
        
        queryset = get_motorcycles_by_criteria(order='age_new_to_old')
                                                                           
        years_and_dates = [(bike.year, bike.date_posted) for bike in queryset]
                                  
        expected_sorted = sorted(years_and_dates, key=lambda x: (x[0], x[1]), reverse=True)
        self.assertEqual(years_and_dates, expected_sorted)

    def test_ordering_age_old_to_new(self):
        
        queryset = get_motorcycles_by_criteria(order='age_old_to_new')
        years_and_dates = [(bike.year, bike.date_posted) for bike in queryset]
        expected_sorted = sorted(years_and_dates, key=lambda x: (x[0], x[1]))
        self.assertEqual(years_and_dates, expected_sorted)

    def test_ordering_default_date_posted(self):
        
                                                                                       
                                                                            
        base_test_time = datetime.datetime(2024, 6, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)

        test_moto_c = MotorcycleFactory(brand='DefaultOrderTest', model='C', year=2019, engine_size=400)
        test_moto_c.date_posted = base_test_time + datetime.timedelta(seconds=0)         
        test_moto_c.save()

        test_moto_a = MotorcycleFactory(brand='DefaultOrderTest', model='A', year=2020, engine_size=500)
        test_moto_a.date_posted = base_test_time + datetime.timedelta(seconds=1)
        test_moto_a.save()

        test_moto_b = MotorcycleFactory(brand='DefaultOrderTest', model='B', year=2021, engine_size=600)
        test_moto_b.date_posted = base_test_time + datetime.timedelta(seconds=2)         
        test_moto_b.save()

        queryset = get_motorcycles_by_criteria(brand='DefaultOrderTest')
                                                                                                                   
        expected_order = [test_moto_b, test_moto_a, test_moto_c]
        self.assertQuerySetEqual(queryset, expected_order, ordered=True)


    def test_no_results_found(self):
        
        queryset = get_motorcycles_by_criteria(brand='NonExistentBrand')
        self.assertEqual(queryset.count(), 0)
        self.assertQuerySetEqual(queryset, [])