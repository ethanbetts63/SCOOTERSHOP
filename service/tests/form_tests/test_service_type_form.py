from django.test import TestCase
from decimal import Decimal
from datetime import timedelta

# Import the form and model
from service.forms import ServiceTypeForm
from service.models import ServiceType

# Import the factory for ServiceType
# Assuming model_factories.py is in a 'test_helpers' directory relative to 'service'
from ..test_helpers.model_factories import ServiceTypeFactory

class AdminAdminAdminServiceTypeFormTest(TestCase):
    """
    Tests for the ServiceTypeForm.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up non-modified objects used by all test methods.
        Create a sample ServiceType instance using the factory.
        """
        cls.service_type_instance = ServiceTypeFactory(
            name="Existing Service",
            description="A pre-existing service for testing updates.",
            estimated_duration=timedelta(days=2, hours=5),
            base_price=Decimal('150.00'),
            is_active=True
        )

    def test_form_valid_data_all_fields(self):
        """
        Test that the form is valid with complete and correct data,
        including both days and hours for estimated duration.
        """
        data = {
            'name': 'Full Service Check',
            'description': 'Comprehensive check-up and minor adjustments.',
            'estimated_duration_days': 1,
            'estimated_duration_hours': 3,
            'base_price': '120.50', # Input as string, cleaned to Decimal
            'is_active': True,
            # 'image' field is optional and not included here
        }
        form = ServiceTypeForm(data=data)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors.as_data()}")

        cleaned_data = form.cleaned_data
        self.assertEqual(cleaned_data['name'], 'Full Service Check')
        self.assertEqual(cleaned_data['description'], 'Comprehensive check-up and minor adjustments.')
        self.assertEqual(cleaned_data['estimated_duration'], timedelta(days=1, hours=3))
        self.assertEqual(cleaned_data['base_price'], Decimal('120.50'))
        self.assertTrue(cleaned_data['is_active'])
        self.assertIsNone(cleaned_data.get('image')) # Image not provided, should be None

    def test_form_valid_data_duration_only_days(self):
        """
        Test valid data with estimated duration specified only in days.
        """
        data = {
            'name': 'Major Repair',
            'description': 'Extensive engine overhaul.',
            'estimated_duration_days': 5,
            'estimated_duration_hours': 0, # Explicitly zero hours
            'base_price': '500.00',
            'is_active': True,
        }
        form = ServiceTypeForm(data=data)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors.as_data()}")
        self.assertEqual(form.cleaned_data['estimated_duration'], timedelta(days=5))

    def test_form_valid_data_duration_only_hours(self):
        """
        Test valid data with estimated duration specified only in hours.
        """
        data = {
            'name': 'Oil Change',
            'description': 'Quick oil and filter replacement.',
            'estimated_duration_days': 0, # Explicitly zero days
            'estimated_duration_hours': 1,
            'base_price': '45.00',
            'is_active': True,
        }
        form = ServiceTypeForm(data=data)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors.as_data()}")
        self.assertEqual(form.cleaned_data['estimated_duration'], timedelta(hours=1))

    def test_form_valid_data_zero_duration(self):
        """
        Test valid data with zero estimated duration (both days and hours are 0).
        The form's clean method explicitly allows this with 'pass'.
        """
        data = {
            'name': 'Consultation',
            'description': 'Initial discussion with no service performed.',
            'estimated_duration_days': 0,
            'estimated_duration_hours': 0,
            'base_price': '0.00',
            'is_active': True,
        }
        form = ServiceTypeForm(data=data)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors.as_data()}")
        self.assertEqual(form.cleaned_data['estimated_duration'], timedelta(days=0, hours=0))

    def test_form_invalid_missing_name(self):
        """
        Test that the form is invalid if 'name' is missing.
        """
        data = {
            'description': 'Some description.',
            'estimated_duration_days': 1,
            'estimated_duration_hours': 0,
            'base_price': '100.00',
            'is_active': True,
        }
        form = ServiceTypeForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)
        self.assertIn('This field is required.', form.errors['name'])

    def test_form_invalid_negative_duration_days(self):
        """
        Test that the form is invalid if estimated_duration_days is negative.
        """
        data = {
            'name': 'Test Service',
            'description': 'Description',
            'estimated_duration_days': -1,
            'estimated_duration_hours': 0,
            'base_price': '10.00',
            'is_active': True,
        }
        form = ServiceTypeForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('estimated_duration_days', form.errors)
        self.assertIn('Ensure this value is greater than or equal to 0.', form.errors['estimated_duration_days'])

    def test_form_invalid_negative_duration_hours(self):
        """
        Test that the form is invalid if estimated_duration_hours is negative.
        """
        data = {
            'name': 'Test Service',
            'description': 'Description',
            'estimated_duration_days': 0,
            'estimated_duration_hours': -5,
            'base_price': '10.00',
            'is_active': True,
        }
        form = ServiceTypeForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('estimated_duration_hours', form.errors)
        self.assertIn('Ensure this value is greater than or equal to 0.', form.errors['estimated_duration_hours'])

    def test_form_invalid_duration_hours_too_high(self):
        """
        Test that the form is invalid if estimated_duration_hours is greater than 23.
        """
        data = {
            'name': 'Test Service',
            'description': 'Description',
            'estimated_duration_days': 0,
            'estimated_duration_hours': 24, # Max is 23
            'base_price': '10.00',
            'is_active': True,
        }
        form = ServiceTypeForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('estimated_duration_hours', form.errors)
        self.assertIn('Ensure this value is less than or equal to 23.', form.errors['estimated_duration_hours'])

    def test_form_initialization_with_instance(self):
        """
        Test that the form correctly loads data from an existing ServiceType instance,
        and correctly splits the estimated_duration into days and hours.
        """
        instance = self.service_type_instance # Using the instance from setUpTestData
        form = ServiceTypeForm(instance=instance)

        self.assertEqual(form.initial['name'], instance.name)
        self.assertEqual(form.initial['description'], instance.description)
        self.assertEqual(form.initial['estimated_duration_days'], 2) # From timedelta(days=2, hours=5)
        self.assertEqual(form.initial['estimated_duration_hours'], 5) # From timedelta(days=2, hours=5)
        self.assertEqual(form.initial['base_price'], instance.base_price)
        self.assertEqual(form.initial['is_active'], instance.is_active)

    def test_form_save_creates_new_instance(self):
        """
        Test that saving the form creates a new ServiceType instance.
        """
        initial_count = ServiceType.objects.count()
        data = {
            'name': 'New Service',
            'description': 'A brand new service offering.',
            'estimated_duration_days': 0,
            'estimated_duration_hours': 4,
            'base_price': '75.00',
            'is_active': False,
        }
        form = ServiceTypeForm(data=data)
        self.assertTrue(form.is_valid(), f"Form not valid for saving new instance: {form.errors.as_data()}")

        new_instance = form.save()
        self.assertEqual(ServiceType.objects.count(), initial_count + 1)
        self.assertIsInstance(new_instance, ServiceType)
        self.assertEqual(new_instance.name, data['name'])
        self.assertEqual(new_instance.description, data['description'])
        self.assertEqual(new_instance.estimated_duration, timedelta(hours=4))
        self.assertEqual(new_instance.base_price, Decimal('75.00'))
        self.assertFalse(new_instance.is_active)

    def test_form_save_updates_existing_instance(self):
        """
        Test that saving the form updates an existing ServiceType instance.
        """
        instance = self.service_type_instance # Using the instance from setUpTestData
        original_name = instance.name

        updated_data = {
            'name': 'Updated Service Name',
            'description': 'Description has been changed.',
            'estimated_duration_days': 3,
            'estimated_duration_hours': 0,
            'base_price': '200.00',
            'is_active': False,
        }

        form = ServiceTypeForm(data=updated_data, instance=instance)
        self.assertTrue(form.is_valid(), f"Form not valid for updating instance: {form.errors.as_data()}")

        updated_instance = form.save()
        # Ensure it's the same instance
        self.assertEqual(updated_instance.pk, instance.pk)
        self.assertEqual(updated_instance.name, updated_data['name'])
        self.assertEqual(updated_instance.description, updated_data['description'])
        self.assertEqual(updated_instance.estimated_duration, timedelta(days=3))
        self.assertEqual(updated_instance.base_price, Decimal('200.00'))
        self.assertFalse(updated_instance.is_active)

        # Verify the database record is also updated
        refreshed_instance = ServiceType.objects.get(pk=instance.pk)
        self.assertEqual(refreshed_instance.name, updated_data['name'])
        self.assertEqual(refreshed_instance.description, updated_data['description'])
        self.assertEqual(refreshed_instance.estimated_duration, timedelta(days=3))
        self.assertEqual(refreshed_instance.base_price, Decimal('200.00'))
        self.assertFalse(refreshed_instance.is_active)

    def test_form_image_field_optional(self):
        """
        Test that the image field is optional and can be left blank.
        """
        data = {
            'name': 'Service with No Image',
            'description': 'This service has no icon image.',
            'estimated_duration_days': 0,
            'estimated_duration_hours': 30, # This will be invalid, but testing image field
            'base_price': '50.00',
            'is_active': True,
        }
        # Test with no image data provided
        form = ServiceTypeForm(data=data)
        # Note: This form will be invalid due to hours > 23, but we're checking image field handling
        # For a truly valid test, ensure all other data is valid.
        # Let's make it valid for this specific test purpose.
        data_valid = {
            'name': 'Service with No Image',
            'description': 'This service has no icon image.',
            'estimated_duration_days': 0,
            'estimated_duration_hours': 1,
            'base_price': '50.00',
            'is_active': True,
        }
        form_no_image = ServiceTypeForm(data=data_valid)
        self.assertTrue(form_no_image.is_valid(), f"Form is not valid with no image: {form_no_image.errors.as_data()}")
        self.assertIsNone(form_no_image.cleaned_data.get('image'))

        # Test with image field explicitly empty
        data_empty_image = data_valid.copy()
        data_empty_image['image'] = None # Or an empty string if it were a CharField
        form_empty_image = ServiceTypeForm(data=data_empty_image)
        self.assertTrue(form_empty_image.is_valid(), f"Form is not valid with empty image data: {form_empty_image.errors.as_data()}")
        self.assertIsNone(form_empty_image.cleaned_data.get('image'))

