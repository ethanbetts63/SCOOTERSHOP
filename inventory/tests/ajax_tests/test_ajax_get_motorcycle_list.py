                                                            

from django.test import TestCase, Client
from django.urls import reverse
from decimal import Decimal
import datetime
import json

from inventory.models import Motorcycle, MotorcycleCondition
from ..test_helpers.model_factories import MotorcycleFactory, MotorcycleConditionFactory

class AjaxGetMotorcycleListTest(TestCase):
    """
    Tests for the AJAX endpoint `get_motorcycle_list`.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up various motorcycles with different conditions, brands, years, prices,
        and engine sizes to thoroughly test the AJAX filtering and sorting.
        We'll explicitly control `date_posted` for predictable ordering.
        """
        cls.client = Client()

                                         
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
                is_available=True,                               
            )
            moto.date_posted = base_time_setup + datetime.timedelta(seconds=delta_seconds)
            moto.save()
            delta_seconds += 1
            return moto

                                                                                
                                                                                      
        cls.moto_honda_new_2023 = create_and_set_date('Honda', 'CBR1000RR', 2023, Decimal('15000.00'), 1000, [cls.condition_new.name])
        cls.moto_yamaha_new_2022 = create_and_set_date('Yamaha', 'YZF-R6', 2022, Decimal('12000.00'), 600, [cls.condition_new.name])
        cls.moto_suzuki_new_2023 = create_and_set_date('Suzuki', 'GSX-R750', 2023, Decimal('13000.00'), 750, [cls.condition_new.name])
        cls.moto_honda_used_2020 = create_and_set_date('Honda', 'CRF250L', 2020, Decimal('8000.00'), 250, [cls.condition_used.name])
        cls.moto_kawasaki_used_2019 = create_and_set_date('Kawasaki', 'Ninja 400', 2019, Decimal('7000.00'), 400, [cls.condition_used.name])
        cls.moto_yamaha_demo_2021 = create_and_set_date('Yamaha', 'MT-07', 2021, Decimal('9500.00'), 700, [cls.condition_demo.name])
        cls.moto_ducati_demo_2021 = create_and_set_date('Ducati', 'Monster 821', 2021, Decimal('11000.00'), 800, [cls.condition_demo.name])
        cls.moto_ktm_used_2022 = create_and_set_date('KTM', 'Duke 390', 2022, Decimal('6000.00'), 390, [cls.condition_used.name])


                                                                       
        for i in range(1, 15):
            create_and_set_date(
                brand=f'PaginatedBrand{i}',
                model=f'PModel{i}',
                year=2020,
                price=Decimal(f'{5000 + i*100}.00'),
                engine_size=500,
                conditions=[cls.condition_used.name]
            )
                                                            

    def test_initial_load_all_motorcycles_default_order(self):
        """
        Test that the endpoint returns all motorcycles with default ordering
        when no filters are applied.
        """
        response = self.client.get(reverse('inventory:ajax-get-motorcycle-list'), {'condition_slug': 'all'})
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertIn('motorcycles', data)
        self.assertIn('page_obj', data)
        self.assertIn('unique_makes_for_filter', data)

                                                        
        self.assertEqual(len(data['motorcycles']), 10)                 
        self.assertEqual(data['page_obj']['number'], 1)
        self.assertTrue(data['page_obj']['has_next'])

                                                            
        all_motorcycles_in_db = list(Motorcycle.objects.all().order_by('-date_posted'))
        expected_first_page_ids = [m.id for m in all_motorcycles_in_db[:10]]
        returned_motorcycle_ids = [m['id'] for m in data['motorcycles']]
        self.assertEqual(returned_motorcycle_ids, expected_first_page_ids)

                                                                                
        expected_unique_makes = {
            'Honda', 'Yamaha', 'Suzuki', 'Kawasaki', 'Ducati', 'Harley-Davidson',
            'BMW', 'KTM'
        }
                                          
        for i in range(1, 15):
            expected_unique_makes.add(f'PaginatedBrand{i}')

        self.assertEqual(set(data['unique_makes_for_filter']), expected_unique_makes)


    def test_filter_by_condition_slug_new(self):
        """
        Test filtering by 'new' condition slug.
        """
        response = self.client.get(reverse('inventory:ajax-get-motorcycle-list'), {'condition_slug': 'new'})
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(len(data['motorcycles']), 3)
        returned_brands = {m['brand'] for m in data['motorcycles']}
        self.assertEqual(returned_brands, {'Honda', 'Yamaha', 'Suzuki'})
        self.assertFalse(data['page_obj']['has_next'])                                           

    def test_filter_by_condition_slug_used(self):
        """
        Test filtering by 'used' condition slug (includes 'demo').
        """
        response = self.client.get(reverse('inventory:ajax-get-motorcycle-list'), {'condition_slug': 'used'})
        self.assertEqual(response.status_code, 200)
        data = response.json()

                                                                                                                                
                                                 
        self.assertEqual(len(data['motorcycles']), 10)                        
        self.assertTrue(data['page_obj']['has_next'])
        self.assertEqual(data['page_obj']['num_pages'], 2)

        total_used_motorcycles = Motorcycle.objects.filter(
            conditions__name__in=['used', 'demo']
        ).distinct().count()
        self.assertEqual(total_used_motorcycles, 20)                                  


    def test_filter_by_brand(self):
        """
        Test filtering by a specific brand.
        """
        response = self.client.get(reverse('inventory:ajax-get-motorcycle-list'), {'brand': 'Honda', 'condition_slug': 'all'})
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(len(data['motorcycles']), 2)
        returned_models = {m['model'] for m in data['motorcycles']}
        self.assertEqual(returned_models, {'CBR1000RR', 'CRF250L'})
        self.assertFalse(data['page_obj']['has_next'])                                      

    def test_filter_by_year_range(self):
        """
        Test filtering by a year range.
        """
        response = self.client.get(reverse('inventory:ajax-get-motorcycle-list'), {
            'year_min': '2021',
            'year_max': '2022',
            'condition_slug': 'all'
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()

                                                                                              
        self.assertEqual(len(data['motorcycles']), 4)
        returned_ids = {m['id'] for m in data['motorcycles']}
        expected_ids = {
            self.moto_yamaha_new_2022.id, self.moto_yamaha_demo_2021.id,
            self.moto_ducati_demo_2021.id, self.moto_ktm_used_2022.id
        }
        self.assertEqual(returned_ids, expected_ids)


    def test_filter_by_price_range(self):
        """
        Test filtering by a price range.
        """
        response = self.client.get(reverse('inventory:ajax-get-motorcycle-list'), {
            'price_min': '8000.00',
            'price_max': '12000.00',
            'condition_slug': 'all'
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()

                                                                                                                         
                                                              
        expected_queryset = Motorcycle.objects.filter(
            price__gte=Decimal('8000.00'),
            price__lte=Decimal('12000.00')
        ).exclude(price__isnull=True)                                                 
        self.assertEqual(len(data['motorcycles']), expected_queryset.count())
        returned_titles = {m['title'] for m in data['motorcycles']}
        self.assertIn(self.moto_honda_used_2020.title, returned_titles)
        self.assertIn(self.moto_yamaha_new_2022.title, returned_titles)
        self.assertIn(self.moto_yamaha_demo_2021.title, returned_titles)
        self.assertIn(self.moto_ducati_demo_2021.title, returned_titles)

    def test_filter_by_engine_size_range(self):
        """
        Test filtering by an engine size range.
        """
        response = self.client.get(reverse('inventory:ajax-get-motorcycle-list'), {
            'engine_min_cc': '600',
            'engine_max_cc': '800',
            'condition_slug': 'all'
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()

                                                                                            
        self.assertEqual(len(data['motorcycles']), 4)
        returned_models = {m['model'] for m in data['motorcycles']}
        self.assertEqual(returned_models, {'YZF-R6', 'GSX-R750', 'MT-07', 'Monster 821'})


    def test_combined_filters_and_pagination(self):
        """
        Test a combination of filters and ensure pagination works correctly.
        """
        response = self.client.get(reverse('inventory:ajax-get-motorcycle-list'), {
            'condition_slug': 'used',
            'brand': 'Kawasaki',
            'year_min': '2019',
            'engine_max_cc': '500',
            'page': 1
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()

                                                                                    
        self.assertEqual(len(data['motorcycles']), 1)
        self.assertEqual(data['motorcycles'][0]['model'], 'Ninja 400')
        self.assertEqual(data['page_obj']['number'], 1)
        self.assertEqual(data['page_obj']['num_pages'], 1)
        self.assertFalse(data['page_obj']['has_next'])


    def test_sorting_price_low_to_high(self):
        """
        Test sorting by price from low to high.
        """
        response = self.client.get(reverse('inventory:ajax-get-motorcycle-list'), {
            'order': 'price_low_to_high',
            'condition_slug': 'all',
            'page': 1
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertGreater(len(data['motorcycles']), 0)
                                                                 
        prices = [m['price'] for m in data['motorcycles'] if m['price'] is not None]
        self.assertEqual(prices, sorted(prices))

    def test_pagination_second_page(self):
        """
        Test retrieving the second page of results.
        """
        response = self.client.get(reverse('inventory:ajax-get-motorcycle-list'), {
            'condition_slug': 'all',
            'page': 2
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()

                                                       
                                                              
        self.assertEqual(len(data['motorcycles']), 10)
        self.assertEqual(data['page_obj']['number'], 2)
        self.assertTrue(data['page_obj']['has_previous'])
        self.assertTrue(data['page_obj']['has_next'])

                                                                                        
        all_motorcycles_in_db = list(Motorcycle.objects.all().order_by('-date_posted'))
        expected_second_page_ids = [m.id for m in all_motorcycles_in_db[10:20]]
        returned_motorcycle_ids = [m['id'] for m in data['motorcycles']]
        self.assertEqual(returned_motorcycle_ids, expected_second_page_ids)


    def test_pagination_last_page_empty(self):
        """
        Test requesting a page beyond the last available page.
        Should return the last page.
        """
        response = self.client.get(reverse('inventory:ajax-get-motorcycle-list'), {
            'condition_slug': 'all',
            'page': 100                          
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()

                                                                              
        self.assertEqual(len(data['motorcycles']), 4)                                
        self.assertEqual(data['page_obj']['number'], 3)
        self.assertTrue(data['page_obj']['has_previous'])
        self.assertFalse(data['page_obj']['has_next'])


    def test_invalid_number_format_for_filters(self):
        """
        Test that an invalid number format for filters returns a 400 error.
        """
        response = self.client.get(reverse('inventory:ajax-get-motorcycle-list'), {
            'price_min': 'invalid_price'
        })
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'Invalid number format for filters')

    def test_unique_makes_for_filter_context(self):
        """
        Test that unique_makes_for_filter correctly reflects the brands for the given condition slug.
        """
        response = self.client.get(reverse('inventory:ajax-get-motorcycle-list'), {'condition_slug': 'new'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        expected_unique_makes = sorted(list({'Honda', 'Yamaha', 'Suzuki'}))
        self.assertEqual(data['unique_makes_for_filter'], expected_unique_makes)

        response_used = self.client.get(reverse('inventory:ajax-get-motorcycle-list'), {'condition_slug': 'used'})
        self.assertEqual(response_used.status_code, 200)
        data_used = response_used.json()
                                                                                                   
        expected_unique_makes_used_raw = {
            'Honda', 'Kawasaki', 'Yamaha', 'Ducati', 'BMW', 'KTM'
        }
        for i in range(1, 15):
            expected_unique_makes_used_raw.add(f'PaginatedBrand{i}')
        self.assertEqual(set(data_used['unique_makes_for_filter']), expected_unique_makes_used_raw)


    def test_serialization_of_price(self):
        """
        Test that Decimal fields (price) are correctly converted to float.
        """
        response_honda_cbr = self.client.get(reverse('inventory:ajax-get-motorcycle-list'), {'condition_slug': 'all', 'brand': 'Honda', 'model': 'CBR1000RR'})
        self.assertEqual(response_honda_cbr.status_code, 200)
        data_honda_cbr = response_honda_cbr.json()
        self.assertEqual(len(data_honda_cbr['motorcycles']), 1)                                   
        moto_data_honda_cbr = data_honda_cbr['motorcycles'][0]
        self.assertEqual(moto_data_honda_cbr['model'], 'CBR1000RR')                              
        self.assertIsInstance(moto_data_honda_cbr['price'], float)
        self.assertEqual(moto_data_honda_cbr['price'], 15000.0)

