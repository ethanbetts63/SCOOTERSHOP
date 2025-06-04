from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from datetime import datetime

# Import the ServiceBrand model
from service.models import ServiceBrand

# Import the ServiceBrandFactory from your factories file
# Adjust the import path if your model_factories.py is in a different location
from ..test_helpers.model_factories import ServiceBrandFactory

class ServiceBrandModelTest(TestCase):
    """
    Tests for the ServiceBrand model.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up non-modified objects used by all test methods.
        We'll create a single ServiceBrand instance using the factory.
        """
        cls.service_brand = ServiceBrandFactory()

    def test_service_brand_creation(self):
        """
        Test that a ServiceBrand instance can be created successfully using the factory.
        """
        self.assertIsInstance(self.service_brand, ServiceBrand)
        self.assertIsNotNone(self.service_brand.pk) # Check if it has a primary key (saved to DB)

    def test_name_field(self):
        """
        Test the 'name' field properties.
        """
        service_brand = self.service_brand
        self.assertEqual(service_brand._meta.get_field('name').max_length, 100)
        self.assertTrue(service_brand._meta.get_field('name').unique)
        self.assertIsInstance(service_brand.name, str)
        self.assertIsNotNone(service_brand.name)
        self.assertEqual(service_brand._meta.get_field('name').help_text, "Name of the service brand (e.g., 'Yamaha', 'Vespa').")

    def test_is_primary_field(self):
        """
        Test the 'is_primary' field properties and default value.
        """
        service_brand = self.service_brand
        self.assertIsInstance(service_brand.is_primary, bool)
        self.assertEqual(service_brand.is_primary, False) # Factory sets it to False by default
        self.assertEqual(service_brand._meta.get_field('is_primary').help_text, "Check if this is a primary brand to display prominently (limited to 5 total).")

        # Test with is_primary set to True
        primary_brand = ServiceBrandFactory(name="Primary Brand Test", is_primary=True)
        self.assertEqual(primary_brand.is_primary, True)

    def test_image_field(self):
        """
        Test the 'image' field properties.
        """
        service_brand = self.service_brand
        image_field = service_brand._meta.get_field('image')
        self.assertTrue(image_field.null)
        self.assertTrue(image_field.blank)
        self.assertEqual(image_field.upload_to, 'brands/')
        self.assertEqual(image_field.help_text, "Optional image for primary brands. Only used if 'Is Primary' is checked.")

        # Test saving with a dummy image
        dummy_image = SimpleUploadedFile("test_image.jpg", b"file_content", content_type="image/jpeg")
        brand_with_image = ServiceBrandFactory(name="Brand with Image", image=dummy_image, is_primary=True)
        self.assertIsNotNone(brand_with_image.image)
        self.assertIn('brands/', brand_with_image.image.name) # Check if path is correct

    def test_last_updated_field(self):
        """
        Test the 'last_updated' field properties.
        """
        service_brand = self.service_brand
        self.assertIsInstance(service_brand.last_updated, datetime)
        # Check that auto_now updates the field on save
        old_last_updated = service_brand.last_updated
        service_brand.name = "Updated Name"
        service_brand.save()
        self.assertGreater(service_brand.last_updated, old_last_updated)

    def test_str_method(self):
        """
        Test the __str__ method of the ServiceBrand model.
        It should return the name of the service brand.
        """
        service_brand = self.service_brand
        self.assertEqual(str(service_brand), service_brand.name)

    def test_verbose_name_plural(self):
        """
        Test the verbose name plural for the model.
        """
        self.assertEqual(str(ServiceBrand._meta.verbose_name_plural), 'Service Brands')

    def test_unique_name_constraint(self):
        """
        Test that the 'name' field is unique.
        Attempting to create a brand with an existing name should raise an IntegrityError.
        """
        # Create an initial brand
        initial_brand = ServiceBrandFactory()
        existing_name = initial_brand.name

        # Attempt to create another brand with the exact same name directly using the model
        # This will force a database insert attempt, triggering the IntegrityError
        with self.assertRaises(IntegrityError):
            # is_primary is a non-nullable field, so it must be provided
            ServiceBrand.objects.create(name=existing_name, is_primary=False)

    def test_primary_brand_limit(self):
        """
        Test the custom save method logic for limiting primary brands to 5.
        """
        # Ensure we start with no primary brands for a clean test
        ServiceBrand.objects.all().delete()

        # Create 5 primary brands - this should succeed
        primary_brands = []
        for i in range(5):
            brand = ServiceBrandFactory(name=f"Primary Brand {i+1}", is_primary=True)
            primary_brands.append(brand)
            self.assertEqual(ServiceBrand.objects.filter(is_primary=True).count(), i + 1)

        # Attempt to create a 6th primary brand - this should fail
        with self.assertRaisesMessage(ValueError, "Cannot have more than 5 primary brands."):
            ServiceBrandFactory(name="Primary Brand 6", is_primary=True)

        # Verify that only 5 primary brands exist
        self.assertEqual(ServiceBrand.objects.filter(is_primary=True).count(), 5)

        # Test updating an existing non-primary brand to primary when limit is reached
        non_primary_brand = ServiceBrandFactory(name="Non-Primary Brand", is_primary=False)
        self.assertEqual(ServiceBrand.objects.filter(is_primary=True).count(), 5) # Still 5 primary

        non_primary_brand.is_primary = True
        with self.assertRaisesMessage(ValueError, "Cannot have more than 5 primary brands."):
            non_primary_brand.save()

        # Test updating an existing primary brand (it should not count itself)
        # Change one of the existing primary brands' name and save
        first_primary_brand = primary_brands[0]
        old_name = first_primary_brand.name
        first_primary_brand.name = "Updated Primary Brand 1"
        first_primary_brand.save() # This should succeed
        self.assertEqual(ServiceBrand.objects.filter(is_primary=True).count(), 5)
        self.assertFalse(ServiceBrand.objects.filter(name=old_name).exists())
        self.assertTrue(ServiceBrand.objects.filter(name="Updated Primary Brand 1").exists())

        # Test changing a primary brand to non-primary
        primary_brands[1].is_primary = False
        primary_brands[1].save()
        self.assertEqual(ServiceBrand.objects.filter(is_primary=True).count(), 4)

        # Now, creating a new primary brand should succeed as we are below the limit
        new_primary_brand = ServiceBrandFactory(name="New Primary Brand After Removal", is_primary=True)
        self.assertEqual(ServiceBrand.objects.filter(is_primary=True).count(), 5)
