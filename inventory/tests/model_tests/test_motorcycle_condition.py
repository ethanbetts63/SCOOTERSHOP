from django.test import TestCase
from django.db.utils import IntegrityError                                 

                                      
from inventory.models import MotorcycleCondition

                                                                
from ..test_helpers.model_factories import MotorcycleConditionFactory


class MotorcycleConditionModelTest(TestCase):
    """
    Tests for the MotorcycleCondition model.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up non-modified objects used by all test methods.
        We'll create a single MotorcycleCondition instance using the factory.
        """
        cls.condition_new = MotorcycleConditionFactory(name='new', display_name='New')
        cls.condition_used = MotorcycleConditionFactory(name='used', display_name='Used Bike')

    def test_motorcycle_condition_creation(self):
        """
        Test that a MotorcycleCondition instance can be created successfully.
        """
        self.assertIsInstance(self.condition_new, MotorcycleCondition)
        self.assertIsNotNone(self.condition_new.pk)
        self.assertEqual(self.condition_new.name, 'new')
        self.assertEqual(self.condition_new.display_name, 'New')

        self.assertIsInstance(self.condition_used, MotorcycleCondition)
        self.assertIsNotNone(self.condition_used.pk)
        self.assertEqual(self.condition_used.name, 'used')
        self.assertEqual(self.condition_used.display_name, 'Used Bike')

    def test_name_field(self):
        """
        Test the 'name' field properties.
        """
        field = self.condition_new._meta.get_field('name')
        self.assertIsInstance(self.condition_new.name, str)
        self.assertEqual(field.max_length, 20)
        self.assertTrue(field.unique)
        self.assertFalse(field.blank)
        self.assertFalse(field.null)

                                           
        with self.assertRaises(IntegrityError):
            MotorcycleCondition.objects.create(name='new', display_name='Another New')

    def test_display_name_field(self):
        """
        Test the 'display_name' field properties.
        """
        field = self.condition_new._meta.get_field('display_name')
        self.assertIsInstance(self.condition_new.display_name, str)
        self.assertEqual(field.max_length, 50)
        self.assertFalse(field.blank)
        self.assertFalse(field.null)

    def test_str_method(self):
        """
        Test the __str__ method.
        """
        self.assertEqual(str(self.condition_new), 'New')
        self.assertEqual(str(self.condition_used), 'Used Bike')

    def test_verbose_names_meta(self):
        """
        Test the Meta 'verbose_name' and 'verbose_name_plural' options
        (Django's defaults if not explicitly set in the model).
        """
        self.assertEqual(MotorcycleCondition._meta.verbose_name, "motorcycle condition")
        self.assertEqual(MotorcycleCondition._meta.verbose_name_plural, "motorcycle conditions")

