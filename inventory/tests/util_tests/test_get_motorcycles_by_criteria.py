# inventory/tests/test_utils/test_get_motorcycles_by_criteria.py

from django.test import TestCase
from decimal import Decimal
import datetime
from inventory.models import Motorcycle
from inventory.utils.get_motorcycles_by_criteria import get_motorcycles_by_criteria
from ..test_helpers.model_factories import MotorcycleFactory, MotorcycleConditionFactory

class GetMotorcyclesByCriteriaTest(TestCase):
    """
    Tests for the get_motorcycles_by_criteria utility function.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up various conditions and motorcycles for all tests in this class,
        covering different brands, years, prices, engine sizes, and conditions.
        To ensure deterministic ordering by date_posted, we'll create them
        and then explicitly set the date_posted and save.
        """
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
            )
            # Manually set date_posted to ensure unique, predictable timestamps
            moto.date_posted = base_time_setup + datetime.timedelta(seconds=delta_seconds)
            moto.save()
            delta_seconds += 1 # Increment for the next motorcycle
            return moto

        # Motorcycles will be created in this order, and their date_posted will be updated sequentially.
        # So, when sorted by '-date_posted', the ones created later in this sequence will appear first.

        # Order of creation (and thus ascending date_posted)
        cls.honda_new = create_and_set_date('Honda', 'CBR', 2023, Decimal('15000.00'), 1000, [cls.condition_new.name])
        cls.yamaha_new = create_and_set_date('Yamaha', 'YZF', 2022, Decimal('12000.00'), 800, [cls.condition_new.name])
        cls.suzuki_new = create_and_set_date('Suzuki', 'GSXR', 2023, Decimal('13000.00'), 750, [cls.condition_new.name])
        cls.honda_used = create_and_set_date('Honda', 'CRF', 2020, Decimal('8000.00'), 650, [cls.condition_used.name])
        cls.kawasaki_used = create_and_set_date('Kawasaki', 'Ninja', 2019, Decimal('7000.00'), 400, [cls.condition_used.name])
        cls.yamaha_demo = create_and_set_date('Yamaha', 'MT', 2021, Decimal('9500.00'), 900, [cls.condition_demo.name])
        cls.ducati_demo = create_and_set_date('Ducati', 'Monster', 2021, Decimal('11000.00'), 1100, [cls.condition_demo.name])
        cls.harley_hire = create_and_set_date('Harley-Davidson', 'Fat Boy', 2018, Decimal('5000.00'), 1600, [cls.condition_hire.name], daily_hire_rate=Decimal('50.00'), hourly_hire_rate=Decimal('10.00'))
        cls.bmw_hire_used = create_and_set_date('BMW', 'GS', 2020, Decimal('10000.00'), 1250, [cls.condition_used.name, cls.condition_hire.name], daily_hire_rate=Decimal('100.00'), hourly_hire_rate=Decimal('20.00'))

        # The expected order for default (`-date_posted`) will be the reverse of the creation order above.
        cls.expected_default_order_full_dataset = [
            cls.bmw_hire_used,
            cls.harley_hire,
            cls.ducati_demo,
            cls.yamaha_demo,
            cls.kawasaki_used,
            cls.honda_used,
            cls.suzuki_new,
            cls.yamaha_new,
            cls.honda_new,
        ]

    def test_get_motorcycles_no_filters(self):
        """
        Test that all motorcycles are returned when no filters are applied,
        and they are correctly ordered by date_posted descending.
        """
        queryset = get_motorcycles_by_criteria()
        self.assertEqual(queryset.count(), 9)
        self.assertQuerySetEqual(queryset, self.expected_default_order_full_dataset, ordered=True)

    def test_filter_by_new_condition_slug(self):
        """
        Test filtering by 'new' condition slug.
        """
        queryset = get_motorcycles_by_criteria(condition_slug='new')
        self.assertEqual(queryset.count(), 3)
        self.assertIn(self.honda_new, queryset)
        self.assertIn(self.yamaha_new, queryset)
        self.assertIn(self.suzuki_new, queryset)
        self.assertNotIn(self.honda_used, queryset)
        self.assertNotIn(self.yamaha_demo, queryset)

    def test_filter_by_used_condition_slug(self):
        """
        Test filtering by 'used' condition slug, which should include 'demo'.
        """
        queryset = get_motorcycles_by_criteria(condition_slug='used')
        self.assertEqual(queryset.count(), 5) # honda_used, kawasaki_used, yamaha_demo, ducati_demo, bmw_hire_used (as it has 'used' condition)
        self.assertIn(self.honda_used, queryset)
        self.assertIn(self.kawasaki_used, queryset)
        self.assertIn(self.yamaha_demo, queryset)
        self.assertIn(self.ducati_demo, queryset)
        self.assertIn(self.bmw_hire_used, queryset)
        self.assertNotIn(self.honda_new, queryset) # Should not include new bikes
        self.assertNotIn(self.harley_hire, queryset) # Should not include pure hire bikes

    def test_filter_by_specific_condition_slug(self):
        """
        Test filtering by a specific condition slug like 'hire'.
        """
        queryset = get_motorcycles_by_criteria(condition_slug='hire')
        self.assertEqual(queryset.count(), 2)
        self.assertIn(self.harley_hire, queryset)
        self.assertIn(self.bmw_hire_used, queryset) # BMW has both used and hire
        self.assertNotIn(self.honda_new, queryset)

    def test_filter_by_brand(self):
        """
        Test filtering by brand name.
        """
        queryset = get_motorcycles_by_criteria(brand='Honda')
        self.assertEqual(queryset.count(), 2)
        self.assertIn(self.honda_new, queryset)
        self.assertIn(self.honda_used, queryset)

    def test_filter_by_model_contains(self):
        """
        Test filtering by model name (case-insensitive contains).
        """
        # Models containing 'R': CBR, GSXR, CRF, Monster
        queryset = get_motorcycles_by_criteria(model='R')
        self.assertEqual(queryset.count(), 4) # Corrected count from 3 to 4
        self.assertIn(self.honda_new, queryset)
        self.assertIn(self.suzuki_new, queryset)
        self.assertIn(self.honda_used, queryset) # CRF contains 'R'
        self.assertIn(self.ducati_demo, queryset) # 'Monster' contains 'R'
        self.assertNotIn(self.yamaha_new, queryset)

        queryset_ninja = get_motorcycles_by_criteria(model='ninja') # Case-insensitive
        self.assertEqual(queryset_ninja.count(), 1)
        self.assertIn(self.kawasaki_used, queryset_ninja)

    def test_filter_by_year_range(self):
        """
        Test filtering by minimum and maximum year.
        """
        queryset = get_motorcycles_by_criteria(year_min=2021, year_max=2022)
        self.assertEqual(queryset.count(), 3) # Yamaha New (2022), Yamaha Demo (2021), Ducati Demo (2021)
        self.assertIn(self.yamaha_new, queryset)
        self.assertIn(self.yamaha_demo, queryset)
        self.assertIn(self.ducati_demo, queryset)
        self.assertNotIn(self.honda_new, queryset) # 2023
        self.assertNotIn(self.honda_used, queryset) # 2020

        queryset_min_only = get_motorcycles_by_criteria(year_min=2022)
        self.assertEqual(queryset_min_only.count(), 3) # Honda New (2023), Yamaha New (2022), Suzuki New (2023)
        self.assertIn(self.honda_new, queryset_min_only)
        self.assertIn(self.yamaha_new, queryset_min_only)
        self.assertIn(self.suzuki_new, queryset_min_only)

    def test_filter_by_price_range(self):
        """
        Test filtering by minimum and maximum price.
        """
        # Price range from 9000 to 13000
        queryset = get_motorcycles_by_criteria(price_min=Decimal('9000.00'), price_max=Decimal('13000.00'))
        # Expected: Yamaha New (12000), Suzuki New (13000), Yamaha Demo (9500), Ducati Demo (11000), BMW (10000)
        self.assertEqual(queryset.count(), 5)
        self.assertIn(self.yamaha_new, queryset)
        self.assertIn(self.suzuki_new, queryset)
        self.assertIn(self.yamaha_demo, queryset)
        self.assertIn(self.ducati_demo, queryset)
        self.assertIn(self.bmw_hire_used, queryset)
        self.assertNotIn(self.honda_new, queryset) # 15000
        self.assertNotIn(self.honda_used, queryset) # 8000

        # Max price only
        queryset_max_only = get_motorcycles_by_criteria(price_max=Decimal('7000.00'))
        # Expected: Kawasaki Used (7000), Harley Hire (5000)
        self.assertEqual(queryset_max_only.count(), 2)
        self.assertIn(self.kawasaki_used, queryset_max_only)
        self.assertIn(self.harley_hire, queryset_max_only)

    def test_filter_by_engine_size_range(self):
        """
        Test filtering by minimum and maximum engine size.
        """
        # Engine range from 700cc to 1000cc
        queryset = get_motorcycles_by_criteria(engine_min_cc=700, engine_max_cc=1000)
        # Expected: Honda New (1000), Yamaha New (800), Suzuki New (750), Yamaha Demo (900)
        self.assertEqual(queryset.count(), 4)
        self.assertIn(self.honda_new, queryset)
        self.assertIn(self.yamaha_new, queryset)
        self.assertIn(self.suzuki_new, queryset)
        self.assertIn(self.yamaha_demo, queryset)
        self.assertNotIn(self.honda_used, queryset) # 650
        self.assertNotIn(self.ducati_demo, queryset) # 1100

    def test_combined_filters(self):
        """
        Test a combination of multiple filters.
        """
        # Used or demo bikes, Honda brand, year 2020-2021, price max 9000
        queryset = get_motorcycles_by_criteria(
            condition_slug='used',
            brand='Honda',
            year_min=2020,
            year_max=2021,
            price_max=Decimal('9000.00')
        )
        # Expected: Only honda_used (2020, 8000)
        self.assertEqual(queryset.count(), 1)
        self.assertIn(self.honda_used, queryset)
        self.assertNotIn(self.honda_new, queryset) # New condition
        self.assertNotIn(self.yamaha_demo, queryset) # Not Honda

        # New bikes, engine size >= 800cc
        queryset_new_large_engine = get_motorcycles_by_criteria(
            condition_slug='new',
            engine_min_cc=800
        )
        # Expected: Honda New (1000), Yamaha New (800)
        self.assertEqual(queryset_new_large_engine.count(), 2)
        self.assertIn(self.honda_new, queryset_new_large_engine)
        self.assertIn(self.yamaha_new, queryset_new_large_engine)
        self.assertNotIn(self.suzuki_new, queryset_new_large_engine) # 750cc

    def test_ordering_price_low_to_high(self):
        """
        Test ordering by price from low to high.
        """
        queryset = get_motorcycles_by_criteria(order='price_low_to_high')
        # Filter out bikes with None price for consistent ordering test if any exist
        # (Our factories ensure prices are set for these tests)
        prices = [bike.price for bike in queryset if bike.price is not None]
        sorted_prices = sorted(prices)
        self.assertEqual(prices, sorted_prices)

    def test_ordering_price_high_to_low(self):
        """
        Test ordering by price from high to low.
        """
        queryset = get_motorcycles_by_criteria(order='price_high_to_low')
        prices = [bike.price for bike in queryset if bike.price is not None]
        sorted_prices = sorted(prices, reverse=True)
        self.assertEqual(prices, sorted_prices)

    def test_ordering_age_new_to_old(self):
        """
        Test ordering by year (age) new to old.
        """
        queryset = get_motorcycles_by_criteria(order='age_new_to_old')
        # Get (year, date_posted) tuples to check correct secondary sorting
        years_and_dates = [(bike.year, bike.date_posted) for bike in queryset]
        # Sort manually to compare
        expected_sorted = sorted(years_and_dates, key=lambda x: (x[0], x[1]), reverse=True)
        self.assertEqual(years_and_dates, expected_sorted)

    def test_ordering_age_old_to_new(self):
        """
        Test ordering by year (age) old to new.
        """
        queryset = get_motorcycles_by_criteria(order='age_old_to_new')
        years_and_dates = [(bike.year, bike.date_posted) for bike in queryset]
        expected_sorted = sorted(years_and_dates, key=lambda x: (x[0], x[1]))
        self.assertEqual(years_and_dates, expected_sorted)

    def test_ordering_default_date_posted(self):
        """
        Test default ordering when no order is specified.
        This test uses newly created motorcycles to isolate from setUpTestData
        and explicitly controls date_posted for predictable ordering.
        """
        # Create motorcycles with distinct date_posted for predictable default ordering
        # Using a distinct base time and incrementing for this specific test
        base_test_time = datetime.datetime(2024, 6, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)

        test_moto_c = MotorcycleFactory(brand='DefaultOrderTest', model='C', year=2019, engine_size=400)
        test_moto_c.date_posted = base_test_time + datetime.timedelta(seconds=0) # Oldest
        test_moto_c.save()

        test_moto_a = MotorcycleFactory(brand='DefaultOrderTest', model='A', year=2020, engine_size=500)
        test_moto_a.date_posted = base_test_time + datetime.timedelta(seconds=1)
        test_moto_a.save()

        test_moto_b = MotorcycleFactory(brand='DefaultOrderTest', model='B', year=2021, engine_size=600)
        test_moto_b.date_posted = base_test_time + datetime.timedelta(seconds=2) # Newest
        test_moto_b.save()

        queryset = get_motorcycles_by_criteria(brand='DefaultOrderTest')
        # Expected order: test_moto_b (latest date_posted), then test_moto_a, then test_moto_c (oldest date_posted)
        expected_order = [test_moto_b, test_moto_a, test_moto_c]
        self.assertQuerySetEqual(queryset, expected_order, ordered=True)


    def test_no_results_found(self):
        """
        Test that an empty queryset is returned when no motorcycles match.
        """
        queryset = get_motorcycles_by_criteria(brand='NonExistentBrand')
        self.assertEqual(queryset.count(), 0)
        self.assertQuerySetEqual(queryset, [])

