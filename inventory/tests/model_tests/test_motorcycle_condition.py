from django.test import TestCase
from django.db.utils import IntegrityError
from inventory.models import MotorcycleCondition
from inventory.tests.test_helpers.model_factories import MotorcycleConditionFactory


class MotorcycleConditionModelTest(TestCase):

    @classmethod
    def setUpTestData(cls):

        cls.condition_new = MotorcycleConditionFactory(name="new", display_name="New")
        cls.condition_used = MotorcycleConditionFactory(
            name="used", display_name="Used Bike"
        )

    def test_motorcycle_condition_creation(self):

        self.assertIsInstance(self.condition_new, MotorcycleCondition)
        self.assertIsNotNone(self.condition_new.pk)
        self.assertEqual(self.condition_new.name, "new")
        self.assertEqual(self.condition_new.display_name, "New")

        self.assertIsInstance(self.condition_used, MotorcycleCondition)
        self.assertIsNotNone(self.condition_used.pk)
        self.assertEqual(self.condition_used.name, "used")
        self.assertEqual(self.condition_used.display_name, "Used Bike")

    def test_name_field(self):

        field = self.condition_new._meta.get_field("name")
        self.assertIsInstance(self.condition_new.name, str)
        self.assertEqual(field.max_length, 20)
        self.assertTrue(field.unique)
        self.assertFalse(field.blank)
        self.assertFalse(field.null)

        with self.assertRaises(IntegrityError):
            MotorcycleCondition.objects.create(name="new", display_name="Another New")

    def test_display_name_field(self):

        field = self.condition_new._meta.get_field("display_name")
        self.assertIsInstance(self.condition_new.display_name, str)
        self.assertEqual(field.max_length, 50)
        self.assertFalse(field.blank)
        self.assertFalse(field.null)

    def test_str_method(self):

        self.assertEqual(str(self.condition_new), "New")
        self.assertEqual(str(self.condition_used), "Used Bike")

    def test_verbose_names_meta(self):

        self.assertEqual(MotorcycleCondition._meta.verbose_name, "motorcycle condition")
        self.assertEqual(
            MotorcycleCondition._meta.verbose_name_plural, "motorcycle conditions"
        )
