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
        We need to ensure the factory provides all currently required fields.
        """
        cls.customer_motorcycle = CustomerMotorcycleFactory(
            # Ensure all required fields are provided for the factory
            brand="Honda",
            model="CBR600RR", # Ensure model is provided for __str__ test
            year=2020,
            rego="XYZ123",
            odometer=10000,
            transmission="MANUAL",
            engine_size="600cc",
        )

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
        Updated to reflect removal of 'make' field.
        """
        expected_str = (
            f"{self.customer_motorcycle.year} {self.customer_motorcycle.brand} {self.customer_motorcycle.model} "
            f"(Owner: {self.customer_motorcycle.service_profile.name})"
        )
        self.assertEqual(str(self.customer_motorcycle), expected_str)

    def test_field_attributes(self):
        """
        Test the attributes of various fields in the CustomerMotorcycle model.
        Updated to reflect changes in required/optional fields.
        """
        motorcycle = self.customer_motorcycle

        # service_profile
        field = motorcycle._meta.get_field('service_profile')
        self.assertIsInstance(field, models.ForeignKey)
        self.assertEqual(field.related_model.__name__, 'ServiceProfile')
        self.assertEqual(field.remote_field.on_delete, models.CASCADE)
        self.assertTrue(field.blank) # service_profile can be blank/null
        self.assertTrue(field.null)

        # brand, model, year, rego, odometer, transmission, engine_size (REQUIRED FIELDS)
        for field_name in ['brand', 'model', 'year', 'rego', 'odometer', 'transmission', 'engine_size']:
            field = motorcycle._meta.get_field(field_name)
            # These fields are now required, so they should not be blank/null in the model definition
            self.assertFalse(field.blank, f"{field_name} should not be blank.")
            self.assertFalse(field.null, f"{field_name} should not be null.")
            
            # Specific type checks
            if field_name in ['brand', 'model', 'rego', 'engine_size', 'transmission']:
                self.assertIsInstance(field, models.CharField)
            elif field_name in ['year', 'odometer']:
                self.assertIsInstance(field, models.PositiveIntegerField)
            
            # Max length checks
            if field_name in ['brand', 'model']:
                self.assertEqual(field.max_length, 100)
            elif field_name == 'rego':
                self.assertEqual(field.max_length, 20)
            elif field_name == 'engine_size':
                self.assertEqual(field.max_length, 50)
            elif field_name == 'transmission':
                self.assertEqual(field.max_length, 20)
                self.assertGreater(len(field.choices), 0) # Ensure choices are present for transmission

        # vin_number (OPTIONAL FIELD)
        field = motorcycle._meta.get_field('vin_number')
        self.assertIsInstance(field, models.CharField)
        self.assertEqual(field.max_length, 17)
        self.assertTrue(field.blank)
        self.assertTrue(field.null)
        self.assertTrue(field.unique)

        # engine_number (OPTIONAL FIELD)
        field = motorcycle._meta.get_field('engine_number')
        self.assertIsInstance(field, models.CharField)
        self.assertEqual(field.max_length, 50)
        self.assertTrue(field.blank)
        self.assertTrue(field.null)

        # image (OPTIONAL FIELD)
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
        Test clean method for all required fields.
        Updated to correctly assert the error messages, accounting for Django's default messages.
        """
        service_profile = ServiceProfileFactory()

        # Test missing brand
        motorcycle = CustomerMotorcycleFactory.build(
            service_profile=service_profile, brand="", model="600RR", year=2020,
            rego="ABC123", odometer=10000, transmission="MANUAL", engine_size="600cc"
        )
        with self.assertRaises(ValidationError) as cm:
            motorcycle.full_clean()
        self.assertIn('Motorcycle brand is required.', cm.exception.message_dict['brand'])

        # Test missing model
        motorcycle = CustomerMotorcycleFactory.build(
            service_profile=service_profile, brand="Honda", model="", year=2020,
            rego="ABC123", odometer=10000, transmission="MANUAL", engine_size="600cc"
        )
        with self.assertRaises(ValidationError) as cm:
            motorcycle.full_clean()
        self.assertIn('Motorcycle model is required.', cm.exception.message_dict['model'])

        # Test missing year
        motorcycle = CustomerMotorcycleFactory.build(
            service_profile=service_profile, brand="Honda", model="600RR", year=None,
            rego="ABC123", odometer=10000, transmission="MANUAL", engine_size="600cc"
        )
        with self.assertRaises(ValidationError) as cm:
            motorcycle.full_clean()
        self.assertIn('Motorcycle year is required.', cm.exception.message_dict['year'])
        
        # Test missing rego
        motorcycle = CustomerMotorcycleFactory.build(
            service_profile=service_profile, brand="Honda", model="600RR", year=2020,
            rego="", odometer=10000, transmission="MANUAL", engine_size="600cc"
        )
        with self.assertRaises(ValidationError) as cm:
            motorcycle.full_clean()
        # Check for either the custom message or Django's default blank message
        self.assertTrue(
            'Motorcycle registration is required.' in cm.exception.message_dict['rego'] or
            'This field cannot be blank.' in cm.exception.message_dict['rego']
        )

        # Test missing odometer
        motorcycle = CustomerMotorcycleFactory.build(
            service_profile=service_profile, brand="Honda", model="600RR", year=2020,
            rego="ABC123", odometer=None, transmission="MANUAL", engine_size="600cc"
        )
        with self.assertRaises(ValidationError) as cm:
            motorcycle.full_clean()
        self.assertIn('Motorcycle odometer is required.', cm.exception.message_dict['odometer'])

        # Test missing transmission
        motorcycle = CustomerMotorcycleFactory.build(
            service_profile=service_profile, brand="Honda", model="600RR", year=2020,
            rego="ABC123", odometer=10000, transmission="", engine_size="600cc"
        )
        with self.assertRaises(ValidationError) as cm:
            motorcycle.full_clean()
        self.assertIn('Motorcycle transmission type is required.', cm.exception.message_dict['transmission'])

        # Test missing engine_size
        motorcycle = CustomerMotorcycleFactory.build(
            service_profile=service_profile, brand="Honda", model="600RR", year=2020,
            rego="ABC123", odometer=10000, transmission="MANUAL", engine_size=""
        )
        with self.assertRaises(ValidationError) as cm:
            motorcycle.full_clean()
        self.assertIn('Motorcycle engine size is required.', cm.exception.message_dict['engine_size'])

        # Test all required fields present (should pass)
        motorcycle = CustomerMotorcycleFactory.build(
            service_profile=service_profile, brand="Honda", model="600RR", year=2020,
            rego="ABC123", odometer=10000, transmission="MANUAL", engine_size="600cc"
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
            service_profile=service_profile, year=current_year + 1,
            brand="Honda", model="600RR", rego="ABC123", odometer=10000,
            transmission="MANUAL", engine_size="600cc"
        )
        with self.assertRaises(ValidationError) as cm:
            motorcycle.full_clean()
        self.assertIn('Motorcycle year cannot be in the future.', cm.exception.message_dict['year'])

        # Test year too old (more than 100 years ago)
        motorcycle = CustomerMotorcycleFactory.build(
            service_profile=service_profile, year=current_year - 101,
            brand="Honda", model="600RR", rego="ABC123", odometer=10000,
            transmission="MANUAL", engine_size="600cc"
        )
        with self.assertRaises(ValidationError) as cm:
            motorcycle.full_clean()
        self.assertIn('Motorcycle year seems too old. Please check the year.', cm.exception.message_dict['year'])

        # Test valid year (current year)
        motorcycle = CustomerMotorcycleFactory.build(
            service_profile=service_profile, year=current_year,
            brand="Honda", model="600RR", rego="ABC123", odometer=10000,
            transmission="MANUAL", engine_size="600cc"
        )
        try:
            motorcycle.full_clean()
        except ValidationError as e:
            self.fail(f"full_clean raised ValidationError unexpectedly for current year: {e.message_dict}")

        # Test valid year (100 years ago)
        motorcycle = CustomerMotorcycleFactory.build(
            service_profile=service_profile, year=current_year - 100,
            brand="Honda", model="600RR", rego="ABC123", odometer=10000,
            transmission="MANUAL", engine_size="600cc"
        )
        try:
            motorcycle.full_clean()
        except ValidationError as e:
            self.fail(f"full_clean raised ValidationError unexpectedly for 100 years ago: {e.message_dict}")

    def test_clean_method_vin_number_validation(self):
        """
        Test clean method for VIN number length validation.
        Updated to correctly assert the error messages, accounting for Django's default messages.
        """
        service_profile = ServiceProfileFactory()

        # Test VIN number too short
        motorcycle = CustomerMotorcycleFactory.build(
            service_profile=service_profile, vin_number="SHORTVIN",
            brand="Honda", model="600RR", year=2020, rego="ABC123", odometer=10000,
            transmission="MANUAL", engine_size="600cc"
        )
        with self.assertRaises(ValidationError) as cm:
            motorcycle.full_clean()
        self.assertIn('VIN number must be 17 characters long.', cm.exception.message_dict['vin_number'])

        # Test VIN number too long
        motorcycle = CustomerMotorcycleFactory.build(
            service_profile=service_profile, vin_number="TOOLONGVINNUMBER123",
            brand="Honda", model="600RR", year=2020, rego="ABC123", odometer=10000,
            transmission="MANUAL", engine_size="600cc"
        )
        with self.assertRaises(ValidationError) as cm:
            motorcycle.full_clean()
        # Check for either the custom message or Django's default max_length message
        self.assertTrue(
            'VIN number must be 17 characters long.' in cm.exception.message_dict['vin_number'] or
            'Ensure this value has at most 17 characters' in cm.exception.message_dict['vin_number'][0]
        )


        # Correct the valid VIN number to be exactly 17 characters
        motorcycle = CustomerMotorcycleFactory.build(
            service_profile=service_profile, vin_number="VALIDVINNUMB12345", # 17 characters
            brand="Honda", model="600RR", year=2020, rego="ABC123", odometer=10000,
            transmission="MANUAL", engine_size="600cc"
        )
        try:
            motorcycle.full_clean()
        except ValidationError as e:
            self.fail(f"full_clean raised ValidationError unexpectedly for valid VIN: {e.message_dict}")

        # Test VIN number as None (should pass for optional field)
        motorcycle = CustomerMotorcycleFactory.build(
            service_profile=service_profile, vin_number=None,
            brand="Honda", model="600RR", year=2020, rego="ABC123", odometer=10000,
            transmission="MANUAL", engine_size="600cc"
        )
        try:
            motorcycle.full_clean()
        except ValidationError as e:
            self.fail(f"full_clean raised ValidationError unexpectedly for None VIN: {e.message_dict}")

    def test_clean_method_odometer_validation(self):
        """
        Test clean method for odometer reading validation (not negative).
        Updated to correctly assert the error messages, accounting for Django's default messages.
        """
        service_profile = ServiceProfileFactory()

        # Test negative odometer
        motorcycle = CustomerMotorcycleFactory.build(
            service_profile=service_profile, odometer=-100,
            brand="Honda", model="600RR", year=2020, rego="ABC123",
            transmission="MANUAL", engine_size="600cc"
        )
        with self.assertRaises(ValidationError) as cm:
            motorcycle.full_clean()
        # Check for either the custom message or Django's default min_value message
        self.assertTrue(
            'Odometer reading cannot be negative.' in cm.exception.message_dict['odometer'] or
            'Ensure this value is greater than or equal to 0.' in cm.exception.message_dict['odometer']
        )


        # Test zero odometer (should pass as it's a valid positive integer)
        motorcycle = CustomerMotorcycleFactory.build(
            service_profile=service_profile, odometer=0,
            brand="Honda", model="600RR", year=2020, rego="ABC123",
            transmission="MANUAL", engine_size="600cc"
        )
        try:
            motorcycle.full_clean()
        except ValidationError as e:
            self.fail(f"full_clean raised ValidationError unexpectedly for zero odometer: {e.message_dict}")

        # Test positive odometer (should pass)
        motorcycle = CustomerMotorcycleFactory.build(
            service_profile=service_profile, odometer=50000,
            brand="Honda", model="600RR", year=2020, rego="ABC123",
            transmission="MANUAL", engine_size="600cc"
        )
        try:
            motorcycle.full_clean()
        except ValidationError as e:
            self.fail(f"full_clean raised ValidationError unexpectedly for positive odometer: {e.message_dict}")

    def test_vin_number_unique_constraint_non_null(self):
        """
        Test that vin_number enforces uniqueness for non-null values.
        """
        # Create a motorcycle with a specific VIN, providing all required fields
        existing_motorcycle = CustomerMotorcycleFactory(
            vin_number="UNIQUEVIN123456789",
            brand="Honda", model="CBR600RR", year=2020, rego="ABC123", odometer=10000,
            transmission="MANUAL", engine_size="600cc"
        )
        
        # Attempt to create another motorcycle with the same VIN, providing all required fields
        with self.assertRaises(IntegrityError) as cm:
            CustomerMotorcycleFactory(
                vin_number="UNIQUEVIN123456789",
                brand="Yamaha", model="YZF-R1", year=2021, rego="DEF456", odometer=12000,
                transmission="AUTOMATIC", engine_size="1000cc"
            )
        self.assertIn("unique constraint failed", str(cm.exception).lower())

    def test_vin_number_unique_constraint_null_values(self):
        """
        Test that multiple null vin_number values are allowed.
        Ensure all required fields are provided.
        """
        # Test that None VINs are allowed (unique=True allows multiple NULLs in SQLite/PostgreSQL)
        CustomerMotorcycleFactory(
            vin_number=None,
            brand="Honda", model="CBR600RR", year=2020, rego="ABC123", odometer=10000,
            transmission="MANUAL", engine_size="600cc"
        )
        CustomerMotorcycleFactory(
            vin_number=None,
            brand="Yamaha", model="YZF-R1", year=2021, rego="DEF456", odometer=12000,
            transmission="AUTOMATIC", engine_size="1000cc"
        ) # Should not raise error
        self.assertEqual(CustomerMotorcycle.objects.filter(vin_number=None).count(), 2)


    def test_timestamps_auto_now_add_and_auto_now(self):
        """
        Test that created_at is set on creation and updated_at is updated on save.
        Ensure all required fields are provided.
        """
        motorcycle = CustomerMotorcycleFactory(
            brand="Suzuki", model="GSX-R", year=2019, rego="GHI789", odometer=8000,
            transmission="MANUAL", engine_size="750cc"
        )
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

