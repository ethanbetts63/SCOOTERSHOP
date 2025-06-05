from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from service.forms import CustomerMotorcycleForm
from ..test_helpers.model_factories import CustomerMotorcycleFactory, ServiceProfileFactory, ServiceBrandFactory
from service.models import CustomerMotorcycle, ServiceSettings
import datetime
import random

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
        ServiceSettings.objects.get_or_create(pk=1)

        cls.honda_brand = ServiceBrandFactory(name="Honda")
        cls.yamaha_brand = ServiceBrandFactory(name="Yamaha")
        # Ensure 'Other' option exists in the form choices, though it's not a ServiceBrand model instance
        # It's handled by the form's __init__ adding it to choices.
        # We don't need a ServiceBrandFactory(name="Other") here if 'Other' is always a form choice.

    def _get_valid_data(self, brand_name="Honda", include_other_brand_name=False, other_brand_value=""):
        valid_transmission_choice = random.choice([choice[0] for choice in CustomerMotorcycle.transmission_choices])

        data = {
            'brand': brand_name,
            'model': '600RR',
            'year': 2020,
            'engine_size': '600cc',
            'rego': 'ABC123',
            'vin_number': '1HFPC4000L7000010',
            'odometer': 15000,
            'transmission': valid_transmission_choice,
            'engine_number': 'ENG12345',
        }
        if include_other_brand_name:
            data['other_brand_name'] = other_brand_value
        else:
            data['other_brand_name'] = ''

        return data

    def test_form_valid_data_new_motorcycle(self):
        data = self._get_valid_data(brand_name=self.honda_brand.name)
        form = CustomerMotorcycleForm(data=data)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors}")
        self.assertEqual(form.cleaned_data['other_brand_name'], '')
        motorcycle = form.save(commit=False)
        motorcycle.service_profile = self.service_profile
        motorcycle.save()
        self.assertIsNotNone(motorcycle.pk)
        self.assertEqual(motorcycle.brand, self.honda_brand.name)
        self.assertEqual(motorcycle.odometer, 15000)
        self.assertEqual(motorcycle.service_profile, self.service_profile)

    def test_form_valid_data_new_motorcycle_other_brand_provided(self):
        # Pass 'Other' as the brand name, and the custom value in other_brand_value
        data = self._get_valid_data(brand_name='Other', include_other_brand_name=True, other_brand_value="MyCustomBrand")
        form = CustomerMotorcycleForm(data=data)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors}")
        self.assertEqual(form.cleaned_data['brand'], 'Other')
        self.assertEqual(form.cleaned_data['other_brand_name'], "MyCustomBrand")

        motorcycle = form.save(commit=False)
        motorcycle.service_profile = self.service_profile
        motorcycle.save()
        self.assertEqual(motorcycle.brand, "MyCustomBrand")

    def test_form_invalid_data_other_brand_missing_name(self):
        data = self._get_valid_data(brand_name='Other', include_other_brand_name=True, other_brand_value="")
        form = CustomerMotorcycleForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('other_brand_name', form.errors)
        self.assertIn("Please specify the brand name when 'Other' is selected.", form.errors['other_brand_name'])

    def test_form_valid_data_specific_brand_with_other_name_cleared(self):
        data = self._get_valid_data(brand_name=self.yamaha_brand.name, include_other_brand_name=True, other_brand_value="ShouldBeCleared")
        form = CustomerMotorcycleForm(data=data)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors}")
        self.assertEqual(form.cleaned_data['other_brand_name'], '')
        motorcycle = form.save(commit=False)
        motorcycle.service_profile = self.service_profile
        motorcycle.save()
        self.assertEqual(motorcycle.brand, self.yamaha_brand.name)

    def test_form_initialization_with_instance(self):
        existing_motorcycle = CustomerMotorcycleFactory(
            service_profile=self.service_profile,
            brand=self.honda_brand.name, # Ensure this brand exists as a ServiceBrand
            model='600RR',
            year=2018,
            odometer=25000
        )
        form = CustomerMotorcycleForm(instance=existing_motorcycle)

        self.assertEqual(form.initial['brand'], existing_motorcycle.brand)
        self.assertEqual(form.initial['model'], existing_motorcycle.model)
        self.assertEqual(form.initial['year'], existing_motorcycle.year)
        self.assertEqual(form.initial['odometer'], existing_motorcycle.odometer)
        self.assertEqual(form.initial.get('other_brand_name', ''), '') # Should be empty for a known brand

    def test_form_initialization_with_instance_other_brand(self):
        """
        Test that the form correctly pre-populates fields when initialized with an existing
        CustomerMotorcycle instance where the brand was originally 'Other' and a custom name was saved.
        """
        # Create an instance with a brand that is NOT in the predefined ServiceBrands
        custom_brand_name = "MyPreviouslyEnteredOtherBrand"
        existing_motorcycle = CustomerMotorcycleFactory(
            service_profile=self.service_profile,
            brand=custom_brand_name, # This brand does not exist as a ServiceBrand object
            model='Bike',
            year=2021,
            odometer=1000
        )
        
        form = CustomerMotorcycleForm(instance=existing_motorcycle)

        # Expected: 'brand' dropdown should show 'Other', 'other_brand_name' should show the custom text
        self.assertEqual(form.initial['brand'], 'Other')
        self.assertEqual(form.initial['other_brand_name'], custom_brand_name)


    def test_form_update_existing_motorcycle(self):
        original_motorcycle = CustomerMotorcycleFactory(
            service_profile=self.service_profile,
            brand=self.honda_brand.name,
            model='600RR',
            year=2018,
            odometer=25000,
            rego='OLD123'
        )

        updated_data = self._get_valid_data(brand_name=self.yamaha_brand.name)
        updated_data['rego'] = 'NEW456'

        form = CustomerMotorcycleForm(data=updated_data, instance=original_motorcycle)
        self.assertTrue(form.is_valid(), f"Form is not valid for update: {form.errors}")

        updated_motorcycle = form.save()
        original_motorcycle.refresh_from_db()

        self.assertEqual(original_motorcycle.rego, 'NEW456')
        self.assertEqual(original_motorcycle.brand, self.yamaha_brand.name)
        self.assertEqual(original_motorcycle.odometer, 15000)
        self.assertEqual(updated_motorcycle, original_motorcycle)

    def test_form_update_existing_motorcycle_to_other_brand(self):
        original_motorcycle = CustomerMotorcycleFactory(
            service_profile=self.service_profile,
            brand=self.honda_brand.name,
            model='600RR',
            year=2018,
            odometer=25000,
            rego='OLD123'
        )

        updated_data = self._get_valid_data(brand_name='Other', include_other_brand_name=True, other_brand_value="UpdatedCustomBrand")
        form = CustomerMotorcycleForm(data=updated_data, instance=original_motorcycle)
        self.assertTrue(form.is_valid(), f"Form is not valid for update to other brand: {form.errors}")

        updated_motorcycle = form.save()
        updated_motorcycle.refresh_from_db()

        self.assertEqual(updated_motorcycle.brand, "UpdatedCustomBrand")

    def test_form_required_fields_missing(self):
        data = {}
        form = CustomerMotorcycleForm(data=data)
        self.assertFalse(form.is_valid())

        expected_required_fields = [
            'brand', 'model', 'year'
        ]

        for field_name in expected_required_fields:
            self.assertIn(field_name, form.errors)
            self.assertTrue(
                'This field is required.' in form.errors[field_name] or
                f"Motorcycle {field_name.replace('_', ' ')} is required." in form.errors[field_name]
            )

        self.assertNotIn('other_brand_name', form.errors)

    def test_form_year_validation_invalid_type(self):
        data = self._get_valid_data()
        data['year'] = 'not-a-year'
        form = CustomerMotorcycleForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('year', form.errors)
        self.assertIn('Enter a whole number.', form.errors['year'])

    def test_form_year_validation_future_year(self):
        current_year = datetime.date.today().year
        data = self._get_valid_data()
        data['year'] = current_year + 1
        form = CustomerMotorcycleForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('year', form.errors)
        self.assertIn('Motorcycle year cannot be in the future.', form.errors['year'])

    def test_form_odometer_validation_invalid_type(self):
        data = self._get_valid_data()
        data['odometer'] = 'not-an-odometer'
        form = CustomerMotorcycleForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('odometer', form.errors)
        self.assertIn('Enter a whole number.', form.errors['odometer'])

    def test_form_odometer_validation_negative(self):
        data = self._get_valid_data()
        data['odometer'] = -100
        form = CustomerMotorcycleForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('odometer', form.errors)
        self.assertIn('Ensure this value is greater than or equal to 0.', form.errors['odometer'])

    def test_form_image_upload(self):
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
        self.assertIn('test_image', motorcycle.image.name)
        self.assertTrue(motorcycle.image.name.endswith('.gif'))
        motorcycle.image.delete(save=False)

    def test_form_image_clear(self):
        image_content = b'GIF89a\x01\x00\x01\x00\x00\xff\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
        original_filename = "existing_image.gif"
        existing_image_file = SimpleUploadedFile(original_filename, image_content, content_type="image/gif")

        existing_motorcycle = CustomerMotorcycleFactory(
            service_profile=self.service_profile,
            image=existing_image_file
        )
        self.assertIsNotNone(existing_motorcycle.image)
        self.assertIn('existing_image', existing_motorcycle.image.name)
        self.assertTrue(existing_motorcycle.image.name.endswith('.gif'))

        data = self._get_valid_data()
        data['image-clear'] = True

        form = CustomerMotorcycleForm(data=data, instance=existing_motorcycle)
        self.assertTrue(form.is_valid(), f"Form is not valid for image clear: {form.errors}")

        updated_motorcycle = form.save()
        updated_motorcycle.refresh_from_db()

        self.assertFalse(updated_motorcycle.image)
