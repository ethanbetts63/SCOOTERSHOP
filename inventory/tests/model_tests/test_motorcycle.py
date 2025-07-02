from django.test import TestCase
from django.urls import reverse
from datetime import date
import datetime
from django.db import IntegrityError
from decimal import Decimal
from django.db.models.deletion import SET_NULL

from inventory.models import Motorcycle, MotorcycleCondition
from django.contrib.auth import get_user_model
from django.db import models

from ..test_helpers.model_factories import (
    MotorcycleFactory,
    MotorcycleConditionFactory,
    UserFactory,
)

User = get_user_model()


class MotorcycleModelTest(TestCase):

    @classmethod
    def setUpTestData(cls):

        cls.user = UserFactory()
        cls.condition_new = MotorcycleConditionFactory(name="new", display_name="New")
        cls.condition_used = MotorcycleConditionFactory(
            name="used", display_name="Used"
        )

        cls.motorcycle_for_sale = MotorcycleFactory(
            brand="Honda",
            model="CBR1000RR",
            year=2022,
            price=Decimal("15000.00"),
            conditions=[cls.condition_new.name],
            is_available=True,
        )

        cls.motorcycle_unavailable = MotorcycleFactory(
            brand="Kawasaki",
            model="Ninja 400",
            year=2021,
            price=Decimal("8000.00"),
            conditions=[cls.condition_used.name],
            is_available=False,
        )

    def test_motorcycle_creation(self):

        self.assertIsInstance(self.motorcycle_for_sale, Motorcycle)
        self.assertIsNotNone(self.motorcycle_for_sale.pk)
        self.assertEqual(self.motorcycle_for_sale.brand, "Honda")
        self.assertEqual(self.motorcycle_for_sale.model, "CBR1000RR")
        self.assertEqual(self.motorcycle_for_sale.year, 2022)
        self.assertEqual(self.motorcycle_for_sale.price, Decimal("15000.00"))
        self.assertTrue(self.motorcycle_for_sale.is_available)
        self.assertEqual(self.motorcycle_for_sale.conditions.count(), 1)
        self.assertTrue(self.motorcycle_for_sale.conditions.filter(name="new").exists())

    def test_title_field(self):

        field = self.motorcycle_for_sale._meta.get_field("title")
        self.assertIsInstance(self.motorcycle_for_sale.title, str)
        self.assertEqual(field.max_length, 200)
        self.assertEqual(self.motorcycle_for_sale.title, "2022 Honda CBR1000RR")

    def test_brand_field(self):

        field = self.motorcycle_for_sale._meta.get_field("brand")
        self.assertIsInstance(self.motorcycle_for_sale.brand, str)
        self.assertEqual(field.max_length, 100)

    def test_model_field(self):

        field = self.motorcycle_for_sale._meta.get_field("model")
        self.assertIsInstance(self.motorcycle_for_sale.model, str)
        self.assertEqual(field.max_length, 100)

    def test_year_field(self):

        field = self.motorcycle_for_sale._meta.get_field("year")
        self.assertIsInstance(self.motorcycle_for_sale.year, int)

    def test_price_field(self):

        field = self.motorcycle_for_sale._meta.get_field("price")
        self.assertIsInstance(self.motorcycle_for_sale.price, Decimal)
        self.assertEqual(field.max_digits, 10)
        self.assertEqual(field.decimal_places, 2)
        self.assertTrue(field.null)
        self.assertTrue(field.blank)
        self.assertEqual(field.help_text, "Sale price (if applicable)")

    def test_vin_number_field(self):

        field = self.motorcycle_for_sale._meta.get_field("vin_number")
        self.assertIsInstance(self.motorcycle_for_sale.vin_number, (str, type(None)))
        self.assertEqual(field.max_length, 50)
        self.assertTrue(field.blank)
        self.assertTrue(field.null)
        self.assertEqual(field.help_text, "Vehicle Identification Number")

    def test_engine_number_field(self):

        field = self.motorcycle_for_sale._meta.get_field("engine_number")
        self.assertIsInstance(self.motorcycle_for_sale.engine_number, (str, type(None)))
        self.assertEqual(field.max_length, 50)
        self.assertTrue(field.blank)
        self.assertTrue(field.null)
        self.assertEqual(field.help_text, "Engine number/identifier")

    def test_conditions_many_to_many_field(self):

        field = self.motorcycle_for_sale._meta.get_field("conditions")
        self.assertIsInstance(field, models.ManyToManyField)
        self.assertEqual(field.related_model, MotorcycleCondition)

        self.assertEqual(field.remote_field.related_name, "motorcycles")
        self.assertTrue(field.blank)
        self.assertEqual(
            field.help_text, "Select all applicable conditions (e.g., Used, New, Demo.)"
        )

        motorcycle = MotorcycleFactory(conditions=["new", "demo"])
        self.assertEqual(motorcycle.conditions.count(), 2)
        self.assertTrue(motorcycle.conditions.filter(name="new").exists())
        self.assertTrue(motorcycle.conditions.filter(name="demo").exists())

    def test_odometer_field(self):

        field = self.motorcycle_for_sale._meta.get_field("odometer")
        self.assertIsInstance(self.motorcycle_for_sale.odometer, int)
        self.assertEqual(field.default, 0)

    def test_engine_size_field(self):

        field = self.motorcycle_for_sale._meta.get_field("engine_size")
        self.assertIsInstance(self.motorcycle_for_sale.engine_size, int)
        self.assertEqual(field.help_text, "Engine size in cubic centimeters (cc)")

    def test_seats_field(self):

        field = self.motorcycle_for_sale._meta.get_field("seats")
        self.assertIsInstance(self.motorcycle_for_sale.seats, (int, type(None)))
        self.assertTrue(field.null)
        self.assertTrue(field.blank)
        self.assertEqual(field.help_text, "Number of seats on the motorcycle")

    def test_transmission_field(self):

        field = self.motorcycle_for_sale._meta.get_field("transmission")
        self.assertIsInstance(self.motorcycle_for_sale.transmission, (str, type(None)))
        self.assertEqual(field.max_length, 20)
        self.assertEqual(field.choices, Motorcycle.TRANSMISSION_CHOICES)
        self.assertTrue(field.null)
        self.assertTrue(field.blank)
        self.assertEqual(field.help_text, "Motorcycle transmission type")

    def test_description_field(self):

        field = self.motorcycle_for_sale._meta.get_field("description")
        self.assertIsInstance(self.motorcycle_for_sale.description, (str, type(None)))
        self.assertTrue(field.null)
        self.assertTrue(field.blank)

    def test_image_field(self):

        field = self.motorcycle_for_sale._meta.get_field("image")
        self.assertIsInstance(field, models.FileField)
        self.assertEqual(field.upload_to, "motorcycles/")
        self.assertTrue(field.null)
        self.assertTrue(field.blank)

    def test_date_posted_field(self):

        field = self.motorcycle_for_sale._meta.get_field("date_posted")
        self.assertIsInstance(self.motorcycle_for_sale.date_posted, datetime.datetime)
        self.assertTrue(field.auto_now_add)

    def test_is_available_field(self):

        field = self.motorcycle_for_sale._meta.get_field("is_available")
        self.assertIsInstance(self.motorcycle_for_sale.is_available, bool)
        self.assertTrue(field.default)
        self.assertEqual(field.help_text, "Is this bike generally available for sale?")
        self.assertTrue(self.motorcycle_for_sale.is_available)
        self.assertFalse(self.motorcycle_unavailable.is_available)

    def test_rego_field(self):

        field = self.motorcycle_for_sale._meta.get_field("rego")
        self.assertIsInstance(self.motorcycle_for_sale.rego, (str, type(None)))
        self.assertEqual(field.max_length, 20)
        self.assertTrue(field.null)
        self.assertTrue(field.blank)
        self.assertEqual(field.help_text, "Registration number")

    def test_rego_exp_field(self):

        field = self.motorcycle_for_sale._meta.get_field("rego_exp")
        self.assertIsInstance(self.motorcycle_for_sale.rego_exp, (date, type(None)))
        self.assertTrue(field.null)
        self.assertTrue(field.blank)
        self.assertEqual(field.help_text, "Registration expiration date")

    def test_stock_number_field(self):

        field = self.motorcycle_for_sale._meta.get_field("stock_number")
        self.assertIsInstance(self.motorcycle_for_sale.stock_number, (str, type(None)))
        self.assertEqual(field.max_length, 50)
        self.assertTrue(field.unique)
        self.assertTrue(field.null)
        self.assertTrue(field.blank)

        with self.assertRaises(IntegrityError):
            Motorcycle.objects.create(
                brand="Test",
                model="Bike",
                year=2000,
                engine_size=100,
                stock_number=self.motorcycle_for_sale.stock_number,
            )

    def test_str_method(self):

        self.assertEqual(str(self.motorcycle_for_sale), "2022 Honda CBR1000RR")

    def test_get_conditions_display_method(self):

        self.assertEqual(self.motorcycle_for_sale.get_conditions_display(), "New")

        moto_no_conditions = MotorcycleFactory(conditions=[])
        moto_no_conditions.conditions.clear()
        self.assertEqual(moto_no_conditions.get_conditions_display(), "N/A")

        moto_old_condition = MotorcycleFactory(conditions=[], condition="demo")
        moto_old_condition.conditions.clear()
        self.assertEqual(moto_old_condition.get_conditions_display(), "Demo")

    def test_verbose_names_meta(self):

        self.assertEqual(Motorcycle._meta.verbose_name, "motorcycle")
        self.assertEqual(Motorcycle._meta.verbose_name_plural, "motorcycles")
