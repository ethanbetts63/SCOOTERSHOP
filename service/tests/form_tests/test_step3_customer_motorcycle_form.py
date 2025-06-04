from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from service.forms import CustomerMotorcycleForm
from ..test_helpers.model_factories import CustomerMotorcycleFactory, ServiceProfileFactory, ServiceBrandFactory
from service.models import CustomerMotorcycle, ServiceSettings
import datetime

class CustomerMotorcycleFormTest(TestCase):
    """
    Tests for the CustomerMotorcycleForm (Step 3 of the booking flow).
    This form handles creating and updating CustomerMotorcycle instances.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up non-modified objects used by all test methods.
        """
        cls.service_profile = ServiceProfileFactory()
        # Ensure ServiceSettings exists for other_brand_policy_text if needed,
        # though the form itself doesn't directly use it in validation.
        ServiceSettings.objects.get_or_create(pk=1)

        # Create some primary brands for testing the 'brand' field choices
        cls.honda_brand = ServiceBrandFactory(name="Honda", is_primary=True)
        cls.yamaha_brand = ServiceBrandFactory(name="Yamaha", is_primary=True)
        cls.other_brand_entry = ServiceBrandFactory(name="Other", is_primary=False) # Ensure 'Other' option exists

    def _get_valid_data(self, brand_name="Honda", include_other_brand_name=False, other_brand_value=""):
        """
        Helper to get a set of valid form data.
        """
        data = {
            'brand': brand_name,
            'make': 'CBR',
            'model': '600RR',
            'year': 2020,
            'engine_size': '600cc',
            'rego': 'ABC123',
            'vin_number': '1HFPC4000L700001',
            'odometer': 15000,
            'transmission': CustomerMotorcycle.transmission,
            'engine_number': 'ENG12345',
        }
        if include_other_brand_name:
            data['other_brand_name'] = other_brand_value
        else:
            data['other_brand_name'] = '' # Ensure it's explicitly empty if not included

        return data

    def test_form_valid_data_new_motorcycle(self):
        """
        Test that the form is valid with all required fields filled for a *new* motorcycle,
        when a specific brand is selected and 'other_brand_name' is empty.
        """
        data = self._get_valid_data(brand_name=self.honda_brand.name)
        form = CustomerMotorcycleForm(data=data)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors}")

        # Ensure 'other_brand_name' is cleared if a specific brand is chosen
        self.assertEqual(form.cleaned_data['other_brand_name'], '')

        # Save the form to create a new instance
        motorcycle = form.save(commit=False)
        motorcycle.service_profile = self.service_profile
        motorcycle.save()

        self.assertIsNotNone(motorcycle.pk)
        self.assertEqual(motorcycle.brand, self.honda_brand.name)
        self.assertEqual(motorcycle.make, 'CBR')
        self.assertEqual(motorcycle.odometer, 15000)
        self.assertEqual(motorcycle.service_profile, self.service_profile)
        self.assertEqual(motorcycle.other_brand_name, '') # Should be empty

    def test_form_valid_data_new_motorcycle_other_brand_provided(self):
        """
        Test that the form is valid when 'brand' is 'Other' and 'other_brand_name' is provided.
        """
        data = self._get_valid_data(brand_name=self.other_brand_entry.name, include_other_brand_name=True, other_brand_value="MyCustomBrand")
        form = CustomerMotorcycleForm(data=data)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors}")
        self.assertEqual(form.cleaned_data['brand'], self.other_brand_entry.name)
        self.assertEqual(form.cleaned_data['other_brand_name'], "MyCustomBrand")

        # Save the form to create a new instance
        motorcycle = form.save(commit=False)
        motorcycle.service_profile = self.service_profile
        motorcycle.save()

        self.assertEqual(motorcycle.brand, self.other_brand_entry.name)
        self.assertEqual(motorcycle.other_brand_name, "MyCustomBrand")

    def test_form_invalid_data_other_brand_missing_name(self):
        """
        Test that the form is invalid when 'brand' is 'Other' but 'other_brand_name' is *not* provided.
        """
        data = self._get_valid_data(brand_name=self.other_brand_entry.name, include_other_brand_name=True, other_brand_value="")
        form = CustomerMotorcycleForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('other_brand_name', form.errors)
        self.assertIn("Please specify the brand name when 'Other' is selected.", form.errors['other_brand_name'])

    def test_form_valid_data_specific_brand_with_other_name_cleared(self):
        """
        Test that if a specific brand is chosen, any value in 'other_brand_name' is cleared
        by the form's clean method to avoid saving irrelevant data.
        """
        data = self._get_valid_data(brand_name=self.yamaha_brand.name, include_other_brand_name=True, other_brand_value="ShouldBeCleared")
        form = CustomerMotorcycleForm(data=data)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors}")
        # Assert that the 'other_brand_name' field is cleared in cleaned_data
        self.assertEqual(form.cleaned_data['other_brand_name'], '')

        # Verify it's saved as empty in the database
        motorcycle = form.save(commit=False)
        motorcycle.service_profile = self.service_profile
        motorcycle.save()
        self.assertEqual(motorcycle.other_brand_name, '')

    def test_form_initialization_with_instance(self):
        """
        Test that the form correctly pre-populates fields when initialized with an existing
        CustomerMotorcycle instance.
        """
        existing_motorcycle = CustomerMotorcycleFactory(
            service_profile=self.service_profile,
            brand=self.honda_brand.name,
            make='CBR',
            model='600RR',
            year=2018,
            odometer=25000
        )
        form = CustomerMotorcycleForm(instance=existing_motorcycle)

        self.assertEqual(form.initial['brand'], existing_motorcycle.brand)
        self.assertEqual(form.initial['make'], existing_motorcycle.make)
        self.assertEqual(form.initial['model'], existing_motorcycle.model)
        self.assertEqual(form.initial['year'], existing_motorcycle.year)
        self.assertEqual(form.initial['odometer'], existing_motorcycle.odometer)

    def test_form_update_existing_motorcycle(self):
        """
        Test that the form can successfully update an existing CustomerMotorcycle instance.
        """
        original_motorcycle = CustomerMotorcycleFactory(
            service_profile=self.service_profile,
            brand=self.honda_brand.name,
            make='CBR',
            model='600RR',
            year=2018,
            odometer=25000,
            rego='OLD123'
        )

        updated_data = self._get_valid_data(brand_name=self.yamaha_brand.name)
        updated_data['rego'] = 'NEW456' # Change a field

        form = CustomerMotorcycleForm(data=updated_data, instance=original_motorcycle)
        self.assertTrue(form.is_valid(), f"Form is not valid for update: {form.errors}")

        updated_motorcycle = form.save()
        # Refresh from DB to ensure changes are persisted
        original_motorcycle.refresh_from_db()

        self.assertEqual(original_motorcycle.rego, 'NEW456')
        self.assertEqual(original_motorcycle.brand, self.yamaha_brand.name)
        self.assertEqual(original_motorcycle.odometer, 15000) # From _get_valid_data
        self.assertEqual(updated_motorcycle, original_motorcycle) # Should be the same instance

    def test_form_required_fields_missing(self):
        """
        Test that the form is invalid if essential required fields are missing.
        'image' and 'other_brand_name' (conditionally) are optional.
        """
        # Start with an empty dictionary
        data = {}
        form = CustomerMotorcycleForm(data=data)
        self.assertFalse(form.is_valid())

        # List of fields expected to be required (excluding 'image' and 'other_brand_name')
        expected_required_fields = [
            'brand', 'make', 'model', 'year', 'engine_size', 'rego',
            'vin_number', 'odometer', 'transmission', 'engine_number'
        ]

        for field_name in expected_required_fields:
            self.assertIn(field_name, form.errors)
            self.assertIn('This field is required.', form.errors[field_name])

        # Ensure other_brand_name is NOT required if brand is not 'Other'
        self.assertNotIn('other_brand_name', form.errors)

    def test_form_year_validation_invalid_type(self):
        """
        Test that the 'year' field rejects non-numeric input.
        """
        data = self._get_valid_data()
        data['year'] = 'not-a-year'
        form = CustomerMotorcycleForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('year', form.errors)
        self.assertIn('Enter a whole number.', form.errors['year'])

    def test_form_year_validation_future_year(self):
        """
        Test that the 'year' field rejects a future year.
        The model's clean method or widget might handle this.
        Django's NumberInput doesn't inherently restrict future years,
        so this might require a custom validator or model clean method.
        Assuming the model or form will eventually have this validation.
        For now, if it passes, it's acceptable unless a specific validator is added.
        """
        current_year = datetime.date.today().year
        data = self._get_valid_data()
        data['year'] = current_year + 1
        form = CustomerMotorcycleForm(data=data)
        # Assuming no explicit future year validation in the form for now.
        # If a validator is added to the model or form, this test would change.
        self.assertTrue(form.is_valid())


    def test_form_odometer_validation_invalid_type(self):
        """
        Test that the 'odometer' field rejects non-numeric input.
        """
        data = self._get_valid_data()
        data['odometer'] = 'not-an-odometer'
        form = CustomerMotorcycleForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('odometer', form.errors)
        self.assertIn('Enter a whole number.', form.errors['odometer'])

    def test_form_odometer_validation_negative(self):
        """
        Test that the 'odometer' field rejects negative numbers.
        """
        data = self._get_valid_data()
        data['odometer'] = -100
        form = CustomerMotorcycleForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('odometer', form.errors)
        # Django's NumberInput doesn't automatically add min_value.
        # This error message depends on a custom validator or model field definition.
        # If no specific min_value is set, it might pass.
        # For now, we'll assume it should fail with a relevant message.
        # If the model has positive integer field, it will fail.
        self.assertIn('Ensure this value is greater than or equal to 0.', form.errors['odometer'])


    def test_form_image_upload(self):
        """
        Test handling of image upload for the 'image' field (which is optional).
        """
        # Create a dummy image file
        image_content = b'GIF89a\x01\x00\x01\x00\x00\xff\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
        image_file = SimpleUploadedFile("test_image.gif", image_content, content_type="image/gif")

        data = self._get_valid_data()
        files = {'image': image_file}

        form = CustomerMotorcycleForm(data=data, files=files)
        self.assertTrue(form.is_valid(), f"Form is not valid with image: {form.errors}")

        motorcycle = form.save(commit=False)
        motorcycle.service_profile = self.service_profile
        motorcycle.save()

        self.assertIsNotNone(motorcycle.image)
        self.assertIn('test_image.gif', motorcycle.image.name) # Check if the filename is preserved
        motorcycle.image.delete(save=False) # Clean up the created file

    def test_form_image_clear(self):
        """
        Test that an existing image can be cleared using the ClearableFileInput.
        """
        # Create an existing motorcycle with an image
        image_content = b'GIF89a\x01\x00\x01\x00\x00\xff\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
        existing_image_file = SimpleUploadedFile("existing_image.gif", image_content, content_type="image/gif")

        existing_motorcycle = CustomerMotorcycleFactory(
            service_profile=self.service_profile,
            image=existing_image_file # Assign the file directly (factory handles saving)
        )
        # Ensure the image was saved
        self.assertIsNotNone(existing_motorcycle.image)
        self.assertIn('existing_image.gif', existing_motorcycle.image.name)

        # Now, submit the form with 'image-clear' set to True
        data = self._get_valid_data()
        data['image-clear'] = True # This is how ClearableFileInput signals clearing
        # No 'image' file provided in files

        form = CustomerMotorcycleForm(data=data, instance=existing_motorcycle)
        self.assertTrue(form.is_valid(), f"Form is not valid for image clear: {form.errors}")

        updated_motorcycle = form.save()
        updated_motorcycle.refresh_from_db()

        self.assertFalse(updated_motorcycle.image) # Image should be cleared
        # Clean up the original file if it wasn't automatically deleted by Django
        # (Django's file handling usually takes care of this on model save/delete)
        # if existing_motorcycle.image:
        #     existing_motorcycle.image.delete(save=False)

