# inventory/tests/test_views/test_motorcycle_list_view.py

from django.test import TestCase, Client
from django.urls import reverse
from decimal import Decimal
import datetime

from inventory.models import Motorcycle, MotorcycleCondition
from ...test_helpers.model_factories import MotorcycleFactory, MotorcycleConditionFactory

class MotorcycleListViewTest(TestCase):
    """
    Tests for the MotorcycleListView.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up various motorcycles with different conditions and properties
        to test the ListView's context and queryset filtering.
        We explicitly control `date_posted` for predictable default ordering.
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

        # Create a set of motorcycles for different conditions and general testing
        # These will dictate the initial unique_makes and queryset for each view
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

        # Create enough motorcycles for pagination tests (total 24 for 3 pages of 10)
        # 10 existing + 14 more
        for i in range(1, 15):
            create_and_set_date(
                brand=f'PaginatedBrand{i}',
                model=f'PModel{i}',
                year=2020,
                price=Decimal(f'{5000 + i*100}.00'),
                engine_size=500,
                conditions=[cls.condition_used.name]
            )
        cls.total_motorcycles = Motorcycle.objects.count() # Should be 24

    def test_all_motorcycles_page_renders_correctly(self):
        """
        Test that the '/motorcycles/' (all) page renders correctly,
        shows the first page of results, and has correct context.
        """
        response = self.client.get(reverse('inventory:all')) # Using named URL for 'all'
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'inventory/motorcycle_list.html')

        # Check context data
        self.assertIn('motorcycles', response.context)
        self.assertIn('page_obj', response.context)
        self.assertIn('unique_makes', response.context)
        self.assertIn('current_condition_slug', response.context)
        self.assertIn('page_title', response.context)
        self.assertIn('years', response.context)

        # Verify page_obj and pagination
        page_obj = response.context['page_obj']
        self.assertEqual(page_obj.number, 1)
        self.assertEqual(len(page_obj.object_list), 10) # Paginate by 10
        self.assertTrue(page_obj.has_next())
        self.assertEqual(page_obj.paginator.num_pages, 3) # 24 bikes / 10 per page = 3 pages

        # Verify initial queryset is as expected (default order: -date_posted)
        expected_first_page_motorcycles = list(Motorcycle.objects.all().order_by('-date_posted')[:10])
        self.assertQuerySetEqual(page_obj.object_list, expected_first_page_motorcycles)

        # Verify unique_makes
        expected_all_makes = set(Motorcycle.objects.values_list('brand', flat=True).distinct())
        self.assertEqual(set(response.context['unique_makes']), expected_all_makes)

        # Verify other context variables
        self.assertEqual(response.context['current_condition_slug'], 'all')
        self.assertEqual(response.context['page_title'], 'All Motorcycles')
        self.assertIsInstance(response.context['years'], list)
        self.assertGreater(len(response.context['years']), 0) # Should contain years

    def test_new_motorcycles_page_renders_correctly(self):
        """
        Test that the '/motorcycles/new/' page renders correctly
        with only 'new' motorcycles and appropriate context.
        """
        response = self.client.get(reverse('inventory:new')) # Using named URL for 'new'
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'inventory/motorcycle_list.html')

        page_obj = response.context['page_obj']
        self.assertEqual(len(page_obj.object_list), 3) # Only 3 new bikes
        self.assertFalse(page_obj.has_next()) # No next page

        # Verify queryset
        expected_new_motorcycles = list(Motorcycle.objects.filter(conditions__name='new').order_by('-date_posted'))
        self.assertQuerySetEqual(page_obj.object_list, expected_new_motorcycles)

        # Verify unique_makes for 'new' condition
        expected_new_makes = {'Honda', 'Yamaha', 'Suzuki'}
        self.assertEqual(set(response.context['unique_makes']), expected_new_makes)

        self.assertEqual(response.context['current_condition_slug'], 'new')
        self.assertEqual(response.context['page_title'], 'New Motorcycles')

    def test_used_motorcycles_page_renders_correctly(self):
        """
        Test that the '/motorcycles/used/' page renders correctly
        with 'used' and 'demo' motorcycles and appropriate context.
        """
        response = self.client.get(reverse('inventory:used')) # Using named URL for 'used'
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'inventory/motorcycle_list.html')

        page_obj = response.context['page_obj']
        # 6 initial used/demo bikes + 14 paginated = 20 total. First page should have 10.
        self.assertEqual(len(page_obj.object_list), 10)
        self.assertTrue(page_obj.has_next())
        self.assertEqual(page_obj.paginator.num_pages, 2)

        # Verify queryset (should include 'used' and 'demo')
        used_demo_bikes = Motorcycle.objects.filter(
            conditions__name__in=['used', 'demo']
        ).distinct().order_by('-date_posted')
        expected_used_first_page_motorcycles = list(used_demo_bikes[:10])
        self.assertQuerySetEqual(page_obj.object_list, expected_used_first_page_motorcycles)


        # Verify unique_makes for 'used' condition (includes 'used' and 'demo' brands + paginated brands)
        expected_used_makes = {
            'Honda', 'Kawasaki', 'Yamaha', 'Ducati', 'BMW', 'KTM'
        }
        for i in range(1, 15):
            expected_used_makes.add(f'PaginatedBrand{i}')
        self.assertEqual(set(response.context['unique_makes']), expected_used_makes)

        self.assertEqual(response.context['current_condition_slug'], 'used')
        self.assertEqual(response.context['page_title'], 'Used Motorcycles')

    def test_pagination_second_page(self):
        """
        Test that requesting the second page of 'all' motorcycles works.
        """
        response = self.client.get(reverse('inventory:all'), {'page': 2})
        self.assertEqual(response.status_code, 200)

        page_obj = response.context['page_obj']
        self.assertEqual(page_obj.number, 2)
        self.assertEqual(len(page_obj.object_list), 10) # Second page should also have 10
        self.assertTrue(page_obj.has_previous())
        self.assertTrue(page_obj.has_next())
        self.assertEqual(page_obj.paginator.num_pages, 3)

        # Verify the motorcycles on the second page
        all_motorcycles_in_db = list(Motorcycle.objects.all().order_by('-date_posted'))
        expected_second_page_motorcycles = all_motorcycles_in_db[10:20]
        self.assertQuerySetEqual(page_obj.object_list, expected_second_page_motorcycles)


    def test_pagination_last_page(self):
        """
        Test that requesting the last page of 'all' motorcycles works.
        """
        response = self.client.get(reverse('inventory:all'), {'page': 3})
        self.assertEqual(response.status_code, 200)

        page_obj = response.context['page_obj']
        self.assertEqual(page_obj.number, 3)
        self.assertEqual(len(page_obj.object_list), 4) # Last page (24 total, 10 per page) should have 4 bikes
        self.assertTrue(page_obj.has_previous())
        self.assertFalse(page_obj.has_next()) # No next page
        self.assertEqual(page_obj.paginator.num_pages, 3)

        # Verify the motorcycles on the last page
        all_motorcycles_in_db = list(Motorcycle.objects.all().order_by('-date_posted'))
        expected_last_page_motorcycles = all_motorcycles_in_db[20:24]
        self.assertQuerySetEqual(page_obj.object_list, expected_last_page_motorcycles)


    def test_pagination_invalid_page_number(self):
        """
        Test that an invalid page number defaults to the first page.
        (Django's Paginator raises EmptyPage for out of range, which ListView handles)
        """
        response = self.client.get(reverse('inventory:all'), {'page': 'abc'})
        self.assertEqual(response.status_code, 200)
        page_obj = response.context['page_obj']
        self.assertEqual(page_obj.number, 1) # Should default to page 1

    def test_pagination_out_of_range_page_number(self):
        """
        Test that an out-of-range page number returns the last page.
        (Django's Paginator handles this by returning the last page if EmptyPage is caught)
        """
        response = self.client.get(reverse('inventory:all'), {'page': 999}) # Very large page number
        self.assertEqual(response.status_code, 200)
        page_obj = response.context['page_obj']
        self.assertEqual(page_obj.number, page_obj.paginator.num_pages) # Should be the last page (3)
        self.assertEqual(len(page_obj.object_list), 4) # Last page has 4 bikes

    def test_no_motorcycles_found_display(self):
        """
        Test the display when no motorcycles are found for a given condition.
        """
        # Create a condition with no associated motorcycles
        condition_empty = MotorcycleConditionFactory(name='empty', display_name='Empty Condition')
        response = self.client.get(reverse('inventory:all'), {'condition_slug': condition_empty.name}) # Pass as query param for testing
        # NOTE: For the ListView, 'condition_slug' is usually passed as a URL kwarg,
        # but for direct testing with the client, we can simulate.
        # However, the current URL structure for ListView relies on URL kwargs.
        # So we'll test a scenario where the queryset genuinely becomes empty.
        # This will be better done by dynamically creating a view with a very specific condition slug.

        # Let's override the queryset for this specific test case without changing the URL structure
        # A simpler way is to fetch a list with a non-existent brand, which will yield no results.
        response = self.client.get(reverse('inventory:all') + '?brand=NonExistent')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No motorcycles match the current criteria.')
        self.assertEqual(len(response.context['motorcycles']), 0)
        self.assertFalse(response.context['page_obj'].object_list)
