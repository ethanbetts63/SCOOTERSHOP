from django.test import TestCase
from django.core.exceptions import ValidationError
from datetime import date, timedelta

# Import the form and model
from service.forms import BlockedServiceDateForm
from service.models import BlockedServiceDate

# Import the factory for BlockedServiceDate
# Assuming model_factories.py is in a 'test_helpers' directory relative to 'service'
from ..test_helpers.model_factories import BlockedServiceDateFactory

class BlockedServiceDateFormTest(TestCase):
    """
    Tests for the BlockedServiceDateForm.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up non-modified objects used by all test methods.
        We'll use the factory to create a base instance for some tests,
        but many tests will create data directly to test specific scenarios.
        """
        cls.today = date.today()
        cls.tomorrow = cls.today + timedelta(days=1)
        cls.yesterday = cls.today - timedelta(days=1)

        # Create a sample instance using the factory for tests that need an existing object
        cls.blocked_date_instance = BlockedServiceDateFactory()

    def test_form_valid_data_single_day(self):
        """
        Test that the form is valid when blocking a single day (start_date == end_date).
        """
        data = {
            'start_date': self.today,
            'end_date': self.today,
            'description': 'Public holiday',
        }
        form = BlockedServiceDateForm(data=data)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors.as_data()}")
        self.assertEqual(form.cleaned_data['start_date'], self.today)
        self.assertEqual(form.cleaned_data['end_date'], self.today)
        self.assertEqual(form.cleaned_data['description'], 'Public holiday')

    def test_form_valid_data_date_range(self):
        """
        Test that the form is valid when blocking a range of dates (start_date < end_date).
        """
        data = {
            'start_date': self.today,
            'end_date': self.tomorrow,
            'description': 'Maintenance period',
        }
        form = BlockedServiceDateForm(data=data)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors.as_data()}")
        self.assertEqual(form.cleaned_data['start_date'], self.today)
        self.assertEqual(form.cleaned_data['end_date'], self.tomorrow)
        self.assertEqual(form.cleaned_data['description'], 'Maintenance period')

    def test_form_invalid_end_date_before_start_date(self):
        """
        Test that the form is invalid if end_date is before start_date.
        This tests the custom clean method in the form.
        """
        data = {
            'start_date': self.today,
            'end_date': self.yesterday,
            'description': 'Invalid range',
        }
        form = BlockedServiceDateForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('__all__', form.errors) # Form-level error
        self.assertIn("End date cannot be before the start date.", str(form.errors['__all__']))

    def test_form_missing_start_date(self):
        """
        Test that the form is invalid if start_date is missing.
        """
        data = {
            'end_date': self.today,
            'description': 'Missing start date',
        }
        form = BlockedServiceDateForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('start_date', form.errors)
        self.assertIn('This field is required.', form.errors['start_date'])

    def test_form_missing_end_date(self):
        """
        Test that the form is invalid if end_date is missing.
        """
        data = {
            'start_date': self.today,
            'description': 'Missing end date',
        }
        form = BlockedServiceDateForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('end_date', form.errors)
        self.assertIn('This field is required.', form.errors['end_date'])

    def test_form_description_optional(self):
        """
        Test that the description field is optional.
        When submitted as an empty string, it should clean to None.
        """
        data = {
            'start_date': self.today,
            'end_date': self.today,
            'description': '', # Empty description
        }
        form = BlockedServiceDateForm(data=data)
        self.assertTrue(form.is_valid(), f"Form is not valid with empty description: {form.errors.as_data()}")
        # Changed assertion: For CharField with null=True, empty string cleans to None
        self.assertIsNone(form.cleaned_data['description']) 

        data_no_description = {
            'start_date': self.today,
            'end_date': self.today,
        }
        form_no_desc = BlockedServiceDateForm(data=data_no_description)
        self.assertTrue(form_no_desc.is_valid(), f"Form is not valid with no description field: {form_no_desc.errors.as_data()}")
        self.assertIsNone(form_no_desc.cleaned_data['description']) # Should be None if not provided

    def test_form_initialization_with_instance(self):
        """
        Test that the form correctly loads data from an existing BlockedServiceDate instance.
        """
        instance = self.blocked_date_instance # Use the instance created in setUpTestData
        form = BlockedServiceDateForm(instance=instance)

        self.assertEqual(form.initial['start_date'], instance.start_date)
        self.assertEqual(form.initial['end_date'], instance.end_date)
        self.assertEqual(form.initial['description'], instance.description)

    def test_form_save_creates_new_instance(self):
        """
        Test that saving the form creates a new BlockedServiceDate instance.
        """
        initial_count = BlockedServiceDate.objects.count()
        data = {
            'start_date': self.today + timedelta(days=10),
            'end_date': self.today + timedelta(days=12),
            'description': 'New holiday block',
        }
        form = BlockedServiceDateForm(data=data)
        self.assertTrue(form.is_valid(), f"Form not valid for saving new instance: {form.errors.as_data()}")

        new_instance = form.save()
        self.assertEqual(BlockedServiceDate.objects.count(), initial_count + 1)
        self.assertIsInstance(new_instance, BlockedServiceDate)
        self.assertEqual(new_instance.start_date, data['start_date'])
        self.assertEqual(new_instance.end_date, data['end_date'])
        self.assertEqual(new_instance.description, data['description'])

    def test_form_save_updates_existing_instance(self):
        """
        Test that saving the form updates an existing BlockedServiceDate instance.
        """
        instance = self.blocked_date_instance # Use the instance created in setUpTestData
        original_start_date = instance.start_date
        original_end_date = instance.end_date

        updated_data = {
            'start_date': original_start_date + timedelta(days=5),
            'end_date': original_end_date + timedelta(days=5),
            'description': 'Updated block description',
        }

        form = BlockedServiceDateForm(data=updated_data, instance=instance)
        self.assertTrue(form.is_valid(), f"Form not valid for updating instance: {form.errors.as_data()}")

        updated_instance = form.save()
        # Ensure it's the same instance
        self.assertEqual(updated_instance.pk, instance.pk)
        self.assertEqual(updated_instance.start_date, updated_data['start_date'])
        self.assertEqual(updated_instance.end_date, updated_data['end_date'])
        self.assertEqual(updated_instance.description, updated_data['description'])

        # Verify the database record is also updated
        refreshed_instance = BlockedServiceDate.objects.get(pk=instance.pk)
        self.assertEqual(refreshed_instance.start_date, updated_data['start_date'])
        self.assertEqual(refreshed_instance.end_date, updated_data['end_date'])
        self.assertEqual(refreshed_instance.description, updated_data['description'])

