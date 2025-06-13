# inventory/tests/test_ajax/test_ajax_get_motorcycle_list.py

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

        # Create common condition objects
        cls.condition_new = MotorcycleConditionFactory(name='new', display_name='New')
        cls.condition_used = MotorcycleConditionFactory(name='used', display_name='Used')
        cls.condition_demo = MotorcycleConditionFactory(name='demo', display_name='Demo')
        cls.condition_hire = MotorcycleConditionFactory(name='hire', display_name='For Hire')

        # Using a base time and incrementing seconds to ensure unique date_posted values
        base_time_setup = datetime.datetime(2023, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
        delta_seconds = 0

        # Helper function to create and set date_posted explicitly
        def create_and_set_date(brand, model, year, price, engine_size, conditions, daily_hire_rate=None, hourly_hire_rate=None):
            nonlocal delta_seconds
            moto = MotorcycleFactory(
                brand=brand,
                model=model,
                year=year,
                price=price,
                engine_size=engine_size,
                conditions=conditions,
                daily_hire_rate=daily_hire_rate,
                hourly_hire_rate=hourly_hire_rate,
                is_available=True, # Ensure available for display
            )
            moto.date_posted = base_time_setup + datetime.timedelta(seconds=delta_seconds)
            moto.save()
            delta_seconds += 1
            return moto

        # Create motorcycles with distinct properties and controlled date_posted
        # (Order of creation here is important for default date_posted ordering tests)
        cls.moto_honda_new_2023 = create_and_set_date('Honda', 'CBR1000RR', 2023, Decimal('15000.00'), 1000, [cls.condition_new.name])
        cls.moto_yamaha_new_2022 = create_and_set_date('Yamaha', 'YZF-R6', 2022, Decimal('12000.00'), 600, [cls.condition_new.name])
        cls.moto_suzuki_new_2023 = create_and_set_date('Suzuki', 'GSX-R750', 2023, Decimal('13000.00'), 750, [cls.condition_new.name])
        cls.moto_honda_used_2020 = create_and_set_date('Honda', 'CRF250L', 2020, Decimal('8000.00'), 250, [cls.condition_used.name])
        cls.moto_kawasaki_used_2019 = create_and_set_date('Kawasaki', 'Ninja 400', 2019, Decimal('7000.00'), 400, [cls.condition_used.name])
        cls.moto_yamaha_demo_2021 = create_and_set_date('Yamaha', 'MT-07', 2021, Decimal('9500.00'), 700, [cls.condition_demo.name])
        cls.moto_ducati_demo_2021 = create_and_set_date('Ducati', 'Monster 821', 2021, Decimal('11000.00'), 800, [cls.condition_demo.name])
        cls.moto_harley_hire_2018 = create_and_set_date('Harley-Davidson', 'Fat Boy', 2018, None, 1600, [cls.condition_hire.name], daily_hire_rate=Decimal('150.00'))
        cls.moto_bmw_used_hire_2020 = create_and_set_date('BMW', 'R1250GS', 2020, Decimal('10500.00'), 1250, [cls.condition_used.name, cls.condition_hire.name], daily_hire_rate=Decimal('180.00'))
        cls.moto_ktm_used_2022 = create_and_set_date('KTM', 'Duke 390', 2022, Decimal('6000.00'), 390, [cls.condition_used.name])


        # Motorcycles specifically for pagination tests (14 more bikes)
        for i in range(1, 15):
            create_and_set_date(
                brand=f'PaginatedBrand{i}',
                model=f'PModel{i}',
                year=2020,
                price=Decimal(f'{5000 + i*100}.00'),
                engine_size=500,
                conditions=[cls.condition_used.name]
            )
        # Total motorcycles: 10 original + 14 paginated = 24

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

        # Check total number of motorcycles (first page)
        self.assertEqual(len(data['motorcycles']), 10) # Paginate by 10
        self.assertEqual(data['page_obj']['number'], 1)
        self.assertTrue(data['page_obj']['has_next'])

        # Verify default ordering (latest date_posted first)
        all_motorcycles_in_db = list(Motorcycle.objects.all().order_by('-date_posted'))
        expected_first_page_ids = [m.id for m in all_motorcycles_in_db[:10]]
        returned_motorcycle_ids = [m['id'] for m in data['motorcycles']]
        self.assertEqual(returned_motorcycle_ids, expected_first_page_ids)

        # Check unique makes (should be all unique makes across all motorcycles)
        expected_unique_makes = {
            'Honda', 'Yamaha', 'Suzuki', 'Kawasaki', 'Ducati', 'Harley-Davidson',
            'BMW', 'KTM'
        }
        # Add paginated brands dynamically
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
        self.assertFalse(data['page_obj']['has_next']) # Only 3 new bikes, should fit on one page

    def test_filter_by_condition_slug_used(self):
        """
        Test filtering by 'used' condition slug (includes 'demo').
        """
        response = self.client.get(reverse('inventory:ajax-get-motorcycle-list'), {'condition_slug': 'used'})
        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Count of used/demo bikes: honda_used, kawasaki_used, yamaha_demo, ducati_demo, bmw_used_hire, KTM + 14 paginated bikes
        # = 1 + 1 + 1 + 1 + 1 + 1 + 14 = 20 bikes
        self.assertEqual(len(data['motorcycles']), 10) # Still paginated to 10
        self.assertTrue(data['page_obj']['has_next'])
        self.assertEqual(data['page_obj']['num_pages'], 2)

        total_used_motorcycles = Motorcycle.objects.filter(
            conditions__name__in=['used', 'demo']
        ).distinct().count()
        self.assertEqual(total_used_motorcycles, 20) # <--- MODIFIED: Changed 19 to 20


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
        self.assertFalse(data['page_obj']['has_next']) # Only 2 Hondas, no pagination needed

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

        # Expected: Yamaha New (2022), Yamaha Demo (2021), Ducati Demo (2021), KTM Used (2022)
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

        # Expected: Honda Used (8000), Yamaha Demo (9500), Ducati Demo (11000), BMW Used/Hire (10500), Yamaha New (12000)
        # Plus any PaginatedBrandX that falls into this range.
        expected_queryset = Motorcycle.objects.filter(
            price__gte=Decimal('8000.00'),
            price__lte=Decimal('12000.00')
        ).exclude(price__isnull=True) # Exclude bikes with null price from calculation
        self.assertEqual(len(data['motorcycles']), expected_queryset.count())
        returned_titles = {m['title'] for m in data['motorcycles']}
        self.assertIn(self.moto_honda_used_2020.title, returned_titles)
        self.assertIn(self.moto_yamaha_new_2022.title, returned_titles)
        self.assertIn(self.moto_yamaha_demo_2021.title, returned_titles)
        self.assertIn(self.moto_ducati_demo_2021.title, returned_titles)
        self.assertIn(self.moto_bmw_used_hire_2020.title, returned_titles)


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

        # Expected: Yamaha New (600), Suzuki New (750), Yamaha Demo (700), Ducati Demo (800)
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

        # Expected: moto_kawasaki_used_2019 (Ninja 400) - only one matches all these
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
        # Check if prices are truly ascending for available items
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

        # Total bikes: 24 (10 original + 14 paginated).
        # Page 1: 10 bikes, Page 2: 10 bikes, Page 3: 4 bikes.
        self.assertEqual(len(data['motorcycles']), 10)
        self.assertEqual(data['page_obj']['number'], 2)
        self.assertTrue(data['page_obj']['has_previous'])
        self.assertTrue(data['page_obj']['has_next'])

        # Verify the IDs are different from the first page (fetched by default ordering)
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
            'page': 100 # A very high page number
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Total bikes: 24. Paginator by 10. Last page is page 3, with 4 bikes.
        self.assertEqual(len(data['motorcycles']), 4) # <--- MODIFIED: Changed 3 to 4
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
        # For 'used', it should include brands from 'used' and 'demo' conditions + paginated brands
        expected_unique_makes_used_raw = {
            'Honda', 'Kawasaki', 'Yamaha', 'Ducati', 'BMW', 'KTM'
        }
        for i in range(1, 15):
            expected_unique_makes_used_raw.add(f'PaginatedBrand{i}')
        self.assertEqual(set(data_used['unique_makes_for_filter']), expected_unique_makes_used_raw)


    def test_serialization_of_price_and_hire_rates(self):
        """
        Test that Decimal fields (price, daily_hire_rate) are correctly converted to float.
        Also, ensure that the correct motorcycle is returned when filtering by model.
        """
        # Test Harley-Davidson (no sale price, has hire rate)
        response_harley = self.client.get(reverse('inventory:ajax-get-motorcycle-list'), {'condition_slug': 'all', 'brand': 'Harley-Davidson'})
        self.assertEqual(response_harley.status_code, 200)
        data_harley = response_harley.json()
        self.assertEqual(len(data_harley['motorcycles']), 1)
        moto_data_harley = data_harley['motorcycles'][0]
        self.assertEqual(moto_data_harley['brand'], 'Harley-Davidson')
        self.assertIsNone(moto_data_harley['price'])
        self.assertIsInstance(moto_data_harley['daily_hire_rate'], float)
        self.assertEqual(moto_data_harley['daily_hire_rate'], 150.0)

        # Test Honda CBR1000RR (has sale price, no hire rate)
        response_honda_cbr = self.client.get(reverse('inventory:ajax-get-motorcycle-list'), {'condition_slug': 'all', 'brand': 'Honda', 'model': 'CBR1000RR'})
        self.assertEqual(response_honda_cbr.status_code, 200)
        data_honda_cbr = response_honda_cbr.json()
        self.assertEqual(len(data_honda_cbr['motorcycles']), 1) # Ensure only one bike is returned
        moto_data_honda_cbr = data_honda_cbr['motorcycles'][0]
        self.assertEqual(moto_data_honda_cbr['model'], 'CBR1000RR') # Verify the model is correct
        self.assertIsInstance(moto_data_honda_cbr['price'], float)
        self.assertEqual(moto_data_honda_cbr['price'], 15000.0) # <--- MODIFIED: Expected price is 15000.0
        self.assertIsNone(moto_data_honda_cbr['daily_hire_rate'])

