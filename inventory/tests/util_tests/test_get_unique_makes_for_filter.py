from django.test import TestCase
from inventory.models import MotorcycleCondition
from inventory.utils.get_unique_makes_for_filter import get_unique_makes_for_filter
from ..test_helpers.model_factories import MotorcycleFactory, MotorcycleConditionFactory


class GetUniqueMakesForFilterTest(TestCase):

    @classmethod
    def setUpTestData(cls):

        cls.condition_new = MotorcycleConditionFactory(name="new", display_name="New")
        cls.condition_used = MotorcycleConditionFactory(
            name="used", display_name="Used"
        )
        cls.condition_demo = MotorcycleConditionFactory(
            name="demo", display_name="Demo"
        )

        MotorcycleFactory(
            brand="Honda", model="CBR", conditions=[cls.condition_new.name]
        )
        MotorcycleFactory(
            brand="Yamaha", model="YZF", conditions=[cls.condition_new.name]
        )
        MotorcycleFactory(
            brand="Suzuki", model="GSXR", conditions=[cls.condition_new.name]
        )

        MotorcycleFactory(
            brand="Honda", model="CRF", conditions=[cls.condition_used.name]
        )
        MotorcycleFactory(
            brand="Kawasaki", model="Ninja", conditions=[cls.condition_used.name]
        )

        MotorcycleFactory(
            brand="Yamaha", model="MT", conditions=[cls.condition_demo.name]
        )
        MotorcycleFactory(
            brand="Ducati", model="Monster", conditions=[cls.condition_demo.name]
        )

        MotorcycleFactory(brand="KTM", model="Duke")

    def test_get_unique_makes_all_conditions(self):

        expected_makes = {"Honda", "Yamaha", "Suzuki", "Kawasaki", "Ducati", "KTM"}

        makes_all = get_unique_makes_for_filter(condition_slug="all")
        self.assertEqual(makes_all, expected_makes)

        makes_none = get_unique_makes_for_filter(condition_slug=None)
        self.assertEqual(makes_none, expected_makes)

    def test_get_unique_makes_new_condition(self):

        expected_makes = {"Honda", "Yamaha", "Suzuki"}
        makes = get_unique_makes_for_filter(condition_slug="new")
        self.assertEqual(makes, expected_makes)

    def test_get_unique_makes_used_condition(self):

        expected_makes = {"Honda", "Kawasaki", "Yamaha", "Ducati", "KTM"}
        makes = get_unique_makes_for_filter(condition_slug="used")
        self.assertEqual(makes, expected_makes)

    def test_get_unique_makes_demo_condition(self):

        expected_makes = {"Yamaha", "Ducati"}
        makes = get_unique_makes_for_filter(condition_slug="demo")
        self.assertEqual(makes, expected_makes)

    def test_get_unique_makes_no_matching_condition(self):

        MotorcycleConditionFactory(name="rare_condition", display_name="Rare Condition")
        makes = get_unique_makes_for_filter(condition_slug="rare_condition")
        self.assertEqual(makes, set())

    def test_get_unique_makes_empty_database(self):

        MotorcycleFactory._meta.model.objects.all().delete()
        makes = get_unique_makes_for_filter(condition_slug="all")
        self.assertEqual(makes, set())
