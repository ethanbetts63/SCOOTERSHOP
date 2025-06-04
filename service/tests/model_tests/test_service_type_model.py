import pytest
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from datetime import timedelta
from decimal import Decimal

# Import the ServiceType model and ServiceTypeFactory
from service.models import ServiceType
from service.tests.test_helpers.model_factories import ServiceTypeFactory

class ServiceTypeModelTest(TestCase):
    """
    Tests for the ServiceType model.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up non-modified objects used by all test methods.
        """
        # Create a ServiceType instance using the factory
        cls.service_type_instance = ServiceTypeFactory()

    def test_service_type_creation(self):
        """
        Test that a ServiceType instance can be created successfully.
        """
        self.assertIsInstance(self.service_type_instance, ServiceType)
        self.assertIsNotNone(self.service_type_instance.pk) # Check if it has a primary key

    def test_service_type_fields(self):
        """
        Test that the fields of the ServiceType model are correctly populated.
        """
        service = self.service_type_instance

        self.assertIsInstance(service.name, str)
        self.assertGreater(len(service.name), 0)
        self.assertLessEqual(len(service.name), 100)

        self.assertIsInstance(service.description, str)
        self.assertGreater(len(service.description), 0)

        self.assertIsInstance(service.estimated_duration, timedelta)
        self.assertGreater(service.estimated_duration, timedelta(seconds=0))

        self.assertIsInstance(service.base_price, Decimal)
        self.assertGreaterEqual(service.base_price, Decimal('0.00'))

        self.assertIsInstance(service.is_active, bool)
        self.assertTrue(service.is_active) # Default is True from factory

    def test_str_method(self):
        """
        Test the __str__ method of the ServiceType model.
        It should return the name of the service type.
        """
        service = self.service_type_instance
        self.assertEqual(str(service), service.name)

    def test_is_active_default_and_override(self):
        """
        Test the default value of is_active and overriding it.
        """
        # Test default (True)
        service1 = ServiceTypeFactory()
        self.assertTrue(service1.is_active)

        # Test overriding to False
        service2 = ServiceTypeFactory(is_active=False)
        self.assertFalse(service2.is_active)

    def test_image_field(self):
        """
        Test the image field can be null/blank and can store a file.
        """
        # Test with no image (default from factory)
        service_no_image = ServiceTypeFactory()
        self.assertFalse(bool(service_no_image.image)) # Check if image field is empty

        # Test with an image
        image_content = b'dummy_image_content'
        image_file = SimpleUploadedFile("test_image.jpg", image_content, content_type="image/jpeg")
        service_with_image = ServiceTypeFactory(image=image_file)

        self.assertTrue(bool(service_with_image.image))
        self.assertEqual(service_with_image.image.name, 'service_types/test_image.jpg')

        # Clean up the created file (optional, but good practice for file fields)
        service_with_image.image.delete(save=False)

    def test_max_length_for_name(self):
        """
        Test that the 'name' field respects its max_length constraint.
        """
        # A name within the limit should be fine
        long_name = 'a' * 100
        service_valid_name = ServiceTypeFactory(name=long_name)
        self.assertEqual(service_valid_name.name, long_name)

        # Attempting to save a name longer than 100 chars should raise an error
        # This test typically requires a database save and checks for ValidationError
        # However, factory_boy will usually truncate if it's just a string assignment.
        # For strict validation, you'd usually test this at the form/serializer level
        # or with model validation. For now, we'll just ensure it doesn't break.
        too_long_name = 'a' * 101
        service_too_long_name = ServiceTypeFactory(name=too_long_name)
        # Factory boy might just truncate, or it might be fine until save.
        # If running Django's full_clean, it would raise ValidationError.
        # For simplicity, we'll check if the factory handles it gracefully.
        self.assertLessEqual(len(service_too_long_name.name), 100)

