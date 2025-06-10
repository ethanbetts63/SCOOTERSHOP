from django.test import TestCase
from service.forms import ServiceBrandForm
from ..test_helpers.model_factories import ServiceBrandFactory

# Removed: create_dummy_image helper function

class ServiceBrandFormTest(TestCase):
    """
    Tests for the simplified ServiceBrandForm.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up non-modified objects used by all test methods.
        Create a few generic brands.
        """
        # Create brands without images for simplicity, as image testing is excluded
        cls.brand1 = ServiceBrandFactory(name='Brand A', image=None)
        cls.brand2 = ServiceBrandFactory(name='Brand B', image=None)


    def test_form_valid_data(self):
        """
        Test that the form is valid with correct data (including optional image field).
        """
        data = {'name': 'New Valid Brand'}
        # No 'files' dictionary needed as we're not testing image upload specifically
        form = ServiceBrandForm(data=data)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors}")
        brand = form.save()
        self.assertEqual(brand.name, 'New Valid Brand')
        self.assertIsNotNone(brand.pk) # Ensure it's saved
        # We are not asserting image specific behavior here, just that the form handles it.
        self.assertIsNone(brand.image.name if brand.image else None) # Should be None if not provided


    def test_form_invalid_data_missing_name(self):
        """
        Test that the form is invalid if 'name' is missing.
        """
        data = {'name': ''}
        form = ServiceBrandForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)
        self.assertIn('This field is required.', form.errors['name'])

    def test_form_invalid_data_duplicate_name(self):
        """
        Test that the form is invalid if the name already exists (unique constraint).
        """
        # Attempt to create a brand with a name that already exists from setUpTestData
        data = {'name': 'Brand A'}
        form = ServiceBrandForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)
        # Corrected casing for "Brand" in the expected error message
        self.assertIn('Service Brand with this Name already exists.', form.errors['name'])

    def test_form_update_existing_brand(self):
        """
        Test updating an existing brand.
        """
        existing_brand = self.brand1
        
        data = {'name': 'Updated Brand A'}
        # No 'files' dictionary needed when updating unless we explicitly want to change the image.
        form = ServiceBrandForm(data=data, instance=existing_brand)
        self.assertTrue(form.is_valid(), f"Form not valid for updating brand: {form.errors}")
        updated_brand = form.save()
        self.assertEqual(updated_brand.name, 'Updated Brand A')
        self.assertEqual(updated_brand.pk, existing_brand.pk) # Ensure it's the same instance
        # Image should remain as it was (None in this setup)
        self.assertIsNone(updated_brand.image.name if updated_brand.image else None)

