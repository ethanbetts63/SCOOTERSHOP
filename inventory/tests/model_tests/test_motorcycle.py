from django.test import TestCase
from django.urls import reverse
from datetime import date
import datetime
from django.db import IntegrityError
from decimal import Decimal
from django.db.models.deletion import SET_NULL

# Import the Motorcycle, MotorcycleCondition, and User models
from inventory.models import Motorcycle, MotorcycleCondition
from django.contrib.auth import get_user_model # To get the User model
from django.db import models
# Import factories
from ..test_helpers.model_factories import (
    MotorcycleFactory,
    MotorcycleConditionFactory,
    UserFactory
)

User = get_user_model()

class MotorcycleModelTest(TestCase):
    """
    Tests for the Motorcycle model.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up non-modified objects used by all test methods.
        """
        cls.user = UserFactory()
        cls.condition_new = MotorcycleConditionFactory(name='new', display_name='New')
        cls.condition_used = MotorcycleConditionFactory(name='used', display_name='Used')
        cls.condition_hire = MotorcycleConditionFactory(name='hire', display_name='For Hire')

        cls.motorcycle_for_sale = MotorcycleFactory(
            brand='Honda',
            model='CBR1000RR',
            year=2022,
            price=Decimal('15000.00'),
            conditions=[cls.condition_new.name], # Pass name to post_generation
            is_available=True,
            daily_hire_rate=None,
            hourly_hire_rate=None,
        )
        cls.motorcycle_for_hire = MotorcycleFactory(
            brand='Yamaha',
            model='MT-07',
            year=2020,
            price=None,
            conditions=[cls.condition_used.name, cls.condition_hire.name],
            is_available=True,
            daily_hire_rate=Decimal('100.00'),
            hourly_hire_rate=Decimal('20.00'),
        )
        cls.motorcycle_unavailable = MotorcycleFactory(
            brand='Kawasaki',
            model='Ninja 400',
            year=2021,
            price=Decimal('8000.00'),
            conditions=[cls.condition_used.name],
            is_available=False,
            daily_hire_rate=None,
            hourly_hire_rate=None,
        )

    def test_motorcycle_creation(self):
        """
        Test that Motorcycle instances can be created successfully.
        """
        self.assertIsInstance(self.motorcycle_for_sale, Motorcycle)
        self.assertIsNotNone(self.motorcycle_for_sale.pk)
        self.assertEqual(self.motorcycle_for_sale.brand, 'Honda')
        self.assertEqual(self.motorcycle_for_sale.model, 'CBR1000RR')
        self.assertEqual(self.motorcycle_for_sale.year, 2022)
        self.assertEqual(self.motorcycle_for_sale.price, Decimal('15000.00'))
        self.assertTrue(self.motorcycle_for_sale.is_available)
        self.assertEqual(self.motorcycle_for_sale.conditions.count(), 1)
        self.assertTrue(self.motorcycle_for_sale.conditions.filter(name='new').exists())
        self.assertFalse(self.motorcycle_for_sale.conditions.filter(name='hire').exists())


        self.assertIsInstance(self.motorcycle_for_hire, Motorcycle)
        self.assertEqual(self.motorcycle_for_hire.brand, 'Yamaha')
        self.assertIsNone(self.motorcycle_for_hire.price)
        self.assertEqual(self.motorcycle_for_hire.daily_hire_rate, Decimal('100.00'))
        self.assertEqual(self.motorcycle_for_hire.hourly_hire_rate, Decimal('20.00'))
        self.assertEqual(self.motorcycle_for_hire.conditions.count(), 2)
        self.assertTrue(self.motorcycle_for_hire.conditions.filter(name='used').exists())
        self.assertTrue(self.motorcycle_for_hire.conditions.filter(name='hire').exists())

    def test_title_field(self):
        """Test the 'title' field."""
        field = self.motorcycle_for_sale._meta.get_field('title')
        self.assertIsInstance(self.motorcycle_for_sale.title, str)
        self.assertEqual(field.max_length, 200)
        self.assertEqual(self.motorcycle_for_sale.title, "2022 Honda CBR1000RR")

    def test_brand_field(self):
        """Test the 'brand' field."""
        field = self.motorcycle_for_sale._meta.get_field('brand')
        self.assertIsInstance(self.motorcycle_for_sale.brand, str)
        self.assertEqual(field.max_length, 100)

    def test_model_field(self):
        """Test the 'model' field."""
        field = self.motorcycle_for_sale._meta.get_field('model')
        self.assertIsInstance(self.motorcycle_for_sale.model, str)
        self.assertEqual(field.max_length, 100)

    def test_year_field(self):
        """Test the 'year' field."""
        field = self.motorcycle_for_sale._meta.get_field('year')
        self.assertIsInstance(self.motorcycle_for_sale.year, int)

    def test_price_field(self):
        """Test the 'price' field."""
        field = self.motorcycle_for_sale._meta.get_field('price')
        self.assertIsInstance(self.motorcycle_for_sale.price, Decimal)
        self.assertEqual(field.max_digits, 10)
        self.assertEqual(field.decimal_places, 2)
        self.assertTrue(field.null)
        self.assertTrue(field.blank)
        self.assertEqual(field.help_text, "Sale price (if applicable)")

    def test_vin_number_field(self):
        """Test the 'vin_number' field."""
        field = self.motorcycle_for_sale._meta.get_field('vin_number')
        self.assertIsInstance(self.motorcycle_for_sale.vin_number, (str, type(None)))
        self.assertEqual(field.max_length, 50)
        self.assertTrue(field.blank)
        self.assertTrue(field.null)
        self.assertEqual(field.help_text, "Vehicle Identification Number")

    def test_engine_number_field(self):
        """Test the 'engine_number' field."""
        field = self.motorcycle_for_sale._meta.get_field('engine_number')
        self.assertIsInstance(self.motorcycle_for_sale.engine_number, (str, type(None)))
        self.assertEqual(field.max_length, 50)
        self.assertTrue(field.blank)
        self.assertTrue(field.null)
        self.assertEqual(field.help_text, "Engine number/identifier")

    def test_conditions_many_to_many_field(self):
        """Test the 'conditions' ManyToMany field."""
        field = self.motorcycle_for_sale._meta.get_field('conditions')
        self.assertIsInstance(field, models.ManyToManyField)
        self.assertEqual(field.related_model, MotorcycleCondition)
        # Access related_name through remote_field for consistency/robustness
        self.assertEqual(field.remote_field.related_name, 'motorcycles')
        self.assertTrue(field.blank)
        self.assertEqual(field.help_text, "Select all applicable conditions (e.g., Used, Hire)")

        # Test adding and retrieving conditions
        motorcycle = MotorcycleFactory(conditions=['new', 'demo'])
        self.assertEqual(motorcycle.conditions.count(), 2)
        self.assertTrue(motorcycle.conditions.filter(name='new').exists())
        self.assertTrue(motorcycle.conditions.filter(name='demo').exists())

    def test_odometer_field(self):
        """Test the 'odometer' field."""
        field = self.motorcycle_for_sale._meta.get_field('odometer')
        self.assertIsInstance(self.motorcycle_for_sale.odometer, int)
        self.assertEqual(field.default, 0)

    def test_engine_size_field(self):
        """Test the 'engine_size' field."""
        field = self.motorcycle_for_sale._meta.get_field('engine_size')
        self.assertIsInstance(self.motorcycle_for_sale.engine_size, int)
        self.assertEqual(field.help_text, "Engine size in cubic centimeters (cc)")

    def test_seats_field(self):
        """Test the 'seats' field."""
        field = self.motorcycle_for_sale._meta.get_field('seats')
        self.assertIsInstance(self.motorcycle_for_sale.seats, (int, type(None)))
        self.assertTrue(field.null)
        self.assertTrue(field.blank)
        self.assertEqual(field.help_text, "Number of seats on the motorcycle")

    def test_transmission_field(self):
        """Test the 'transmission' field."""
        field = self.motorcycle_for_sale._meta.get_field('transmission')
        self.assertIsInstance(self.motorcycle_for_sale.transmission, (str, type(None)))
        self.assertEqual(field.max_length, 20)
        self.assertEqual(field.choices, Motorcycle.TRANSMISSION_CHOICES)
        self.assertTrue(field.null)
        self.assertTrue(field.blank)
        self.assertEqual(field.help_text, "Motorcycle transmission type")

    def test_description_field(self):
        """Test the 'description' field."""
        field = self.motorcycle_for_sale._meta.get_field('description')
        self.assertIsInstance(self.motorcycle_for_sale.description, (str, type(None)))
        self.assertTrue(field.null)
        self.assertTrue(field.blank)

    def test_image_field(self):
        """Test the 'image' FileField."""
        field = self.motorcycle_for_sale._meta.get_field('image')
        self.assertIsInstance(field, models.FileField)
        self.assertEqual(field.upload_to, 'motorcycles/')
        self.assertTrue(field.null)
        self.assertTrue(field.blank)

    def test_date_posted_field(self):
        """Test the 'date_posted' field."""
        field = self.motorcycle_for_sale._meta.get_field('date_posted')
        self.assertIsInstance(self.motorcycle_for_sale.date_posted, datetime.datetime)
        self.assertTrue(field.auto_now_add)

    def test_is_available_field(self):
        """Test the 'is_available' field."""
        field = self.motorcycle_for_sale._meta.get_field('is_available')
        self.assertIsInstance(self.motorcycle_for_sale.is_available, bool)
        self.assertTrue(field.default)
        self.assertEqual(field.help_text, "Is this bike generally available for sale or in the active hire fleet?")
        self.assertTrue(self.motorcycle_for_sale.is_available)
        self.assertFalse(self.motorcycle_unavailable.is_available)

    def test_rego_field(self):
        """Test the 'rego' field."""
        field = self.motorcycle_for_sale._meta.get_field('rego')
        self.assertIsInstance(self.motorcycle_for_sale.rego, (str, type(None)))
        self.assertEqual(field.max_length, 20)
        self.assertTrue(field.null)
        self.assertTrue(field.blank)
        self.assertEqual(field.help_text, "Registration number")

    def test_rego_exp_field(self):
        """Test the 'rego_exp' field."""
        field = self.motorcycle_for_sale._meta.get_field('rego_exp')
        self.assertIsInstance(self.motorcycle_for_sale.rego_exp, (date, type(None)))
        self.assertTrue(field.null)
        self.assertTrue(field.blank)
        self.assertEqual(field.help_text, "Registration expiration date")

    def test_stock_number_field(self):
        """Test the 'stock_number' field."""
        field = self.motorcycle_for_sale._meta.get_field('stock_number')
        self.assertIsInstance(self.motorcycle_for_sale.stock_number, (str, type(None)))
        self.assertEqual(field.max_length, 50)
        self.assertTrue(field.unique)
        self.assertTrue(field.null)
        self.assertTrue(field.blank)

        # Test unique constraint
        with self.assertRaises(IntegrityError):
            Motorcycle.objects.create(
                brand='Test', model='Bike', year=2000, engine_size=100,
                stock_number=self.motorcycle_for_sale.stock_number # Duplicate stock number
            )

    def test_daily_hire_rate_field(self):
        """Test the 'daily_hire_rate' field."""
        field = self.motorcycle_for_hire._meta.get_field('daily_hire_rate')
        self.assertIsInstance(self.motorcycle_for_hire.daily_hire_rate, Decimal)
        self.assertEqual(field.max_digits, 8)
        self.assertEqual(field.decimal_places, 2)
        self.assertTrue(field.null)
        self.assertTrue(field.blank)
        self.assertEqual(field.help_text, "Price per day for hiring (if applicable)")
        self.assertEqual(self.motorcycle_for_hire.daily_hire_rate, Decimal('100.00'))
        self.assertIsNone(self.motorcycle_for_sale.daily_hire_rate)

    def test_hourly_hire_rate_field(self):
        """Test the 'hourly_hire_rate' field."""
        field = self.motorcycle_for_hire._meta.get_field('hourly_hire_rate')
        self.assertIsInstance(self.motorcycle_for_hire.hourly_hire_rate, Decimal)
        self.assertEqual(field.max_digits, 8)
        self.assertEqual(field.decimal_places, 2)
        self.assertTrue(field.null)
        self.assertTrue(field.blank)
        self.assertEqual(field.help_text, "Price per hour for hiring (if applicable)")
        self.assertEqual(self.motorcycle_for_hire.hourly_hire_rate, Decimal('20.00'))
        self.assertIsNone(self.motorcycle_for_sale.hourly_hire_rate)

    def test_str_method(self):
        """
        Test the __str__ method of Motorcycle.
        """
        self.assertEqual(str(self.motorcycle_for_sale), "2022 Honda CBR1000RR")
        self.assertEqual(str(self.motorcycle_for_hire), "2020 Yamaha MT-07")

    def test_get_conditions_display_method(self):
        """
        Test the get_conditions_display method.
        """
        # Test with a single condition
        self.assertEqual(self.motorcycle_for_sale.get_conditions_display(), 'New')

        # Test with multiple conditions
        expected_display = f"{self.condition_used.display_name}, {self.condition_hire.display_name}"
        self.assertEqual(self.motorcycle_for_hire.get_conditions_display(), expected_display)

        # Test with no conditions (if possible, though factory adds 'used' by default)
        # To truly test 'N/A', we'd need a motorcycle with no conditions.
        # Let's create one explicitly and clear conditions.
        moto_no_conditions = MotorcycleFactory(conditions=[]) # Create with no conditions initially
        moto_no_conditions.conditions.clear() # Ensure no conditions are present
        self.assertEqual(moto_no_conditions.get_conditions_display(), 'N/A')

        # Test with the old 'condition' charfield if set, and no ManyToMany conditions
        moto_old_condition = MotorcycleFactory(conditions=[], condition='demo')
        moto_old_condition.conditions.clear()
        self.assertEqual(moto_old_condition.get_conditions_display(), 'Demo')


    def test_is_for_hire_method(self):
        """
        Test the is_for_hire method.
        """
        self.assertFalse(self.motorcycle_for_sale.is_for_hire())
        self.assertTrue(self.motorcycle_for_hire.is_for_hire())
        self.assertFalse(self.motorcycle_unavailable.is_for_hire())

    def test_verbose_names_meta(self):
        """
        Test the Meta 'verbose_name' and 'verbose_name_plural' options
        (Django's defaults if not explicitly set in the model).
        """
        self.assertEqual(Motorcycle._meta.verbose_name, "motorcycle")
        self.assertEqual(Motorcycle._meta.verbose_name_plural, "motorcycles")

