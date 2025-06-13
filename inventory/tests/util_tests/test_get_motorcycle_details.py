# inventory/tests/test_utils/test_get_motorcycle_details.py

from django.test import TestCase
from inventory.models import Motorcycle, MotorcycleCondition
from ..test_helpers.model_factories import MotorcycleFactory, MotorcycleConditionFactory
from inventory.utils.get_motorcycle_details import get_motorcycle_details
from django.db import connection
from decimal import Decimal

class GetMotorcycleDetailsUtilityTest(TestCase):
    """
    Tests for the get_motorcycle_details utility function.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up test data for the utility function.
        """
        cls.condition_new = MotorcycleConditionFactory(name='new', display_name='New')
        cls.condition_used = MotorcycleConditionFactory(name='used', display_name='Used')
        cls.condition_demo = MotorcycleConditionFactory(name='demo', display_name='Demo')

        cls.moto_simple = MotorcycleFactory(
            brand='TestBrand', model='TestModel', year=2020,
            engine_size=500, price=Decimal('5000.00'),
            conditions=[cls.condition_new.name]
        )
        cls.moto_complex = MotorcycleFactory(
            brand='AnotherBrand', model='AnotherModel', year=2022,
            engine_size=1000, price=Decimal('10000.00'),
            conditions=[cls.condition_used.name, cls.condition_demo.name]
        )
        # Explicitly create a motorcycle with no conditions
        cls.moto_no_conditions = MotorcycleFactory(
            brand='NoCond', model='NoCond', year=2020, engine_size=300, price=Decimal('3000.00'),
            conditions=[] # <--- ADDED THIS TO ENSURE NO CONDITIONS ARE SET
        )


    def test_get_motorcycle_details_success(self):
        """
        Test that the utility successfully retrieves a motorcycle by PK.
        """
        motorcycle = get_motorcycle_details(self.moto_simple.pk)
        self.assertIsNotNone(motorcycle)
        self.assertEqual(motorcycle.pk, self.moto_simple.pk)
        self.assertEqual(motorcycle.brand, 'TestBrand')
        condition_names = {c.name for c in motorcycle.conditions.all()}
        self.assertIn('new', condition_names)

    def test_get_motorcycle_details_not_found(self):
        """
        Test that the utility returns None if the motorcycle is not found.
        """
        non_existent_pk = self.moto_simple.pk + 999
        motorcycle = get_motorcycle_details(non_existent_pk)
        self.assertIsNone(motorcycle)

    def test_get_motorcycle_details_prefetch_related(self):
        """
        Test that prefetch_related reduces queries when accessing related conditions.
        """
        # Test for a motorcycle with multiple conditions
        with self.assertNumQueries(2):
            motorcycle = get_motorcycle_details(self.moto_complex.pk)
            prefetched_condition_names = {c.name for c in motorcycle.conditions.all()}
            self.assertEqual(len(prefetched_condition_names), 2)
            self.assertIn('used', prefetched_condition_names)
            self.assertIn('demo', prefetched_condition_names)

        # Test for a motorcycle with no conditions
        with self.assertNumQueries(2):
            motorcycle_no_cond = get_motorcycle_details(self.moto_no_conditions.pk) # Use the pre-created instance
            self.assertEqual(motorcycle_no_cond.conditions.count(), 0) # This should now pass


    def test_get_motorcycle_details_invalid_pk_type(self):
        """
        Test handling of invalid PK type (e.g., non-integer), which should be caught.
        """
        motorcycle = get_motorcycle_details("invalid_pk")
        self.assertIsNone(motorcycle)
