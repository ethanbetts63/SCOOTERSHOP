from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import IntegrityError # Import IntegrityError for unique constraint tests
from datetime import date
from django.db import models

# Import the CustomerMotorcycle model
from service.models import CustomerMotorcycle

# Import the CustomerMotorcycleFactory from your factories file
from ..test_helpers.model_factories import CustomerMotorcycleFactory, ServiceProfileFactory

class CustomerMotorcycleModelTest(TestCase):
    """
    Tests for the CustomerMotorcycle model, including field validations
    and unique constraints.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up non-modified objects used by all test methods.
        """
        cls.customer_motorcycle = CustomerMotorcycleFactory()

    def test_customer_motorcycle_creation(self):
        """
        Test that a CustomerMotorcycle instance can be created using the factory.
        """
        self.assertIsNotNone(self.customer_motorcycle)
        self.assertIsInstance(self.customer_motorcycle, CustomerMotorcycle)
        self.assertEqual(CustomerMotorcycle.objects.count(), 1)

    def test_str_method(self):
        """
        Test the __str__ method of the CustomerMotorcycle model.
        """
        expected_str = (
            f"{self.customer_motorcycle.year} {self.customer_motorcycle.brand} "
            f"{self.customer_motorcycle.make} (Owner: {self.customer_motorcycle.service_profile.name})"
        )
        self.assertEqual(str(self.customer_motorcycle), expected_str)

    def test_field_attributes(self):
        """
        Test the attributes of various fields in the CustomerMotorcycle model.
        """
        motorcycle = self.customer_motorcycle

        # service_profile
        field = motorcycle._meta.get_field('service_profile')
        self.assertIsInstance(field, models.ForeignKey)
        self.assertEqual(field.related_model.__name__, 'ServiceProfile')
        self.assertEqual(field.remote_field.on_delete, models.CASCADE)

        # brand, make, model
        for field_name in ['brand', 'make', 'model']:
            field = motorcycle._meta.get_field(field_name)
            self.assertIsInstance(field, models.CharField)
            self.assertEqual(field.max_length, 100)
            self.assertFalse(field.blank) # These are required by clean method
            self.assertFalse(field.null)

        # year
        field = motorcycle._meta.get_field('year')
        self.assertIsInstance(field, models.PositiveIntegerField)
        self.assertFalse(field.blank) # Required by clean method
        self.assertFalse(field.null)

        # engine_size
        field = motorcycle._meta.get_field('engine_size')
        self.assertIsInstance(field, models.CharField)
        self.assertEqual(field.max_length, 50)
        self.assertTrue(field.blank)
        self.assertTrue(field.null)

        # rego
        field = motorcycle._meta.get_field('rego')
        self.assertIsInstance(field, models.CharField)
        self.assertEqual(field.max_length, 20)
        self.assertTrue(field.blank)
        self.assertTrue(field.null)

        # vin_number
        field = motorcycle._meta.get_field('vin_number')
        self.assertIsInstance(field, models.CharField)
        self.assertEqual(field.max_length, 17)
        self.assertTrue(field.blank)
        self.assertTrue(field.null)
        self.assertTrue(field.unique)

        # odometer
        field = motorcycle._meta.get_field('odometer')
        self.assertIsInstance(field, models.PositiveIntegerField)
        self.assertTrue(field.blank)
        self.assertTrue(field.null)

        # transmission
        field = motorcycle._meta.get_field('transmission')
        self.assertIsInstance(field, models.CharField)
        self.assertEqual(field.max_length, 20)
        self.assertTrue(field.blank)
        self.assertTrue(field.null)
        self.assertGreater(len(field.choices), 0)

        # engine_number
        field = motorcycle._meta.get_field('engine_number')
        self.assertIsInstance(field, models.CharField)
        self.assertEqual(field.max_length, 50)
        self.assertTrue(field.blank)
        self.assertTrue(field.null)

        # image
        field = motorcycle._meta.get_field('image')
        self.assertIsInstance(field, models.ImageField)
        self.assertTrue(field.blank)
        self.assertTrue(field.null)
        self.assertEqual(field.upload_to, 'motorcycle_images/')

        # created_at, updated_at
        field = motorcycle._meta.get_field('created_at')
        self.assertIsInstance(field, models.DateTimeField)
        self.assertTrue(field.auto_now_add)
        field = motorcycle._meta.get_field('updated_at')
        self.assertIsInstance(field, models.DateTimeField)
        self.assertTrue(field.auto_now)

    def test_clean_method_required_fields(self):
        """
        Test clean method for required fields (brand, make, model, year).
        """
        service_profile = ServiceProfileFactory()

        # Test missing brand
        motorcycle = CustomerMotorcycleFactory.build(
            service_profile=service_profile, brand="", make="CBR", model="600RR", year=2020
        )
        with self.assertRaisesMessage(ValidationError, "Motorcycle brand is required."):
            motorcycle.full_clean()

        # Test missing make
        motorcycle = CustomerMotorcycleFactory.build(
            service_profile=service_profile, brand="Honda", make="", model="600RR", year=2020
        )
        with self.assertRaisesMessage(ValidationError, "Motorcycle make is required."):
            motorcycle.full_clean()

        # Test missing model
        motorcycle = CustomerMotorcycleFactory.build(
            service_profile=service_profile, brand="Honda", make="CBR", model="", year=2020
        )
        with self.assertRaisesMessage(ValidationError, "Motorcycle model is required."):
            motorcycle.full_clean()

        # Test missing year
        motorcycle = CustomerMotorcycleFactory.build(
            service_profile=service_profile, brand="Honda", make="CBR", model="600RR", year=None
        )
        with self.assertRaisesMessage(ValidationError, "Motorcycle year is required."):
            motorcycle.full_clean()

        # Test all required fields present (should pass)
        motorcycle = CustomerMotorcycleFactory.build(
            service_profile=service_profile, brand="Honda", make="CBR", model="600RR", year=2020
        )
        try:
            motorcycle.full_clean()
        except ValidationError as e:
            self.fail(f"full_clean raised ValidationError unexpectedly: {e.message_dict}")


    def test_clean_method_year_validation(self):
        """
        Test clean method for motorcycle year validation.
        """
        service_profile = ServiceProfileFactory()
        current_year = date.today().year

        # Test year in the future
        motorcycle = CustomerMotorcycleFactory.build(
            service_profile=service_profile, year=current_year + 1
        )
        with self.assertRaisesMessage(ValidationError, "Motorcycle year cannot be in the future."):
            motorcycle.full_clean()

        # Test year too old (more than 100 years ago)
        motorcycle = CustomerMotorcycleFactory.build(
            service_profile=service_profile, year=current_year - 101
        )
        with self.assertRaisesMessage(ValidationError, "Motorcycle year seems too old. Please check the year."):
            motorcycle.full_clean()

        # Test valid year (current year)
        motorcycle = CustomerMotorcycleFactory.build(
            service_profile=service_profile, year=current_year
        )
        try:
            motorcycle.full_clean()
        except ValidationError as e:
            self.fail(f"full_clean raised ValidationError unexpectedly for current year: {e.message_dict}")

        # Test valid year (100 years ago)
        motorcycle = CustomerMotorcycleFactory.build(
            service_profile=service_profile, year=current_year - 100
        )
        try:
            motorcycle.full_clean()
        except ValidationError as e:
            self.fail(f"full_clean raised ValidationError unexpectedly for 100 years ago: {e.message_dict}")

    def test_clean_method_vin_number_validation(self):
        """
        Test clean method for VIN number length validation.
        """
        service_profile = ServiceProfileFactory()

        # Test VIN number too short
        motorcycle = CustomerMotorcycleFactory.build(
            service_profile=service_profile, vin_number="SHORTVIN"
        )
        with self.assertRaisesMessage(ValidationError, "VIN number must be 17 characters long."):
            motorcycle.full_clean()

        # Test VIN number too long
        motorcycle = CustomerMotorcycleFactory.build(
            service_profile=service_profile, vin_number="TOOLONGVINNUMBER123"
        )
        with self.assertRaisesMessage(ValidationError, "VIN number must be 17 characters long."):
            motorcycle.full_clean()

        # FIX: Correct the valid VIN number to be exactly 17 characters
        motorcycle = CustomerMotorcycleFactory.build(
            service_profile=service_profile, vin_number="VALIDVINNUMB12345" # 17 characters
        )
        try:
            motorcycle.full_clean()
        except ValidationError as e:
            self.fail(f"full_clean raised ValidationError unexpectedly for valid VIN: {e.message_dict}")

        # Test VIN number as None (should pass)
        motorcycle = CustomerMotorcycleFactory.build(
            service_profile=service_profile, vin_number=None
        )
        try:
            motorcycle.full_clean()
        except ValidationError as e:
            self.fail(f"full_clean raised ValidationError unexpectedly for None VIN: {e.message_dict}")

    def test_clean_method_odometer_validation(self):
        """
        Test clean method for odometer reading validation (not negative).
        """
        service_profile = ServiceProfileFactory()

        # Test negative odometer
        motorcycle = CustomerMotorcycleFactory.build(
            service_profile=service_profile, odometer=-100
        )
        with self.assertRaisesMessage(ValidationError, "Odometer reading cannot be negative."):
            motorcycle.full_clean()

        # Test zero odometer (should pass)
        motorcycle = CustomerMotorcycleFactory.build(
            service_profile=service_profile, odometer=0
        )
        try:
            motorcycle.full_clean()
        except ValidationError as e:
            self.fail(f"full_clean raised ValidationError unexpectedly for zero odometer: {e.message_dict}")

        # Test positive odometer (should pass)
        motorcycle = CustomerMotorcycleFactory.build(
            service_profile=service_profile, odometer=50000
        )
        try:
            motorcycle.full_clean()
        except ValidationError as e:
            self.fail(f"full_clean raised ValidationError unexpectedly for positive odometer: {e.message_dict}")

        # Test odometer as None (should pass)
        motorcycle = CustomerMotorcycleFactory.build(
            service_profile=service_profile, odometer=None
        )
        try:
            motorcycle.full_clean()
        except ValidationError as e:
            self.fail(f"full_clean raised ValidationError unexpectedly for None odometer: {e.message_dict}")

    def test_vin_number_unique_constraint_non_null(self):
        """
        Test that vin_number enforces uniqueness for non-null values.
        """
        # Create a motorcycle with a specific VIN
        existing_motorcycle = CustomerMotorcycleFactory(vin_number="UNIQUEVIN123456789")
        
        # Attempt to create another motorcycle with the same VIN
        with self.assertRaises(IntegrityError) as cm:
            CustomerMotorcycleFactory(vin_number="UNIQUEVIN123456789")
        self.assertIn("unique constraint failed", str(cm.exception).lower())

    def test_vin_number_unique_constraint_null_values(self):
        """
        Test that multiple null vin_number values are allowed.
        """
        # Test that None VINs are allowed (unique=True allows multiple NULLs in SQLite/PostgreSQL)
        CustomerMotorcycleFactory(vin_number=None)
        CustomerMotorcycleFactory(vin_number=None) # Should not raise error
        self.assertEqual(CustomerMotorcycle.objects.filter(vin_number=None).count(), 2)


    def test_timestamps_auto_now_add_and_auto_now(self):
        """
        Test that created_at is set on creation and updated_at is updated on save.
        """
        motorcycle = CustomerMotorcycleFactory()
        initial_created_at = motorcycle.created_at
        initial_updated_at = motorcycle.updated_at

        # created_at should be set on creation
        self.assertIsNotNone(initial_created_at)
        self.assertIsNotNone(initial_updated_at)
        self.assertLessEqual(initial_created_at, initial_updated_at)

        # Update the motorcycle and save
        import time
        time.sleep(0.01) # Ensure a slight time difference for updated_at to change
        motorcycle.rego = "NEWREG"
        motorcycle.save()

        # updated_at should be greater than its initial value
        self.assertGreater(motorcycle.updated_at, initial_updated_at)
        # created_at should remain the same
        self.assertEqual(motorcycle.created_at, initial_created_at)

