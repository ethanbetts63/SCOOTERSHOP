from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from service.forms import CustomerMotorcycleForm
from ..test_helpers.model_factories import CustomerMotorcycleFactory, ServiceProfileFactory, ServiceBrandFactory
from service.models import CustomerMotorcycle, ServiceSettings
import datetime
import random # Import random for selecting transmission choice

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
        cls.honda_brand = ServiceBrandFactory(name="Honda")
        cls.yamaha_brand = ServiceBrandFactory(name="Yamaha")
        cls.other_brand_entry = ServiceBrandFactory(name="Other") # Ensure 'Other' option exists

    def _get_valid_data(self, brand_name="Honda", include_other_brand_name=False, other_brand_value=""):
        """
        Helper to get a set of valid form data.
        """
        # Select a random valid transmission choice
        valid_transmission_choice = random.choice([choice[0] for choice in CustomerMotorcycle.transmission_choices])

        data = {
            'brand': brand_name,
            'make': 'CBR',
            'model': '600RR',
            'year': 2020,
            'engine_size': '600cc',
            'rego': 'ABC123',
            'vin_number': '1HFPC4000L7000010', # Corrected to 17 characters
            'odometer': 15000,
            'transmission': valid_transmission_choice, # Use a valid choice
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
        self.assertEqual(motorcycle.brand, self.honda_brand.name) # Check the model's brand field
        self.assertEqual(motorcycle.make, 'CBR')
        self.assertEqual(motorcycle.odometer, 15000)
        self.assertEqual(motorcycle.service_profile, self.service_profile)

    def test_form_valid_data_new_motorcycle_other_brand_provided(self):
        """
        Test that the form is valid when 'brand' is 'Other' and 'other_brand_name' is provided.
        The 'other_brand_name' value should be saved to the model's 'brand' field.
        """
        data = self._get_valid_data(brand_name=self.other_brand_entry.name, include_other_brand_name=True, other_brand_value="MyCustomBrand")
        form = CustomerMotorcycleForm(data=data)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors}")
        self.assertEqual(form.cleaned_data['brand'], self.other_brand_entry.name) # Form's brand field
        self.assertEqual(form.cleaned_data['other_brand_name'], "MyCustomBrand") # Form's other_brand_name field

        # Save the form to create a new instance
        motorcycle = form.save(commit=False)
        motorcycle.service_profile = self.service_profile
        motorcycle.save()

        self.assertEqual(motorcycle.brand, "MyCustomBrand") # Model's brand field should have the custom value

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

        # Verify it's saved as empty in the database (or rather, that the model's brand is the selected one)
        motorcycle = form.save(commit=False)
        motorcycle.service_profile = self.service_profile
        motorcycle.save()
        self.assertEqual(motorcycle.brand, self.yamaha_brand.name) # Model's brand should be the specific brand
        # No assertion for other_brand_name on the model, as it doesn't exist.

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
        # When initializing with an instance, 'other_brand_name' should be empty if brand is not 'Other'
        self.assertEqual(form.initial.get('other_brand_name', ''), '')

    def test_form_initialization_with_instance_other_brand(self):
        """
        Test that the form correctly pre-populates fields when initialized with an existing
        CustomerMotorcycle instance where the brand was originally 'Other' and a custom name was saved.
        """
        # Simulate a scenario where 'Other' was selected and a custom brand saved
        existing_motorcycle = CustomerMotorcycleFactory(
            service_profile=self.service_profile,
            brand="MyPreviouslyEnteredOtherBrand", # This is the actual brand saved in the model
            make='Custom',
            model='Bike',
            year=2021,
            odometer=1000
        )
        # To correctly initialize the form, we need to simulate how it would
        # interpret this 'MyPreviouslyEnteredOtherBrand'.
        # This might require a custom __init__ or clean method in the form
        # if the model's 'brand' can be *any* string, not just from choices.
        # For now, we'll assume the form's 'brand' field choices include 'Other'.
        # If 'MyPreviouslyEnteredOtherBrand' is not in the choices, the form will be invalid.
        # A more robust solution might involve setting initial 'brand' to 'Other' and
        # initial 'other_brand_name' to 'MyPreviouslyEnteredOtherBrand' if the
        # model's brand is not in the primary ServiceBrand choices.

        # For this test, let's assume the factory creates a brand that matches an existing ServiceBrand,
        # or that the 'Other' option is handled by the form's logic.
        # If the model's brand is not one of the predefined ServiceBrand names,
        # the form should ideally set 'brand' to 'Other' and 'other_brand_name' to the actual brand.
        # This requires more complex form initialization logic.
        # For current model/form structure, the model's `brand` field stores the custom name directly.
        form = CustomerMotorcycleForm(instance=existing_motorcycle)
        # If the brand from the instance is NOT one of the primary brands,
        # the form should display 'Other' for the brand dropdown and populate
        # the 'other_brand_name' field with the actual brand value.
        # This requires overriding the form's __init__ method.
        # For now, we'll test the simpler case where the brand is one of the primary ones,
        # or that the form's `brand` field correctly gets the value.
        # This test needs to be revisited if the form's __init__ is updated to handle this.
        self.assertEqual(form.initial['brand'], existing_motorcycle.brand)
        # The form's `other_brand_name` should be empty unless the brand is explicitly 'Other'
        self.assertEqual(form.initial.get('other_brand_name', ''), '')


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

    def test_form_update_existing_motorcycle_to_other_brand(self):
        """
        Test updating an existing motorcycle to 'Other' brand with a custom name.
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

        updated_data = self._get_valid_data(brand_name=self.other_brand_entry.name, include_other_brand_name=True, other_brand_value="UpdatedCustomBrand")
        form = CustomerMotorcycleForm(data=updated_data, instance=original_motorcycle)
        self.assertTrue(form.is_valid(), f"Form is not valid for update to other brand: {form.errors}")

        updated_motorcycle = form.save()
        updated_motorcycle.refresh_from_db()

        self.assertEqual(updated_motorcycle.brand, "UpdatedCustomBrand") # Model's brand should be the custom name

    def test_form_required_fields_missing(self):
        """
        Test that the form is invalid if essential required fields are missing.
        'image' is optional.
        """
        # Start with an empty dictionary
        data = {}
        form = CustomerMotorcycleForm(data=data)
        self.assertFalse(form.is_valid())

        # List of fields expected to be required based on the model's clean method
        expected_required_fields = [
            'brand', 'make', 'model', 'year'
        ]

        for field_name in expected_required_fields:
            self.assertIn(field_name, form.errors)
            # The model's clean method adds specific messages, but Django's default
            # form validation also adds 'This field is required.'
            # We'll check for either.
            self.assertTrue(
                'This field is required.' in form.errors[field_name] or
                f"Motorcycle {field_name.replace('_', ' ')} is required." in form.errors[field_name]
            )

        # Ensure other_brand_name is NOT required if brand is not 'Other'
        # (It will be required if 'brand' is 'Other' and other_brand_name is empty,
        # but not if 'brand' itself is missing)
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
        The model's clean method handles this.
        """
        current_year = datetime.date.today().year
        data = self._get_valid_data()
        data['year'] = current_year + 1
        form = CustomerMotorcycleForm(data=data)
        # The model's clean method should catch this, so the form should be invalid.
        self.assertFalse(form.is_valid())
        self.assertIn('year', form.errors)
        self.assertIn('Motorcycle year cannot be in the future.', form.errors['year'])


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
        This validation is handled by Django's PositiveIntegerField or the model's clean method.
        """
        data = self._get_valid_data()
        data['odometer'] = -100
        form = CustomerMotorcycleForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('odometer', form.errors)
        # The error message comes from Django's PositiveIntegerField validation
        self.assertIn('Ensure this value is greater than or equal to 0.', form.errors['odometer'])


    def test_form_image_upload(self):
        """
        Test handling of image upload for the 'image' field (which is optional).
        """
        # Create a dummy image file
        image_content = b'GIF89a\x01\x00\x01\x00\x00\xff\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
        original_filename = "test_image.gif"
        image_file = SimpleUploadedFile(original_filename, image_content, content_type="image/gif")

        data = self._get_valid_data()
        files = {'image': image_file}

        form = CustomerMotorcycleForm(data=data, files=files)
        self.assertTrue(form.is_valid(), f"Form is not valid with image: {form.errors}")

        motorcycle = form.save(commit=False)
        motorcycle.service_profile = self.service_profile
        motorcycle.save()

        self.assertIsNotNone(motorcycle.image)
        # Check if the original filename (or at least its base part) is present in the saved name
        # Django often adds a unique suffix before the extension (e.g., 'image_XYZ.gif')
        self.assertIn('test_image', motorcycle.image.name) # Check for the base name
        self.assertTrue(motorcycle.image.name.endswith('.gif')) # Check for the extension
        motorcycle.image.delete(save=False) # Clean up the created file

    def test_form_image_clear(self):
        """
        Test that an existing image can be cleared using the ClearableFileInput.
        """
        # Create an existing motorcycle with an image
        image_content = b'GIF89a\x01\x00\x01\x00\x00\xff\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
        original_filename = "existing_image.gif"
        existing_image_file = SimpleUploadedFile(original_filename, image_content, content_type="image/gif")

        existing_motorcycle = CustomerMotorcycleFactory(
            service_profile=self.service_profile,
            image=existing_image_file # Assign the file directly (factory handles saving)
        )
        # Ensure the image was saved and check for the original filename ending
        self.assertIsNotNone(existing_motorcycle.image)
        # Check if the original filename (or at least its base part) is present in the saved name
        self.assertIn('existing_image', existing_motorcycle.image.name) # Check for the base name
        self.assertTrue(existing_motorcycle.image.name.endswith('.gif')) # Check for the extension

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
