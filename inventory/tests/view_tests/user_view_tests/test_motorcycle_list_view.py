# inventory/tests/test_views/test_motorcycle_list_view.py

from django.test import TestCase, Client
from django.urls import reverse
from decimal import Decimal
import datetime

# We still import these for setUpTestData, but note that the ListView
# will no longer actively query them directly based on URL params for initial display.
from inventory.models import Motorcycle, MotorcycleCondition
from ...test_helpers.model_factories import MotorcycleFactory, MotorcycleConditionFactory

class MotorcycleListViewTest(TestCase):
    """
    Tests for the MotorcycleListView's initial render and context.
    This view now primarily serves the static shell and initial context,
    with actual motorcycle data loaded via AJAX.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up common condition objects and some motorcycles.
        These motorcycles are used by the AJAX endpoint (not directly by this view's initial render).
        """
        cls.client = Client()

        # Create common condition objects (still needed for filter dropdowns)
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
        # These are relevant for the AJAX endpoint tests, not the ListView's initial render.
        create_and_set_date('Honda', 'CBR1000RR', 2023, Decimal('15000.00'), 1000, [cls.condition_new.name])
        create_and_set_date('Yamaha', 'YZF-R6', 2022, Decimal('12000.00'), 600, [cls.condition_new.name])
        create_and_set_date('Suzuki', 'GSX-R750', 2023, Decimal('13000.00'), 750, [cls.condition_new.name])

        create_and_set_date('Honda', 'CRF250L', 2020, Decimal('8000.00'), 250, [cls.condition_used.name])
        create_and_set_date('Kawasaki', 'Ninja 400', 2019, Decimal('7000.00'), 400, [cls.condition_used.name])
        create_and_set_date('Yamaha', 'MT-07', 2021, Decimal('9500.00'), 700, [cls.condition_demo.name])
        create_and_set_date('Ducati', 'Monster 821', 2021, Decimal('11000.00'), 800, [cls.condition_demo.name])
        create_and_set_date('Harley-Davidson', 'Fat Boy', 2018, None, 1600, [cls.condition_hire.name], daily_hire_rate=Decimal('150.00'))
        create_and_set_date('BMW', 'R1250GS', 2020, Decimal('10500.00'), 1250, [cls.condition_used.name, cls.condition_hire.name], daily_hire_rate=Decimal('180.00'))
        create_and_set_date('KTM', 'Duke 390', 2022, Decimal('6000.00'), 390, [cls.condition_used.name])

        # Create enough motorcycles for pagination tests (total 24 for 3 pages of 10)
        for i in range(1, 15):
            create_and_set_date(
                brand=f'PaginatedBrand{i}',
                model=f'PModel{i}',
                year=2020,
                price=Decimal(f'{5000 + i*100}.00'),
                engine_size=500,
                conditions=[cls.condition_used.name]
            )

    def test_all_motorcycles_page_renders_empty_initially(self):
        """
        Test that the '/motorcycles/' (all) page renders correctly,
        but initially shows an empty list of motorcycles (as data is loaded via AJAX).
        """
        response = self.client.get(reverse('inventory:all'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'inventory/motorcycle_list.html')

        # Check context data
        self.assertIn('motorcycles', response.context)
        self.assertIn('page_obj', response.context)
        self.assertIn('unique_makes', response.context)
        self.assertIn('current_condition_slug', response.context)
        self.assertIn('page_title', response.context)
        self.assertIn('years', response.context)

        # Verify page_obj and motorcycles are empty as expected for initial render
        page_obj = response.context['page_obj']
        self.assertEqual(len(response.context['motorcycles']), 0)
        self.assertFalse(page_obj.object_list) # object_list should be empty

        # Verify unique_makes (still populated from context)
        expected_all_makes = set(Motorcycle.objects.values_list('brand', flat=True).distinct())
        self.assertEqual(set(response.context['unique_makes']), expected_all_makes)

        # Verify other context variables
        self.assertEqual(response.context['current_condition_slug'], 'all')
        self.assertEqual(response.context['page_title'], 'All Motorcycles')
        self.assertIsInstance(response.context['years'], list)
        self.assertGreater(len(response.context['years']), 0)
        self.assertContains(response, 'No motorcycles match the current criteria.')


    def test_new_motorcycles_page_renders_empty_initially(self):
        """
        Test that the '/motorcycles/new/' page renders correctly,
        but initially shows an empty list of motorcycles.
        """
        response = self.client.get(reverse('inventory:new'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'inventory/motorcycle_list.html')

        page_obj = response.context['page_obj']
        self.assertEqual(len(response.context['motorcycles']), 0)
        self.assertFalse(page_obj.object_list)

        # Verify unique_makes for 'new' condition (still populated from context)
        expected_new_makes = set(Motorcycle.objects.filter(conditions__name='new').values_list('brand', flat=True).distinct())
        self.assertEqual(set(response.context['unique_makes']), expected_new_makes)

        self.assertEqual(response.context['current_condition_slug'], 'new')
        self.assertEqual(response.context['page_title'], 'New Motorcycles')
        self.assertContains(response, 'No motorcycles match the current criteria.')


    def test_used_motorcycles_page_renders_empty_initially(self):
        """
        Test that the '/motorcycles/used/' page renders correctly,
        but initially shows an empty list of motorcycles.
        """
        response = self.client.get(reverse('inventory:used'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'inventory/motorcycle_list.html')

        page_obj = response.context['page_obj']
        self.assertEqual(len(response.context['motorcycles']), 0)
        self.assertFalse(page_obj.object_list)

        # Verify unique_makes for 'used' condition (includes 'used' and 'demo' brands)
        expected_used_makes = set(Motorcycle.objects.filter(
            conditions__name__in=['used', 'demo']
        ).values_list('brand', flat=True).distinct())
        self.assertEqual(set(response.context['unique_makes']), expected_used_makes)

        self.assertEqual(response.context['current_condition_slug'], 'used')
        self.assertEqual(response.context['page_title'], 'Used Motorcycles')
        self.assertContains(response, 'No motorcycles match the current criteria.')


    def test_no_motorcycles_found_display_initial_load(self):
        """
        Test the display when no motorcycles are found for a given condition on initial page load.
        Since the view's queryset is always empty now, this tests the 'no results' message appears.
        """
        response = self.client.get(reverse('inventory:all')) # No filters applied, just initial load
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No motorcycles match the current criteria.')
        self.assertEqual(len(response.context['motorcycles']), 0)
        self.assertFalse(response.context['page_obj'].object_list)

    # Removed tests for direct pagination via URL parameters as that is now handled by AJAX endpoint.
    # E.g., test_pagination_second_page, test_pagination_last_page,
    # test_pagination_invalid_page_number, test_pagination_out_of_range_page_number
    # These tests should now be part of the test suite for inventory.ajax.get_motorcycle_list.
