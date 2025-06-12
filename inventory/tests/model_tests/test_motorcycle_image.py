from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile # For testing FileField
import os # For file path operations

# Import the MotorcycleImage and Motorcycle models
from inventory.models import Motorcycle, MotorcycleImage
from django.db import models
# Import the MotorcycleFactory and MotorcycleImageFactory from your factories file
from ..test_helpers.model_factories import MotorcycleFactory, MotorcycleImageFactory


class MotorcycleImageModelTest(TestCase):
    """
    Tests for the MotorcycleImage model.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up non-modified objects used by all test methods.
        We'll create a Motorcycle and an associated MotorcycleImage.
        """
        cls.motorcycle = MotorcycleFactory(brand='TestBrand', model='TestModel', year=2020)
        cls.motorcycle_image = MotorcycleImageFactory(motorcycle=cls.motorcycle)

    def test_motorcycle_image_creation(self):
        """
        Test that a MotorcycleImage instance can be created successfully using the factory.
        """
        self.assertIsInstance(self.motorcycle_image, MotorcycleImage)
        self.assertIsNotNone(self.motorcycle_image.pk) # Check if it has a primary key (saved to DB)

        # Verify the foreign key relationship
        self.assertEqual(self.motorcycle_image.motorcycle, self.motorcycle)

    def test_motorcycle_field(self):
        """
        Test the 'motorcycle' ForeignKey field properties.
        """
        field = self.motorcycle_image._meta.get_field('motorcycle')
        self.assertIsInstance(field, type(MotorcycleImage._meta.get_field('motorcycle'))) # Ensure it's a ForeignKey
        self.assertEqual(field.related_model, Motorcycle) # Check related model
        self.assertEqual(field._related_name, 'images') # Check related_name

    def test_image_field(self):
        """
        Test the 'image' FileField properties.
        """
        field = self.motorcycle_image._meta.get_field('image')
        self.assertIsInstance(field, models.FileField) # Ensure it's a FileField
        self.assertEqual(field.upload_to, 'motorcycles/additional/') # Check upload_to path

        # Test that the image file exists and has content
        self.assertTrue(self.motorcycle_image.image)
        self.assertGreater(self.motorcycle_image.image.size, 0)
        

    def test_str_method(self):
        """
        Test the __str__ method of MotorcycleImage.
        """
        expected_str = f"Image for {self.motorcycle}"
        self.assertEqual(str(self.motorcycle_image), expected_str)

    def test_verbose_names_meta(self):
        """
        Test the Meta 'verbose_name' and 'verbose_name_plural' options
        (Django's defaults if not explicitly set in the model).
        """
        self.assertEqual(MotorcycleImage._meta.verbose_name, "motorcycle image")
        self.assertEqual(MotorcycleImage._meta.verbose_name_plural, "motorcycle images")

